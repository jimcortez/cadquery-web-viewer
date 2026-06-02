<script lang="ts" setup>
import { VExpansionPanels } from "vuetify/lib/components/index.mjs";
import type ModelViewerWrapper from "../viewer/ModelViewerWrapper.vue";
import { Document, Mesh } from "@gltf-transform/core";
import { extrasNameKey, extrasNameValueHelpers } from "../misc/gltf";
import Model from "./Model.vue";
import { inject, ref } from "vue";
import { sceneDocumentKey } from "../injectionKeys";

const props = defineProps<{ viewer: InstanceType<typeof ModelViewerWrapper> | null }>();
const emit = defineEmits<{ removeModel: [string] }>();

const { sceneDocument } = inject(sceneDocumentKey)!;

const expandedNames = ref<string[]>([]);

function meshesList(sceneDocument: Document): Array<Array<Mesh>> {
  return sceneDocument
    .getRoot()
    .listMeshes()
    .reduce((acc, mesh) => {
      const name = mesh.getExtras()[extrasNameKey]?.toString() ?? "Unnamed";
      if (name === extrasNameValueHelpers) return acc;
      const group = acc.find((group) => group[0] && meshName(group[0]) === name);
      if (group) {
        group.push(mesh);
      } else {
        acc.push([mesh]);
      }
      return acc;
    }, [] as Array<Array<Mesh>>);
}

function meshName(mesh: Mesh) {
  return mesh.getExtras()[extrasNameKey]?.toString() ?? "Unnamed";
}

function onRemove(mesh: Mesh) {
  emit("removeModel", meshName(mesh));
}

function findModel(name: string) {
  if (!expandedNames.value.includes(name)) expandedNames.value.push(name);
}

defineExpose({ findModel });
</script>

<template>
  <v-expansion-panels
    v-for="meshes in meshesList(sceneDocument)"
    :key="meshes[0] ? meshName(meshes[0]) : 'unnamed'"
    v-model="expandedNames"
    multiple
  >
    <model :meshes="meshes" :viewer="props.viewer" @remove="meshes[0] ? onRemove(meshes[0]) : undefined" />
  </v-expansion-panels>
</template>
