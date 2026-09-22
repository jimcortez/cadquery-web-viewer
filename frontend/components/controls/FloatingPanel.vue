<script lang="ts" setup>
import { ref } from "vue";
import { VTooltip } from "vuetify/lib/components/index.mjs";
import SvgIcon from "@jamescoyle/vue-icon";
import { mdiChevronDown, mdiChevronUp } from "@mdi/js";

const props = withDefaults(defineProps<{ title: string; startMinimized?: boolean }>(), {
  startMinimized: false,
});

const minimized = ref(props.startMinimized);
</script>

<template>
  <div class="cq-float" :class="{ minimized }">
    <header class="cq-float__header">
      <span class="cq-float__title">{{ title }}</span>
      <button
        type="button"
        class="cq-float__toggle"
        :aria-expanded="!minimized"
        @click="minimized = !minimized"
      >
        <v-tooltip activator="parent" location="left">
          {{ minimized ? "Expand" : "Minimize" }}
        </v-tooltip>
        <svg-icon :path="minimized ? mdiChevronDown : mdiChevronUp" type="mdi" size="16" />
      </button>
    </header>
    <div v-show="!minimized" class="cq-float__body cq-scroll cq-panel">
      <slot />
    </div>
  </div>
</template>

<style scoped>
.cq-float {
  position: absolute;
  top: var(--cq-space-3);
  right: var(--cq-space-3);
  z-index: 4;
  display: flex;
  flex-direction: column;
  width: var(--cq-float-w);
  /* Leaves the bottom-right corner clear for the orientation gizmo. */
  max-height: calc(100% - 160px);
  background: rgba(var(--v-theme-surface), 0.86);
  backdrop-filter: blur(12px);
  border: var(--cq-border);
  border-radius: var(--cq-radius-lg);
  box-shadow: var(--cq-shadow-float);
  overflow: hidden;
}

.cq-float.minimized {
  max-height: none;
}

.cq-float__header {
  display: flex;
  align-items: center;
  gap: var(--cq-space-2);
  flex: 0 0 auto;
  padding: var(--cq-space-2) var(--cq-space-2) var(--cq-space-2) var(--cq-space-3);
  border-bottom: var(--cq-border);
}

.cq-float.minimized .cq-float__header {
  border-bottom: 0;
}

.cq-float__title {
  flex: 1 1 auto;
  font-size: var(--cq-text-label);
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  opacity: 0.8;
}

.cq-float__toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border: 0;
  border-radius: var(--cq-radius-sm);
  background: transparent;
  color: rgb(var(--v-theme-on-surface));
  opacity: 0.7;
  cursor: pointer;
}

.cq-float__toggle:hover {
  background: rgba(var(--v-theme-on-surface), 0.1);
  opacity: 1;
}

.cq-float__body {
  flex: 1 1 auto;
  min-height: 0;
}
</style>
