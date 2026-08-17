<script lang="ts" setup>
import { computed, defineAsyncComponent, provide, ref, shallowRef, type Ref } from "vue";
import { VTooltip } from "vuetify/lib/components/index.mjs";
import { Document } from "@gltf-transform/core";
import SvgIcon from "@jamescoyle/vue-icon";
import { mdiChevronRight } from "@mdi/js";
import Loading from "./misc/Loading.vue";
import ObjectsPanel from "./objects/ObjectsPanel.vue";
import ScenePanel from "./scene/ScenePanel.vue";
import ViewportToolbar from "./viewer/ViewportToolbar.vue";
import EmptyState from "./viewer/EmptyState.vue";
import OrientationGizmo from "./tools/OrientationGizmo.vue";
import ObjectPickerDialog from "./models/ObjectPickerDialog.vue";
import type ModelViewerWrapperT from "./viewer/ModelViewerWrapper.vue";
import { disableTapKey, sceneDocumentKey } from "./injectionKeys";
import { createViewerSceneSettingsProvider } from "./composables/useViewerSceneSettings";
import { createModelDisplaySettingsProvider } from "./composables/useModelDisplaySettings";
import { createSceneObjectsProvider } from "./composables/useSceneObjects";
import { useModelEffectsManager } from "./composables/useModelEffectsManager";
import { createSelectionToolsProvider } from "./composables/useSelectionTools";
import { createCameraToolsProvider } from "./composables/useCameraTools";
import { useKeyboardShortcuts } from "./composables/useKeyboardShortcuts";
import { settings } from "./misc/settings";
import { useAppModelLoading } from "./composables/useAppModelLoading";
import { useGltfFileDrop } from "./composables/useGltfFileDrop";

const ModelViewerWrapper = defineAsyncComponent({
  loader: () => import("./viewer/ModelViewerWrapper.vue"),
  loadingComponent: Loading,
  delay: 0,
});

const railOpen = ref(window.innerWidth > 900);

const sceneUrl = ref("");
const viewer: Ref<InstanceType<typeof ModelViewerWrapperT> | null> = ref(null);
const sceneDocument = shallowRef(new Document());
provide(sceneDocumentKey, { sceneDocument });

const viewerSceneSettings = createViewerSceneSettingsProvider();
const modelDisplaySettings = createModelDisplaySettingsProvider();
void settings.then((s) => modelDisplaySettings.setDefaultEdgeWidth(s.edgeWidth));

const sceneObjects = createSceneObjectsProvider(sceneDocument);
// Each object's three.js effects run in their own scope, so they keep applying
// while the inspector is showing some other object.
useModelEffectsManager(sceneObjects, modelDisplaySettings, viewer);

const disableTap = ref(false);
function setDisableTap(val: boolean) {
  disableTap.value = val;
}
provide(disableTapKey, { disableTap, setDisableTap });

// These providers take their dependencies as arguments rather than injecting
// them: App is the root component, and Vue resolves a root instance's injections
// against the app context, not against its own provides.
const selectionTools = createSelectionToolsProvider({
  viewer,
  sceneDocument,
  setDisableTap,
  onFindModel: (name) => {
    railOpen.value = true;
    sceneObjects.select(name);
  },
});
const cameraTools = createCameraToolsProvider(viewer, viewerSceneSettings);
useKeyboardShortcuts(selectionTools, cameraTools);

const { preloadingModels, onModelRemoveRequest, openObjectPicker, pickerOpen, networkMgr, apiBaseUrl, objects, listLoading, listError, urlInput, urlLoading, urlError, refreshObjectList, isSelected, getRowVersion, allVersions, toggleObject, onVersionChange, loadFromUrl } =
  useAppModelLoading(viewer, sceneDocument, selectionTools, sceneUrl);

useGltfFileDrop(networkMgr);

const hasModels = computed(
  () => sceneDocument.value.getRoot().listMeshes().length > 0 && !!sceneUrl.value,
);

// `dev+` entries are the SSE subscription, not a model — it never "finishes"
// loading, so listing it under "still trying to load" just reads as an error.
const pendingModels = computed(() => preloadingModels.value.filter((m) => !m.startsWith("dev+")));
</script>

<template>
  <div class="cq-app">
    <objects-panel
      v-show="railOpen"
      @add="openObjectPicker"
      @remove="onModelRemoveRequest"
      @collapse="railOpen = false"
    />

    <div class="cq-viewport" :class="{ 'rail-collapsed': !railOpen }">
      <button v-if="!railOpen" type="button" class="cq-reopen" @click="railOpen = true">
        <v-tooltip activator="parent" location="right">Show objects</v-tooltip>
        <svg-icon :path="mdiChevronRight" type="mdi" size="18" />
      </button>

      <model-viewer-wrapper v-if="hasModels" ref="viewer" :src="sceneUrl" />
      <empty-state v-else :preloading="pendingModels" @add="openObjectPicker" />

      <template v-if="hasModels">
        <viewport-toolbar />
        <scene-panel :viewer="viewer" />
        <div class="cq-gizmo">
          <orientation-gizmo v-if="viewer?.scene" :viewer="viewer" />
        </div>
      </template>
    </div>

    <object-picker-dialog
      v-model="pickerOpen"
      v-model:url-input="urlInput"
      :api-base-url="apiBaseUrl"
      :objects="objects"
      :list-loading="listLoading"
      :list-error="listError"
      :url-loading="urlLoading"
      :url-error="urlError"
      :is-selected="isSelected"
      :get-row-version="getRowVersion"
      :all-versions="allVersions"
      @refresh="refreshObjectList()"
      @toggle-object="(desc, selected) => toggleObject(desc, selected)"
      @version-change="onVersionChange"
      @load-from-url="loadFromUrl()"
    />
  </div>
</template>

<style scoped>
/* Two columns: the object rail sizes to its content (and to zero when hidden),
   the viewport takes the rest. Vuetify's layout components exist to reserve space
   for docked drawers, which this no longer has. */
.cq-app {
  display: grid;
  grid-template-columns: auto 1fr;
  height: 100dvh;
  overflow: hidden;
  background: rgb(var(--v-theme-background));
  color: rgb(var(--v-theme-on-surface));
}

/* Positioned so the toolbar, scene panel and gizmo anchor to the viewport rather
   than the window — otherwise they drift over the rail. */
.cq-viewport {
  /* Pinned to column 2. Hiding the rail sets display:none, which drops it out of
     grid flow entirely — without this the viewport would auto-place into the
     now-empty `auto` column and collapse to zero width. */
  grid-column: 2;
  position: relative;
  min-width: 0;
  height: 100%;
  overflow: hidden;
  /* Where top-left overlays start. Shifts right to clear the reopen button when
     the rail is hidden. */
  --cq-vp-left: var(--cq-space-3);
}

.cq-viewport.rail-collapsed {
  --cq-vp-left: 52px;
}

.cq-reopen {
  position: absolute;
  top: var(--cq-space-3);
  left: var(--cq-space-3);
  z-index: 5;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: var(--cq-border);
  border-radius: var(--cq-radius-md);
  background: rgba(var(--v-theme-surface), 0.86);
  backdrop-filter: blur(12px);
  color: rgb(var(--v-theme-on-surface));
  cursor: pointer;
}

.cq-reopen:hover {
  background: rgb(var(--v-theme-surface-light));
}

/* Bottom-right, clear of the scene panel's reserved height. */
.cq-gizmo {
  position: absolute;
  right: var(--cq-space-3);
  bottom: var(--cq-space-3);
  z-index: 3;
  width: 92px;
  height: 92px;
  pointer-events: auto;
}
</style>

<style>
.cq-gizmo .orientation-gizmo {
  display: block;
  width: 100%;
  height: 100%;
}

/* The colour picker menu is rendered in an overlay outside the panel tree. */
.v-overlay--active > .v-overlay__content {
  display: block !important;
}
</style>
