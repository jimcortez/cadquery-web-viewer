import {
  computed,
  inject,
  markRaw,
  provide,
  ref,
  watch,
  type ComputedRef,
  type InjectionKey,
  type Ref,
  type ShallowRef,
} from "vue";
import type { Document } from "@gltf-transform/core";
import type { ModelViewerElement } from "@google/model-viewer";
import type { ModelScene } from "@google/model-viewer/lib/three-components/ModelScene";
import type { Intersection, Object3D } from "three";
import { Box3 } from "three/src/math/Box3.js";
import { Raycaster } from "three/src/core/Raycaster.js";
import { Vector3 } from "three/src/math/Vector3.js";
import { AxesColors } from "../misc/helpers";
import { distances } from "../misc/distances";
import { getOwningModelTag, type TaggedObject3D } from "../misc/modelOwnership";
import { SceneMgr } from "../misc/scene";
import { highlight, highlightUndo, hitToSelectionInfo, type SelectionInfo } from "../tools/selection";
import type { MObject3D } from "../tools/types";
import { isViewerReady } from "../viewer/viewerUtils";
import type ModelViewerWrapper from "../viewer/ModelViewerWrapper.vue";

export type SelectionFilter = "any" | "faces" | "edges" | "vertices";

/** Filter options, with the single-key shortcut each one is bound to. */
export const SELECTION_FILTERS: ReadonlyArray<{
  value: SelectionFilter;
  label: string;
  shortcut: string;
}> = [
  { value: "any", label: "Any", shortcut: "s" },
  { value: "faces", label: "Faces", shortcut: "f" },
  { value: "edges", label: "Edges", shortcut: "e" },
  { value: "vertices", label: "Vertices", shortcut: "v" },
];

export type SelectionCounts = { face: number; edge: number; vertex: number };

export type SelectionToolsContext = {
  selected: Ref<SelectionInfo[]>;
  selectionEnabled: Ref<boolean>;
  selectFilter: Ref<SelectionFilter>;
  showBoundingBox: Ref<boolean>;
  showDistances: Ref<boolean>;
  openNextSelection: Ref<boolean>;
  counts: ComputedRef<SelectionCounts>;
  toggleSelection: () => void;
  setFilter: (filter: SelectionFilter) => void;
  toggleOpenNextSelection: () => void;
  toggleShowBoundingBox: () => void;
  toggleShowDistances: () => void;
  deselect: (selInfo: SelectionInfo, alsoRemove?: boolean) => void;
  deselectAll: () => void;
  updateBoundingBox: () => void;
  updateDistances: () => void;
  removeObjectSelections: (objectName: string) => void;
};

export const selectionToolsKey: InjectionKey<SelectionToolsContext> =
  Symbol("cadquery.selectionTools");

export type SelectionToolsOptions = {
  viewer: Ref<InstanceType<typeof ModelViewerWrapper> | null>;
  /**
   * Passed in rather than injected: this provider is created in App.vue's own
   * setup, and a root component cannot inject what it itself provides.
   */
  sceneDocument: ShallowRef<Document>;
  setDisableTap: (value: boolean) => void;
  onFindModel: (name: string) => void;
};

export function createSelectionToolsProvider(
  options: SelectionToolsOptions,
): SelectionToolsContext {
  const { viewer, sceneDocument, setDisableTap, onFindModel } = options;

  const selected = ref<SelectionInfo[]>([]);
  const selectionEnabled = ref(false);
  const selectFilter = ref<SelectionFilter>("any");
  const showBoundingBox = ref(false);
  const showDistances = ref(true);
  /** "Reveal the next clicked object in the list" mode. */
  const openNextSelection = ref(false);
  let selectionEnabledBeforeReveal = false;

  const counts = computed<SelectionCounts>(() => ({
    face: selected.value.filter((s) => s.kind === "face").length,
    edge: selected.value.filter((s) => s.kind === "edge").length,
    vertex: selected.value.filter((s) => s.kind === "vertex").length,
  }));

  // --- picking --------------------------------------------------------------

  let mouseDownAt: [number, number] | null = null;
  let mouseDownTime = 0;
  const raycaster = new Raycaster();

  function mouseDownListener(event: MouseEvent) {
    mouseDownAt = [event.clientX, event.clientY];
    mouseDownTime = performance.now();
  }

  function mouseUpListener(event: MouseEvent) {
    // Treat a drag or a long press as camera movement, not a pick.
    if (mouseDownAt) {
      const [x, y] = mouseDownAt;
      mouseDownAt = null;
      if (
        Math.abs(event.clientX - x) > 5 ||
        Math.abs(event.clientY - y) > 5 ||
        performance.now() - mouseDownTime > 500
      ) {
        return;
      }
    }
    if (!selectionEnabled.value) return;

    const scene = viewer.value?.scene;
    if (!scene) return;

    // Vertices and edges have no area, so the pick radius scales with how far
    // away the camera is.
    let paramScale = 1;
    const lookAtCenter = scene.getTarget().clone().add(scene.target.position);
    paramScale = scene.camera.position.distanceTo(lookAtCenter) / 150;

    const filter = selectFilter.value;
    raycaster.params.Line.threshold = filter === "any" || filter === "edges" ? paramScale : 0;
    raycaster.params.Points.threshold =
      filter === "any" ? paramScale * 2 : filter === "vertices" ? paramScale : 0;

    const ndcCoords = scene.getNDC(event.clientX, event.clientY);
    raycaster.setFromCamera(ndcCoords, scene.camera);
    if (!scene.camera.isPerspectiveCamera) {
      // FIXME: still inaccurate for off-centre clicks under an ortho camera.
      raycaster.ray.direction.copy(scene.camera.getWorldDirection(new Vector3()));
    }

    const kindMatches = (type: string) => {
      const isFace = type === "Mesh" || type === "SkinnedMesh";
      const isEdge = type === "Line" || type === "LineSegments";
      const isVertex = type === "Points";
      if (filter === "any") return isFace || isEdge || isVertex;
      if (filter === "faces") return isFace;
      if (filter === "edges") return isEdge;
      return isVertex;
    };

    const objects: Object3D[] = [];
    scene.traverse((obj) => {
      if (obj.userData.noHit !== true && kindMatches(obj.type)) objects.push(obj);
    });

    (raycaster as unknown as { firstHitOnly: boolean }).firstHitOnly = true;
    const hits = raycaster.intersectObjects(objects, false);
    const hit = hits
      .filter((h: Intersection<Object3D>) => {
        if (!h.object) return false;
        const isFace = h.object.type === "Mesh" || h.object.type === "SkinnedMesh";
        return (!isFace || h.object.visible) && kindMatches(h.object.type);
      })
      // Faces are far easier to hit than zero-width edges and vertices, so bias
      // the ordering to let the smaller features win ties.
      .sort((a, b) => {
        const score = (h: Intersection<Object3D>) => {
          let s = h.distance;
          if (h.object.type === "Mesh" || h.object.type === "SkinnedMesh") s += paramScale;
          if (h.object.type === "Line" || h.object.type === "LineSegments") s += paramScale / 2;
          return s;
        };
        return score(a) - score(b);
      })[0] as Intersection<MObject3D> | undefined;

    if (!openNextSelection.value) {
      const selInfo = hit ? hitToSelectionInfo(hit) : null;
      if (hit && selInfo !== null) {
        const wasSelected = selected.value.some((m) => m.getKey() === selInfo.getKey());
        if (wasSelected) deselect(selInfo);
        else select(selInfo);
      } else {
        deselectAll();
      }
      updateBoundingBox();
      updateDistances();
    } else if (hit) {
      const name = getOwningModelTag(hit.object as unknown as TaggedObject3D);
      if (name) onFindModel(name);
      toggleOpenNextSelection();
    }
    scene.queueRender();
  }

  function select(selInfo: SelectionInfo) {
    if (!selected.value.some((m) => m.getKey() === selInfo.getKey())) {
      // markRaw, or Vue turns the whole three.js object graph hanging off this
      // SelectionInfo into reactive proxies. Only the list identity needs to be
      // reactive; nothing renders the three.js object itself.
      selected.value.push(markRaw(selInfo));
    }
    highlight(selInfo);
  }

  function deselect(selInfo: SelectionInfo, alsoRemove = true) {
    if (alsoRemove) {
      const index = selected.value.findIndex((m) => m.getKey() === selInfo.getKey());
      if (index !== -1) selected.value.splice(index, 1);
    }
    highlightUndo(selInfo);
  }

  function deselectAll(alsoRemove = true) {
    for (const selInfo of selected.value.slice()) deselect(selInfo, alsoRemove);
  }

  function removeObjectSelections(objectName: string) {
    for (const selInfo of selected.value.filter((s) => s.getObjectName() === objectName)) {
      deselect(selInfo);
    }
    updateBoundingBox();
    updateDistances();
  }

  // --- modes ----------------------------------------------------------------

  function toggleSelection() {
    if (!viewer.value?.elem) return;
    selectionEnabled.value = !selectionEnabled.value;
    setDisableTap(selectionEnabled.value);
  }

  function setFilter(filter: SelectionFilter) {
    if (selectFilter.value === filter) {
      toggleSelection();
      return;
    }
    selectFilter.value = filter;
    if (!selectionEnabled.value) toggleSelection();
  }

  function toggleOpenNextSelection() {
    if (!openNextSelection.value) {
      selectionEnabledBeforeReveal = selectionEnabled.value;
      openNextSelection.value = true;
      if (!selectionEnabled.value) toggleSelection();
    } else {
      openNextSelection.value = false;
      if (selectionEnabled.value !== selectionEnabledBeforeReveal) toggleSelection();
      selectionEnabledBeforeReveal = false;
    }
  }

  function toggleShowBoundingBox() {
    showBoundingBox.value = !showBoundingBox.value;
    updateBoundingBox();
  }

  function toggleShowDistances() {
    showDistances.value = !showDistances.value;
    updateDistances();
  }

  // --- bounding box overlay -------------------------------------------------

  let boundingBoxLines: Record<string, number> = {};

  function updateBoundingBox() {
    if (!showBoundingBox.value) {
      for (const lineId of Object.values(boundingBoxLines)) viewer.value?.removeLine3D(lineId);
      boundingBoxLines = {};
      return;
    }
    let bb: Box3;
    let toRemove = Object.keys(boundingBoxLines);
    if (selected.value.length > 0) {
      bb = new Box3();
      for (const hit of selected.value) bb.union(hit.getBox());
    } else {
      const boundingBox = SceneMgr.getBoundingBox(sceneDocument.value);
      if (!boundingBox) return;
      bb = boundingBox;
    }
    const corners = [
      [bb.min.x, bb.min.y, bb.min.z],
      [bb.min.x, bb.min.y, bb.max.z],
      [bb.min.x, bb.max.y, bb.min.z],
      [bb.min.x, bb.max.y, bb.max.z],
      [bb.max.x, bb.min.y, bb.min.z],
      [bb.max.x, bb.min.y, bb.max.z],
      [bb.max.x, bb.max.y, bb.min.z],
      [bb.max.x, bb.max.y, bb.max.z],
    ];
    // Axis order is CAD X / Z / Y — the viewer presents glTF Y-up as CAD Z-up.
    const edgesByAxis = [
      [[0, 4], [1, 5], [2, 6], [3, 7]],
      [[0, 2], [1, 3], [4, 6], [5, 7]],
      [[0, 1], [2, 3], [4, 5], [6, 7]],
    ];

    for (const axisIndex of edgesByAxis.keys()) {
      let axisEdges = edgesByAxis[axisIndex] ?? [];
      let edge: number[] = axisEdges[0] ?? [];
      // Draw one edge per axis: the second closest to the camera, so the label
      // sits on a visible edge rather than the one nearest the viewer.
      for (let i = 0; i < 2; i++) {
        if (axisEdges.length === 0) break;
        edge = axisEdges[0] ?? [];
        let edgeDist = Infinity;
        const cameraPos = viewer.value?.scene?.camera?.position ?? new Vector3();
        for (const testEdge of axisEdges) {
          if (!testEdge || testEdge.length < 2) continue;
          const cornerA = corners[testEdge[0] ?? 0];
          const cornerB = corners[testEdge[1] ?? 0];
          if (!cornerA || !cornerB) continue;
          const mid = new Vector3(...(cornerA as [number, number, number]))
            .add(new Vector3(...(cornerB as [number, number, number])))
            .multiplyScalar(0.5);
          const newDist = cameraPos.distanceTo(mid);
          if (newDist < edgeDist) {
            edge = testEdge;
            edgeDist = newDist;
          }
        }
        axisEdges = axisEdges.filter((e) => e !== edge);
      }
      if (!edge || edge.length < 2) continue;
      const cornerA = corners[edge[0] ?? 0];
      const cornerB = corners[edge[1] ?? 0];
      if (!cornerA || !cornerB) continue;
      const from = new Vector3(...(cornerA as [number, number, number]));
      const to = new Vector3(...(cornerB as [number, number, number]));
      const length = to.clone().sub(from).length();
      if (length < 0.05) continue;
      const colorArray = [AxesColors.x, AxesColors.y, AxesColors.z][axisIndex];
      const color = colorArray ? colorArray[1] : [255, 255, 255];
      const lineCacheKey = JSON.stringify([from, to]);
      if (boundingBoxLines[lineCacheKey]) {
        toRemove = toRemove.filter((l) => l !== lineCacheKey);
      } else {
        const newLineId = viewer.value?.addLine3D(from, to, `${length.toFixed(1)}mm`, {
          stroke: `rgb(${(color ?? [255, 255, 255]).join(",")})`,
          "stroke-width": "2",
        });
        if (newLineId) boundingBoxLines[lineCacheKey] = newLineId;
      }
    }
    for (const lineLocator of toRemove) {
      const id = boundingBoxLines[lineLocator];
      if (id !== undefined && viewer.value?.removeLine3D(id)) delete boundingBoxLines[lineLocator];
    }
  }

  // --- distance overlay -----------------------------------------------------

  let distanceLines: Record<string, number> = {};

  function updateDistances() {
    if (!showDistances.value || selected.value.length !== 2) {
      for (const lineId of Object.values(distanceLines)) viewer.value?.removeLine3D(lineId);
      distanceLines = {};
      return;
    }
    let toRemove = Object.keys(distanceLines);

    function ensureLine(from: Vector3, to: Vector3, text: string, color: string) {
      const lineCacheKey = JSON.stringify([from, to]);
      if (distanceLines[lineCacheKey]) {
        toRemove = toRemove.filter((l) => l !== lineCacheKey);
      } else {
        const id = viewer.value?.addLine3D(from, to, text, {
          stroke: color,
          "stroke-width": "2",
          "stroke-dasharray": "5",
        });
        if (id) distanceLines[lineCacheKey] = id;
      }
    }

    const a = selected.value[0];
    const b = selected.value[1];
    const scene = viewer.value?.scene;
    if (!a || !b || !scene) return;
    // defineExpose widens ModelScene past its private members; the runtime object
    // is the real thing.
    const { min, center, max } = distances(a, b, scene as unknown as ModelScene);
    if (max[0] && max[1]) ensureLine(max[0], max[1], `${max[1].distanceTo(max[0]).toFixed(1)}mm`, "orange");
    if (center[0] && center[1])
      ensureLine(center[0], center[1], `${center[1].distanceTo(center[0]).toFixed(1)}mm`, "green");
    if (min[0] && min[1]) ensureLine(min[0], min[1], `${min[1].distanceTo(min[0]).toFixed(1)}mm`, "cyan");

    for (const lineLocator of toRemove) {
      const id = distanceLines[lineLocator];
      if (id !== undefined) viewer.value?.removeLine3D(id);
      delete distanceLines[lineLocator];
    }
  }

  // --- viewer wiring --------------------------------------------------------

  let firstLoad = true;
  let boundElem: ModelViewerElement | null = null;
  let cameraChangeWaiting = false;
  let cameraChangeLast = 0;

  function onCameraChange() {
    // Recomputing the box is slow, so wait for the camera (and its inertia) to settle.
    cameraChangeLast = performance.now();
    if (cameraChangeWaiting) return;
    cameraChangeWaiting = true;
    const waitingHandler = () => {
      if (performance.now() - cameraChangeLast > 250) {
        updateBoundingBox();
        cameraChangeWaiting = false;
      } else {
        setTimeout(waitingHandler, 100);
      }
    };
    setTimeout(waitingHandler, 100);
  }

  function onBeforeRender() {
    // A scene reload replaces every three.js object, so re-resolve the selected
    // ones by identity tag and re-apply their highlight.
    for (const sel of selected.value.slice()) {
      const scene = viewer.value?.scene;
      if (!scene) continue;
      let foundObject: MObject3D | null = null;
      scene.traverse((obj) => {
        if (sel.matches(obj as unknown as MObject3D)) foundObject = obj as unknown as MObject3D;
      });
      if (foundObject) {
        sel.object = markRaw(foundObject);
        highlight(sel);
      } else {
        selected.value = selected.value.filter((m) => m.getKey() !== sel.getKey());
      }
    }
    if (firstLoad) {
      toggleShowBoundingBox();
      firstLoad = false;
    }
  }

  function bindViewer(current: InstanceType<typeof ModelViewerWrapper> | null) {
    if (!isViewerReady(current)) return;
    current.onElemReady((elem: ModelViewerElement) => {
      // Keyed on the element, not a one-shot flag: emptying and refilling the
      // scene remounts the wrapper, and a flag left picking wired to the
      // discarded element — clicks then did nothing at all.
      if (boundElem === elem) return;
      unbindElem();
      boundElem = elem;
      elem.addEventListener("mousedown", mouseDownListener);
      elem.addEventListener("mouseup", mouseUpListener);
      elem.addEventListener("before-render", onBeforeRender);
      elem.addEventListener("camera-change", onCameraChange);
    });
  }

  function unbindElem() {
    if (!boundElem) return;
    boundElem.removeEventListener("mousedown", mouseDownListener);
    boundElem.removeEventListener("mouseup", mouseUpListener);
    boundElem.removeEventListener("before-render", onBeforeRender);
    boundElem.removeEventListener("camera-change", onCameraChange);
    boundElem = null;
  }

  watch(viewer, bindViewer, { immediate: true });

  const ctx: SelectionToolsContext = {
    selected,
    selectionEnabled,
    selectFilter,
    showBoundingBox,
    showDistances,
    openNextSelection,
    counts,
    toggleSelection,
    setFilter,
    toggleOpenNextSelection,
    toggleShowBoundingBox,
    toggleShowDistances,
    deselect,
    deselectAll,
    updateBoundingBox,
    updateDistances,
    removeObjectSelections,
  };
  provide(selectionToolsKey, ctx);
  return ctx;
}

export function useSelectionTools(): SelectionToolsContext {
  const ctx = inject(selectionToolsKey);
  if (!ctx) throw new Error("useSelectionTools() called without provider");
  return ctx;
}
