<script lang="ts" setup>
import {
  VBtn,
  VExpansionPanel,
  VExpansionPanelText,
  VExpansionPanelTitle,
  VSelect,
  VSlider,
  VFileInput,
} from "vuetify/lib/components/index.mjs";
import { computed, ref } from "vue";
import ColorSwatchField from "../../components/ColorSwatchField.vue";
import { useViewerSceneSettings, type ToneMappingValue } from "../../composables/useViewerSceneSettings";
import {
  addCachedEnvironmentImage,
  clearCachedEnvironmentImages,
  ENV_PRESET_DEFAULT,
  ENV_PRESET_LEGACY,
  ENV_PRESET_NEUTRAL,
  listCachedEnvironmentImages,
  type EnvironmentPresetId,
} from "../../misc/environmentImageCache";

const { scene } = useViewerSceneSettings();
const cachedImages = ref(listCachedEnvironmentImages());

const toneMappingItems: { title: string; value: ToneMappingValue }[] = [
  { title: "Auto", value: "auto" },
  { title: "Neutral (PBR)", value: "neutral" },
  { title: "Commerce", value: "commerce" },
  { title: "ACES", value: "aces" },
  { title: "AgX", value: "agx" },
  { title: "Reinhard", value: "reinhard" },
  { title: "Cineon", value: "cineon" },
  { title: "Linear", value: "linear" },
  { title: "None", value: "none" },
];

const environmentItems = computed(() => {
  const items: { title: string; value: EnvironmentPresetId }[] = [
    { title: "Default", value: ENV_PRESET_DEFAULT },
    { title: "Neutral", value: ENV_PRESET_NEUTRAL },
    { title: "Legacy", value: ENV_PRESET_LEGACY },
  ];
  for (const img of cachedImages.value) {
    items.push({ title: img.name, value: `cache:${img.id}` });
  }
  return items;
});

async function onEnvFile(files: File | File[] | null) {
  const file = Array.isArray(files) ? files[0] : files;
  if (!file) return;
  try {
    await addCachedEnvironmentImage(file);
    cachedImages.value = listCachedEnvironmentImages();
    scene.environmentPreset = `cache:${cachedImages.value[0]!.id}`;
  } catch (e) {
    console.error(e);
  }
}

function clearCustomEnvironments() {
  clearCachedEnvironmentImages();
  cachedImages.value = [];
  if (scene.environmentPreset.startsWith("cache:")) {
    scene.environmentPreset = ENV_PRESET_DEFAULT;
  }
}
</script>

<template>
  <v-expansion-panel value="lighting" class="scene-subsection">
    <v-expansion-panel-title class="scene-subsection-title">Lighting</v-expansion-panel-title>
    <v-expansion-panel-text>
      <div class="row">
        <span class="text-caption">Background</span>
        <color-swatch-field v-model="scene.backgroundColor" />
      </div>
      <v-slider v-model="scene.exposure" label="Exposure" min="0" max="3" step="0.05" hide-details density="compact" />
      <v-select
        v-model="scene.environmentPreset"
        :items="environmentItems"
        item-title="title"
        item-value="value"
        label="Environment"
        density="compact"
        hide-details
      />
      <v-file-input
        label="Upload environment (HDR/PNG)"
        density="compact"
        hide-details
        accept="image/*,.hdr"
        @update:model-value="onEnvFile"
      />
      <v-btn v-if="cachedImages.length" size="x-small" variant="text" @click="clearCustomEnvironments">
        Clear custom environments
      </v-btn>
      <v-slider
        v-model="scene.environmentIntensity"
        label="Environment intensity"
        min="0"
        max="3"
        step="0.05"
        hide-details
        density="compact"
      />
      <v-slider
        v-model="scene.shadowIntensity"
        label="Shadow intensity"
        min="0"
        max="1"
        step="0.05"
        hide-details
        density="compact"
      />
      <v-slider
        v-model="scene.shadowSoftness"
        label="Shadow softness"
        min="0"
        max="1"
        step="0.05"
        hide-details
        density="compact"
      />
      <v-select
        v-model="scene.toneMapping"
        :items="toneMappingItems"
        item-title="title"
        item-value="value"
        label="Tone mapping"
        density="compact"
        hide-details
      />
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
