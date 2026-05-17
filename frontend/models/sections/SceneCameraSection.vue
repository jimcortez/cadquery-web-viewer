<script lang="ts" setup>
import {
  VCheckbox,
  VExpansionPanel,
  VExpansionPanelText,
  VExpansionPanelTitle,
  VSlider,
  VTextField,
} from "vuetify/lib/components/index.mjs";
import { useViewerSceneSettings } from "../../composables/useViewerSceneSettings";

const { scene } = useViewerSceneSettings();
</script>

<template>
  <v-expansion-panel value="camera" class="scene-subsection">
    <v-expansion-panel-title class="scene-subsection-title">Camera</v-expansion-panel-title>
    <v-expansion-panel-text>
      <v-checkbox v-model="scene.autoRotate" label="Auto-rotate" hide-details density="compact" />
      <v-slider
        v-model="scene.autoRotateDelay"
        label="Auto-rotate delay (ms)"
        min="0"
        max="10000"
        step="100"
        hide-details
        density="compact"
        :disabled="!scene.autoRotate"
      />
      <div class="text-caption mt-2 mb-1">Target (m)</div>
      <v-text-field
        v-model.number="scene.cameraTarget.x"
        label="X"
        type="number"
        density="compact"
        hide-details
        class="mb-1"
      />
      <v-text-field
        v-model.number="scene.cameraTarget.y"
        label="Y"
        type="number"
        density="compact"
        hide-details
        class="mb-1"
      />
      <v-text-field v-model.number="scene.cameraTarget.z" label="Z" type="number" density="compact" hide-details />
    </v-expansion-panel-text>
  </v-expansion-panel>
</template>
