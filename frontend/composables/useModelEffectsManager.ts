import { effectScope, onScopeDispose, watch, type EffectScope, type Ref } from "vue";
import type ModelViewerWrapper from "../viewer/ModelViewerWrapper.vue";
import { useModelSceneEffects } from "./useModelSceneEffects";
import type { ModelDisplaySettingsContext } from "./useModelDisplaySettings";
import type { SceneObjectsContext } from "./useSceneObjects";

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
