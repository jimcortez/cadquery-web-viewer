<script lang="ts" setup>
import { VExpansionPanels } from "vuetify/lib/components/index.mjs";
import { ref } from "vue";
import SceneLightingSection from "./sections/SceneLightingSection.vue";
import SceneCameraSection from "./sections/SceneCameraSection.vue";
import SceneAxisSection from "./sections/SceneAxisSection.vue";
import type ModelViewerWrapper from "../viewer/ModelViewerWrapper.vue";

defineProps<{
  viewer: InstanceType<typeof ModelViewerWrapper> | null;
}>();

const sectionOpen = ref<string[]>(["lighting"]);
</script>

<template>
  <v-expansion-panels v-model="sectionOpen" multiple density="compact" class="scene-section-panels">
    <scene-lighting-section />
    <scene-camera-section />
    <scene-axis-section :viewer="viewer" />
  </v-expansion-panels>
</template>

<style scoped>
.scene-section-panels :deep(.v-expansion-panel-title) {
  padding: 0 4px;
  min-height: 36px;
}
</style>
