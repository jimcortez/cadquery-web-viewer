<script lang="ts" setup>
import {
  VCheckboxBtn,
  VDivider,
  VExpansionPanel,
  VExpansionPanelText,
  VExpansionPanelTitle,
  VSlider,
  VTooltip,
} from "vuetify/lib/components/index.mjs";
import SvgIcon from "@jamescoyle/vue-icon";
import {
  mdiArrowExpand,
  mdiCircleOpacity,
  mdiCube,
  mdiSwapHorizontal,
  mdiVectorLine,
} from "@mdi/js";
import type { ModelDisplayState } from "../../composables/useModelDisplaySettings";

defineProps<{
  display: ModelDisplayState;
  edgeCount: number;
  vertexCount: number;
}>();
</script>

<template>
  <v-expansion-panel value="controls">
    <v-expansion-panel-title>Controls</v-expansion-panel-title>
    <v-expansion-panel-text>
      <v-slider v-model="display.opacity" :step="0.1" hide-details max="1" min="0">
        <template #prepend>
          <v-tooltip activator="parent">Opacity</v-tooltip>
          <svg-icon :path="mdiCircleOpacity" type="mdi" />
        </template>
        <template #append>
          <v-tooltip activator="parent">Wireframe</v-tooltip>
          <v-checkbox-btn v-model="display.wireframe" false-icon="mdi-triangle" true-icon="mdi-triangle-outline" />
        </template>
      </v-slider>
      <v-slider v-model="display.explodeStrength" hide-details max="1" min="0">
        <template #prepend>
          <v-tooltip activator="parent">Explode</v-tooltip>
          <svg-icon :path="mdiArrowExpand" type="mdi" />
        </template>
        <template #append>
          <v-checkbox-btn v-model="display.explodeSwapped" false-icon="mdi-checkbox-blank-outline" true-icon="mdi-checkbox-marked-outline">
            <template #label>
              <svg-icon :path="mdiSwapHorizontal" type="mdi" />
            </template>
          </v-checkbox-btn>
        </template>
      </v-slider>
      <v-slider v-if="edgeCount > 0 || vertexCount > 0" v-model="display.edgeWidth" hide-details max="1" min="0">
        <template #prepend>
          <v-tooltip activator="parent">Edge / vertex size</v-tooltip>
          <svg-icon :path="mdiVectorLine" type="mdi" />
        </template>
      </v-slider>
      <v-divider />
      <v-slider v-model="display.clipPlaneX" hide-details max="1" min="0">
        <template #prepend>X</template>
        <template #append>
          <v-checkbox-btn v-model="display.clipPlaneSwappedX" false-icon="mdi-checkbox-blank-outline" true-icon="mdi-checkbox-marked-outline">
            <template #label><svg-icon :path="mdiSwapHorizontal" type="mdi" /></template>
          </v-checkbox-btn>
        </template>
      </v-slider>
      <v-slider v-model="display.clipPlaneZ" hide-details max="1" min="0">
        <template #prepend>Y</template>
        <template #append>
          <v-checkbox-btn v-model="display.clipPlaneSwappedZ" false-icon="mdi-checkbox-blank-outline" true-icon="mdi-checkbox-marked-outline">
            <template #label><svg-icon :path="mdiSwapHorizontal" type="mdi" /></template>
          </v-checkbox-btn>
        </template>
      </v-slider>
      <v-slider v-model="display.clipPlaneY" hide-details max="1" min="0">
        <template #prepend>
          <svg-icon :path="mdiCube" type="mdi" />
          Z
        </template>
        <template #append>
          <v-checkbox-btn v-model="display.clipPlaneSwappedY" false-icon="mdi-checkbox-blank-outline" true-icon="mdi-checkbox-marked-outline">
            <template #label><svg-icon :path="mdiSwapHorizontal" type="mdi" /></template>
          </v-checkbox-btn>
        </template>
      </v-slider>
    </v-expansion-panel-text>
  </v-expansion-panel>
</template>
