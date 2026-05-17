<script lang="ts" setup>
import {
  VBtn,
  VCard,
  VCardText,
  VCheckboxBtn,
  VSelect,
  VDialog,
  VDivider,
  VProgressCircular,
  VSpacer,
  VTextField,
  VToolbar,
  VToolbarTitle,
} from "vuetify/lib/components/index.mjs";
import { computed, ref, watch } from "vue";
import { mdiClose, mdiRefresh } from "@mdi/js";
import SvgIcon from "@jamescoyle/vue-icon";
import { sampleModelUrls } from "../misc/sampleModelUrls";
import type { ServerObjectDescriptor } from "../misc/objectApi";

const open = defineModel<boolean>({ required: true });
const urlInput = defineModel<string>("urlInput", { required: true });

const selectedSample = ref<string | null>(null);

const sampleTitleByUrl = computed(() => {
  const map = new Map<string, string>();
  for (const item of sampleModelUrls) map.set(item.value, item.title);
  return map;
});

watch(urlInput, (url) => {
  selectedSample.value = url && sampleTitleByUrl.value.has(url) ? url : null;
});

function onSampleSelect(url: string | null) {
  selectedSample.value = url;
  if (url) urlInput.value = url;
}

defineProps<{
  apiBaseUrl: string | null;
  objects: ServerObjectDescriptor[];
  listLoading: boolean;
  listError: string | null;
  urlLoading: boolean;
  urlError: string | null;
  isSelected: (name: string) => boolean;
  getRowVersion: (name: string, desc: ServerObjectDescriptor) => number;
  allVersions: (desc: ServerObjectDescriptor) => Array<{ version: number; hash: string; label: string }>;
}>();

const emit = defineEmits<{
  refresh: [];
  toggleObject: [desc: ServerObjectDescriptor, selected: boolean];
  versionChange: [desc: ServerObjectDescriptor, version: number];
  loadFromUrl: [];
}>();

const sampleListProps = { maxHeight: 240, class: "sample-model-list" };
const sampleMenuProps = {
  maxHeight: 280,
  scrollStrategy: "block" as const,
  contentClass: "sample-model-menu",
};
</script>

<template>
  <v-dialog v-model="open" max-width="520">
    <v-card>
      <v-toolbar density="compact" class="popup">
        <v-toolbar-title>Add models</v-toolbar-title>
        <v-spacer />
        <v-btn
          v-if="apiBaseUrl"
          icon
          :disabled="listLoading"
          @click="emit('refresh')"
        >
          <svg-icon :path="mdiRefresh" type="mdi" />
        </v-btn>
        <v-btn icon @click="open = false">
          <svg-icon :path="mdiClose" type="mdi" />
        </v-btn>
      </v-toolbar>

      <v-card-text class="pa-4 dialog-body">
        <h6 class="text-subtitle-2 mb-2">Server cache</h6>
        <div v-if="!apiBaseUrl" class="text-body-2 text-medium-emphasis mb-4">
          Backend not connected. Objects on the server will appear here when the viewer is served by
          <code>cadquery-web-viewer</code>.
        </div>
        <div v-else-if="listLoading" class="d-flex justify-center my-4">
          <v-progress-circular indeterminate size="32" />
        </div>
        <p v-else-if="listError" class="text-error text-body-2 mb-4">{{ listError }}</p>
        <p v-else-if="objects.length === 0" class="text-body-2 text-medium-emphasis mb-4">
          No objects in cache yet. Import a model below or publish from Python.
        </p>
        <div v-else class="server-object-list mb-4">
          <div
            v-for="obj in objects"
            :key="obj.name"
            class="d-flex align-center ga-2 mb-2"
          >
            <v-checkbox-btn
              :model-value="isSelected(obj.name)"
              hide-details
              density="compact"
              @update:model-value="(v: boolean | null) => emit('toggleObject', obj, !!v)"
            />
            <span class="text-body-2">{{ obj.name }}</span>
            <v-select
              v-if="allVersions(obj).length > 1"
              :model-value="getRowVersion(obj.name, obj)"
              :items="allVersions(obj)"
              item-title="label"
              item-value="version"
              density="compact"
              hide-details
              variant="outlined"
              class="version-select flex-grow-1"
              @update:model-value="(v: number) => emit('versionChange', obj, v)"
            />
          </div>
        </div>

        <v-divider class="my-3" />

        <h6 class="text-subtitle-2 mb-2">Load from URL</h6>
        <v-select
          :model-value="selectedSample"
          :items="sampleModelUrls"
          :list-props="sampleListProps"
          :menu-props="sampleMenuProps"
          item-title="title"
          item-value="value"
          label="Sample models"
          density="compact"
          hide-details
          clearable
          placeholder="Choose a model…"
          class="mb-2"
          @update:model-value="onSampleSelect"
        />
        <v-text-field
          v-model="urlInput"
          label="Model URL (.glb / .gltf)"
          density="compact"
          hide-details
          class="mb-2"
        />
        <p v-if="urlError" class="text-error text-body-2 mb-2">{{ urlError }}</p>
        <v-btn
          color="primary"
          :loading="urlLoading"
          :disabled="!urlInput.trim()"
          @click="emit('loadFromUrl')"
        >
          Load
        </v-btn>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<style scoped>
.dialog-body {
  max-height: min(70vh, 520px);
  overflow-y: auto;
}
.server-object-list {
  max-height: 240px;
  overflow-y: auto;
}
.version-select {
  max-width: 140px;
}
</style>

<!-- Teleported VMenu is outside the component tree -->
<style>
.sample-model-menu {
  max-height: 280px;
  overflow: hidden;
}
.sample-model-menu .v-list.sample-model-list,
.sample-model-menu .v-list {
  max-height: 240px !important;
  overflow-y: auto !important;
  overscroll-behavior: contain;
}
</style>
