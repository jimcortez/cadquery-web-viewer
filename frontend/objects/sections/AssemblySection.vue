<script lang="ts" setup>
import { computed } from "vue";
import SvgIcon from "@jamescoyle/vue-icon";
import { mdiRestore } from "@mdi/js";
import { VTooltip } from "vuetify/lib/components/index.mjs";
import PanelSection from "../../components/controls/PanelSection.vue";
import SettingRow from "../../components/controls/SettingRow.vue";
import ToggleControl from "../../components/controls/ToggleControl.vue";
import ColorSwatchField from "../../components/ColorSwatchField.vue";
import { useModelDisplaySettings } from "../../composables/useModelDisplaySettings";
import type { SceneObject } from "../../composables/useSceneObjects";

const props = defineProps<{ object: SceneObject; selectedPart: string | null }>();

const { getPartSettings } = useModelDisplaySettings();

const part = computed(() => props.object.parts.find((p) => p.name === props.selectedPart) ?? null);
// Reactive per-part state for the focused part (the inspector is keyed by object name,
// so this only has to follow part changes within one object).
const partState = computed(() => (part.value ? getPartSettings(props.object.name, part.value.name) : null));

const swatch = computed<string>({
  get: () => partState.value?.color ?? part.value?.color ?? "#ffffff",
  set: (v) => {
    if (partState.value) partState.value.color = v;
  },
});

const partVisible = computed<boolean>({
  get: () => partState.value?.visible ?? true,
  set: (v) => {
    if (partState.value) partState.value.visible = v;
  },
});
</script>

<template>
  <panel-section title="Assembly">
    <template #meta>{{ object.parts.length }} {{ object.parts.length === 1 ? "part" : "parts" }}</template>

    <setting-row v-if="object.tags.length" label="Tags" stacked>
      <span class="cq-tags">
        <span v-for="tag in object.tags" :key="tag" class="cq-tag">{{ tag }}</span>
      </span>
    </setting-row>

    <template v-if="part && partState">
      <setting-row label="Part">
        <span class="cq-part-name" :title="part.name">{{ part.name }}</span>
      </setting-row>
      <setting-row v-if="part.tags.length" label="Part tags" stacked>
        <span class="cq-tags">
          <span v-for="tag in part.tags" :key="tag" class="cq-tag">{{ tag }}</span>
        </span>
      </setting-row>
      <toggle-control v-model="partVisible" label="Visible" hint="Show or hide just this part" />
      <setting-row label="Color" hint="Face colour of this part; reset restores the baked colour">
        <color-swatch-field v-model="swatch" />
        <span class="cq-hex">{{ swatch }}</span>
        <template #trailing>
          <button
            type="button"
            class="cq-reset"
            :disabled="partState.color === null"
            aria-label="Reset part colour"
            @click="partState.color = null"
          >
            <v-tooltip activator="parent" location="top">Reset to baked colour</v-tooltip>
            <svg-icon :path="mdiRestore" type="mdi" size="15" />
          </button>
        </template>
      </setting-row>
    </template>
    <p v-else-if="object.parts.length > 1" class="cq-hint">
      Select a part in the list (or pick one in the viewport) to hide or recolour it.
    </p>
  </panel-section>
</template>

<style scoped>
.cq-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--cq-space-1);
}

.cq-tag {
  font-size: 0.6875rem;
  line-height: 1.4;
  padding: 1px 6px;
  border-radius: 999px;
  background: rgba(var(--v-theme-on-surface), 0.1);
  white-space: nowrap;
}

.cq-part-name {
  font-size: var(--cq-text-body);
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.cq-hex {
  margin-left: var(--cq-space-2);
  font-size: var(--cq-text-label);
  font-variant-numeric: tabular-nums;
  opacity: 0.55;
  text-transform: uppercase;
}

.cq-reset {
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

.cq-reset:hover:not(:disabled) {
  background: rgba(var(--v-theme-on-surface), 0.1);
  opacity: 1;
}

.cq-reset:disabled {
  opacity: 0.25;
  cursor: default;
}

.cq-hint {
  margin: 0;
  padding: var(--cq-space-1) 0;
  font-size: var(--cq-text-label);
  line-height: 1.5;
  opacity: 0.55;
}
</style>
