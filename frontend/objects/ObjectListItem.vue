<script lang="ts" setup>
import { computed, ref } from "vue";
import { VTooltip } from "vuetify/lib/components/index.mjs";
import SvgIcon from "@jamescoyle/vue-icon";
import { mdiChevronRight, mdiDelete, mdiEye, mdiEyeOff } from "@mdi/js";
import type { SceneObject } from "../composables/useSceneObjects";
import { useModelDisplaySettings } from "../composables/useModelDisplaySettings";
import ObjectPartItem from "./ObjectPartItem.vue";

const props = defineProps<{
  object: SceneObject;
  selected: boolean;
  /** Focused part of this object, or null when the whole assembly is selected. */
  selectedPart: string | null;
}>();
const emit = defineEmits<{ select: []; remove: []; selectPart: [string] }>();

const { getSettings } = useModelDisplaySettings();
const display = getSettings(props.object.name);

// Only assemblies with several parts get a tree; a one-part object reads as a plain row.
const hasParts = computed(() => props.object.parts.length > 1);
const expanded = ref(true);
</script>

<template>
  <div class="cq-obj-group">
  <div
    class="cq-obj"
    :class="{ selected: selected && selectedPart === null, hidden: !display.visible }"
    role="button"
    tabindex="0"
    @click="emit('select')"
    @keydown.enter="emit('select')"
    @keydown.space.prevent="emit('select')"
  >
    <button
      v-if="hasParts"
      type="button"
      class="cq-obj__icon cq-obj__chevron"
      :class="{ open: expanded }"
      :aria-label="expanded ? `Collapse ${object.name}` : `Expand ${object.name}`"
      :aria-expanded="expanded"
      @click.stop="expanded = !expanded"
    >
      <svg-icon :path="mdiChevronRight" type="mdi" size="16" />
    </button>
    <span v-else class="cq-obj__chevron-gap" />

    <button
      type="button"
      class="cq-obj__icon"
      :aria-label="display.visible ? `Hide ${object.name}` : `Show ${object.name}`"
      @click.stop="display.visible = !display.visible"
    >
      <v-tooltip activator="parent" location="top">
        {{ display.visible ? "Hide" : "Show" }}
      </v-tooltip>
      <svg-icon :path="display.visible ? mdiEye : mdiEyeOff" type="mdi" size="16" />
    </button>

    <span class="cq-obj__name" :title="object.name">
      {{ object.name }}
      <small v-if="hasParts" class="cq-obj__parts">{{ object.parts.length }}</small>
    </span>

    <span class="cq-obj__counts">
      <v-tooltip activator="parent" location="top">
        {{ object.faceCount }} faces · {{ object.edgeCount }} edges · {{ object.vertexCount }} vertices
      </v-tooltip>
      {{ object.faceCount }}<i>F</i> {{ object.edgeCount }}<i>E</i> {{ object.vertexCount }}<i>V</i>
    </span>

    <button
      type="button"
      class="cq-obj__icon danger"
      :aria-label="`Remove ${object.name}`"
      @click.stop="emit('remove')"
    >
      <v-tooltip activator="parent" location="top">
        {{ hasParts ? "Remove the whole assembly from the scene" : "Remove from scene" }}
      </v-tooltip>
      <svg-icon :path="mdiDelete" type="mdi" size="15" />
    </button>
  </div>

  <div v-if="hasParts && expanded" class="cq-obj__children" role="group" :aria-label="`Parts of ${object.name}`">
    <object-part-item
      v-for="part in object.parts"
      :key="part.name"
      :object-name="object.name"
      :part="part"
      :selected="selected && selectedPart === part.name"
      :parent-visible="display.visible"
      @select="emit('selectPart', part.name)"
    />
  </div>
  </div>
</template>

<style scoped>
.cq-obj-group {
  display: flex;
  flex-direction: column;
}

.cq-obj__children {
  display: flex;
  flex-direction: column;
}

.cq-obj__chevron svg {
  transition: transform 120ms ease;
}

.cq-obj__chevron.open svg {
  transform: rotate(90deg);
}

.cq-obj__chevron-gap {
  flex: 0 0 auto;
  width: 24px;
}

.cq-obj__parts {
  margin-left: 4px;
  font-size: 0.625rem;
  font-variant-numeric: tabular-nums;
  padding: 0 5px;
  border-radius: 999px;
  background: rgba(var(--v-theme-on-surface), 0.1);
  opacity: 0.8;
}

.cq-obj {
  display: flex;
  align-items: center;
  gap: var(--cq-space-2);
  min-height: var(--cq-list-row-h);
  padding: 0 var(--cq-space-2) 0 var(--cq-space-1);
  /* Reserved so the selected accent does not shift the row. */
  border-left: 2px solid transparent;
  cursor: pointer;
  user-select: none;
}

.cq-obj:hover {
  background: rgba(var(--v-theme-on-surface), 0.05);
}

.cq-obj.selected {
  background: rgba(var(--v-theme-primary), 0.14);
  border-left-color: rgb(var(--v-theme-primary));
}

.cq-obj:focus-visible {
  outline: 1px solid rgb(var(--v-theme-primary));
  outline-offset: -1px;
}

.cq-obj.hidden .cq-obj__name {
  opacity: 0.45;
  text-decoration: line-through;
}

.cq-obj__icon {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border: 0;
  border-radius: var(--cq-radius-sm);
  background: transparent;
  color: rgb(var(--v-theme-on-surface));
  opacity: 0.62;
  cursor: pointer;
}

.cq-obj__icon:hover {
  background: rgba(var(--v-theme-on-surface), 0.1);
  opacity: 1;
}

.cq-obj__icon.danger:hover {
  color: rgb(var(--v-theme-error));
}

.cq-obj__name {
  flex: 1 1 auto;
  min-width: 0;
  font-size: var(--cq-text-body);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.cq-obj__counts {
  flex: 0 0 auto;
  font-size: 0.6875rem;
  font-variant-numeric: tabular-nums;
  opacity: 0.5;
  white-space: nowrap;
}

.cq-obj__counts i {
  font-style: normal;
  opacity: 0.7;
  margin-right: 3px;
}
</style>
