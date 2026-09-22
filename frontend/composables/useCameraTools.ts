import { inject, onScopeDispose, provide, ref, type InjectionKey, type Ref } from "vue";
import type { PerspectiveCamera } from "three/src/cameras/PerspectiveCamera.js";
import { OrthographicCamera } from "three/src/cameras/OrthographicCamera.js";
import { Box3 } from "three/src/math/Box3.js";
import { Matrix4 } from "three/src/math/Matrix4.js";
import { Vector3 } from "three/src/math/Vector3.js";
import { isSceneHelperObject, type TaggedObject3D } from "../misc/modelOwnership";
import type ModelViewerWrapper from "../viewer/ModelViewerWrapper.vue";
import type { ViewerSceneSettingsContext } from "./useViewerSceneSettings";

export type Projection = "perspective" | "orthographic";

export type CameraToolsContext = {
  projection: Ref<Projection>;
  toggleProjection: () => Promise<void>;
  centerCamera: () => void;
  downloadSceneGlb: () => Promise<void>;
  /**
   * The camera that actually tracks user input. Under an orthographic view the
   * scene camera is replaced every frame, so anything that holds a reference —
   * the orientation gizmo — must follow this instead.
   */
  trackingCamera: () => PerspectiveCamera | null;
};

export const cameraToolsKey: InjectionKey<CameraToolsContext> = Symbol("cadquery.cameraTools");

type SceneWithCameras = {
  camera: PerspectiveCamera & { isPerspectiveCamera?: boolean };
  __perspectiveCamera?: PerspectiveCamera;
  aspect: number;
  getTarget: () => { clone: () => { add: (v: unknown) => unknown } };
  setTarget: (x: number, y: number, z: number) => void;
  /** Model-space bounds of everything loaded, which model-viewer keeps current. */
  boundingBox: Box3;
  target: { position: unknown; matrixWorld: Matrix4 };
  _model?: object;
  jumpToGoal: () => void;
  queueRender: () => void;
};

export function createCameraToolsProvider(
  viewer: Ref<InstanceType<typeof ModelViewerWrapper> | null>,
  viewerScene: ViewerSceneSettingsContext,
): CameraToolsContext {
  const projection = ref<Projection>("perspective");

  let orthoFrame: number | null = null;

  function sceneOf(): SceneWithCameras | null {
    return (viewer.value?.scene ?? null) as unknown as SceneWithCameras | null;
  }

  /**
   * model-viewer has no orthographic mode, so we swap `scene.camera` for one we
   * build from the perspective camera's framing and keep re-deriving each frame.
   * The original perspective camera stays live and keeps receiving control input.
   */
  function syncOrthoCamera(force: boolean) {
    const scene = sceneOf();
    if (!scene) return;
    const perspectiveCam = scene.__perspectiveCamera;
    if (!perspectiveCam) return;
    if (force || scene.camera !== perspectiveCam) {
      const lookAtCenter = scene.getTarget().clone().add(scene.target.position) as {
        // three's Vector3, narrowed to what distanceTo needs.
        distanceTo?: unknown;
      };
      const perspectiveWidthAtCenter =
        2 *
        Math.tan(((perspectiveCam.fov * Math.PI) / 180) / 2) *
        perspectiveCam.position.distanceTo(lookAtCenter as never);
      const w = perspectiveWidthAtCenter;
      const h = perspectiveWidthAtCenter / scene.aspect;
      const ortho = new OrthographicCamera(-w, w, h, -h, perspectiveCam.near, perspectiveCam.far);
      ortho.position.copy(perspectiveCam.position);
      ortho.rotation.copy(perspectiveCam.rotation);
      scene.camera = ortho as unknown as SceneWithCameras["camera"];
      if (force) scene.queueRender();
      orthoFrame = requestAnimationFrame(() => syncOrthoCamera(false));
    } else {
      orthoFrame = null;
    }
  }

  function stopOrthoLoop() {
    if (orthoFrame !== null) cancelAnimationFrame(orthoFrame);
    orthoFrame = null;
  }

  async function toggleProjection() {
    const scene = sceneOf();
    if (!scene) return;
    const prevCam = scene.camera;
    const wasPerspective = !!prevCam.isPerspectiveCamera;
    if (wasPerspective) {
      scene.__perspectiveCamera = prevCam;
      stopOrthoLoop();
      syncOrthoCamera(true);
    } else {
      stopOrthoLoop();
      if (scene.__perspectiveCamera) scene.camera = scene.__perspectiveCamera;
      scene.queueRender();
    }
    projection.value = wasPerspective ? "orthographic" : "perspective";
    // The swap needs a frame to take effect before dependents recompute.
    await new Promise((resolve) => requestAnimationFrame(resolve));
    viewer.value?.elem?.dispatchEvent(new CustomEvent("camera-change", { detail: { source: "none" } }));
  }

  /**
   * Bounds of the real geometry, in the model coordinates `setTarget` expects.
   *
   * Deliberately not `scene.boundingBox`: that includes the helpers, and the axes
   * helper is drawn at the world origin however far away the part sits. Framing it
   * centres the camera on the empty space between the origin and the model.
   */
  function modelBounds(scene: SceneWithCameras): Box3 {
    const box = new Box3();
    const root = scene._model as
      | (TaggedObject3D & { traverse: (cb: (o: TaggedObject3D) => void) => void })
      | undefined;
    if (!root) return box;
    const toModelSpace = new Matrix4().copy(scene.target.matrixWorld).invert();
    root.traverse((child) => {
      const obj = child as TaggedObject3D & { geometry?: unknown; userData?: Record<string, unknown> };
      if (!obj.geometry || isSceneHelperObject(obj)) return;
      // The back-face clones sit exactly on their originals, so they add nothing
      // but cost.
      if (obj.userData?.noHit) return;
      box.union(new Box3().setFromObject(child as never).applyMatrix4(toModelSpace));
    });
    return box;
  }

  function centerCamera() {
    const scene = sceneOf();
    const center = new Vector3();
    if (scene) {
      const bounds = modelBounds(scene);
      if (!bounds.isEmpty()) bounds.getCenter(center);
      else if (!scene.boundingBox.isEmpty()) scene.boundingBox.getCenter(center);
    }
    // Mirrored into the settings object so the Target readout matches the camera,
    // and applied directly because an unchanged value would not re-fire the watch
    // even though panning has since moved the live target.
    viewerScene.scene.cameraTarget = { x: center.x, y: center.y, z: center.z };
    if (scene) {
      scene.setTarget(center.x, center.y, center.z);
      scene.jumpToGoal();
      scene.queueRender();
    }
    viewer.value?.elem?.zoom(-1000000);
  }

  async function downloadSceneGlb() {
    const viewerEl = viewer.value?.elem;
    if (!viewerEl) return;
    const glTF = await viewerEl.exportScene({ onlyVisible: true, binary: true });
    const file = new File([glTF], "export.glb");
    const link = document.createElement("a");
    link.download = file.name;
    link.href = URL.createObjectURL(file);
    link.click();
    URL.revokeObjectURL(link.href);
  }

  function trackingCamera(): PerspectiveCamera | null {
    const scene = sceneOf();
    if (!scene) return null;
    return scene.__perspectiveCamera ?? scene.camera ?? null;
  }

  onScopeDispose(stopOrthoLoop);

  const ctx: CameraToolsContext = {
    projection,
    toggleProjection,
    centerCamera,
    downloadSceneGlb,
    trackingCamera,
  };
  provide(cameraToolsKey, ctx);
  return ctx;
}

export function useCameraTools(): CameraToolsContext {
  const ctx = inject(cameraToolsKey);
  if (!ctx) throw new Error("useCameraTools() called without provider");
  return ctx;
}
