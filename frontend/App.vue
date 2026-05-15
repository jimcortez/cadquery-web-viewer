<!--suppress SillyAssignmentJS -->
<script lang="ts" setup>
import { defineAsyncComponent, provide, type Ref, ref, shallowRef } from "vue";
import Sidebar from "./misc/Sidebar.vue";
import Loading from "./misc/Loading.vue";
import Tools from "./tools/Tools.vue";
import Models from "./models/Models.vue";
import { VBtn, VLayout, VMain, VToolbarTitle } from "vuetify/lib/components/index.mjs";
import { Document } from "@gltf-transform/core";
import type ModelViewerWrapperT from "./viewer/ModelViewerWrapper.vue";
import { mdiPlus } from "@mdi/js";
import SvgIcon from "@jamescoyle/vue-icon";
import { disableTapKey, sceneDocumentKey } from "./injectionKeys";
import { useAppModelLoading } from "./composables/useAppModelLoading";
import { useGltfFileDrop } from "./composables/useGltfFileDrop";

const ModelViewerWrapper = defineAsyncComponent({
  loader: () => import("./viewer/ModelViewerWrapper.vue"),
  loadingComponent: Loading,
  delay: 0,
});

const openSidebarsByDefault: Ref<boolean> = ref(window.innerWidth > window.innerHeight);

const sceneUrl = ref("");
const viewer: Ref<InstanceType<typeof ModelViewerWrapperT> | null> = ref(null);
const sceneDocument = shallowRef(new Document());
provide(sceneDocumentKey, { sceneDocument });

const models: Ref<InstanceType<typeof Models> | null> = ref(null);
const tools: Ref<InstanceType<typeof Tools> | null> = ref(null);

const disableTap = ref(false);
function setDisableTap(val: boolean) {
  disableTap.value = val;
}
provide(disableTapKey, { disableTap, setDisableTap });

const { preloadingModels, onModelRemoveRequest, loadModelManual, networkMgr } =
  useAppModelLoading(viewer, sceneDocument, tools, sceneUrl);

useGltfFileDrop(networkMgr);
</script>

<template>
  <v-layout full-height>
    <v-main id="main">
      <model-viewer-wrapper
        v-if="sceneDocument.getRoot().listMeshes().length > 0"
        ref="viewer"
        :src="sceneUrl"
      />
      <div v-else style="height: 100%; overflow-y: auto">
        <v-toolbar-title class="text-center ma-16 text-h5">No model loaded</v-toolbar-title>
        <v-btn class="mx-auto d-block my-4" @click="loadModelManual">
          <svg-icon :path="mdiPlus" type="mdi" />&nbsp; Load model manually...
        </v-btn>
        <span v-if="preloadingModels.length > 0" class="d-block text-center my-16">
          <span class="d-block text-center text-h6">Still trying to load the following:</span>
          <span v-for="(model, index) in preloadingModels" :key="index" class="d-block text-center">
            <template v-if="model !== undefined">
              {{ model }}<span v-if="index < preloadingModels.length - 1">, </span>
            </template>
          </span>
        </span>
      </div>
    </v-main>

    <sidebar :opened-init="openSidebarsByDefault" :width="300" side="left">
      <template #toolbar>
        <v-toolbar-title>Models</v-toolbar-title>
      </template>
      <template #toolbar-items>
        <v-btn icon="" @click="loadModelManual">
          <svg-icon :path="mdiPlus" type="mdi" />
        </v-btn>
      </template>
      <models ref="models" :viewer="viewer" @remove-model="onModelRemoveRequest" />
    </sidebar>

    <sidebar :opened-init="openSidebarsByDefault" :width="48 * 3 + 1" side="right">
      <template #toolbar>
        <v-toolbar-title>Tools</v-toolbar-title>
      </template>
      <tools ref="tools" :viewer="viewer" @find-model="models?.findModel" />
    </sidebar>
  </v-layout>
</template>

<!--suppress CssUnusedSymbol -->
<style>
html,
body {
  height: 100%;
  overflow: hidden !important;
}
</style>
