<script lang="ts" setup>
import { computed } from "vue";
import { VTooltip } from "vuetify/lib/components/index.mjs";
import SvgIcon from "@jamescoyle/vue-icon";
import { mdiChevronLeft, mdiPlus } from "@mdi/js";
import { useSceneObjects } from "../composables/useSceneObjects";
import ObjectListItem from "./ObjectListItem.vue";
import ObjectInspector from "./ObjectInspector.vue";

const emit = defineEmits<{ add: []; remove: [string]; collapse: [] }>();

const { objects, selectedObjectName, select } = useSceneObjects();

const selectedObject = computed(
  () => objects.value.find((o) => o.name === selectedObjectName.value) ?? null,
);
</script>

<template>
  <aside class="cq-rail cq-panel">
    <header class="cq-rail__header">
      <span class="cq-rail__title">Objects</span>
      <span class="cq-rail__count">{{ objects.length }}</span>
      <button type="button" class="cq-rail__btn" aria-label="Add objects" @click="emit('add')">
        <v-tooltip activator="parent" location="bottom">Add objects</v-tooltip>
        <svg-icon :path="mdiPlus" type="mdi" size="18" />
      </button>
      <button type="button" class="cq-rail__btn" aria-label="Collapse panel" @click="emit('collapse')">
        <v-tooltip activator="parent" location="bottom">Collapse panel</v-tooltip>
        <svg-icon :path="mdiChevronLeft" type="mdi" size="18" />
      </button>
    </header>

    <div class="cq-rail__list cq-scroll">
      <p v-if="objects.length === 0" class="cq-rail__empty">
        Nothing loaded yet. Use <strong>+</strong> to add objects, or publish from Python with
        <code>show()</code>.
      </p>
      <object-list-item
        v-for="object in objects"
        :key="object.name"
        :object="object"
        :selected="object.name === selectedObjectName"
        @select="select(object.name)"
        @remove="emit('remove', object.name)"
      />
    </div>

    <div class="cq-rail__inspector">
      <object-inspector v-if="selectedObject" :key="selectedObject.name" :object="selectedObject" />
      <p v-else class="cq-rail__empty">Select an object to edit its settings.</p>
    </div>
  </aside>
</template>

<style scoped>
.cq-rail {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  width: var(--cq-rail-w);
  background: rgb(var(--v-theme-surface));
  border-right: var(--cq-border);
}

.cq-rail__header {
  display: flex;
  align-items: center;
  gap: var(--cq-space-2);
  flex: 0 0 auto;
  height: 44px;
  padding: 0 var(--cq-space-2) 0 var(--cq-space-3);
  border-bottom: var(--cq-border);
}

.cq-rail__title {
  font-size: var(--cq-text-label);
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  opacity: 0.85;
}

.cq-rail__count {
  flex: 1 1 auto;
  font-size: var(--cq-text-label);
  font-variant-numeric: tabular-nums;
  opacity: 0.45;
}

.cq-rail__btn {
  flex: 0 0 auto;
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

.cq-rail__btn:hover {
  background: rgba(var(--v-theme-on-surface), 0.1);
  opacity: 1;
}

/* The list takes what it needs up to a share of the rail; the inspector gets the
   rest, so a long object list can never squeeze the settings out of view. */
.cq-rail__list {
  flex: 0 1 auto;
  max-height: 42%;
  padding: var(--cq-space-1) 0;
  border-bottom: var(--cq-border);
}

.cq-rail__inspector {
  flex: 1 1 auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.cq-rail__empty {
  padding: var(--cq-space-4) var(--cq-space-3);
  font-size: var(--cq-text-label);
  line-height: 1.5;
  opacity: 0.55;
}

.cq-rail__empty code {
  font-size: 0.75em;
  padding: 1px 4px;
  border-radius: 3px;
  background: rgba(var(--v-theme-on-surface), 0.1);
}
</style>
