<script lang="ts" setup>
import { VTooltip } from "vuetify/lib/components/index.mjs";
import SvgIcon from "@jamescoyle/vue-icon";
import { mdiCrosshairsGps, mdiCursorDefaultClick } from "@mdi/js";
import { useCameraTools } from "../composables/useCameraTools";
import { useSelectionTools } from "../composables/useSelectionTools";

// The handful of actions used constantly while inspecting, kept next to the model
// rather than buried in the settings panel.
const { projection, toggleProjection, centerCamera } = useCameraTools();
const { selectionEnabled, toggleSelection } = useSelectionTools();
</script>

<template>
  <div class="cq-vptools">
    <button type="button" class="cq-vptools__btn wide" @click="toggleProjection">
      <v-tooltip activator="parent" location="bottom">
        Toggle projection (P) — currently {{ projection }}
      </v-tooltip>
      {{ projection === "perspective" ? "PERSP" : "ORTHO" }}
    </button>
    <button type="button" class="cq-vptools__btn" aria-label="Recenter camera" @click="centerCamera">
      <v-tooltip activator="parent" location="bottom">Recenter &amp; fit (C)</v-tooltip>
      <svg-icon :path="mdiCrosshairsGps" type="mdi" size="16" />
    </button>
    <button
      type="button"
      class="cq-vptools__btn"
      :class="{ active: selectionEnabled }"
      aria-label="Toggle selection mode"
      @click="toggleSelection"
    >
      <v-tooltip activator="parent" location="bottom">
        {{ selectionEnabled ? "Disable" : "Enable" }} selection mode (S)
      </v-tooltip>
      <svg-icon :path="mdiCursorDefaultClick" type="mdi" size="16" />
    </button>
  </div>
</template>

<style scoped>
.cq-vptools {
  position: absolute;
  top: var(--cq-space-3);
  left: var(--cq-vp-left, var(--cq-space-3));
  z-index: 3;
  display: flex;
  background: rgba(var(--v-theme-surface), 0.86);
  backdrop-filter: blur(12px);
  border: var(--cq-border);
  border-radius: var(--cq-radius-md);
  overflow: hidden;
}

.cq-vptools__btn {
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 30px;
  height: 28px;
  padding: 0 var(--cq-space-1);
  border: 0;
  background: transparent;
  color: rgb(var(--v-theme-on-surface));
  font-size: 0.625rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  opacity: 0.72;
  cursor: pointer;
}

.cq-vptools__btn.wide {
  min-width: 46px;
}

.cq-vptools__btn + .cq-vptools__btn {
  border-left: var(--cq-border);
}

.cq-vptools__btn:hover {
  background: rgba(var(--v-theme-on-surface), 0.08);
  opacity: 1;
}

.cq-vptools__btn.active {
  background: rgba(var(--v-theme-primary), 0.24);
  color: rgb(var(--v-theme-primary));
  opacity: 1;
}
</style>
