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

/** One addressable object in the scene: every mesh sharing a glTF extras name tag. */
export type SceneObject = {
  name: string;
  meshes: Mesh[];
  faceCount: number;
  edgeCount: number;
  vertexCount: number;
};

export type SceneObjectsContext = {
  /** Grouped scene contents, excluding the `__helpers` pseudo-model. */
  objects: ComputedRef<SceneObject[]>;
  /** Which object the inspector is showing. */
  selectedObjectName: Ref<string | null>;
  getObject: (name: string) => SceneObject | undefined;
  select: (name: string | null) => void;
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

function groupMeshes(document: Document): SceneObject[] {
  const byName = new Map<string, Mesh[]>();
  for (const mesh of document.getRoot().listMeshes()) {
    const name = meshName(mesh);
    if (name === extrasNameValueHelpers) continue;
    const group = byName.get(name);
    if (group) group.push(mesh);
    else byName.set(name, [mesh]);
  }
  return [...byName].map(([name, meshes]) => ({ name, meshes, ...countFeatures(meshes) }));
}

export function createSceneObjectsProvider(
  sceneDocument: ShallowRef<Document>,
): SceneObjectsContext {
  const objects = computed(() => groupMeshes(sceneDocument.value));
  const selectedObjectName = ref<string | null>(null);

  function getObject(name: string): SceneObject | undefined {
    return objects.value.find((o) => o.name === name);
  }

  function select(name: string | null) {
    selectedObjectName.value = name;
  }

  // Keep the inspector pointed at something real: select the first object when
  // nothing is selected, and fall back to a neighbour when the current one goes away.
  watch(
    objects,
    (list) => {
      const current = selectedObjectName.value;
      if (current !== null && list.some((o) => o.name === current)) return;
      selectedObjectName.value = list[0]?.name ?? null;
    },
    { immediate: true },
  );

  const ctx: SceneObjectsContext = { objects, selectedObjectName, getObject, select };
  provide(sceneObjectsKey, ctx);
  return ctx;
}

export function useSceneObjects(): SceneObjectsContext {
  const ctx = inject(sceneObjectsKey);
  if (!ctx) throw new Error("useSceneObjects() called without provider");
  return ctx;
}
