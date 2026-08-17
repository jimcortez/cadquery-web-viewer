<script lang="ts" setup>
// The one row primitive every parameter uses. The fixed label column is what
// makes controls line up across unrelated panels.
//
// `wrapControl` renders the row as a <label> so the visible text implicitly
// labels the control inside it — Vuetify puts its real <input> deep in its own
// tree, so a sibling <label for=...> has nothing stable to point at. Rows whose
// control is a button (or a group of them) must leave it off, or clicking
// anywhere in the row would activate the first button.
withDefaults(
  defineProps<{ label?: string; hint?: string; stacked?: boolean; wrapControl?: boolean }>(),
  { stacked: false, wrapControl: false },
);
</script>

<template>
  <component :is="wrapControl ? 'label' : 'div'" class="cq-row" :class="{ stacked }">
    <span v-if="label" class="cq-row__label" :title="hint ?? label">{{ label }}</span>
    <span class="cq-row__control">
      <slot />
    </span>
    <span v-if="$slots.trailing" class="cq-row__trailing">
      <slot name="trailing" />
    </span>
  </component>
</template>

<style scoped>
.cq-row {
  display: flex;
  align-items: center;
  gap: var(--cq-space-2);
  min-height: var(--cq-row-h);
}

.cq-row.stacked {
  flex-direction: column;
  align-items: stretch;
  gap: var(--cq-space-1);
}

.cq-row__label {
  flex: 0 0 var(--cq-label-w);
  width: var(--cq-label-w);
  font-size: var(--cq-text-label);
  opacity: 0.78;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.cq-row.stacked .cq-row__label {
  flex: 0 0 auto;
  width: auto;
}

.cq-row__control {
  flex: 1 1 auto;
  min-width: 0;
  display: flex;
  align-items: center;
}

.cq-row__trailing {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
}
</style>
