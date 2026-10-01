<script lang="ts" setup>
import { computed } from "vue";
import { VTooltip } from "vuetify/lib/components/index.mjs";
import SvgIcon from "@jamescoyle/vue-icon";
import { mdiEye, mdiEyeOff } from "@mdi/js";
import ColorSwatchField from "../components/ColorSwatchField.vue";
import type { ScenePart } from "../composables/useSceneObjects";
import { useModelDisplaySettings } from "../composables/useModelDisplaySettings";

const props = defineProps<{
  objectName: string;
  part: ScenePart;
  selected: boolean;
  /** The owning assembly's master visibility; a hidden assembly greys out its parts. */
  parentVisible: boolean;
}>();
const emit = defineEmits<{ select: [] }>();

const { getPartSettings } = useModelDisplaySettings();
const state = getPartSettings(props.objectName, props.part.name);

// The swatch shows the override when set, else the colour the tessellator baked in.
const swatch = computed<string>({
  get: () => state.color ?? props.part.color ?? "#ffffff",
  set: (v) => {
    state.color = v;
  },
});
</script>

<template>
  <div
    class="cq-part"
    :class="{ selected, hidden: !state.visible || !parentVisible }"
    role="button"
    tabindex="0"
    @click="emit('select')"
    @keydown.enter="emit('select')"
    @keydown.space.prevent="emit('select')"
  >
    <button
      type="button"
      class="cq-part__icon"
      :aria-label="state.visible ? `Hide ${part.name}` : `Show ${part.name}`"
      @click.stop="state.visible = !state.visible"
    >
      <v-tooltip activator="parent" location="top">
        {{ state.visible ? "Hide part" : "Show part" }}
      </v-tooltip>
      <svg-icon :path="state.visible ? mdiEye : mdiEyeOff" type="mdi" size="14" />
    </button>

    <span class="cq-part__swatch" @click.stop>
      <color-swatch-field v-model="swatch" :label="undefined" />
    </span>

    <span class="cq-part__name" :title="part.name">{{ part.name }}</span>

    <span class="cq-part__counts">
      <v-tooltip activator="parent" location="top">
        {{ part.faceCount }} faces · {{ part.edgeCount }} edges · {{ part.vertexCount }} vertices
      </v-tooltip>
      {{ part.faceCount }}<i>F</i> {{ part.edgeCount }}<i>E</i> {{ part.vertexCount }}<i>V</i>
    </span>
  </div>
</template>

<style scoped>
.cq-part {
  display: flex;
  align-items: center;
  gap: var(--cq-space-2);
  min-height: calc(var(--cq-list-row-h) - 4px);
  /* Indented under the assembly row; the accent border matches the parent. */
  padding: 0 var(--cq-space-2) 0 calc(var(--cq-space-1) + 26px);
  border-left: 2px solid transparent;
  cursor: pointer;
  user-select: none;
}

.cq-part:hover {
  background: rgba(var(--v-theme-on-surface), 0.05);
}

.cq-part.selected {
  background: rgba(var(--v-theme-primary), 0.14);
  border-left-color: rgb(var(--v-theme-primary));
}

.cq-part:focus-visible {
  outline: 1px solid rgb(var(--v-theme-primary));
  outline-offset: -1px;
}

.cq-part.hidden .cq-part__name {
  opacity: 0.45;
  text-decoration: line-through;
}

.cq-part__icon {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border: 0;
  border-radius: var(--cq-radius-sm);
  background: transparent;
  color: rgb(var(--v-theme-on-surface));
  opacity: 0.62;
  cursor: pointer;
}

.cq-part__icon:hover {
  background: rgba(var(--v-theme-on-surface), 0.1);
  opacity: 1;
}

.cq-part__swatch {
  flex: 0 0 auto;
  display: flex;
}

.cq-part__swatch :deep(.swatch) {
  width: 14px;
  height: 14px;
}

.cq-part__name {
  flex: 1 1 auto;
  min-width: 0;
  font-size: var(--cq-text-label);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.cq-part__counts {
  flex: 0 0 auto;
  font-size: 0.625rem;
  font-variant-numeric: tabular-nums;
  opacity: 0.45;
  white-space: nowrap;
}

.cq-part__counts i {
  font-style: normal;
  opacity: 0.7;
  margin-right: 3px;
}
</style>
