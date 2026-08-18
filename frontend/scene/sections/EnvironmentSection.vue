<script lang="ts" setup>
import { computed, ref } from "vue";
import PanelSection from "../../components/controls/PanelSection.vue";
import SettingRow from "../../components/controls/SettingRow.vue";
import SliderControl from "../../components/controls/SliderControl.vue";
import SelectControl from "../../components/controls/SelectControl.vue";
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
const fileInput = ref<HTMLInputElement | null>(null);
const uploadError = ref<string | null>(null);

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
  for (const img of cachedImages.value) items.push({ title: img.name, value: `cache:${img.id}` });
  return items;
});

async function onEnvFile(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0];
  if (!file) return;
  uploadError.value = null;
  try {
    await addCachedEnvironmentImage(file);
    cachedImages.value = listCachedEnvironmentImages();
    const newest = cachedImages.value[0];
    if (newest) scene.environmentPreset = `cache:${newest.id}`;
  } catch (e) {
    uploadError.value = e instanceof Error ? e.message : String(e);
  } finally {
    if (fileInput.value) fileInput.value.value = "";
  }
}

function clearCustomEnvironments() {
  clearCachedEnvironmentImages();
  cachedImages.value = [];
  if (scene.environmentPreset.startsWith("cache:")) scene.environmentPreset = ENV_PRESET_DEFAULT;
}
</script>

<template>
  <panel-section title="Environment">
    <setting-row label="Background">
      <color-swatch-field v-model="scene.backgroundColor" />
      <span class="cq-hex">{{ scene.backgroundColor }}</span>
    </setting-row>
    <slider-control v-model="scene.exposure" label="Exposure" :min="0" :max="3" :step="0.05" />
    <select-control
      v-model="scene.environmentPreset"
      label="Environment"
      :items="environmentItems"
    />
    <slider-control
      v-model="scene.environmentIntensity"
      label="Env intensity"
      :min="0"
      :max="3"
      :step="0.05"
    />
    <slider-control v-model="scene.shadowIntensity" label="Shadow" :min="0" :max="1" :step="0.05" />
    <slider-control v-model="scene.shadowSoftness" label="Softness" :min="0" :max="1" :step="0.05" />
    <select-control v-model="scene.toneMapping" label="Tone map" :items="toneMappingItems" />

    <setting-row label="Custom HDR">
      <input ref="fileInput" class="cq-file" type="file" accept="image/*,.hdr" @change="onEnvFile" />
      <button v-if="cachedImages.length" type="button" class="cq-link" @click="clearCustomEnvironments">
        Clear
      </button>
    </setting-row>
    <p v-if="uploadError" class="cq-error">{{ uploadError }}</p>
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

.cq-file {
  flex: 1 1 auto;
  min-width: 0;
  font-size: 0.6875rem;
  color: inherit;
}

.cq-file::file-selector-button {
  margin-right: var(--cq-space-2);
  padding: 3px var(--cq-space-2);
  font-size: 0.6875rem;
  color: rgb(var(--v-theme-on-surface));
  background: rgba(var(--v-theme-on-surface), 0.08);
  border: var(--cq-border);
  border-radius: var(--cq-radius-sm);
  cursor: pointer;
}

.cq-link {
  flex: 0 0 auto;
  border: 0;
  background: none;
  color: rgb(var(--v-theme-primary));
  font-size: var(--cq-text-label);
  cursor: pointer;
}

.cq-error {
  font-size: var(--cq-text-label);
  color: rgb(var(--v-theme-error));
}
</style>
