<script lang="ts" setup>
import { ref } from "vue";
import SvgIcon from "@jamescoyle/vue-icon";
import { mdiChevronRight } from "@mdi/js";

// Deliberately plain markup rather than a v-expansion-panel wrapper: the Vuetify
// version brings padding and min-height rules that the panels then have to fight.
const props = withDefaults(defineProps<{ title: string; defaultOpen?: boolean }>(), {
  defaultOpen: true,
});

const open = ref(props.defaultOpen);
</script>

<template>
  <section class="cq-section">
    <button type="button" class="cq-section__header" :aria-expanded="open" @click="open = !open">
      <svg-icon class="cq-section__chevron" :class="{ open }" :path="mdiChevronRight" type="mdi" size="14" />
      <span class="cq-section__title">{{ title }}</span>
      <span class="cq-section__meta"><slot name="meta" /></span>
    </button>
    <div v-show="open" class="cq-section__body">
      <slot />
    </div>
  </section>
</template>

<style scoped>
.cq-section + .cq-section {
  border-top: var(--cq-border);
}

.cq-section__header {
  display: flex;
  align-items: center;
  gap: var(--cq-space-2);
  width: 100%;
  min-height: var(--cq-row-h);
  padding: var(--cq-space-1) var(--cq-space-3);
  background: none;
  border: 0;
  cursor: pointer;
  color: rgb(var(--v-theme-on-surface));
  text-align: left;
}

.cq-section__header:hover {
  background: rgba(var(--v-theme-on-surface), 0.04);
}

.cq-section__chevron {
  flex: 0 0 auto;
  opacity: 0.6;
  transition: transform 0.15s ease;
}

.cq-section__chevron.open {
  transform: rotate(90deg);
}

.cq-section__title {
  flex: 1 1 auto;
  font-size: var(--cq-text-section);
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  opacity: 0.72;
}

.cq-section__meta {
  flex: 0 0 auto;
  font-size: var(--cq-text-label);
  opacity: 0.55;
}

.cq-section__body {
  padding: var(--cq-space-2) var(--cq-space-3) var(--cq-space-3);
  display: flex;
  flex-direction: column;
  gap: var(--cq-space-1);
}
</style>
