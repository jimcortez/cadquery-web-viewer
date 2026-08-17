<script lang="ts" setup>
import PanelSection from "../../components/controls/PanelSection.vue";
import SettingRow from "../../components/controls/SettingRow.vue";
import SliderControl from "../../components/controls/SliderControl.vue";
import ToggleControl from "../../components/controls/ToggleControl.vue";
import ColorSwatchField from "../../components/ColorSwatchField.vue";
import type { ModelDisplayState } from "../../composables/useModelDisplaySettings";

defineProps<{ display: ModelDisplayState }>();
</script>

<template>
  <panel-section title="Appearance">
    <setting-row label="Base color">
      <color-swatch-field v-model="display.baseColor" />
      <span class="cq-hex">{{ display.baseColor }}</span>
    </setting-row>
    <slider-control v-model="display.metalness" label="Metalness" :min="0" :max="1" :step="0.05" />
    <slider-control v-model="display.roughness" label="Roughness" :min="0" :max="1" :step="0.05" />
    <setting-row label="Emissive">
      <color-swatch-field v-model="display.emissiveColor" />
      <span class="cq-hex">{{ display.emissiveColor }}</span>
    </setting-row>
    <slider-control
      v-model="display.emissiveIntensity"
      label="Emission"
      hint="Emissive intensity"
      :min="0"
      :max="5"
      :step="0.05"
    />
    <toggle-control v-model="display.doubleSided" label="Double-sided" />
  </panel-section>
</template>

<style scoped>
.cq-hex {
  margin-left: var(--cq-space-2);
  font-size: var(--cq-text-label);
  font-variant-numeric: tabular-nums;
  opacity: 0.55;
  text-transform: uppercase;
}
</style>
