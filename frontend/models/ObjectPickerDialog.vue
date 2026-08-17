<script lang="ts" setup>
import {
  VCard,
  VCheckboxBtn,
  VDialog,
  VProgressCircular,
  VSelect,
  VTextField,
  VTooltip,
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
  <v-dialog v-model="open" max-width="540">
    <v-card class="cq-dialog cq-panel">
      <header class="cq-dialog__head">
        <span class="cq-dialog__title">Add objects</span>
        <button
          v-if="apiBaseUrl"
          type="button"
          class="cq-dialog__btn"
          :disabled="listLoading"
          aria-label="Refresh list"
          @click="emit('refresh')"
        >
          <v-tooltip activator="parent" location="bottom">Refresh</v-tooltip>
          <svg-icon :path="mdiRefresh" type="mdi" size="17" />
        </button>
        <button type="button" class="cq-dialog__btn" aria-label="Close" @click="open = false">
          <svg-icon :path="mdiClose" type="mdi" size="17" />
        </button>
      </header>

      <div class="cq-dialog__body cq-scroll">
        <h6 class="cq-dialog__section">Server cache</h6>
        <p v-if="!apiBaseUrl" class="cq-dialog__note">
          Backend not connected. Objects on the server appear here when the viewer is served by
          <code>cadquery-web-viewer</code>.
        </p>
        <div v-else-if="listLoading" class="cq-dialog__loading">
          <v-progress-circular indeterminate size="28" />
        </div>
        <p v-else-if="listError" class="cq-dialog__error">{{ listError }}</p>
        <p v-else-if="objects.length === 0" class="cq-dialog__note">
          No objects in the cache yet. Import one below, or publish from Python.
        </p>
        <ul v-else class="cq-dialog__list cq-scroll">
          <li v-for="obj in objects" :key="obj.name">
            <v-checkbox-btn
              :model-value="isSelected(obj.name)"
              hide-details
              density="compact"
              @update:model-value="(v: boolean | null) => emit('toggleObject', obj, !!v)"
            />
            <span class="cq-dialog__name">{{ obj.name }}</span>
            <v-select
              v-if="allVersions(obj).length > 1"
              :model-value="getRowVersion(obj.name, obj)"
              :items="allVersions(obj)"
              item-title="label"
              item-value="version"
              density="compact"
              hide-details
              variant="outlined"
              class="cq-dialog__version"
              @update:model-value="(v: number) => emit('versionChange', obj, v)"
            />
          </li>
        </ul>

        <h6 class="cq-dialog__section">Load from URL</h6>
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
          variant="outlined"
          placeholder="Choose a model…"
          class="mb-2"
          @update:model-value="onSampleSelect"
        />
        <v-text-field
          v-model="urlInput"
          label="Model URL (.glb / .gltf)"
          density="compact"
          hide-details
          variant="outlined"
          class="mb-2"
        />
        <p v-if="urlError" class="cq-dialog__error">{{ urlError }}</p>
        <button
          type="button"
          class="cq-dialog__cta"
          :disabled="urlLoading || !urlInput.trim()"
          @click="emit('loadFromUrl')"
        >
          {{ urlLoading ? "Loading…" : "Load" }}
        </button>
      </div>
    </v-card>
  </v-dialog>
</template>

<style scoped>
.cq-dialog {
  border: var(--cq-border);
  border-radius: var(--cq-radius-lg);
}

.cq-dialog__head {
  display: flex;
  align-items: center;
  gap: var(--cq-space-1);
  padding: var(--cq-space-2) var(--cq-space-2) var(--cq-space-2) var(--cq-space-4);
  border-bottom: var(--cq-border);
}

.cq-dialog__title {
  flex: 1 1 auto;
  font-size: var(--cq-text-label);
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  opacity: 0.85;
}

.cq-dialog__btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: 0;
  border-radius: var(--cq-radius-sm);
  background: transparent;
  color: rgb(var(--v-theme-on-surface));
  opacity: 0.7;
  cursor: pointer;
}

.cq-dialog__btn:hover:not(:disabled) {
  background: rgba(var(--v-theme-on-surface), 0.1);
  opacity: 1;
}

.cq-dialog__body {
  max-height: min(70vh, 540px);
  padding: var(--cq-space-4);
}

.cq-dialog__section {
  margin: 0 0 var(--cq-space-2);
  font-size: var(--cq-text-section);
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  opacity: 0.6;
}

.cq-dialog__section + * {
  margin-bottom: var(--cq-space-4);
}

.cq-dialog__list + .cq-dialog__section,
.cq-dialog__note + .cq-dialog__section,
.cq-dialog__loading + .cq-dialog__section,
.cq-dialog__error + .cq-dialog__section {
  margin-top: var(--cq-space-5);
  padding-top: var(--cq-space-4);
  border-top: var(--cq-border);
}

.cq-dialog__note {
  font-size: var(--cq-text-label);
  line-height: 1.5;
  opacity: 0.6;
}

.cq-dialog__note code {
  font-size: 0.85em;
  padding: 1px 4px;
  border-radius: 3px;
  background: rgba(var(--v-theme-on-surface), 0.1);
}

.cq-dialog__error {
  font-size: var(--cq-text-label);
  color: rgb(var(--v-theme-error));
}

.cq-dialog__loading {
  display: flex;
  justify-content: center;
  padding: var(--cq-space-4) 0;
}

.cq-dialog__list {
  list-style: none;
  margin: 0;
  padding: 0;
  max-height: 220px;
}

.cq-dialog__list li {
  display: flex;
  align-items: center;
  gap: var(--cq-space-2);
  min-height: var(--cq-list-row-h);
}

/* Vuetify's selection control grows by default, which pushed the name to the
   middle of the row. */
.cq-dialog__list :deep(.v-selection-control) {
  flex: 0 0 auto;
  min-height: 0;
}

.cq-dialog__name {
  flex: 1 1 auto;
  min-width: 0;
  font-size: var(--cq-text-body);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.cq-dialog__version {
  flex: 0 0 130px;
  width: 130px;
  font-size: var(--cq-text-label);
}

.cq-dialog__version :deep(.v-field) {
  border-radius: var(--cq-radius-sm);
  font-size: var(--cq-text-label);
}

.cq-dialog__version :deep(.v-field__input) {
  min-height: var(--cq-control-h);
  padding-top: 0;
  padding-bottom: 0;
}

.cq-dialog__cta {
  padding: var(--cq-space-2) var(--cq-space-4);
  font-size: var(--cq-text-body);
  font-weight: 600;
  color: rgb(var(--v-theme-on-surface));
  background: rgba(var(--v-theme-primary), 0.9);
  border: 0;
  border-radius: var(--cq-radius-md);
  cursor: pointer;
}

.cq-dialog__cta:hover:not(:disabled) {
  background: rgb(var(--v-theme-primary));
}

.cq-dialog__cta:disabled {
  opacity: 0.4;
  cursor: not-allowed;
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
