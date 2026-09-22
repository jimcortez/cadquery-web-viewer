<script lang="ts" setup>
import { computed } from "vue";
import PanelSection from "../../components/controls/PanelSection.vue";
import SettingRow from "../../components/controls/SettingRow.vue";
import SelectControl from "../../components/controls/SelectControl.vue";
import ToggleControl from "../../components/controls/ToggleControl.vue";
import { SELECTION_FILTERS, useSelectionTools } from "../../composables/useSelectionTools";
import { useSceneObjects } from "../../composables/useSceneObjects";

const {
  selected,
  selectionEnabled,
  selectFilter,
  showBoundingBox,
  showDistances,
  counts,
  toggleSelection,
  deselect,
  deselectAll,
  updateBoundingBox,
  updateDistances,
} = useSelectionTools();
const { select: selectObject } = useSceneObjects();

const filterItems = SELECTION_FILTERS.map((f) => ({ title: f.label, value: f.value }));

/** Flat, readable list of what is currently picked. */
const entries = computed(() =>
  selected.value.map((s, index) => ({
    index,
    key: s.getKey(),
    kind: s.kind,
    objectName: s.getObjectName() ?? "unknown",
    info: s,
  })),
);

function clearAll() {
  deselectAll();
  updateBoundingBox();
  updateDistances();
}

function removeOne(info: (typeof entries.value)[number]["info"]) {
  deselect(info);
  updateBoundingBox();
  updateDistances();
}
</script>

<template>
  <panel-section title="Selection">
    <template #meta>{{ counts.face }}F · {{ counts.edge }}E · {{ counts.vertex }}V</template>

    <setting-row label="Picking">
      <button
        type="button"
        class="cq-action"
        :class="{ active: selectionEnabled }"
        @click="toggleSelection"
      >
        {{ selectionEnabled ? "Enabled" : "Disabled" }}
      </button>
    </setting-row>
    <select-control
      v-model="selectFilter"
      label="Filter"
      :items="filterItems"
      :disabled="!selectionEnabled"
    />
    <toggle-control v-model="showBoundingBox" label="Bounds" @update:model-value="updateBoundingBox" />
    <toggle-control v-model="showDistances" label="Distances" @update:model-value="updateDistances" />

    <div v-if="entries.length" class="cq-sel">
      <div class="cq-sel__head">
        <span>{{ entries.length }} selected</span>
        <button type="button" class="cq-link" @click="clearAll">Clear all</button>
      </div>
      <ul class="cq-sel__list cq-scroll">
        <li v-for="entry in entries" :key="entry.key">
          <button
            type="button"
            class="cq-sel__name"
            :title="`Reveal ${entry.objectName} in the object list`"
            @click="selectObject(entry.objectName)"
          >
            <span class="cq-sel__kind" :class="entry.kind">{{ entry.kind.charAt(0).toUpperCase() }}</span>
            {{ entry.objectName }}
          </button>
          <button type="button" class="cq-sel__x" aria-label="Deselect" @click="removeOne(entry.info)">
            ×
          </button>
        </li>
      </ul>
    </div>
    <p v-else class="cq-hint">
      {{ selectionEnabled ? "Click a face, edge or vertex in the viewport." : "Enable picking to select features." }}
    </p>
  </panel-section>
</template>

<style scoped>
.cq-action {
  padding: 3px var(--cq-space-2);
  font-size: var(--cq-text-label);
  border: var(--cq-border);
  border-radius: var(--cq-radius-sm);
  background: transparent;
  color: rgb(var(--v-theme-on-surface));
  cursor: pointer;
}

.cq-action.active {
  background: rgba(var(--v-theme-primary), 0.22);
  color: rgb(var(--v-theme-primary));
}

.cq-sel {
  margin-top: var(--cq-space-1);
}

.cq-sel__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: var(--cq-text-label);
  opacity: 0.6;
  margin-bottom: var(--cq-space-1);
}

.cq-sel__list {
  list-style: none;
  margin: 0;
  padding: 0;
  max-height: 132px;
  border: var(--cq-border);
  border-radius: var(--cq-radius-sm);
}

.cq-sel__list li {
  display: flex;
  align-items: center;
  gap: var(--cq-space-1);
  padding: 2px var(--cq-space-1) 2px 0;
}

.cq-sel__list li + li {
  border-top: var(--cq-border);
}

.cq-sel__name {
  flex: 1 1 auto;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: var(--cq-space-2);
  padding: 2px var(--cq-space-2);
  border: 0;
  background: none;
  color: inherit;
  font-size: var(--cq-text-label);
  text-align: left;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: pointer;
}

.cq-sel__name:hover {
  color: rgb(var(--v-theme-primary));
}

.cq-sel__kind {
  flex: 0 0 auto;
  width: 15px;
  height: 15px;
  display: grid;
  place-items: center;
  border-radius: 3px;
  font-size: 0.625rem;
  font-weight: 700;
  background: rgba(var(--v-theme-on-surface), 0.12);
}

.cq-sel__kind.face {
  background: rgba(var(--v-theme-primary), 0.28);
}

.cq-sel__kind.edge {
  background: rgba(var(--v-theme-success), 0.28);
}

.cq-sel__kind.vertex {
  background: rgba(var(--v-theme-warning), 0.28);
}

.cq-sel__x {
  flex: 0 0 auto;
  width: 18px;
  height: 18px;
  border: 0;
  border-radius: 3px;
  background: none;
  color: inherit;
  opacity: 0.5;
  cursor: pointer;
}

.cq-sel__x:hover {
  opacity: 1;
  color: rgb(var(--v-theme-error));
}

.cq-link {
  border: 0;
  background: none;
  color: rgb(var(--v-theme-primary));
  font-size: var(--cq-text-label);
  cursor: pointer;
}

.cq-hint {
  font-size: var(--cq-text-label);
  line-height: 1.4;
  opacity: 0.5;
}
</style>
