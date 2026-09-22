<script lang="ts" setup>
import { computed } from "vue";
import { mdiRectangle, mdiRectangleOutline, mdiVectorRectangle } from "@mdi/js";
import SegmentedToggle, { type Segment } from "../components/controls/SegmentedToggle.vue";
import { useModelDisplaySettings } from "../composables/useModelDisplaySettings";
import type { SceneObject } from "../composables/useSceneObjects";
import DisplaySection from "./sections/DisplaySection.vue";
import AppearanceSection from "./sections/AppearanceSection.vue";
import SectionSection from "./sections/SectionSection.vue";
import ArrangementSection from "./sections/ArrangementSection.vue";

const props = defineProps<{ object: SceneObject }>();

const { getSettings } = useModelDisplaySettings();
// ObjectsPanel keys this component by object name, so a new selection remounts it
// and this resolves against the newly selected object.
const display = getSettings(props.object.name);

const segments = computed<Segment[]>(() => [
  { value: 0, icon: mdiRectangle, label: "Faces", badge: props.object.faceCount, disabled: props.object.faceCount === 0 },
  { value: 1, icon: mdiRectangleOutline, label: "Edges", badge: props.object.edgeCount, disabled: props.object.edgeCount === 0 },
  { value: 2, icon: mdiVectorRectangle, label: "Vertices", badge: props.object.vertexCount, disabled: props.object.vertexCount === 0 },
]);
</script>

<template>
  <div class="cq-inspector cq-panel">
    <header class="cq-inspector__header">
      <span class="cq-inspector__name" :title="object.name">{{ object.name }}</span>
      <segmented-toggle v-model="display.enabledFeatures" :segments="segments" />
    </header>

    <div class="cq-inspector__sections cq-scroll">
      <display-section
        :display="display"
        :edge-count="object.edgeCount"
        :vertex-count="object.vertexCount"
      />
      <appearance-section :display="display" />
      <section-section :display="display" />
      <arrangement-section :display="display" />
    </div>
  </div>
</template>

<style scoped>
.cq-inspector {
  display: flex;
  flex-direction: column;
  min-height: 0;
  height: 100%;
}

.cq-inspector__header {
  display: flex;
  align-items: center;
  gap: var(--cq-space-2);
  flex: 0 0 auto;
  padding: var(--cq-space-2) var(--cq-space-3);
  border-bottom: var(--cq-border);
}

.cq-inspector__name {
  flex: 1 1 auto;
  min-width: 0;
  font-size: var(--cq-text-body);
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.cq-inspector__sections {
  flex: 1 1 auto;
  min-height: 0;
}
</style>
