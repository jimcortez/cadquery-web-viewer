<script lang="ts" setup>
import { VTooltip } from "vuetify/lib/components/index.mjs";
import SvgIcon from "@jamescoyle/vue-icon";
import { mdiSwapHorizontal } from "@mdi/js";
import PanelSection from "../../components/controls/PanelSection.vue";
import SliderControl from "../../components/controls/SliderControl.vue";
import type { ModelDisplayState } from "../../composables/useModelDisplaySettings";

/*
 * The axis-to-property mapping looks transposed and is not: the viewer presents
 * glTF's Y-up scene as CAD Z-up throughout. UI "Y" drives clipPlaneZ and UI "Z"
 * drives clipPlaneY, matching newAxes() drawing Z along -z, the (1 - clipPlaneZ)
 * inversion in useModelSceneEffects, and the orientation gizmo's axis swaps.
 * Straightening this out here would clip the wrong direction.
 */
defineProps<{ display: ModelDisplayState }>();
</script>

<template>
  <panel-section title="Section" :default-open="false">
    <slider-control v-model="display.clipPlaneX" label="X" :min="0" :max="1" :step="0.01">
      <template #after>
        <button
          type="button"
          class="cq-flip"
          :class="{ active: display.clipPlaneSwappedX }"
          @click="display.clipPlaneSwappedX = !display.clipPlaneSwappedX"
        >
          <v-tooltip activator="parent" location="top">Flip X side</v-tooltip>
          <svg-icon :path="mdiSwapHorizontal" type="mdi" size="14" />
        </button>
      </template>
    </slider-control>

    <slider-control v-model="display.clipPlaneZ" label="Y" :min="0" :max="1" :step="0.01">
      <template #after>
        <button
          type="button"
          class="cq-flip"
          :class="{ active: display.clipPlaneSwappedZ }"
          @click="display.clipPlaneSwappedZ = !display.clipPlaneSwappedZ"
        >
          <v-tooltip activator="parent" location="top">Flip Y side</v-tooltip>
          <svg-icon :path="mdiSwapHorizontal" type="mdi" size="14" />
        </button>
      </template>
    </slider-control>

    <slider-control v-model="display.clipPlaneY" label="Z" :min="0" :max="1" :step="0.01">
      <template #after>
        <button
          type="button"
          class="cq-flip"
          :class="{ active: display.clipPlaneSwappedY }"
          @click="display.clipPlaneSwappedY = !display.clipPlaneSwappedY"
        >
          <v-tooltip activator="parent" location="top">Flip Z side</v-tooltip>
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
