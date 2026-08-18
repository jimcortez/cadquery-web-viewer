import { inject, provide, reactive, watch, type InjectionKey } from "vue";
import { settings } from "../misc/settings";
import {
  isSceneHelperObject,
  stampOwnershipFromGeometry,
  type TaggedObject3D,
} from "../misc/modelOwnership";
import { FrontSide } from "three/src/constants.js";
import type { ModelViewerElement } from "@google/model-viewer";
import type { ModelScene } from "@google/model-viewer/lib/three-components/ModelScene";
import {
  ENV_PRESET_DEFAULT,
  environmentImageFromPreset,
  type EnvironmentPresetId,
} from "../misc/environmentImageCache";

export type ToneMappingValue =
  | "auto"
  | "aces"
  | "agx"
  | "commerce"
  | "neutral"
  | "reinhard"
  | "cineon"
  | "linear"
  | "none";

export type ViewerSceneSettingsState = {
  backgroundColor: string;
  exposure: number;
  environmentPreset: EnvironmentPresetId;
  environmentIntensity: number;
  shadowIntensity: number;
  shadowSoftness: number;
  toneMapping: ToneMappingValue;
  autoRotate: boolean;
  autoRotateDelay: number;
  cameraTarget: { x: number; y: number; z: number };
  axisEnabledFeatures: number[];
};

export type ViewerSceneSettingsContext = {
  scene: ViewerSceneSettingsState;
  ready: Promise<void>;
  bindViewer: (getElem: () => ModelViewerElement | null, getModelScene: () => ModelScene | null) => void;
  applyAxisVisibility: (modelScene: ModelScene | null) => void;
};

export const viewerSceneSettingsKey: InjectionKey<ViewerSceneSettingsContext> =
  Symbol("cadquery.viewerSceneSettings");

function sceneModelRoot(modelScene: ModelScene | null): TaggedObject3D | null {
  if (!modelScene) return null;
  return (modelScene as unknown as { _model?: TaggedObject3D })._model ?? null;
}

export function createViewerSceneSettingsProvider(): ViewerSceneSettingsContext {
  const scene = reactive<ViewerSceneSettingsState>({
    backgroundColor: "#d0d0d0",
    exposure: 1,
    environmentPreset: ENV_PRESET_DEFAULT,
    environmentIntensity: 1,
    shadowIntensity: 0,
    shadowSoftness: 1,
    toneMapping: "auto",
    autoRotate: false,
    autoRotateDelay: 3000,
    cameraTarget: { x: 0, y: 0, z: 0 },
    axisEnabledFeatures: [0, 1, 2],
  });

  const ready = (async () => {
    const s = await settings;
    scene.backgroundColor = s.backgroundColor;
    scene.exposure = s.exposure;
    scene.environmentIntensity = s.environmentIntensity;
    scene.shadowIntensity = s.shadowIntensity;
    if (s.environment === "neutral" || s.environment === "legacy") {
      scene.environmentPreset = s.environment;
    } else if (s.environment) {
      scene.environmentPreset = s.environment;
    }
  })();

  function applyAxisVisibility(modelScene: ModelScene | null) {
    if (!modelScene) return;
    const sceneModel = sceneModelRoot(modelScene);
    if (!sceneModel) return;

    stampOwnershipFromGeometry(sceneModel);

    const showFaces = scene.axisEnabledFeatures.includes(0);
    const showEdges = scene.axisEnabledFeatures.includes(1);
    const showVertices = scene.axisEnabledFeatures.includes(2);

    sceneModel.traverse((child) => {
      if (!isSceneHelperObject(child)) return;

      const childIsFace = child.type === "Mesh" || child.type === "SkinnedMesh";
      const childIsEdge =
        child.type === "Line" ||
        child.type === "LineSegments" ||
        child.type === "LineSegments2";
      const childIsVertex = child.type === "Points";
      if (!childIsFace && !childIsEdge && !childIsVertex) return;

      const mat = (child as { material?: { vertexColors?: boolean; side?: number; needsUpdate?: boolean } })
        .material;
      if (mat) {
        if ((child as { geometry?: { attributes?: { color?: unknown } } }).geometry?.attributes?.color) {
          mat.vertexColors = true;
        }
        mat.side = FrontSide;
        mat.needsUpdate = true;
      }
      if (!child.userData) child.userData = {};
      child.userData.cadquerySceneHelper = true;

      const visible = childIsFace ? showFaces : childIsEdge ? showEdges : showVertices;
      if (child.visible !== visible) child.visible = visible;
      const back = child.userData?.backChild as { visible?: boolean } | undefined;
      if (back) back.visible = visible;
    });

    modelScene.queueRender();
  }

  function syncToElement(elem: ModelViewerElement | null, modelScene: ModelScene | null) {
    if (!elem) return;
    elem.exposure = scene.exposure;
    elem.shadowIntensity = scene.shadowIntensity;
    elem.shadowSoftness = scene.shadowSoftness;
    (elem as unknown as { toneMapping: ToneMappingValue }).toneMapping = scene.toneMapping;
    elem.autoRotate = scene.autoRotate;
    elem.autoRotateDelay = scene.autoRotateDelay;
    // model-viewer has no background-color feature: its canvas is transparent and
    // whatever CSS paints behind it shows through. Setting it on the element is
    // what actually makes the colour (and any shadow cast onto it) visible.
    elem.style.backgroundColor = scene.backgroundColor;
    const envUrl = environmentImageFromPreset(scene.environmentPreset);
    elem.environmentImage = envUrl || null;
    if (modelScene) {
      modelScene.environmentIntensity = scene.environmentIntensity;
    }
  }

  function bindViewer(
    getElem: () => ModelViewerElement | null,
    getModelScene: () => ModelScene | null,
  ) {
    void ready.then(() => {
      watch(
        scene,
        () => syncToElement(getElem(), getModelScene()),
        { deep: true, immediate: true },
      );
      watch(
        () => scene.axisEnabledFeatures.slice().sort().join(","),
        () => applyAxisVisibility(getModelScene()),
      );
      // Only when the target itself changes, and never on bind: re-targeting from
      // the deep watcher above moved the camera every time an unrelated setting (a
      // colour, the exposure) changed, which read as the view jumping out. Left
      // alone, model-viewer keeps its own default target — the model's centre.
      watch(
        () => [scene.cameraTarget.x, scene.cameraTarget.y, scene.cameraTarget.z],
        ([x, y, z]) => {
          const modelScene = getModelScene();
          if (!modelScene || x === undefined || y === undefined || z === undefined) return;
          modelScene.setTarget(x, y, z);
          modelScene.queueRender();
        },
      );
    });
  }

  const ctx: ViewerSceneSettingsContext = { scene, ready, bindViewer, applyAxisVisibility };
  provide(viewerSceneSettingsKey, ctx);
  return ctx;
}

export function useViewerSceneSettings(): ViewerSceneSettingsContext {
  const ctx = inject(viewerSceneSettingsKey);
  if (!ctx) throw new Error("useViewerSceneSettings() called without provider");
  return ctx;
}
