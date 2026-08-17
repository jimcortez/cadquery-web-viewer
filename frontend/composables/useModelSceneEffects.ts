import { nextTick, onScopeDispose, watch, type Ref } from "vue";
import type { ModelViewerElement } from "@google/model-viewer";
import { BackSide, DoubleSide, FrontSide } from "three/src/constants.js";
import { MeshStandardMaterial } from "three/src/materials/MeshStandardMaterial.js";
import { Box3 } from "three/src/math/Box3.js";
import { Color } from "three/src/math/Color.js";
import { Matrix4 } from "three/src/math/Matrix4.js";
import { Plane } from "three/src/math/Plane.js";
import { Vector3 } from "three/src/math/Vector3.js";
import { extrasNameKey } from "../misc/gltf";
import { objectBelongsToModel } from "../misc/modelOwnership";
import { toLineSegments } from "../misc/lines.js";
import { currentSceneRotation } from "../viewer/lighting";
import { isViewerReady } from "../viewer/viewerUtils";
import type ModelViewerWrapper from "../viewer/ModelViewerWrapper.vue";
import type { ModelDisplayState } from "./useModelDisplaySettings";
import type { MObject3D } from "../tools/types";

export type ModelFeatureCounts = {
  faceCount: number;
  edgeCount: number;
  vertexCount: number;
};

export type ModelSceneEffectsOptions = {
  modelName: string;
  /**
   * Must be a getter, never a captured value: the scene document is rebuilt on
   * every update, so anything read from it goes stale after the first reload.
   */
  getCounts: () => ModelFeatureCounts;
  viewer: Ref<InstanceType<typeof ModelViewerWrapper> | null>;
  display: ModelDisplayState;
};

type SceneLike = {
  queueRender: () => void;
};

/**
 * The three.js root that model-viewer keeps on its private `_model`.
 *
 * Declared structurally so `traverse` hands back MObject3D. Typing it as a real
 * Object3D would widen every callback argument and force a cast at each use.
 */
type SceneRoot = {
  traverse: (cb: (obj: MObject3D) => void) => void;
  add: (obj: MObject3D) => void;
};

/**
 * Owns every three.js side effect for a single scene object.
 *
 * This used to live in Model.vue, which meant the effects only ran while that
 * object's accordion row was mounted. The inspector now renders one object at a
 * time, so this runs in its own effect scope instead — see useModelEffectsManager.
 */
export function useModelSceneEffects(options: ModelSceneEffectsOptions) {
  const { modelName, getCounts, viewer, display } = options;

  function sceneParts(): { scene: SceneLike; sceneModel: SceneRoot } | null {
    const scene = viewer.value?.scene as SceneLike | undefined;
    const sceneModel = (scene as unknown as { _model?: SceneRoot } | undefined)?._model;
    if (!scene || !sceneModel) return null;
    return { scene, sceneModel };
  }

  function isMine(child: MObject3D): boolean {
    return objectBelongsToModel(child, modelName);
  }

  function kindOf(child: MObject3D): "face" | "edge" | "vertex" | null {
    if (child.type === "Mesh" || child.type === "SkinnedMesh") return "face";
    if (child.type === "Line" || child.type === "LineSegments" || child.type === "LineSegments2")
      return "edge";
    if (child.type === "Points") return "vertex";
    return null;
  }

  function prepareMeshMaterial(child: MObject3D) {
    if (!child.material) return;
    if (child.geometry?.attributes?.color) {
      child.material.vertexColors = true;
      child.material.needsUpdate = true;
    }
  }

  // --- visibility -----------------------------------------------------------

  function applyVisibility() {
    const parts = sceneParts();
    if (!parts) return;
    const featureIndex = { face: 0, edge: 1, vertex: 2 } as const;
    parts.sceneModel.traverse((child) => {
      if (!isMine(child)) return;
      const kind = kindOf(child);
      if (!kind) return;
      const visible = display.visible && display.enabledFeatures.includes(featureIndex[kind]);
      if (child.visible !== visible) {
        child.visible = visible;
        const back = child.userData.backChild as MObject3D | undefined;
        if (back) back.visible = visible;
      }
    });
    parts.scene.queueRender();
  }

  watch(() => display.enabledFeatures, applyVisibility, { deep: true });
  watch(() => display.visible, applyVisibility);

  // --- opacity / wireframe --------------------------------------------------

  function applyOpacity(newOpacity: number) {
    const parts = sceneParts();
    if (!parts) return;
    parts.sceneModel.traverse((child) => {
      if (!isMine(child)) return;
      if (child.material && child.material.opacity !== newOpacity) {
        child.material.transparent = newOpacity < 1;
        child.material.opacity = newOpacity;
        child.material.needsUpdate = true;
      }
    });
    parts.scene.queueRender();
  }

  watch(() => display.opacity, applyOpacity);

  function applyWireframe(newWireframe: boolean) {
    const parts = sceneParts();
    if (!parts) return;
    parts.sceneModel.traverse((child) => {
      if (!isMine(child)) return;
      if (child.material && child.material.wireframe !== newWireframe && kindOf(child) === "face") {
        child.material.wireframe = newWireframe;
        child.material.needsUpdate = true;
      }
    });
    parts.scene.queueRender();
  }

  watch(() => display.wireframe, applyWireframe);

  // --- clipping planes ------------------------------------------------------

  function applyClipPlanes() {
    const parts = sceneParts();
    if (!parts) return;
    const { scene, sceneModel } = parts;
    const enabledX =
      (display.clipPlaneX < 1 && !display.clipPlaneSwappedX) ||
      (display.clipPlaneX > 0 && display.clipPlaneSwappedX);
    const enabledY =
      (display.clipPlaneY < 1 && !display.clipPlaneSwappedY) ||
      (display.clipPlaneY > 0 && display.clipPlaneSwappedY);
    const enabledZ =
      (display.clipPlaneZ < 1 && !display.clipPlaneSwappedZ) ||
      (display.clipPlaneZ > 0 && display.clipPlaneSwappedZ);
    let bbox: Box3 | undefined;
    if (viewer.value?.renderer && (enabledX || enabledY || enabledZ)) {
      viewer.value.renderer.threeRenderer.localClippingEnabled = true;
      bbox = new Box3();
      sceneModel.traverse((child) => {
        if (isMine(child)) bbox!.expandByObject(child);
      });
    }
    sceneModel.traverse((child) => {
      if (!isMine(child) || !child.material) return;
      if (bbox?.isEmpty() === false) {
        const offsetX = bbox.min.x + display.clipPlaneX * (bbox.max.x - bbox.min.x);
        const offsetY = bbox.min.y + display.clipPlaneY * (bbox.max.y - bbox.min.y);
        const offsetZ = bbox.min.z + (1 - display.clipPlaneZ) * (bbox.max.z - bbox.min.z);
        const rotSceneMatrix = new Matrix4().makeRotationY(currentSceneRotation);
        const planes = [
          new Plane(new Vector3(-1, 0, 0), offsetX).applyMatrix4(rotSceneMatrix),
          new Plane(new Vector3(0, -1, 0), offsetY).applyMatrix4(rotSceneMatrix),
          new Plane(new Vector3(0, 0, 1), -offsetZ).applyMatrix4(rotSceneMatrix),
        ];
        if (display.clipPlaneSwappedX) planes[0]?.negate();
        if (display.clipPlaneSwappedY) planes[1]?.negate();
        if (display.clipPlaneSwappedZ) planes[2]?.negate();
        if (!enabledZ) planes.pop();
        if (!enabledY) planes.splice(1, 1);
        if (!enabledX) planes.shift();
        child.material.clippingPlanes = planes;
        const back = child.userData.backChild as MObject3D | undefined;
        if (back?.material) back.material.clippingPlanes = planes;
      } else {
        child.material.clippingPlanes = [];
        const back = child.userData.backChild as MObject3D | undefined;
        if (back?.material) back.material.clippingPlanes = [];
      }
    });
    scene.queueRender();
  }

  watch(
    () => [
      display.clipPlaneX,
      display.clipPlaneY,
      display.clipPlaneZ,
      display.clipPlaneSwappedX,
      display.clipPlaneSwappedY,
      display.clipPlaneSwappedZ,
    ],
    applyClipPlanes,
  );

  // --- edge / vertex width --------------------------------------------------

  type FatLine = Awaited<ReturnType<typeof toLineSegments>>;

  let edgeWidthGeneration = 0;
  let edgeWidthCleanup: Array<() => void> = [];
  let fatLines: FatLine[] = [];

  function applyLineResolution(line2: FatLine) {
    const elem = viewer.value?.elem;
    if (!elem) return;
    line2.material.resolution.set(elem.clientWidth, elem.clientHeight);
    line2.material.needsUpdate = true;
  }

  // Fat lines need pixel dimensions, so they must be refreshed on resize. The
  // original code registered a `resize` listener on the model-viewer element,
  // which never fires, and removed a different closure than it added.
  function onWindowResize() {
    for (const line2 of fatLines) applyLineResolution(line2);
    viewer.value?.scene?.queueRender();
  }
  window.addEventListener("resize", onWindowResize);

  async function applyEdgeWidth(newEdgeWidth: number) {
    const parts = sceneParts();
    if (!parts) return;
    const { scene, sceneModel } = parts;

    // Guards against two overlapping runs: `toLineSegments` is async, so a second
    // call (a slider drag, or the reapply in onModelLoad) could otherwise attach a
    // second fat line per edge and register its cleanup into the wrong array.
    const generation = ++edgeWidthGeneration;
    edgeWidthCleanup.forEach((f) => f());
    edgeWidthCleanup = [];
    fatLines = [];

    const linesToImprove: MObject3D[] = [];
    sceneModel.traverse((child) => {
      if (!isMine(child)) return;
      if (child.type === "Line" || child.type === "LineSegments") {
        if (newEdgeWidth > 0) linesToImprove.push(child);
      }
      if (child.type === "Points") {
        (child.material as unknown as { size: number }).size =
          newEdgeWidth > 0 ? newEdgeWidth * 50 : 5;
        child.material.needsUpdate = true;
      }
    });

    await Promise.all(
      linesToImprove.map(async (line) => {
        const line2 = await toLineSegments(line.geometry, newEdgeWidth);
        // A newer run superseded us while we were awaiting; drop this line.
        if (generation !== edgeWidthGeneration) return;
        applyLineResolution(line2);
        line2.position.copy(line.position);
        line2.computeLineDistances();
        line2.userData = Object.assign({}, line.userData);
        line.parent!.add(line2);
        line.children.forEach((o) => line2.add(o));
        line.visible = false;
        line.userData.niceLine = line2;
        line2.userData.noHit = true;
        line2.visible = display.visible && display.enabledFeatures.includes(1);
        fatLines.push(line2);
        edgeWidthCleanup.push(() => {
          line2.parent?.remove(line2);
          delete line.userData.niceLine;
          line.visible = display.visible && display.enabledFeatures.includes(1);
        });
      }),
    );

    if (generation === edgeWidthGeneration) scene.queueRender();
  }

  watch(() => display.edgeWidth, (w) => void applyEdgeWidth(w));

  // --- explode --------------------------------------------------------------

  function applyExplode(newExplodeStrength: number) {
    const parts = sceneParts();
    if (!parts) return;
    const { scene, sceneModel } = parts;

    const isMovable = (child: MObject3D) =>
      child.type === "Mesh" ||
      child.type === "SkinnedMesh" ||
      child.type === "Line" ||
      child.type === "LineSegments" ||
      child.type === "Points";

    const meBbox = new Box3();
    const othersBbox = new Box3();
    sceneModel.traverse((child) => {
      if ((child as unknown) === (sceneModel as unknown)) return;
      if (!isMovable(child) || child.userData.noHit) return;
      if (isMine(child)) meBbox.expandByObject(child);
      else if (child.userData[extrasNameKey]) othersBbox.expandByObject(child);
    });
    const modelSize = new Vector3();
    meBbox.getSize(modelSize);
    const maxDimension = Math.max(modelSize.x, modelSize.y, modelSize.z);
    const pushDirection = new Vector3()
      .subVectors(meBbox.getCenter(new Vector3()), othersBbox.getCenter(new Vector3()))
      .normalize();

    let strength = Math.abs(newExplodeStrength);
    if (display.explodeSwapped) strength = -strength;

    sceneModel.traverse((child) => {
      if (!isMine(child) || !isMovable(child)) return;
      const direction = pushDirection.clone();
      if (direction.lengthSq() < 0.0001) direction.set(0, 1, 0);
      const newPosition = new Vector3().add(direction.multiplyScalar(strength * maxDimension));
      child.position.copy(newPosition);
      const niceLine = child.userData.niceLine as MObject3D | undefined;
      if (niceLine) niceLine.position.copy(newPosition);
    });
    scene.queueRender();
    applyClipPlanes();
  }

  watch(() => display.explodeStrength, (v) => applyExplode(v));
  watch(() => display.explodeSwapped, () => applyExplode(display.explodeStrength));

  // --- material -------------------------------------------------------------

  function meshHasVertexColors(child: MObject3D): boolean {
    return !!child.geometry?.attributes?.color;
  }

  function applyMaterial() {
    const parts = sceneParts();
    if (!parts) return;
    const base = new Color(display.baseColor);
    const emissive = new Color(display.emissiveColor);
    parts.sceneModel.traverse((child) => {
      if (!isMine(child) || !child.material || kindOf(child) !== "face") return;
      if (!child.userData.materialCloned) {
        child.material = child.material.clone();
        child.userData.materialCloned = true;
      }
      const mat = child.material as MeshStandardMaterial;
      if (meshHasVertexColors(child)) mat.vertexColors = true;
      else mat.color.copy(base);
      mat.metalness = display.metalness;
      mat.roughness = display.roughness;
      mat.emissive.copy(emissive);
      mat.emissiveIntensity = display.emissiveIntensity;
      mat.side = display.doubleSided ? DoubleSide : FrontSide;
      mat.needsUpdate = true;
      const back = child.userData.backChild as MObject3D | undefined;
      if (back?.material) back.material.side = BackSide;
    });
    parts.scene.queueRender();
  }

  watch(
    () => [
      display.baseColor,
      display.metalness,
      display.roughness,
      display.emissiveColor,
      display.emissiveIntensity,
      display.doubleSided,
    ],
    applyMaterial,
  );

  // --- load -----------------------------------------------------------------

  let setupSceneKey: string | null = null;
  let hasDerivedFeatures = false;

  /**
   * Turn off feature toggles for geometry this object doesn't have, once.
   *
   * Deliberately scoped to this effect scope rather than to ModelDisplayState:
   * the settings map outlives a removal, so re-adding an object under the same
   * name re-derives its toggles while keeping opacity, material and so on.
   */
  function deriveEnabledFeatures() {
    if (hasDerivedFeatures) return;
    hasDerivedFeatures = true;
    const { faceCount, edgeCount, vertexCount } = getCounts();
    const sync = (index: number, present: boolean) => {
      const has = display.enabledFeatures.includes(index);
      if (!present && has) {
        display.enabledFeatures = display.enabledFeatures.filter((f) => f !== index);
      } else if (present && !has) {
        display.enabledFeatures.push(index);
      }
    };
    sync(0, faceCount > 0);
    sync(1, edgeCount > 0);
    sync(2, vertexCount > 0);
  }

  function onModelLoad() {
    const parts = sceneParts();
    if (!parts) return;
    const { scene, sceneModel } = parts;

    // The scene is re-serialised to a fresh blob URL on every change, so this
    // guard stops us redoing setup for a scene we already prepared.
    const sceneSrc = viewer.value?.elem?.src?.toString() ?? "";
    const setupKey = `${sceneSrc}:${modelName}`;
    if (setupSceneKey === setupKey) return;
    setupSceneKey = setupKey;

    // Ownership tags are stamped once per load by useViewerSceneSettings'
    // applyAxisVisibility; doing it per model made it O(models x objects).

    deriveEnabledFeatures();

    const childrenToAdd: MObject3D[] = [];
    sceneModel.traverse((child) => {
      child.updateMatrixWorld();
      if (!isMine(child) || kindOf(child) !== "face") return;
      (child.geometry as unknown as { computeBoundsTree?: (o: object) => void }).computeBoundsTree?.(
        { indirect: true },
      );
      prepareMeshMaterial(child);
      if (!child.userData.backChild) {
        const backChild = child.clone() as MObject3D;
        backChild.material = child.material.clone();
        backChild.material.side = BackSide;
        backChild.material.color = new Color(0.25, 0.25, 0.25);
        backChild.userData.noHit = true;
        child.userData.backChild = backChild;
        childrenToAdd.push(backChild);
      }
    });
    childrenToAdd.forEach((child) => sceneModel.add(child));

    applyVisibility();
    applyOpacity(display.opacity);
    applyWireframe(display.wireframe);
    applyClipPlanes();
    void applyEdgeWidth(display.edgeWidth);
    applyMaterial();
    if (display.explodeStrength > 0) void nextTick(() => applyExplode(display.explodeStrength));

    scene.queueRender();
  }

  // --- wiring ---------------------------------------------------------------

  let boundElem: ModelViewerElement | null = null;
  let stopElemWait: (() => void) | null = null;

  function unbindElem() {
    stopElemWait?.();
    stopElemWait = null;
    if (!boundElem) return;
    boundElem.removeEventListener("load", onModelLoad);
    boundElem.removeEventListener("camera-change", applyClipPlanes);
    boundElem = null;
  }

  function bindViewer(current: InstanceType<typeof ModelViewerWrapper> | null) {
    if (!isViewerReady(current)) return;
    unbindElem();
    stopElemWait = current.onElemReady((elem: ModelViewerElement) => {
      boundElem = elem;
      elem.addEventListener("load", onModelLoad);
      elem.addEventListener("camera-change", applyClipPlanes);
      if (elem.loaded) void nextTick(onModelLoad);
    });
  }

  watch(viewer, bindViewer, { immediate: true });

  onScopeDispose(() => {
    unbindElem();
    window.removeEventListener("resize", onWindowResize);
    edgeWidthGeneration++;
    edgeWidthCleanup.forEach((f) => f());
    edgeWidthCleanup = [];
    fatLines = [];
  });

  return { onModelLoad };
}
