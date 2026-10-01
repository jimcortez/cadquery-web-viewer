import type { Document, Mesh } from "@gltf-transform/core";
import { extrasAssemblyKey, extrasNameKey, extrasPartKey } from "./gltf";

/**
 * Assembly manifest, as written by cadquery_web_viewer.assembly (schema 1) into the root
 * node's extras and into the version kwargs. Every object is an assembly; a single shape is
 * an assembly with one part.
 */
export type AssemblyPartManifest = {
  name: string;
  index: number;
  /** `#rrggbb` baked into the part's vertex colours, or null for the default face colour. */
  color: string | null;
  tags: string[];
};

export type AssemblyManifest = {
  schema: number;
  name: string;
  tags: string[];
  parts: AssemblyPartManifest[];
};

/**
 * glTF writers drop `null` values and empty lists from extras, so a manifest read back from
 * a GLB may be missing `color` / `tags`; fill in the defaults.
 */
export function normalizeManifest(raw: unknown): AssemblyManifest | null {
  if (!raw || typeof raw !== "object") return null;
  const r = raw as Record<string, unknown>;
  const partsRaw = Array.isArray(r.parts) ? r.parts : [];
  const parts: AssemblyPartManifest[] = partsRaw.map((p, i) => {
    const q = (p && typeof p === "object" ? p : {}) as Record<string, unknown>;
    return {
      name: String(q.name ?? `part ${i}`),
      index: typeof q.index === "number" ? q.index : i,
      color: typeof q.color === "string" && q.color !== "" ? q.color : null,
      tags: Array.isArray(q.tags) ? q.tags.map(String) : [],
    };
  });
  return {
    schema: typeof r.schema === "number" ? r.schema : 1,
    name: String(r.name ?? ""),
    tags: Array.isArray(r.tags) ? r.tags.map(String) : [],
    parts,
  };
}

/** The manifest stored on the root node that setNames() tagged with `objectName`, if any. */
export function readAssemblyManifest(document: Document, objectName: string): AssemblyManifest | null {
  for (const node of document.getRoot().listNodes()) {
    const extras = node.getExtras();
    if (extras[extrasNameKey]?.toString() !== objectName) continue;
    const raw = extras[extrasAssemblyKey];
    if (raw) return normalizeManifest(raw);
  }
  return null;
}

/** Part name a mesh was tagged with, or null for GLBs that predate assemblies / plain imports. */
export function partNameOfMesh(mesh: Mesh): string | null {
  const v = mesh.getExtras()[extrasPartKey];
  return v == null || v === "" ? null : String(v);
}
