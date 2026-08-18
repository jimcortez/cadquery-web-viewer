<script lang="ts" setup>
import { VTooltip } from "vuetify/lib/components/index.mjs";
import SvgIcon from "@jamescoyle/vue-icon";
import { mdiSwapHorizontal } from "@mdi/js";
import PanelSection from "../../components/controls/PanelSection.vue";
import SliderControl from "../../components/controls/SliderControl.vue";
import type { ModelDisplayState } from "../../composables/useModelDisplaySettings";

defineProps<{ display: ModelDisplayState }>();
</script>

<template>
  <panel-section title="Arrangement" :default-open="false">
    <slider-control
      v-model="display.explodeStrength"
      label="Explode"
      hint="Push this object away from the others"
      :min="0"
      :max="1"
      :step="0.01"
    >
      <template #after>
        <button
          type="button"
          class="cq-flip"
          :class="{ active: display.explodeSwapped }"
          @click="display.explodeSwapped = !display.explodeSwapped"
        >
          <v-tooltip activator="parent" location="top">Reverse direction</v-tooltip>
          <svg-icon :path="mdiSwapHorizontal" type="mdi" size="14" />
        </button>
      </template>
    </slider-control>
  </panel-section>
</template>

<style scoped>
.cq-flip {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  margin-left: var(--cq-space-1);
  border: var(--cq-border);
  border-radius: var(--cq-radius-sm);
  background: transparent;
  color: rgb(var(--v-theme-on-surface));
  opacity: 0.5;
  cursor: pointer;
}

.cq-flip:hover {
  opacity: 0.9;
}

.cq-flip.active {
  background: rgba(var(--v-theme-primary), 0.22);
  color: rgb(var(--v-theme-primary));
  opacity: 1;
}
</style>
