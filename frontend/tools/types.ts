// Shared graphics-side types.
//
// These live here rather than in Selection.vue because selection.ts and
// misc/distances.ts need them while Selection.vue imports from both — exporting
// the type from the SFC made that a cycle held together only by `import type`.

import type { Color, Material, Mesh } from "three";

/** A scene mesh as the viewer traverses it: single material, optional hit opt-out. */
export type MObject3D = Mesh & {
  userData: { noHit?: boolean };
  material: Material & {
    color: Color;
    wireframe?: boolean;
  };
};
