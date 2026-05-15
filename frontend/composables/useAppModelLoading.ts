import type { Ref, ShallowRef } from "vue";
import { ref, triggerRef, watch } from "vue";
import { Document } from "@gltf-transform/core";
import { settings } from "../misc/settings";
import { NetworkManager, NetworkUpdateEvent, NetworkUpdateEventModel } from "../misc/network";
import { SceneMgr } from "../misc/scene";
import { isViewerReady } from "../viewer/viewerUtils";
import type ModelViewerWrapperT from "../viewer/ModelViewerWrapper.vue";

export type ToolsApi = {
  removeObjectSelections: (name: string) => void;
};

export function useAppModelLoading(
  viewer: Ref<InstanceType<typeof ModelViewerWrapperT> | null>,
  sceneDocument: ShallowRef<Document>,
  tools: Ref<ToolsApi | null>,
  sceneUrl: Ref<string>,
) {
  const preloadingModels = ref<string[]>([]);
  const networkMgr = new NetworkManager();

  async function onModelUpdateRequest(event: NetworkUpdateEvent) {
    if (viewer.value && event.models.length > 0) {
      viewer.value.onProgress(0.1);
    }
    console.log("Received model update request", event.models);
    const shutdownRequestIndex = event.models.findIndex((model) => model.isRemove == null);
    let shutdownRequest: NetworkUpdateEventModel | null = null;
    if (shutdownRequestIndex !== -1) {
      console.log("Will shut down the connection after this load, as requested by the server");
      shutdownRequest = event.models.splice(shutdownRequestIndex, 1)[0] ?? null;
    }
    let doc = sceneDocument.value;
    for (const modelIndex in event.models) {
      const isLast = parseInt(modelIndex, 10) === event.models.length - 1;
      const model = event.models[modelIndex];
      if (!model) continue;
      tools.value?.removeObjectSelections(model.name);
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
      console.log("Shutting down the connection as requested by the server");
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

  async function loadModelManual() {
    const modelUrl = prompt(
      "For live CAD/GLTF updates from Python, install the cadquery-web-viewer package and run the Flask app, then load models via the server URL.\n\nOtherwise, enter the URL of a .glb/.gltf file to load:",
    );
    if (modelUrl) await networkMgr.load(modelUrl);
  }

  return {
    networkMgr,
    preloadingModels,
    onModelUpdateRequest,
    onModelRemoveRequest,
    loadModelManual,
  };
}
