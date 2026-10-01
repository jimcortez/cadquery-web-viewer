import { extrasNameKey, extrasNameValueHelpers, extrasPartKey } from "./gltf";

/** Object3D with optional geometry (matches viewer traversal targets). */
export type TaggedObject3D = {
  type: string;
  visible: boolean;
  userData?: Record<string, unknown>;
  geometry?: { userData?: Record<string, unknown>; attributes?: { color?: unknown } };
  parent: TaggedObject3D | null;
  traverse: (cb: (obj: TaggedObject3D) => void) => void;
};

/** Copy glTF primitive extras (object and part tags) onto meshes when the loader only tags geometry. */
export function stampOwnershipFromGeometry(root: TaggedObject3D) {
  root.traverse((child) => {
    for (const key of [extrasNameKey, extrasPartKey]) {
      const geomTag = child.geometry?.userData?.[key];
      if (geomTag != null && child.userData?.[key] == null) {
        if (!child.userData) child.userData = {};
        child.userData[key] = geomTag;
      }
    }
  });
}

function nearestTag(obj: TaggedObject3D | null, key: string): string | undefined {
  let current: TaggedObject3D | null = obj;
  while (current) {
    const selfTag = current.userData?.[key];
    if (selfTag != null && selfTag !== "") return String(selfTag);
    const geomTag = current.geometry?.userData?.[key];
    if (geomTag != null && geomTag !== "") return String(geomTag);
    current = current.parent;
  }
  return undefined;
}

/** Nearest owning model tag (self, geometry, then ancestors). */
export function getOwningModelTag(obj: TaggedObject3D | null): string | undefined {
  return nearestTag(obj, extrasNameKey);
}

/** Nearest owning part tag (self, geometry, then ancestors); undefined for untagged geometry. */
export function getOwningPartTag(obj: TaggedObject3D | null): string | undefined {
  return nearestTag(obj, extrasPartKey);
}

export function isSceneHelperObject(obj: TaggedObject3D): boolean {
  return getOwningModelTag(obj) === extrasNameValueHelpers;
}

export function objectBelongsToModel(obj: TaggedObject3D, modelName: string | undefined): boolean {
  if (!modelName) return false;
  return getOwningModelTag(obj) === modelName;
}

export function objectBelongsToPart(
  obj: TaggedObject3D,
  modelName: string | undefined,
  partName: string | undefined,
): boolean {
  if (!objectBelongsToModel(obj, modelName) || !partName) return false;
  return getOwningPartTag(obj) === partName;
}
