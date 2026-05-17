<script lang="ts" setup>
import SceneSettingsPanel from "./SceneSettingsPanel.vue";
import type ModelViewerWrapper from "../viewer/ModelViewerWrapper.vue";

defineProps<{
  viewer: InstanceType<typeof ModelViewerWrapper> | null;
}>();
</script>

<template>
  <scene-settings-panel :viewer="viewer" />
</template>
