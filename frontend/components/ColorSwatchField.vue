<script lang="ts" setup>
import { Chrome } from "@ckpack/vue-color";
import { VMenu, VSheet } from "vuetify/lib/components/index.mjs";

const model = defineModel<string>({ required: true });

withDefaults(
  defineProps<{
    label?: string;
    disabled?: boolean;
  }>(),
  { disabled: false },
);

function onColorUpdate(payload: { hex?: string }) {
  if (payload.hex) model.value = payload.hex;
}
</script>

<template>
  <div class="color-swatch-field">
    <span v-if="label" class="text-caption mr-2">{{ label }}</span>
    <v-menu :close-on-content-click="false" location="bottom">
      <template #activator="{ props: menuProps }">
        <button
          type="button"
          class="swatch"
          :style="{ backgroundColor: model }"
          :disabled="disabled"
          v-bind="menuProps"
          :aria-label="label ?? 'Pick color'"
        />
      </template>
      <v-sheet class="pa-2">
        <Chrome :model-value="model" @update:model-value="onColorUpdate" />
      </v-sheet>
    </v-menu>
  </div>
</template>

<style scoped>
.color-swatch-field {
  display: flex;
  align-items: center;
}

.swatch {
  width: 24px;
  height: 24px;
  /* Theme token, not a hardcoded white: a white swatch was invisible on the
     light surface. */
  border: 1px solid rgba(var(--v-border-color), 0.9);
  border-radius: var(--cq-radius-sm, 4px);
  cursor: pointer;
  padding: 0;
}

.swatch:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
</style>
