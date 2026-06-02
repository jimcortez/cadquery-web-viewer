<script lang="ts" setup>
import { ref } from "vue";
import {
  VBtn,
  VDivider,
  VNavigationDrawer,
  VSpacer,
  VToolbar,
  VToolbarItems,
} from "vuetify/lib/components/index.mjs";
import { mdiChevronRight, mdiClose } from "@mdi/js";
import SvgIcon from "@jamescoyle/vue-icon";

const props = defineProps<{
  openedInit: boolean;
  width: number;
}>();

const opened = ref(props.openedInit);
</script>

<template>
  <v-btn class="open-button left" icon @click="opened = !opened">
    <svg-icon :path="mdiChevronRight" type="mdi" />
  </v-btn>
  <v-navigation-drawer v-model="opened" location="left" :width="props.width" permanent class="left-sidebar-drawer">
    <div class="left-sidebar-stack">
      <section class="sidebar-pane models-pane">
        <v-toolbar density="compact" class="pane-toolbar models-toolbar">
          <div class="pane-heading">
            <span class="pane-title">Models</span>
            <span class="pane-subtitle">Loaded geometry</span>
          </div>
          <v-spacer />
          <v-toolbar-items>
            <slot name="models-toolbar-items" />
            <v-btn icon @click="opened = false">
              <svg-icon :path="mdiClose" type="mdi" />
            </v-btn>
          </v-toolbar-items>
        </v-toolbar>
        <div class="pane-body models-body">
          <slot name="models" />
        </div>
      </section>

      <v-divider class="pane-split" thickness="2" />

      <section class="sidebar-pane scene-pane">
        <v-toolbar density="compact" class="pane-toolbar scene-toolbar">
          <div class="pane-heading">
            <span class="pane-title">Scene</span>
            <span class="pane-subtitle">Viewer &amp; overlays</span>
          </div>
        </v-toolbar>
        <div class="pane-body scene-body">
          <slot name="scene" />
        </div>
      </section>
    </div>
  </v-navigation-drawer>
</template>

<style scoped>
.open-button {
  position: absolute;
  bottom: 0;
  border-radius: 0;
}

.open-button.left {
  left: 0;
}

.left-sidebar-drawer :deep(.v-navigation-drawer__content) {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.left-sidebar-stack {
  display: flex;
  flex-direction: column;
  flex: 1 1 auto;
  min-height: 0;
  height: 100%;
}

.sidebar-pane {
  display: flex;
  flex-direction: column;
  flex: 1 1 50%;
  min-height: 0;
  overflow: hidden;
}

.models-pane {
  background: rgb(var(--v-theme-surface));
}

.scene-pane {
  background: rgb(var(--v-theme-surface-variant));
}

.pane-split {
  flex: 0 0 auto;
  opacity: 0.85;
}

.pane-toolbar {
  flex: 0 0 auto;
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.models-toolbar {
  min-height: 52px !important;
}

.scene-toolbar {
  min-height: 48px !important;
}

.pane-heading {
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding-left: 12px;
  min-width: 0;
}

.pane-title {
  font-size: 1rem;
  font-weight: 600;
  letter-spacing: 0.02em;
  line-height: 1.25;
}

.pane-subtitle {
  font-size: 0.7rem;
  font-weight: 400;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  opacity: 0.65;
  line-height: 1.2;
}

.pane-body {
  flex: 1 1 auto;
  min-height: 0;
  overflow-x: hidden;
  overflow-y: auto;
}

.scene-body {
  padding-top: 4px;
}
</style>

<style>
.left-sidebar-drawer .mdi-chevron-down,
.left-sidebar-drawer .mdi-menu-down {
  background-image: url('data:image/svg+xml;charset=UTF-8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="white"><path d="M7 10l5 5 5-5H7z"/></svg>');
}

.left-sidebar-drawer .mdi-chevron-up,
.left-sidebar-drawer .mdi-menu-up {
  background-image: url('data:image/svg+xml;charset=UTF-8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="white"><path d="M7 14l5-5 5 5H7z"/></svg>');
}

.left-sidebar-drawer .v-expansion-panel-text__wrapper {
  padding: 0 !important;
}

.left-sidebar-drawer .v-overlay--active > .v-overlay__content {
  display: block !important;
}

.left-sidebar-drawer .scene-subsection-title {
  font-size: 0.8125rem !important;
  font-weight: 600 !important;
  min-height: 36px !important;
}

.left-sidebar-drawer .models-body .v-expansion-panel-title {
  font-size: 0.875rem;
  font-weight: 500;
}
</style>
