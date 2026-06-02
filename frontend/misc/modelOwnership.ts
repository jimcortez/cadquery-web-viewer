import { extrasNameKey, extrasNameValueHelpers } from "./gltf";

/** Object3D with optional geometry (matches viewer traversal targets). */
export type TaggedObject3D = {
  type: string;
  visible: boolean;
  userData?: Record<string, unknown>;
  geometry?: { userData?: Record<string, unknown>; attributes?: { color?: unknown } };
  parent: TaggedObject3D | null;
  traverse: (cb: (obj: TaggedObject3D) => void) => void;
};

/** Copy glTF primitive extras onto meshes when the loader only tags geometry. */
export function stampOwnershipFromGeometry(root: TaggedObject3D) {
  root.traverse((child) => {
    const geomTag = child.geometry?.userData?.[extrasNameKey];
    if (geomTag != null && child.userData?.[extrasNameKey] == null) {
      if (!child.userData) child.userData = {};
      child.userData[extrasNameKey] = geomTag;
    }
  });
}

/** Nearest owning model tag (self, geometry, then ancestors). */
export function getOwningModelTag(obj: TaggedObject3D | null): string | undefined {
  let current: TaggedObject3D | null = obj;
  while (current) {
    const selfTag = current.userData?.[extrasNameKey];
    if (selfTag != null && selfTag !== "") return String(selfTag);
    const geomTag = current.geometry?.userData?.[extrasNameKey];
    if (geomTag != null && geomTag !== "") return String(geomTag);
    current = current.parent;
  }
  return undefined;
}

export function isSceneHelperObject(obj: TaggedObject3D): boolean {
  return getOwningModelTag(obj) === extrasNameValueHelpers;
}

export function objectBelongsToModel(obj: TaggedObject3D, modelName: string | undefined): boolean {
  if (!modelName) return false;
  return getOwningModelTag(obj) === modelName;
}
