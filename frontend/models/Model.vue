<script lang="ts" setup>
import {
  VBtn,
  VBtnToggle,
  VExpansionPanel,
  VExpansionPanelText,
  VExpansionPanelTitle,
  VExpansionPanels,
  VSpacer,
  VTooltip,
} from "vuetify/lib/components/index.mjs";
import { extrasNameKey } from "../misc/gltf";
import { objectBelongsToModel, stampOwnershipFromGeometry } from "../misc/modelOwnership";
import { Mesh } from "@gltf-transform/core";
import { nextTick, ref, watch } from "vue";
import type { ModelViewerElement } from "@google/model-viewer";
import type ModelViewerWrapper from "../viewer/ModelViewerWrapper.vue";
import { isViewerReady } from "../viewer/viewerUtils";
import { mdiDelete, mdiRectangle, mdiRectangleOutline, mdiVectorRectangle } from "@mdi/js";
import SvgIcon from "@jamescoyle/vue-icon";
import { BackSide, DoubleSide, FrontSide } from "three/src/constants.js";
import { MeshStandardMaterial } from "three/src/materials/MeshStandardMaterial.js";
import { Box3 } from "three/src/math/Box3.js";
import { Color } from "three/src/math/Color.js";
import { Plane } from "three/src/math/Plane.js";
import { Vector3 } from "three/src/math/Vector3.js";
import type { MObject3D } from "../tools/Selection.vue";
import { toLineSegments } from "../misc/lines.js";
import { currentSceneRotation } from "../viewer/lighting.ts";
import { Matrix4 } from "three/src/math/Matrix4.js";
import { useModelDisplaySettings } from "../composables/useModelDisplaySettings";
import ModelControlsSection from "./sections/ModelControlsSection.vue";
import ModelMaterialSection from "./sections/ModelMaterialSection.vue";

const props = defineProps<{
  meshes: Array<Mesh>;
  viewer: InstanceType<typeof ModelViewerWrapper> | null;
}>();
const emit = defineEmits<{ remove: [] }>();

const modelName = props.meshes[0]?.getExtras()?.[extrasNameKey]?.toString();
const { getSettings } = useModelDisplaySettings();
const display = getSettings(modelName ?? "Unnamed");

const sectionOpen = ref<string[]>(["controls"]);

function objectMatchesName(obj: MObject3D, name: string | undefined): boolean {
  return objectBelongsToModel(obj, name);
}

function prepareMeshMaterial(child: MObject3D) {
  if (!child.material) return;
  if (child.geometry?.attributes?.color) {
    child.material.vertexColors = true;
    child.material.needsUpdate = true;
  }
}

let faceCount = ref(-1);
let edgeCount = ref(-1);
let vertexCount = ref(-1);

function onEnabledFeaturesChange(newEnabledFeatures: Array<number>) {
  const scene = props.viewer?.scene;
  const sceneModel = (scene as any)?._model;
  if (!scene || !sceneModel) return;
  sceneModel.traverse((child: MObject3D) => {
    if (objectMatchesName(child, modelName)) {
      const childIsFace = child.type == "Mesh" || child.type == "SkinnedMesh";
      const childIsEdge =
        child.type == "Line" || child.type == "LineSegments" || child.type == "LineSegments2";
      const childIsVertex = child.type == "Points";
      if (childIsFace || childIsEdge || childIsVertex) {
        const visible = newEnabledFeatures.includes(childIsFace ? 0 : childIsEdge ? 1 : childIsVertex ? 2 : -1);
        if (child.visible !== visible) {
          child.visible = visible;
          if (child.userData.backChild) child.userData.backChild.visible = visible;
        }
      }
    }
  });
  scene.queueRender();
}

watch(() => display.enabledFeatures, onEnabledFeaturesChange, { deep: true });

function onOpacityChange(newOpacity: number) {
  const scene = props.viewer?.scene;
  const sceneModel = (scene as any)?._model;
  if (!scene || !sceneModel) return;
  sceneModel.traverse((child: MObject3D) => {
    if (objectMatchesName(child, modelName)) {
      if (child.material && child.material.opacity !== newOpacity) {
        child.material.transparent = newOpacity < 1;
        child.material.opacity = newOpacity;
        child.material.needsUpdate = true;
      }
    }
  });
  scene.queueRender();
}

watch(() => display.opacity, onOpacityChange);

function onWireframeChange(newWireframe: boolean) {
  const scene = props.viewer?.scene;
  const sceneModel = (scene as any)?._model;
  if (!scene || !sceneModel) return;
  sceneModel.traverse((child: MObject3D) => {
    if (objectMatchesName(child, modelName)) {
      const childIsFace = child.type == "Mesh" || child.type == "SkinnedMesh";
      if (child.material && child.material.wireframe !== newWireframe && childIsFace) {
        child.material.wireframe = newWireframe;
        child.material.needsUpdate = true;
      }
    }
  });
  scene.queueRender();
}

watch(() => display.wireframe, onWireframeChange);

function onClipPlanesChange() {
  const scene = props.viewer?.scene;
  const sceneModel = (scene as any)?._model;
  if (!scene || !sceneModel) return;
  const enabledX =
    (display.clipPlaneX < 1 && !display.clipPlaneSwappedX) ||
    (display.clipPlaneX > 0 && display.clipPlaneSwappedX);
  const enabledY =
    (display.clipPlaneY < 1 && !display.clipPlaneSwappedY) ||
    (display.clipPlaneY > 0 && display.clipPlaneSwappedY);
  const enabledZ =
    (display.clipPlaneZ < 1 && !display.clipPlaneSwappedZ) ||
    (display.clipPlaneZ > 0 && display.clipPlaneSwappedZ);
  let bbox: Box3 | undefined;
  if (props.viewer?.renderer && (enabledX || enabledY || enabledZ)) {
    props.viewer.renderer.threeRenderer.localClippingEnabled = true;
    bbox = new Box3();
    sceneModel.traverse((child: MObject3D) => {
      if (objectMatchesName(child, modelName)) bbox!.expandByObject(child);
    });
  }
  sceneModel.traverse((child: MObject3D) => {
    if (objectMatchesName(child, modelName)) {
      if (child.material) {
        if (bbox?.isEmpty() == false) {
          const offsetX = bbox.min.x + display.clipPlaneX * (bbox.max.x - bbox.min.x);
          const offsetY = bbox.min.y + display.clipPlaneY * (bbox.max.y - bbox.min.y);
          const offsetZ = bbox.min.z + (1 - display.clipPlaneZ) * (bbox.max.z - bbox.min.z);
          const rotSceneMatrix = new Matrix4().makeRotationY(currentSceneRotation);
          const planes = [
            new Plane(new Vector3(-1, 0, 0), offsetX).applyMatrix4(rotSceneMatrix),
            new Plane(new Vector3(0, -1, 0), offsetY).applyMatrix4(rotSceneMatrix),
            new Plane(new Vector3(0, 0, 1), -offsetZ).applyMatrix4(rotSceneMatrix),
          ];
          if (display.clipPlaneSwappedX) planes[0]?.negate();
          if (display.clipPlaneSwappedY) planes[1]?.negate();
          if (display.clipPlaneSwappedZ) planes[2]?.negate();
          if (!enabledZ) planes.pop();
          if (!enabledY) planes.splice(1, 1);
          if (!enabledX) planes.shift();
          child.material.clippingPlanes = planes;
          if (child.userData.backChild?.material) child.userData.backChild.material.clippingPlanes = planes;
        } else {
          child.material.clippingPlanes = [];
          if (child.userData.backChild?.material) child.userData.backChild.material.clippingPlanes = [];
        }
      }
    }
  });
  scene.queueRender();
}

watch(
  () => [
    display.clipPlaneX,
    display.clipPlaneY,
    display.clipPlaneZ,
    display.clipPlaneSwappedX,
    display.clipPlaneSwappedY,
    display.clipPlaneSwappedZ,
  ],
  onClipPlanesChange,
);

let edgeWidthChangeCleanup = [] as Array<() => void>;

function onEdgeWidthChange(newEdgeWidth: number) {
  const scene = props.viewer?.scene;
  const sceneModel = (scene as any)?._model;
  if (!scene || !sceneModel) return;
  edgeWidthChangeCleanup.forEach((f) => f());
  edgeWidthChangeCleanup = [];
  const linesToImprove: Array<MObject3D> = [];
  sceneModel.traverse((child: MObject3D) => {
    if (objectMatchesName(child, modelName)) {
      if (child.type == "Line" || child.type == "LineSegments") {
        if (newEdgeWidth > 0) linesToImprove.push(child);
      }
      if (child.type == "Points") {
        (child.material as any).size = newEdgeWidth > 0 ? newEdgeWidth * 50 : 5;
        child.material.needsUpdate = true;
      }
    }
  });
  linesToImprove.forEach(async (line: MObject3D) => {
    const line2 = await toLineSegments(line.geometry, newEdgeWidth);
    const resizeListener = (elem: HTMLElement) => {
      line2.material.resolution.set(elem.clientWidth, elem.clientHeight);
      line2.material.needsUpdate = true;
    };
    props.viewer!.onElemReady((elem) => {
      elem.addEventListener("resize", () => resizeListener(elem));
      resizeListener(elem);
    });
    line2.position.copy(line.position);
    line2.computeLineDistances();
    line2.userData = Object.assign({}, line.userData);
    line.parent!.add(line2);
    line.children.forEach((o) => line2.add(o));
    line.visible = false;
    line.userData.niceLine = line2;
    line2.userData.noHit = true;
    line2.visible = display.enabledFeatures.includes(1);
    edgeWidthChangeCleanup.push(() => {
      line2.parent!.remove(line2);
      line.visible = display.enabledFeatures.includes(1);
      props.viewer!.onElemReady((elem) => {
        elem.removeEventListener("resize", () => resizeListener(elem));
      });
    });
  });
  scene.queueRender();
}

watch(() => display.edgeWidth, onEdgeWidthChange);

function onExplodeChange(newExplodeStrength: number) {
  const scene = props.viewer?.scene;
  const sceneModel = (scene as any)?._model;
  if (!scene || !sceneModel) return;

  const meBbox = new Box3();
  const othersBbox = new Box3();
  sceneModel.traverse((child: MObject3D) => {
    if (child == sceneModel) return;
    const isMe = objectMatchesName(child, modelName);
    if (
      (child.type === "Mesh" ||
        child.type === "SkinnedMesh" ||
        child.type === "Line" ||
        child.type === "LineSegments" ||
        child.type === "Points") &&
      !child.userData.noHit
    ) {
      if (isMe) meBbox.expandByObject(child);
      else if (!isMe && child.userData[extrasNameKey]) othersBbox.expandByObject(child);
    }
  });
  const modelSize = new Vector3();
  meBbox.getSize(modelSize);
  const maxDimension = Math.max(modelSize.x, modelSize.y, modelSize.z);
  const pushDirection = new Vector3()
    .subVectors(meBbox.getCenter(new Vector3()), othersBbox.getCenter(new Vector3()))
    .normalize();

  let strength = Math.abs(newExplodeStrength);
  if (display.explodeSwapped) strength = -strength;

  sceneModel.traverse((child: MObject3D) => {
    if (objectMatchesName(child, modelName)) {
      if (
        child.type === "Mesh" ||
        child.type === "SkinnedMesh" ||
        child.type === "Line" ||
        child.type === "LineSegments" ||
        child.type === "Points"
      ) {
        const direction = pushDirection.clone();
        if (direction.lengthSq() < 0.0001) direction.set(0, 1, 0);
        const factor = strength * maxDimension;
        const newPosition = new Vector3().add(direction.multiplyScalar(factor));
        child.position.copy(newPosition);
        if (child.userData.niceLine) child.userData.niceLine.position.copy(newPosition);
      }
    }
  });
  scene.queueRender();
  onClipPlanesChange();
}

watch(() => display.explodeStrength, (v) => onExplodeChange(v));
watch(() => display.explodeSwapped, () => onExplodeChange(display.explodeStrength));

function meshHasVertexColors(child: MObject3D): boolean {
  const geom = (child as { geometry?: { attributes?: { color?: unknown } } }).geometry;
  return !!geom?.attributes?.color;
}

function onMaterialChange() {
  const scene = props.viewer?.scene;
  const sceneModel = (scene as any)?._model;
  if (!scene || !sceneModel) return;
  const base = new Color(display.baseColor);
  const emissive = new Color(display.emissiveColor);
  sceneModel.traverse((child: MObject3D) => {
    if (objectMatchesName(child, modelName)) {
      const childIsFace = child.type == "Mesh" || child.type == "SkinnedMesh";
      if (!child.material || !childIsFace) return;
      if (!child.userData.materialCloned) {
        child.material = child.material.clone();
        child.userData.materialCloned = true;
      }
      const mat = child.material as MeshStandardMaterial;
      const hasVertexColors = meshHasVertexColors(child);
      if (hasVertexColors) {
        mat.vertexColors = true;
      } else {
        mat.color.copy(base);
      }
      mat.metalness = display.metalness;
      mat.roughness = display.roughness;
      mat.emissive.copy(emissive);
      mat.emissiveIntensity = display.emissiveIntensity;
      mat.side = display.doubleSided ? DoubleSide : FrontSide;
      mat.needsUpdate = true;
      if (child.userData.backChild?.material) {
        child.userData.backChild.material.side = BackSide;
      }
    }
  });
  scene.queueRender();
}

watch(
  () => [
    display.baseColor,
    display.metalness,
    display.roughness,
    display.emissiveColor,
    display.emissiveIntensity,
    display.doubleSided,
  ],
  onMaterialChange,
);

let setupSceneKey: string | null = null;

watch(
  () => props.viewer?.elem?.src,
  () => {
    setupSceneKey = null;
  },
);

function onModelLoad() {
  const scene = props.viewer?.scene;
  const sceneModel = (scene as any)?._model;
  if (!scene || !sceneModel) return;

  const sceneSrc = props.viewer?.elem?.src?.toString() ?? "";
  const setupKey = `${sceneSrc}:${modelName}`;
  if (setupSceneKey === setupKey) return;
  setupSceneKey = setupKey;

  stampOwnershipFromGeometry(sceneModel as unknown as import("../misc/modelOwnership").TaggedObject3D);

  const isFirstLoad = faceCount.value === -1;
  faceCount.value = props.meshes
    .flatMap((m) => m.listPrimitives().filter((p) => p.getMode() === WebGL2RenderingContext.TRIANGLES))
    .map((p) => (p.getExtras()?.face_triangles_end as any)?.length ?? 1)
    .reduce((a, b) => a + b, 0);
  edgeCount.value = props.meshes
    .flatMap((m) =>
      m.listPrimitives().filter((p) => {
        const mode = p.getMode();
        return mode === WebGL2RenderingContext.LINE_STRIP || mode === WebGL2RenderingContext.LINES;
      }),
    )
    .map((p) => (p.getExtras()?.edge_points_end as any)?.length ?? 0)
    .reduce((a, b) => a + b, 0);
  vertexCount.value = props.meshes
    .flatMap((m) => m.listPrimitives().filter((p) => p.getMode() === WebGL2RenderingContext.POINTS))
    .map((p) => p.getAttribute("POSITION")?.getCount() ?? 0)
    .reduce((a, b) => a + b, 0);

  if (isFirstLoad) {
    if (faceCount.value === 0) display.enabledFeatures = display.enabledFeatures.filter((f) => f !== 0);
    else if (!display.enabledFeatures.includes(0)) display.enabledFeatures.push(0);
    if (edgeCount.value === 0) display.enabledFeatures = display.enabledFeatures.filter((f) => f !== 1);
    else if (!display.enabledFeatures.includes(1)) display.enabledFeatures.push(1);
    if (vertexCount.value === 0) display.enabledFeatures = display.enabledFeatures.filter((f) => f !== 2);
    else if (!display.enabledFeatures.includes(2)) display.enabledFeatures.push(2);
  }

  const childrenToAdd: Array<MObject3D> = [];
  sceneModel.traverse((child: MObject3D) => {
    child.updateMatrixWorld();
    if (objectMatchesName(child, modelName)) {
      if (child.type == "Mesh" || child.type == "SkinnedMesh") {
        // @ts-ignore
        child.geometry?.computeBoundsTree({ indirect: true });
        prepareMeshMaterial(child);
        if (!child.userData.backChild) {
          const backChild = child.clone();
          backChild.material = child.material.clone();
          backChild.material.side = BackSide;
          backChild.material.color = new Color(0.25, 0.25, 0.25);
          backChild.userData.noHit = true;
          child.userData.backChild = backChild;
          childrenToAdd.push(backChild as MObject3D);
        }
      }
    }
  });
  childrenToAdd.forEach((child: MObject3D) => sceneModel.add(child));

  onEnabledFeaturesChange(display.enabledFeatures);
  onOpacityChange(display.opacity);
  onWireframeChange(display.wireframe);
  onClipPlanesChange();
  onEdgeWidthChange(display.edgeWidth);
  onMaterialChange();
  if (display.explodeStrength > 0) nextTick(() => onExplodeChange(display.explodeStrength));

  scene.queueRender();
}

const onViewerReady = (viewer: InstanceType<typeof ModelViewerWrapper> | null) => {
  if (!isViewerReady(viewer)) return;
  viewer.onElemReady((elem: HTMLElement) => {
    elem.addEventListener("load", onModelLoad);
    elem.addEventListener("camera-change", onClipPlanesChange);
    if ((elem as ModelViewerElement).loaded) void nextTick(onModelLoad);
  });
};

if (isViewerReady(props.viewer)) {
  onViewerReady(props.viewer);
} else {
  watch(() => props.viewer, onViewerReady);
}
</script>

<template>
  <v-expansion-panel :value="modelName">
    <v-expansion-panel-title>
      <v-btn-toggle v-model="display.enabledFeatures" color="surface-light" multiple @click.stop>
        <v-btn icon>
          <v-tooltip activator="parent">Toggle Faces ({{ faceCount }})</v-tooltip>
          <svg-icon :path="mdiRectangle" :rotate="90" type="mdi" />
        </v-btn>
        <v-btn icon>
          <v-tooltip activator="parent">Toggle Edges ({{ edgeCount }})</v-tooltip>
          <svg-icon :path="mdiRectangleOutline" :rotate="90" type="mdi" />
        </v-btn>
        <v-btn icon>
          <v-tooltip activator="parent">Toggle Vertices ({{ vertexCount }})</v-tooltip>
          <svg-icon :path="mdiVectorRectangle" :rotate="90" type="mdi" />
        </v-btn>
      </v-btn-toggle>
      <div class="model-name">{{ modelName }}</div>
      <v-spacer />
      <v-btn icon @click.stop="emit('remove')">
        <v-tooltip activator="parent">Remove</v-tooltip>
        <svg-icon :path="mdiDelete" type="mdi" />
      </v-btn>
    </v-expansion-panel-title>
    <v-expansion-panel-text>
      <v-expansion-panels v-model="sectionOpen" multiple density="compact" flat>
        <model-controls-section :display="display" :edge-count="edgeCount" :vertex-count="vertexCount" />
        <model-material-section :display="display" />
      </v-expansion-panels>
    </v-expansion-panel-text>
  </v-expansion-panel>
</template>

<style scoped>
.v-expansion-panel-title--active + .v-expansion-panel-text {
  display: flex !important;
}

.v-expansion-panel-title {
  padding: 0;
}

.v-expansion-panel-title > .v-btn-toggle {
  margin: 0;
  margin-right: 8px;
}

.v-btn {
  --v-btn-height: 12px;
}

.model-name {
  width: 152px;
  font-size: 110%;
  overflow-x: clip;
  overflow-y: visible;
  word-wrap: break-word;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}
</style>

<style>
.v-expansion-panel-text__wrapper {
  padding: 0 !important;
}

.mdi-checkbox-blank-outline {
  background-image: url('data:image/svg+xml;charset=UTF-8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="white"><path d="M19,3H5C3.89,3 3,3.89 3,5V19A2,2 0 0,0 5,21H19A2,2 0 0,0 21,19V5C21,3.89 20.1,3 19,3M19,5V19H5V5H19Z"/></svg>');
}

.mdi-checkbox-marked-outline {
  background-image: url('data:image/svg+xml;charset=UTF-8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="white"><path d="M19,19H5V5H15V3H5C3.89,3 3,3.89 3,5V19A2,2 0 0,0 5,21H19A2,2 0 0,0 21,19V11H19M7.91,10.08L6.5,11.5L11,16L21,6L19.59,4.58L11,13.17L7.91,10.08Z"/></svg>');
}

.mdi-triangle {
  background-image: url('data:image/svg+xml;charset=UTF-8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="white"><path d="M1 21h22L12 2"/></svg>');
}

.mdi-triangle-outline {
  background-image: url('data:image/svg+xml;charset=UTF-8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="white"><path d="M12 2L1 21h22M12 6l7.53 13H4.47"/></svg>');
}
</style>
