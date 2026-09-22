<script lang="ts" setup>
import { VSelect } from "vuetify/lib/components/index.mjs";
import SettingRow from "./SettingRow.vue";

type Option = { title: string; value: string | number };

const model = defineModel<string | number>({ required: true });

withDefaults(
  defineProps<{
    label: string;
    items: readonly Option[];
    disabled?: boolean;
    hint?: string;
  }>(),
  { disabled: false },
);
</script>

<template>
  <setting-row :label="label" :hint="hint" wrap-control>
    <v-select
      v-model="model"
      :items="items as Option[]"
      item-title="title"
      item-value="value"
      :disabled="disabled"
      hide-details
      density="compact"
      variant="outlined"
      class="cq-select"
    />
  </setting-row>
</template>

<style scoped>
.cq-select {
  flex: 1 1 auto;
  font-size: var(--cq-text-label);
}

.cq-select :deep(.v-field) {
  border-radius: var(--cq-radius-sm);
  font-size: var(--cq-text-label);
}

.cq-select :deep(.v-field__input) {
  min-height: var(--cq-control-h);
  padding-top: 0;
  padding-bottom: 0;
}
</style>
