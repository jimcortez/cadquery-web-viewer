import type { InjectionKey, Ref, ShallowRef } from "vue";
import type { Document } from "@gltf-transform/core";

export type SceneDocumentContext = {
  sceneDocument: ShallowRef<Document>;
};

export const sceneDocumentKey: InjectionKey<SceneDocumentContext> = Symbol("cadquery.sceneDocument");

export type DisableTapContext = {
  disableTap: Ref<boolean>;
  setDisableTap: (val: boolean) => void;
};

export const disableTapKey: InjectionKey<DisableTapContext> = Symbol("cadquery.disableTap");
