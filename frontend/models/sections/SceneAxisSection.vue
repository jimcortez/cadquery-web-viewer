<script lang="ts" setup>
import {
  VBtnToggle,
  VExpansionPanel,
  VExpansionPanelText,
  VExpansionPanelTitle,
  VTooltip,
} from "vuetify/lib/components/index.mjs";
import { computed, inject, watch } from "vue";
import SvgIcon from "@jamescoyle/vue-icon";
import { mdiRectangle, mdiRectangleOutline, mdiVectorRectangle } from "@mdi/js";
import { useViewerSceneSettings } from "../../composables/useViewerSceneSettings";
import { sceneDocumentKey } from "../../injectionKeys";
import { extrasNameKey, extrasNameValueHelpers } from "../../misc/gltf";
import { SceneMgr } from "../../misc/scene";
import type ModelViewerWrapper from "../../viewer/ModelViewerWrapper.vue";
import type { ModelScene } from "@google/model-viewer/lib/three-components/ModelScene";

const props = defineProps<{
  viewer: InstanceType<typeof ModelViewerWrapper> | null;
}>();

const { scene, applyAxisVisibility } = useViewerSceneSettings();
const { sceneDocument } = inject(sceneDocumentKey)!;

const hasRealModels = computed(() => {
  const doc = sceneDocument.value;
  if (SceneMgr.getBoundingBox(doc) === null) return false;
  return doc
    .getRoot()
    .listMeshes()
    .some((m) => m.getExtras()[extrasNameKey]?.toString() !== extrasNameValueHelpers);
});

function modelScene(): ModelScene | null {
  return (props.viewer?.scene ?? null) as ModelScene | null;
}

function refreshAxis() {
  applyAxisVisibility(modelScene());
}

watch(
  () => props.viewer?.elem?.src,
  () => refreshAxis(),
);

watch(
  () => props.viewer?.scene,
  () => refreshAxis(),
);

function onAxisToggle() {
  refreshAxis();
}
</script>

<template>
  <v-expansion-panel value="axis" class="scene-subsection">
    <v-expansion-panel-title class="scene-subsection-title">Axis &amp; grid</v-expansion-panel-title>
    <v-expansion-panel-text>
      <p v-if="!hasRealModels" class="scene-hint mb-3">
        Load a model to show the scene axes and bounding grid.
      </p>
      <p v-else class="scene-hint mb-3">Scene overlays — not part of any loaded model.</p>
      <v-btn-toggle
        v-model="scene.axisEnabledFeatures"
        class="axis-toggle"
        color="primary"
        density="compact"
        multiple
        :disabled="!hasRealModels"
        @update:model-value="onAxisToggle"
      >
        <v-btn :value="0" :disabled="!hasRealModels">
          <v-tooltip activator="parent" location="top">Bounding grid</v-tooltip>
          <svg-icon :path="mdiRectangle" :rotate="90" type="mdi" />
        </v-btn>
        <v-btn :value="1" :disabled="!hasRealModels">
          <v-tooltip activator="parent" location="top">Axis lines</v-tooltip>
          <svg-icon :path="mdiRectangleOutline" :rotate="90" type="mdi" />
        </v-btn>
        <v-btn :value="2" :disabled="!hasRealModels">
          <v-tooltip activator="parent" location="top">Origin point</v-tooltip>
          <svg-icon :path="mdiVectorRectangle" :rotate="90" type="mdi" />
        </v-btn>
      </v-btn-toggle>
    </v-expansion-panel-text>
  </v-expansion-panel>
</template>

<style scoped>
.scene-hint {
  font-size: 0.75rem;
  line-height: 1.35;
  opacity: 0.75;
}

.axis-toggle {
  width: 100%;
  justify-content: center;
}
</style>
