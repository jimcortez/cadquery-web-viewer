<script setup lang="ts">
import {mdiLockQuestion} from "@mdi/js";
import {VBtn, VTooltip} from "vuetify/lib/components/index.mjs";
// @ts-expect-error
import SvgIcon from "@jamescoyle/vue-icon";

// @ts-expect-error
let isSmallBuild = typeof __GLB_PREVIEW_SMALL_BUILD__ !== 'undefined' && __GLB_PREVIEW_SMALL_BUILD__;

function clickedButton() { // Open full build (same deployment, full bundle)
  const u = new URL(".", window.location.href);
  u.search = window.location.search;
  u.hash = window.location.hash;
  window.open(u.href, "_blank");
}
</script>

<template>
  <!--  @ts-ignore-->
  <!-- Include the children as this is a full build -->
  <slot v-if="!isSmallBuild"/>
  <!-- A small info button saying that a feature is missing, and linking to the main build -->
  <v-btn v-else icon @click="clickedButton" base-color="#a00" style="margin: auto; display: block;">
    <v-tooltip activator="parent">
      This feature is not available in the small build.<br/>
      Click to go to the main build.
    </v-tooltip>
    <svg-icon :path="mdiLockQuestion" type="mdi"/>
  </v-btn>
</template>

<style scoped>

</style>