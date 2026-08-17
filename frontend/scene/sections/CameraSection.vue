<script lang="ts" setup>
import PanelSection from "../../components/controls/PanelSection.vue";
import SettingRow from "../../components/controls/SettingRow.vue";
import SliderControl from "../../components/controls/SliderControl.vue";
import ToggleControl from "../../components/controls/ToggleControl.vue";
import { useCameraTools } from "../../composables/useCameraTools";
import { useViewerSceneSettings } from "../../composables/useViewerSceneSettings";

const { scene } = useViewerSceneSettings();
const { projection, toggleProjection, centerCamera } = useCameraTools();
</script>

<template>
  <panel-section title="Camera">
    <setting-row label="Projection">
      <div class="cq-choice">
        <button
          type="button"
          :class="{ active: projection === 'perspective' }"
          @click="projection !== 'perspective' && toggleProjection()"
        >
          Perspective
        </button>
        <button
          type="button"
          :class="{ active: projection === 'orthographic' }"
          @click="projection !== 'orthographic' && toggleProjection()"
        >
          Ortho
        </button>
      </div>
    </setting-row>

    <setting-row label="View">
      <button type="button" class="cq-action" @click="centerCamera">Recenter &amp; fit</button>
    </setting-row>

    <toggle-control v-model="scene.autoRotate" label="Auto-rotate" />
    <slider-control
      v-model="scene.autoRotateDelay"
      label="Rotate delay"
      hint="Delay before auto-rotate starts (ms)"
      :min="0"
      :max="10000"
      :step="100"
      :precision="0"
      :disabled="!scene.autoRotate"
    />

    <setting-row label="Target">
      <div class="cq-vec">
        <label v-for="axis in (['x', 'y', 'z'] as const)" :key="axis">
          <span>{{ axis.toUpperCase() }}</span>
          <input v-model.number="scene.cameraTarget[axis]" type="number" step="1" />
        </label>
      </div>
    </setting-row>
  </panel-section>
</template>

<style scoped>
.cq-choice {
  display: inline-flex;
  border: var(--cq-border);
  border-radius: var(--cq-radius-sm);
  overflow: hidden;
}

.cq-choice button {
  padding: 3px var(--cq-space-2);
  font-size: var(--cq-text-label);
  border: 0;
  background: transparent;
  color: rgb(var(--v-theme-on-surface));
  opacity: 0.6;
  cursor: pointer;
}

.cq-choice button + button {
  border-left: var(--cq-border);
}

.cq-choice button:hover {
  background: rgba(var(--v-theme-on-surface), 0.08);
  opacity: 0.9;
}

.cq-choice button.active {
  background: rgba(var(--v-theme-primary), 0.22);
  color: rgb(var(--v-theme-primary));
  opacity: 1;
}

.cq-action {
  padding: 3px var(--cq-space-2);
  font-size: var(--cq-text-label);
  border: var(--cq-border);
  border-radius: var(--cq-radius-sm);
  background: transparent;
  color: rgb(var(--v-theme-on-surface));
  cursor: pointer;
}

.cq-action:hover {
  background: rgba(var(--v-theme-on-surface), 0.08);
}

.cq-vec {
  display: flex;
  gap: var(--cq-space-1);
  width: 100%;
}

.cq-vec label {
  display: flex;
  align-items: center;
  gap: 3px;
  flex: 1 1 0;
  min-width: 0;
}

.cq-vec span {
  font-size: 0.6875rem;
  opacity: 0.5;
}

.cq-vec input {
  width: 100%;
  min-width: 0;
  height: 24px;
  padding: 0 4px;
  font-size: var(--cq-text-label);
  font-variant-numeric: tabular-nums;
  color: rgb(var(--v-theme-on-surface));
  background: rgba(var(--v-theme-on-surface), 0.06);
  border: 1px solid transparent;
  border-radius: var(--cq-radius-sm);
}

.cq-vec input:focus {
  outline: none;
  border-color: rgb(var(--v-theme-primary));
}
</style>
