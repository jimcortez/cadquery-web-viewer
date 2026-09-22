<script lang="ts" setup>
import { computed } from "vue";
import { VSlider } from "vuetify/lib/components/index.mjs";
import SettingRow from "./SettingRow.vue";

const model = defineModel<number>({ required: true });

const props = withDefaults(
  defineProps<{
    label: string;
    min?: number;
    max?: number;
    step?: number;
    /** Decimal places in the readout; inferred from `step` when omitted. */
    precision?: number;
    disabled?: boolean;
    hint?: string;
  }>(),
  { min: 0, max: 1, step: 0.01, disabled: false },
);

const decimals = computed(() => {
  if (props.precision !== undefined) return props.precision;
  const s = String(props.step);
  const dot = s.indexOf(".");
  return dot === -1 ? 0 : s.length - dot - 1;
});

const display = computed(() => model.value.toFixed(decimals.value));

function commit(raw: string) {
  const parsed = Number(raw);
  if (Number.isNaN(parsed)) return;
  model.value = Math.min(props.max, Math.max(props.min, parsed));
}
</script>

<template>
  <setting-row :label="label" :hint="hint" wrap-control>
    <v-slider
      v-model="model"
      :min="min"
      :max="max"
      :step="step"
      :disabled="disabled"
      hide-details
      density="compact"
      class="cq-slider"
    />
    <template #trailing>
      <!-- Every slider shows and accepts a number; the old panels showed neither. -->
      <input
        class="cq-slider__value"
        type="text"
        inputmode="decimal"
        :value="display"
        :disabled="disabled"
        :aria-label="`${label} value`"
        @change="commit(($event.target as HTMLInputElement).value)"
        @blur="($event.target as HTMLInputElement).value = display"
      />
      <slot name="after" />
    </template>
  </setting-row>
</template>

<style scoped>
.cq-slider {
  flex: 1 1 auto;
}

.cq-slider__value {
  width: 52px;
  height: 24px;
  padding: 0 var(--cq-space-1);
  text-align: right;
  font-size: var(--cq-text-label);
  font-variant-numeric: tabular-nums;
  color: rgb(var(--v-theme-on-surface));
  background: rgba(var(--v-theme-on-surface), 0.06);
  border: 1px solid transparent;
  border-radius: var(--cq-radius-sm);
}

.cq-slider__value:hover:not(:disabled) {
  border-color: rgba(var(--v-border-color), 0.6);
}

.cq-slider__value:focus {
  outline: none;
  border-color: rgb(var(--v-theme-primary));
}

.cq-slider__value:disabled {
  opacity: 0.4;
}
</style>
