import {
  computed,
  inject,
  provide,
  ref,
  watch,
  type ComputedRef,
  type InjectionKey,
  type Ref,
  type ShallowRef,
} from "vue";
import type { Document, Mesh } from "@gltf-transform/core";
import { extrasNameKey, extrasNameValueHelpers } from "../misc/gltf";
import { partNameOfMesh, readAssemblyManifest, type AssemblyManifest } from "../misc/assembly";

/** One named part of a scene object: every mesh sharing the object's part tag. */
export type ScenePart = {
  name: string;
  meshes: Mesh[];
  faceCount: number;
  edgeCount: number;
  vertexCount: number;
  /** Colour the tessellator baked into this part (from the manifest), or null. */
  color: string | null;
  tags: string[];
};

/**
 * One addressable object in the scene: every mesh sharing a glTF extras name tag.
 *
 * Every object is an assembly of one or more parts. Geometry without part tags
 * (plain GLB imports, versions stored before assemblies existed) is a single part
 * named after the object.
 */
export type SceneObject = {
  name: string;
  meshes: Mesh[];
  faceCount: number;
  edgeCount: number;
  vertexCount: number;
  parts: ScenePart[];
  tags: string[];
  manifest: AssemblyManifest | null;
};

export type SceneObjectsContext = {
  /** Grouped scene contents, excluding the `__helpers` pseudo-model. */
  objects: ComputedRef<SceneObject[]>;
  /** Which object the inspector is showing. */
  selectedObjectName: Ref<string | null>;
  /** Which part of the selected object is focused, or null for the whole assembly. */
  selectedPartName: Ref<string | null>;
  getObject: (name: string) => SceneObject | undefined;
  select: (name: string | null) => void;
  selectPart: (objectName: string, partName: string | null) => void;
};

export const sceneObjectsKey: InjectionKey<SceneObjectsContext> = Symbol("cadquery.sceneObjects");

function meshName(mesh: Mesh): string {
  return mesh.getExtras()[extrasNameKey]?.toString() ?? "Unnamed";
}

/**
 * Face / edge / vertex totals straight from the glTF primitives.
 *
 * These used to be counted in Model.vue on the model-viewer `load` event, which
 * meant an object had to be mounted and loaded before its counts were known.
 * They derive purely from the Document, so the list can show them for every
 * object whether or not it is selected.
 */
function countFeatures(meshes: Mesh[]): Pick<SceneObject, "faceCount" | "edgeCount" | "vertexCount"> {
  const primitives = meshes.flatMap((m) => m.listPrimitives());
  const faceCount = primitives
    .filter((p) => p.getMode() === WebGL2RenderingContext.TRIANGLES)
    .map((p) => (p.getExtras()?.face_triangles_end as ArrayLike<number> | undefined)?.length ?? 1)
    .reduce((a, b) => a + b, 0);
  const edgeCount = primitives
    .filter((p) => {
      const mode = p.getMode();
      return mode === WebGL2RenderingContext.LINE_STRIP || mode === WebGL2RenderingContext.LINES;
    })
    .map((p) => (p.getExtras()?.edge_points_end as ArrayLike<number> | undefined)?.length ?? 0)
    .reduce((a, b) => a + b, 0);
  const vertexCount = primitives
    .filter((p) => p.getMode() === WebGL2RenderingContext.POINTS)
    .map((p) => p.getAttribute("POSITION")?.getCount() ?? 0)
    .reduce((a, b) => a + b, 0);
  return { faceCount, edgeCount, vertexCount };
}

/** Split an object's meshes by part tag; manifest order first, then any untagged/extra parts. */
function groupParts(name: string, meshes: Mesh[], manifest: AssemblyManifest | null): ScenePart[] {
  const byPart = new Map<string, Mesh[]>();
  for (const mesh of meshes) {
    const part = partNameOfMesh(mesh) ?? name;
    const group = byPart.get(part);
    if (group) group.push(mesh);
    else byPart.set(part, [mesh]);
  }
  const ordered: string[] = [];
  for (const p of manifest?.parts ?? []) if (byPart.has(p.name)) ordered.push(p.name);
  for (const p of byPart.keys()) if (!ordered.includes(p)) ordered.push(p);
  return ordered.map((partName) => {
    const partMeshes = byPart.get(partName)!;
    const entry = manifest?.parts.find((p) => p.name === partName);
    return {
      name: partName,
      meshes: partMeshes,
      ...countFeatures(partMeshes),
      color: entry?.color ?? null,
      tags: entry?.tags ?? [],
    };
  });
}

function groupMeshes(document: Document): SceneObject[] {
  const byName = new Map<string, Mesh[]>();
  for (const mesh of document.getRoot().listMeshes()) {
    const name = meshName(mesh);
    if (name === extrasNameValueHelpers) continue;
    const group = byName.get(name);
    if (group) group.push(mesh);
    else byName.set(name, [mesh]);
  }
  return [...byName].map(([name, meshes]) => {
    const manifest = readAssemblyManifest(document, name);
    return {
      name,
      meshes,
      ...countFeatures(meshes),
      parts: groupParts(name, meshes, manifest),
      tags: manifest?.tags ?? [],
      manifest,
    };
  });
}

export function createSceneObjectsProvider(
  sceneDocument: ShallowRef<Document>,
): SceneObjectsContext {
  const objects = computed(() => groupMeshes(sceneDocument.value));
  const selectedObjectName = ref<string | null>(null);
  const selectedPartName = ref<string | null>(null);

  function getObject(name: string): SceneObject | undefined {
    return objects.value.find((o) => o.name === name);
  }

  function select(name: string | null) {
    if (selectedObjectName.value !== name) selectedPartName.value = null;
    selectedObjectName.value = name;
  }

  function selectPart(objectName: string, partName: string | null) {
    selectedObjectName.value = objectName;
    selectedPartName.value = partName;
  }

  // Keep the inspector pointed at something real: select the first object when
  // nothing is selected, and fall back to a neighbour when the current one goes away.
  watch(
    objects,
    (list) => {
      const current = selectedObjectName.value;
      const obj = current !== null ? list.find((o) => o.name === current) : undefined;
      if (obj) {
        const part = selectedPartName.value;
        if (part !== null && !obj.parts.some((p) => p.name === part)) selectedPartName.value = null;
        return;
      }
      selectedPartName.value = null;
      selectedObjectName.value = list[0]?.name ?? null;
    },
    { immediate: true },
  );

  const ctx: SceneObjectsContext = {
    objects,
    selectedObjectName,
    selectedPartName,
    getObject,
    select,
    selectPart,
  };
  provide(sceneObjectsKey, ctx);
  return ctx;
}

export function useSceneObjects(): SceneObjectsContext {
  const ctx = inject(sceneObjectsKey);
  if (!ctx) throw new Error("useSceneObjects() called without provider");
  return ctx;
}
