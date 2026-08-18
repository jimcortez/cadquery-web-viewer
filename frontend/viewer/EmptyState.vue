<script lang="ts" setup>
import SvgIcon from "@jamescoyle/vue-icon";
import { mdiCubeOutline, mdiPlus } from "@mdi/js";

defineProps<{ preloading: string[] }>();
const emit = defineEmits<{ add: [] }>();
</script>

<template>
  <div class="cq-empty cq-scroll">
    <div class="cq-empty__card">
      <svg-icon class="cq-empty__icon" :path="mdiCubeOutline" type="mdi" size="44" />
      <h1 class="cq-empty__title">No objects in the scene</h1>
      <p class="cq-empty__body">
        Publish geometry from Python with <code>show()</code>, drop a
        <code>.glb</code> / <code>.gltf</code> file anywhere on this page, or add one from the
        server cache.
      </p>
      <button type="button" class="cq-empty__cta" @click="emit('add')">
        <svg-icon :path="mdiPlus" type="mdi" size="16" />
        Add objects
      </button>

      <div v-if="preloading.length > 0" class="cq-empty__preload">
        <span class="cq-empty__preload-title">Still trying to load</span>
        <span v-for="url in preloading" :key="url" class="cq-empty__preload-item">{{ url }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.cq-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: var(--cq-space-5);
}

.cq-empty__card {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  max-width: 380px;
}

.cq-empty__icon {
  opacity: 0.3;
  margin-bottom: var(--cq-space-3);
}

.cq-empty__title {
  margin: 0 0 var(--cq-space-2);
  font-size: 1rem;
  font-weight: 600;
}

.cq-empty__body {
  margin: 0 0 var(--cq-space-4);
  font-size: var(--cq-text-body);
  line-height: 1.6;
  opacity: 0.62;
}

.cq-empty__body code {
  font-size: 0.85em;
  padding: 1px 5px;
  border-radius: 3px;
  background: rgba(var(--v-theme-on-surface), 0.1);
}

.cq-empty__cta {
  display: inline-flex;
  align-items: center;
  gap: var(--cq-space-2);
  padding: var(--cq-space-2) var(--cq-space-4);
  font-size: var(--cq-text-body);
  font-weight: 600;
  color: rgb(var(--v-theme-on-surface));
  background: rgba(var(--v-theme-primary), 0.9);
  border: 0;
  border-radius: var(--cq-radius-md);
  cursor: pointer;
}

.cq-empty__cta:hover {
  background: rgb(var(--v-theme-primary));
}

.cq-empty__preload {
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin-top: var(--cq-space-5);
  font-size: var(--cq-text-label);
  opacity: 0.45;
}

.cq-empty__preload-title {
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  font-size: var(--cq-text-section);
}

.cq-empty__preload-item {
  word-break: break-all;
}
</style>
