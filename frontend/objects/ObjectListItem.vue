<script lang="ts" setup>
import { VTooltip } from "vuetify/lib/components/index.mjs";
import SvgIcon from "@jamescoyle/vue-icon";
import { mdiDelete, mdiEye, mdiEyeOff } from "@mdi/js";
import type { SceneObject } from "../composables/useSceneObjects";
import { useModelDisplaySettings } from "../composables/useModelDisplaySettings";

const props = defineProps<{ object: SceneObject; selected: boolean }>();
const emit = defineEmits<{ select: []; remove: [] }>();

const { getSettings } = useModelDisplaySettings();
const display = getSettings(props.object.name);
</script>

<template>
  <div
    class="cq-obj"
    :class="{ selected, hidden: !display.visible }"
    role="button"
    tabindex="0"
    @click="emit('select')"
    @keydown.enter="emit('select')"
    @keydown.space.prevent="emit('select')"
  >
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

    <span class="cq-obj__name" :title="object.name">{{ object.name }}</span>

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
      <v-tooltip activator="parent" location="top">Remove from scene</v-tooltip>
      <svg-icon :path="mdiDelete" type="mdi" size="15" />
    </button>
  </div>
</template>

<style scoped>
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
