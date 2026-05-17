<script lang="ts" setup>
import {
  VCheckbox,
  VExpansionPanel,
  VExpansionPanelText,
  VExpansionPanelTitle,
  VSlider,
} from "vuetify/lib/components/index.mjs";
import ColorSwatchField from "../../components/ColorSwatchField.vue";
import type { ModelDisplayState } from "../../composables/useModelDisplaySettings";

defineProps<{
  display: ModelDisplayState;
}>();
</script>

<template>
  <v-expansion-panel value="model">
    <v-expansion-panel-title>Model</v-expansion-panel-title>
    <v-expansion-panel-text>
      <div class="row">
        <span class="text-caption">Base color</span>
        <color-swatch-field v-model="display.baseColor" />
      </div>
      <v-slider v-model="display.metalness" label="Metalness" min="0" max="1" step="0.05" hide-details density="compact" />
      <v-slider v-model="display.roughness" label="Roughness" min="0" max="1" step="0.05" hide-details density="compact" />
      <div class="row">
        <span class="text-caption">Emissive</span>
        <color-swatch-field v-model="display.emissiveColor" />
      </div>
      <v-slider
        v-model="display.emissiveIntensity"
        label="Emissive intensity"
        min="0"
        max="5"
        step="0.05"
        hide-details
        density="compact"
      />
      <v-checkbox v-model="display.doubleSided" label="Double-sided" hide-details density="compact" />
    </v-expansion-panel-text>
  </v-expansion-panel>
</template>

<style scoped>
.row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}
</style>
