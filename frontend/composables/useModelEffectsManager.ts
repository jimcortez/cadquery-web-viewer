import { effectScope, onScopeDispose, watch, type EffectScope, type Ref } from "vue";
import type ModelViewerWrapper from "../viewer/ModelViewerWrapper.vue";
import { useModelSceneEffects } from "./useModelSceneEffects";
import type { ModelDisplaySettingsContext } from "./useModelDisplaySettings";
import type { SceneObjectsContext } from "./useSceneObjects";

export type ModelEffectsManagerOptions = {
  /** Called before a part's vertex colours are rewritten, so face highlights on that object can be dropped. */
  onPartRecolor?: (modelName: string) => void;
};

/**
 * Keeps one live effect scope per scene object.
 *
 * Every object's three.js effects have to keep running whether or not its
 * settings are on screen. Tying them to a component — as the old per-model
 * accordion row did — makes that a property of where the component happens to be
 * rendered, which the master/detail inspector would silently break. Scopes keyed
 * by object name are independent of the view tree.
 */
export function useModelEffectsManager(
  sceneObjects: SceneObjectsContext,
  displaySettings: ModelDisplaySettingsContext,
  viewer: Ref<InstanceType<typeof ModelViewerWrapper> | null>,
  options: ModelEffectsManagerOptions = {},
) {
  const scopes = new Map<string, EffectScope>();

  function disposeAll() {
    for (const scope of scopes.values()) scope.stop();
    scopes.clear();
  }

  watch(
    () => sceneObjects.objects.value.map((o) => o.name),
    (names) => {
      for (const name of names) {
        if (scopes.has(name)) continue;
        const scope = effectScope(true);
        scope.run(() =>
          useModelSceneEffects({
            modelName: name,
            // Read through the registry so counts follow document rebuilds.
            getCounts: () => {
              const obj = sceneObjects.getObject(name);
              return {
                faceCount: obj?.faceCount ?? 0,
                edgeCount: obj?.edgeCount ?? 0,
                vertexCount: obj?.vertexCount ?? 0,
              };
            },
            // Same reason: parts are re-derived from the document on every update.
            getParts: () =>
              (sceneObjects.getObject(name)?.parts ?? []).map((p) => ({
                name: p.name,
                display: displaySettings.getPartSettings(name, p.name),
              })),
            onPartRecolor: options.onPartRecolor,
            viewer,
            display: displaySettings.getSettings(name),
          }),
        );
        scopes.set(name, scope);
      }
      for (const [name, scope] of [...scopes]) {
        if (names.includes(name)) continue;
        scope.stop();
        scopes.delete(name);
      }
    },
    { immediate: true },
  );

  onScopeDispose(disposeAll);

  return { disposeAll };
}
