<script lang="ts" setup>
import { VTooltip } from "vuetify/lib/components/index.mjs";
import SvgIcon from "@jamescoyle/vue-icon";

export type Segment = {
  value: number;
  icon: string;
  label: string;
  /** Shown after the label in the tooltip, e.g. a feature count. */
  badge?: number | string;
  disabled?: boolean;
};

const model = defineModel<number[]>({ required: true });

withDefaults(defineProps<{ segments: readonly Segment[]; disabled?: boolean }>(), {
  disabled: false,
});

function toggle(value: number) {
  const next = model.value.includes(value)
    ? model.value.filter((v) => v !== value)
    : [...model.value, value];
  model.value = next;
}
</script>

<template>
  <div class="cq-segmented" role="group">
    <button
      v-for="segment in segments"
      :key="segment.value"
      type="button"
      class="cq-segmented__btn"
      :class="{ active: model.includes(segment.value) }"
      :disabled="disabled || segment.disabled"
      :aria-pressed="model.includes(segment.value)"
      @click.stop="toggle(segment.value)"
    >
      <v-tooltip activator="parent" location="top">
        {{ segment.label }}<template v-if="segment.badge !== undefined"> ({{ segment.badge }})</template>
      </v-tooltip>
      <svg-icon :path="segment.icon" type="mdi" size="15" />
    </button>
  </div>
</template>

<style scoped>
.cq-segmented {
  display: inline-flex;
  border: var(--cq-border);
  border-radius: var(--cq-radius-sm);
  overflow: hidden;
}

.cq-segmented__btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 22px;
  border: 0;
  background: transparent;
  color: rgb(var(--v-theme-on-surface));
  opacity: 0.45;
  cursor: pointer;
}

.cq-segmented__btn + .cq-segmented__btn {
  border-left: var(--cq-border);
}

.cq-segmented__btn:hover:not(:disabled) {
  background: rgba(var(--v-theme-on-surface), 0.08);
  opacity: 0.8;
}

.cq-segmented__btn.active {
  background: rgba(var(--v-theme-primary), 0.22);
  color: rgb(var(--v-theme-primary));
  opacity: 1;
}

.cq-segmented__btn:disabled {
  opacity: 0.2;
  cursor: not-allowed;
}
</style>
