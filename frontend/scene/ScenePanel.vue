<script lang="ts" setup>
import { defineAsyncComponent, ref } from "vue";
import { VCard, VCardText, VDialog, VSpacer, VToolbar, VToolbarTitle, VTooltip } from "vuetify/lib/components/index.mjs";
import SvgIcon from "@jamescoyle/vue-icon";
import { mdiClose, mdiDownload, mdiGithub, mdiLicense } from "@mdi/js";
import FloatingPanel from "../components/controls/FloatingPanel.vue";
import Loading from "../misc/Loading.vue";
import EnvironmentSection from "./sections/EnvironmentSection.vue";
import CameraSection from "./sections/CameraSection.vue";
import OverlaysSection from "./sections/OverlaysSection.vue";
import SelectionSection from "./sections/SelectionSection.vue";
import { useCameraTools } from "../composables/useCameraTools";
import type ModelViewerWrapper from "../viewer/ModelViewerWrapper.vue";

const LicensesDialogContent = defineAsyncComponent({
  loader: () => import("../tools/LicensesDialogContent.vue"),
  loadingComponent: Loading,
  delay: 0,
});

defineProps<{ viewer: InstanceType<typeof ModelViewerWrapper> | null }>();

const { downloadSceneGlb } = useCameraTools();
const licensesOpen = ref(false);
</script>

<template>
  <floating-panel title="Scene">
    <environment-section />
    <camera-section />
    <overlays-section :viewer="viewer" />
    <selection-section />

    <footer class="cq-foot">
      <button type="button" class="cq-foot__btn" @click="downloadSceneGlb">
        <v-tooltip activator="parent" location="top">Download scene (Ctrl/Cmd+S)</v-tooltip>
        <svg-icon :path="mdiDownload" type="mdi" size="16" />
      </button>
      <button type="button" class="cq-foot__btn" @click="licensesOpen = true">
        <v-tooltip activator="parent" location="top">Licenses</v-tooltip>
        <svg-icon :path="mdiLicense" type="mdi" size="16" />
      </button>
      <a
        class="cq-foot__btn"
        href="https://github.com/jecortez/cadquery-web-viewer"
        target="_blank"
        rel="noreferrer"
      >
        <v-tooltip activator="parent" location="top">Open GitHub</v-tooltip>
        <svg-icon :path="mdiGithub" type="mdi" size="16" />
      </a>
    </footer>
  </floating-panel>

  <v-dialog v-model="licensesOpen" max-width="900">
    <v-card style="height: 90vh">
      <v-toolbar density="compact">
        <v-toolbar-title>Licenses</v-toolbar-title>
        <v-spacer />
        <button type="button" class="cq-foot__btn" aria-label="Close" @click="licensesOpen = false">
          <svg-icon :path="mdiClose" type="mdi" size="18" />
        </button>
      </v-toolbar>
      <v-card-text>
        <licenses-dialog-content />
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<style scoped>
.cq-foot {
  display: flex;
  gap: var(--cq-space-1);
  padding: var(--cq-space-2) var(--cq-space-3);
  border-top: var(--cq-border);
}

.cq-foot__btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  border: 0;
  border-radius: var(--cq-radius-sm);
  background: transparent;
  color: rgb(var(--v-theme-on-surface));
  opacity: 0.65;
  cursor: pointer;
}

.cq-foot__btn:hover {
  background: rgba(var(--v-theme-on-surface), 0.1);
  opacity: 1;
}
</style>
