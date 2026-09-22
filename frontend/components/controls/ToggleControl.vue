<script lang="ts" setup>
import { VSwitch } from "vuetify/lib/components/index.mjs";
import SettingRow from "./SettingRow.vue";

const model = defineModel<boolean>({ required: true });

withDefaults(defineProps<{ label: string; disabled?: boolean; hint?: string }>(), {
  disabled: false,
});
</script>

<template>
  <setting-row :label="label" :hint="hint" wrap-control>
    <v-switch
      v-model="model"
      :disabled="disabled"
      hide-details
      density="compact"
      color="primary"
      class="cq-switch"
    />
  </setting-row>
</template>

<style scoped>
.cq-switch {
  flex: 0 0 auto;
}

.cq-switch :deep(.v-selection-control) {
  min-height: 0;
}
</style>
