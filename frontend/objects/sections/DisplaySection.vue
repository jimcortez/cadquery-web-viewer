<script lang="ts" setup>
import PanelSection from "../../components/controls/PanelSection.vue";
import SliderControl from "../../components/controls/SliderControl.vue";
import ToggleControl from "../../components/controls/ToggleControl.vue";
import type { ModelDisplayState } from "../../composables/useModelDisplaySettings";

defineProps<{ display: ModelDisplayState; edgeCount: number; vertexCount: number }>();
</script>

<template>
  <panel-section title="Display">
    <slider-control v-model="display.opacity" label="Opacity" :min="0" :max="1" :step="0.05" />
    <toggle-control v-model="display.wireframe" label="Wireframe" />
    <slider-control
      v-if="edgeCount > 0 || vertexCount > 0"
      v-model="display.edgeWidth"
      label="Edge size"
      hint="Edge and vertex size"
      :min="0"
      :max="1"
      :step="0.05"
    />
  </panel-section>
</template>
