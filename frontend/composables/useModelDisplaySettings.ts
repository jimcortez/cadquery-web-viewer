import { inject, provide, reactive, type InjectionKey } from "vue";

export type ModelDisplayState = {
  enabledFeatures: number[];
  opacity: number;
  wireframe: boolean;
  clipPlaneX: number;
  clipPlaneSwappedX: boolean;
  clipPlaneY: number;
  clipPlaneSwappedY: boolean;
  clipPlaneZ: number;
  clipPlaneSwappedZ: boolean;
  edgeWidth: number;
  explodeStrength: number;
  explodeSwapped: boolean;
  baseColor: string;
  metalness: number;
  roughness: number;
  emissiveColor: string;
  emissiveIntensity: number;
  doubleSided: boolean;
};

function defaultModelDisplayState(edgeWidthDefault = 0): ModelDisplayState {
  return {
    enabledFeatures: [0, 1, 2],
    opacity: 1,
    wireframe: false,
    clipPlaneX: 1,
    clipPlaneSwappedX: false,
    clipPlaneY: 1,
    clipPlaneSwappedY: false,
    clipPlaneZ: 1,
    clipPlaneSwappedZ: false,
    edgeWidth: edgeWidthDefault,
    explodeStrength: 0,
    explodeSwapped: false,
    baseColor: "#ffffff",
    metalness: 0.1,
    roughness: 1,
    emissiveColor: "#000000",
    emissiveIntensity: 0,
    doubleSided: true,
  };
}

export type ModelDisplaySettingsContext = {
  getSettings: (modelName: string) => ModelDisplayState;
  setDefaultEdgeWidth: (w: number) => void;
};

export const modelDisplaySettingsKey: InjectionKey<ModelDisplaySettingsContext> =
  Symbol("cadquery.modelDisplaySettings");

export function createModelDisplaySettingsProvider(): ModelDisplaySettingsContext {
  const byName = new Map<string, ModelDisplayState>();
  let defaultEdgeWidth = 0;

  function getSettings(modelName: string): ModelDisplayState {
    let state = byName.get(modelName);
    if (!state) {
      state = reactive(defaultModelDisplayState(defaultEdgeWidth));
      byName.set(modelName, state);
    }
    return state;
  }

  function setDefaultEdgeWidth(w: number) {
    defaultEdgeWidth = w;
    for (const state of byName.values()) {
      if (state.edgeWidth === 0) state.edgeWidth = w;
    }
  }

  const ctx = { getSettings, setDefaultEdgeWidth };
  provide(modelDisplaySettingsKey, ctx);
  return ctx;
}

export function useModelDisplaySettings(): ModelDisplaySettingsContext {
  const ctx = inject(modelDisplaySettingsKey);
  if (!ctx) throw new Error("useModelDisplaySettings() called without provider");
  return ctx;
}
