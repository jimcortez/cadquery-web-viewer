const STORAGE_KEY = "cadquery-viewer-env-images-v1";
const MAX_ENTRIES = 8;
const MAX_BYTES_PER_ENTRY = 2 * 1024 * 1024;

export type CachedEnvironmentImage = {
  id: string;
  name: string;
  dataUrl: string;
};

function loadAll(): CachedEnvironmentImage[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as CachedEnvironmentImage[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function saveAll(entries: CachedEnvironmentImage[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(entries));
}

export function listCachedEnvironmentImages(): CachedEnvironmentImage[] {
  return loadAll();
}

export function getCachedEnvironmentUrl(id: string): string | undefined {
  return loadAll().find((e) => e.id === id)?.dataUrl;
}

export async function addCachedEnvironmentImage(file: File): Promise<CachedEnvironmentImage> {
  const dataUrl = await readFileAsDataUrl(file);
  const approxBytes = Math.ceil((dataUrl.length * 3) / 4);
  if (approxBytes > MAX_BYTES_PER_ENTRY) {
    throw new Error(`Image is too large (max ${MAX_BYTES_PER_ENTRY / (1024 * 1024)} MB)`);
  }
  const entry: CachedEnvironmentImage = {
    id: `env-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    name: file.name,
    dataUrl,
  };
  let entries = loadAll();
  entries.unshift(entry);
  if (entries.length > MAX_ENTRIES) entries = entries.slice(0, MAX_ENTRIES);
  saveAll(entries);
  return entry;
}

export function removeCachedEnvironmentImage(id: string) {
  saveAll(loadAll().filter((e) => e.id !== id));
}

export function clearCachedEnvironmentImages() {
  localStorage.removeItem(STORAGE_KEY);
}

function readFileAsDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = () => reject(reader.error ?? new Error("Failed to read file"));
    reader.readAsDataURL(file);
  });
}

/** Built-in environment presets (model-viewer shared assets). */
export const ENV_PRESET_DEFAULT = "";
export const ENV_PRESET_NEUTRAL = "neutral";
export const ENV_PRESET_LEGACY = "legacy";

export type EnvironmentPresetId =
  | typeof ENV_PRESET_DEFAULT
  | typeof ENV_PRESET_NEUTRAL
  | typeof ENV_PRESET_LEGACY
  | `cache:${string}`
  | (string & {});

export function environmentImageFromPreset(preset: EnvironmentPresetId): string {
  if (preset === ENV_PRESET_DEFAULT) return "";
  if (preset === ENV_PRESET_NEUTRAL) return ENV_PRESET_NEUTRAL;
  if (preset === ENV_PRESET_LEGACY) return ENV_PRESET_LEGACY;
  if (typeof preset === "string" && preset.startsWith("cache:")) {
    return getCachedEnvironmentUrl(preset.slice("cache:".length)) ?? "";
  }
  if (typeof preset === "string" && (preset.startsWith("http") || preset.startsWith("data:") || preset.startsWith("blob:"))) {
    return preset;
  }
  return "";
}
