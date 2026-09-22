import type { Ref, ShallowRef } from "vue";
import { ref, triggerRef, watch } from "vue";
import { Document } from "@gltf-transform/core";
import { settings } from "../misc/settings";
import { NetworkManager, NetworkUpdateEvent, NetworkUpdateEventModel } from "../misc/network";
import { SceneMgr } from "../misc/scene";
import { isViewerReady } from "../viewer/viewerUtils";
import type ModelViewerWrapperT from "../viewer/ModelViewerWrapper.vue";
import { useObjectPicker } from "./useObjectPicker";

/** Just the slice of the selection tools this needs, to keep the dependency narrow. */
export type SelectionApi = {
  removeObjectSelections: (name: string) => void;
};

export function useAppModelLoading(
  viewer: Ref<InstanceType<typeof ModelViewerWrapperT> | null>,
  sceneDocument: ShallowRef<Document>,
  selection: SelectionApi,
  sceneUrl: Ref<string>,
) {
  const preloadingModels = ref<string[]>([]);
  const networkMgr = new NetworkManager();

  async function onModelUpdateRequest(event: NetworkUpdateEvent) {
    if (viewer.value && event.models.length > 0) {
      viewer.value.onProgress(0.1);
    }
    const shutdownRequestIndex = event.models.findIndex((model) => model.isRemove == null);
    let shutdownRequest: NetworkUpdateEventModel | null = null;
    if (shutdownRequestIndex !== -1) {
      shutdownRequest = event.models.splice(shutdownRequestIndex, 1)[0] ?? null;
    }
    let doc = sceneDocument.value;
    for (const modelIndex in event.models) {
      const isLast = parseInt(modelIndex, 10) === event.models.length - 1;
      const model = event.models[modelIndex];
      if (!model) continue;
      selection.removeObjectSelections(model.name);
      try {
        const loadHelpers = (await settings).loadHelpers;
        if (!model.isRemove) {
          doc = await SceneMgr.loadModel(sceneUrl, doc, model.name, model.url, isLast && loadHelpers, isLast);
        } else {
          doc = await SceneMgr.removeModel(sceneUrl, doc, model.name, isLast && loadHelpers, isLast);
        }
      } catch (e) {
        console.error("Error loading model", model, e);
      }
    }
    if (shutdownRequest !== null) {
      event.disconnect();
    }
    sceneDocument.value = doc;
    triggerRef(sceneDocument);
  }

  async function onModelRemoveRequest(name: string) {
    await onModelUpdateRequest(
      new NetworkUpdateEvent([new NetworkUpdateEventModel(name, "", null, true)], () => {}),
    );
  }

  function onUpdateEarly(e: Event) {
    const ce = e as CustomEvent<NetworkUpdateEventModel[]>;
    viewer.value?.onProgress(ce.detail.length * 0.01);
  }

  networkMgr.addEventListener("update-early", onUpdateEarly);
  networkMgr.addEventListener("update", (e) => {
    void onModelUpdateRequest(e as NetworkUpdateEvent);
  });

  void (async () => {
    const sett = await settings;
    if (sett.preload.length > 0) {
      watch(viewer, (newViewer) => {
        if (isViewerReady(newViewer)) {
          newViewer.setPosterText(
            '<tspan x="50%" dy="1.2em">Trying to load' +
              " models from:</tspan>" +
              sett.preload.map((url: string) => '<tspan x="50%" dy="1.2em">- ' + url + "</tspan>").join(""),
          );
        }
      });
      for (const model of sett.preload) {
        preloadingModels.value.push(model);
        const removeFromPreloadingModels = () => {
          preloadingModels.value = preloadingModels.value.filter((m) => m !== model);
        };
        networkMgr.load(model).then(removeFromPreloadingModels).catch((e) => {
          removeFromPreloadingModels();
          console.error("Error preloading model", model, e);
        });
      }
    }
  })();

  const pickerOpen = ref(false);
  const objectPicker = useObjectPicker(networkMgr, sceneDocument, pickerOpen);

  function openObjectPicker() {
    void objectPicker.openDialog();
  }

  return {
    networkMgr,
    preloadingModels,
    onModelUpdateRequest,
    onModelRemoveRequest,
    openObjectPicker,
    pickerOpen,
    ...objectPicker,
  };
}
