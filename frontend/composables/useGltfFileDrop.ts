import { onMounted, onUnmounted } from "vue";
import type { NetworkManager } from "../misc/network";

/**
 * Registers global drag/drop handlers on `document.body` for .glb/.gltf files.
 * Cleans up on unmount.
 */
export function useGltfFileDrop(networkMgr: NetworkManager) {
  function onDragOver(e: DragEvent) {
    e.preventDefault();
  }

  async function onDrop(e: DragEvent) {
    e.preventDefault();
    const file = e.dataTransfer?.files?.[0];
    if (!file) return;

    const ext = file.name.split(".").pop()?.toLowerCase();
    if (ext === "glb" || ext === "gltf") {
      await networkMgr.load(file);
    }
  }

  onMounted(() => {
    document.body.addEventListener("dragover", onDragOver);
    document.body.addEventListener("drop", onDrop);
  });

  onUnmounted(() => {
    document.body.removeEventListener("dragover", onDragOver);
    document.body.removeEventListener("drop", onDrop);
  });
}
