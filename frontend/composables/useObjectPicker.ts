import type { Ref, ShallowRef } from "vue";
import { computed, ref, watch } from "vue";
import { Document } from "@gltf-transform/core";
import { extrasNameKey, extrasNameValueHelpers } from "../misc/gltf";
import {
  allVersions,
  fetchObjectList,
  importObjectFromUrl,
  objectNameFromUrl,
  resolveApiBaseUrl,
  type ServerObjectDescriptor,
} from "../misc/objectApi";
import type { NetworkManager } from "../misc/network";

export function getLoadedModelNames(sceneDocument: Document): Set<string> {
  const names = new Set<string>();
  for (const mesh of sceneDocument.getRoot().listMeshes()) {
    const n = mesh.getExtras()[extrasNameKey]?.toString();
    if (n && n !== extrasNameValueHelpers) names.add(n);
  }
  return names;
}

export function useObjectPicker(
  networkMgr: NetworkManager,
  sceneDocument: ShallowRef<Document>,
  dialogOpen: Ref<boolean>,
) {
  const apiBaseUrl = ref<string | null>(null);
  const objects = ref<ServerObjectDescriptor[]>([]);
  const listLoading = ref(false);
  const listError = ref<string | null>(null);
  const rowVersions = ref<Record<string, number>>({});
  const urlInput = ref("");
  const urlLoading = ref(false);
  const urlError = ref<string | null>(null);

  const loadedNames = computed(() => getLoadedModelNames(sceneDocument.value));
  /** Checkbox state in the modal (updated immediately on toggle). */
  const checkedNames = ref<Set<string>>(new Set());

  function syncCheckedFromScene() {
    checkedNames.value = new Set(loadedNames.value);
  }

  function syncRowVersionsFromObjects() {
    const next: Record<string, number> = { ...rowVersions.value };
    for (const obj of objects.value) {
      const loadedVer = networkMgr.getLoadedVersion(obj.name);
      next[obj.name] = loadedVer ?? obj.version;
    }
    rowVersions.value = next;
  }

  async function refreshObjectList() {
    if (!apiBaseUrl.value) return;
    listLoading.value = true;
    listError.value = null;
    try {
      objects.value = await fetchObjectList(apiBaseUrl.value);
      syncRowVersionsFromObjects();
    } catch (e) {
      listError.value = e instanceof Error ? e.message : String(e);
    } finally {
      listLoading.value = false;
    }
  }

  async function openDialog() {
    dialogOpen.value = true;
    urlError.value = null;
    syncCheckedFromScene();
    apiBaseUrl.value = await resolveApiBaseUrl();
    if (apiBaseUrl.value) {
      await refreshObjectList();
    } else {
      objects.value = [];
    }
  }

  function isSelected(name: string): boolean {
    return checkedNames.value.has(name);
  }

  function getRowVersion(name: string, desc: ServerObjectDescriptor): number {
    return rowVersions.value[name] ?? desc.version;
  }

  function setRowVersion(name: string, version: number) {
    rowVersions.value = { ...rowVersions.value, [name]: version };
  }

  function versionHash(desc: ServerObjectDescriptor, version: number): string {
    const opts = allVersions(desc);
    const match = opts.find((o) => o.version === version);
    return match?.hash ?? desc.hash;
  }

  function toggleObject(desc: ServerObjectDescriptor, selected: boolean) {
    if (!apiBaseUrl.value) return;
    const next = new Set(checkedNames.value);
    if (selected) next.add(desc.name);
    else next.delete(desc.name);
    checkedNames.value = next;

    const version = getRowVersion(desc.name, desc);
    const hash = versionHash(desc, version);
    if (selected) {
      if (!loadedNames.value.has(desc.name)) {
        networkMgr.forgetObject(desc.name);
      }
      networkMgr.loadServerObject(desc.name, version, hash, apiBaseUrl.value);
    } else {
      networkMgr.removeServerObject(desc.name);
    }
  }

  async function onVersionChange(desc: ServerObjectDescriptor, version: number) {
    setRowVersion(desc.name, version);
    if (!isSelected(desc.name) || !apiBaseUrl.value) return;
    const hash = versionHash(desc, version);
    networkMgr.loadServerObject(desc.name, version, hash, apiBaseUrl.value);
  }

  async function loadFromUrl() {
    const url = urlInput.value.trim();
    if (!url) {
      urlError.value = "Enter a URL to a .glb or .gltf file";
      return;
    }
    urlLoading.value = true;
    urlError.value = null;
    const name = objectNameFromUrl(url);
    try {
      if (apiBaseUrl.value) {
        const result = await importObjectFromUrl(apiBaseUrl.value, name, url);
        await refreshObjectList();
        setRowVersion(name, result.version);
        networkMgr.loadServerObject(name, result.version, result.hash, apiBaseUrl.value);
      } else {
        await networkMgr.load(url);
      }
    } catch (e) {
      urlError.value = e instanceof Error ? e.message : String(e);
    } finally {
      urlLoading.value = false;
    }
  }

  watch(dialogOpen, (open) => {
    if (open) {
      syncCheckedFromScene();
      void (async () => {
        apiBaseUrl.value = await resolveApiBaseUrl();
        if (apiBaseUrl.value) await refreshObjectList();
      })();
    }
  });

  return {
    apiBaseUrl,
    objects,
    listLoading,
    listError,
    urlInput,
    urlLoading,
    urlError,
    openDialog,
    refreshObjectList,
    isSelected,
    getRowVersion,
    toggleObject,
    onVersionChange,
    loadFromUrl,
    allVersions,
  };
}
