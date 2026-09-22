<script lang="ts" setup>
import { computed, inject, watch } from "vue";
import { mdiGrid, mdiVectorLine, mdiVectorPoint } from "@mdi/js";
import PanelSection from "../../components/controls/PanelSection.vue";
import SettingRow from "../../components/controls/SettingRow.vue";
import SegmentedToggle, { type Segment } from "../../components/controls/SegmentedToggle.vue";
import { useViewerSceneSettings } from "../../composables/useViewerSceneSettings";
import { sceneDocumentKey } from "../../injectionKeys";
import { extrasNameKey, extrasNameValueHelpers } from "../../misc/gltf";
import { SceneMgr } from "../../misc/scene";
import type ModelViewerWrapper from "../../viewer/ModelViewerWrapper.vue";
import type { ModelScene } from "@google/model-viewer/lib/three-components/ModelScene";

const props = defineProps<{ viewer: InstanceType<typeof ModelViewerWrapper> | null }>();

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

const segments = computed<Segment[]>(() => [
  { value: 0, icon: mdiGrid, label: "Bounding grid", disabled: !hasRealModels.value },
  { value: 1, icon: mdiVectorLine, label: "Axis lines", disabled: !hasRealModels.value },
  { value: 2, icon: mdiVectorPoint, label: "Origin point", disabled: !hasRealModels.value },
]);

function refreshAxis() {
  applyAxisVisibility((props.viewer?.scene ?? null) as ModelScene | null);
}

watch(() => props.viewer?.elem?.src, refreshAxis);
watch(() => props.viewer?.scene, refreshAxis);
watch(() => scene.axisEnabledFeatures.slice().sort().join(","), refreshAxis);
</script>

<template>
  <panel-section title="Overlays">
    <setting-row label="Helpers" hint="Scene overlays — not part of any loaded object">
      <segmented-toggle
        v-model="scene.axisEnabledFeatures"
        :segments="segments"
        :disabled="!hasRealModels"
      />
    </setting-row>
    <p v-if="!hasRealModels" class="cq-hint">Load an object to show the scene axes and grid.</p>
  </panel-section>
</template>

<style scoped>
.cq-hint {
  font-size: var(--cq-text-label);
  line-height: 1.4;
  opacity: 0.5;
}
</style>
