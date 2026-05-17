<script lang="ts" setup>
import {onMounted, ref, watch} from "vue";
import type {ModelScene} from "@google/model-viewer/lib/three-components/ModelScene";
// @ts-expect-error
import * as OrientationGizmoRaw from "three-orientation-gizmo/src/OrientationGizmo";
import type ModelViewerWrapper from "../viewer/ModelViewerWrapper.vue";
import {currentSceneRotation} from "../viewer/lighting.ts";

import * as THREE from "three";

const props = defineProps<{ viewer: InstanceType<typeof ModelViewerWrapper> }>();

function createGizmo(expectedParent: HTMLElement, scene: ModelScene): HTMLElement {
  // three-orientation-gizmo expects a full THREE namespace on globalThis at construction time.
  const globalWithTHREE = globalThis as unknown as { THREE?: typeof THREE };
  const prevTHREE = globalWithTHREE.THREE;
  globalWithTHREE.THREE = THREE;
  let gizmo: ReturnType<typeof OrientationGizmoRaw.default>;
  try {
    // noinspection SpellCheckingInspection
    gizmo = new OrientationGizmoRaw.default(scene.camera, {
    size: expectedParent.clientWidth,
    bubbleSizePrimary: expectedParent.clientWidth / 12,
    bubbleSizeSeconday: expectedParent.clientWidth / 12,
    fontSize: (expectedParent.clientWidth / 10) + "px",
    });
  } finally {
    if (prevTHREE === undefined) {
      delete globalWithTHREE.THREE;
    } else {
      globalWithTHREE.THREE = prevTHREE;
    }
  }
  // Make sure all bubbles are labeled
  for (let bubble of gizmo.bubbles) {
    bubble.label = bubble.axis.toUpperCase();
  }
  // HACK: Swap axes to fake the CAD orientation
  for (let swap of [["y", "-z"], ["z", "-y"], ["z", "-z"]]) {
    let indexA = gizmo.bubbles.findIndex((bubble: any) => bubble.axis == swap[0])
    let indexB = gizmo.bubbles.findIndex((bubble: any) => bubble.axis == swap[1])
    let dirA = gizmo.bubbles[indexA].direction.clone();
    let dirB = gizmo.bubbles[indexB].direction.clone();
    gizmo.bubbles[indexA].direction.copy(dirB);
    gizmo.bubbles[indexB].direction.copy(dirA);
  }
  // Append and listen for events
  gizmo.onAxisSelected = (axis: { direction: { x: any; y: any; z: any; }; }) => {
    if (!props.viewer.elem || !props.viewer.controls) return;
    // Animate the controls to the new wanted angle
    const controls = props.viewer.controls;
    const {theta: curTheta/*, phi: curPhi*/} = (controls as any).goalSpherical;
    let wantedTheta = NaN;
    let wantedPhi = NaN;
    let attempt = 0
    while ((attempt == 0 || curTheta == wantedTheta) && attempt < 2) {
      if (attempt > 0) { // Flip the camera if the user clicks on the same axis
        axis.direction.x = -axis.direction.x;
        axis.direction.y = -axis.direction.y;
        axis.direction.z = -axis.direction.z;
      }
      wantedTheta = Math.atan2(axis.direction.x, axis.direction.z) + currentSceneRotation;
      wantedPhi = Math.asin(-axis.direction.y) + Math.PI / 2;
      attempt++;
    }
    controls.setOrbit(wantedTheta, wantedPhi);
    props.viewer.elem?.dispatchEvent(new CustomEvent('camera-change', {detail: {source: 'none'}}))
    scene.queueRender();
  }
  return gizmo;
}

// Mount, unmount and listen for scene changes
let container = ref<HTMLElement | null>(null);

let gizmo: HTMLElement & { update: () => void }

let reinstall = () => {
  if (!container.value || !props.viewer.scene) return;
  if (gizmo) container.value.removeChild(gizmo);
  gizmo = createGizmo(container.value, props.viewer.scene as ModelScene) as typeof gizmo;
  container.value.appendChild(gizmo);
}
// Defer gizmo install until the viewer scene is ready (avoids touching the camera too early).
watch(() => props.viewer.scene, (scene) => {
  if (scene) reinstall();
}, {immediate: true});
// onUnmounted is not needed because the gizmo is removed when the container is removed
</script>

<template>
  <div ref="container" class="orientation-gizmo"/>
</template>