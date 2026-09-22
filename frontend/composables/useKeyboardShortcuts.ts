import { onScopeDispose } from "vue";
import type { CameraToolsContext } from "./useCameraTools";
import { SELECTION_FILTERS, type SelectionToolsContext } from "./useSelectionTools";

const GITHUB_URL = "https://github.com/jecortez/cadquery-web-viewer";

function isTextEntry(target: EventTarget | null): boolean {
  const tag = (target as HTMLElement | null)?.tagName;
  return tag === "INPUT" || tag === "TEXTAREA";
}

/**
 * Single owner of the viewer's keyboard shortcuts.
 *
 * These used to be two module-scope listeners — one on `document` from Tools.vue,
 * one on `window` from Selection.vue — that were never removed and both claimed
 * `d`, so pressing it toggled distance lines *and* downloaded the scene. Export
 * now lives on Ctrl/Cmd+S.
 */
export function useKeyboardShortcuts(
  selection: SelectionToolsContext,
  camera: CameraToolsContext,
) {
  function onKeyDown(event: KeyboardEvent) {
    if (isTextEntry(event.target)) return;

    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "s") {
      event.preventDefault();
      void camera.downloadSceneGlb();
      return;
    }
    if (event.metaKey || event.ctrlKey || event.altKey) return;

    const filter = SELECTION_FILTERS.find((f) => f.shortcut === event.key);
    if (filter) {
      selection.setFilter(filter.value);
      return;
    }

    switch (event.key) {
      case "b":
        selection.toggleShowBoundingBox();
        break;
      case "d":
        selection.toggleShowDistances();
        break;
      case "o":
        selection.toggleOpenNextSelection();
        break;
      case "p":
        void camera.toggleProjection();
        break;
      case "c":
        camera.centerCamera();
        break;
      case "g":
        window.open(GITHUB_URL, "_blank");
        break;
    }
  }

  window.addEventListener("keydown", onKeyDown);
  onScopeDispose(() => window.removeEventListener("keydown", onKeyDown));
}
