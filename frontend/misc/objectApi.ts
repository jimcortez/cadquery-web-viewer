import { settings } from "./settings";

export type ObjectVersionSummary = {
  version: number;
  hash: string;
  created_at: string;
};

export type ServerObjectDescriptor = {
  name: string;
  notes: string | null;
  settings: Record<string, string | number | null>;
  version: number;
  hash: string;
  kwargs: Record<string, unknown>;
  created_at: string;
  in_memory: boolean;
  on_disk: boolean;
  versions: ObjectVersionSummary[];
};

export type VersionOption = {
  version: number;
  hash: string;
  label: string;
};

export function objectNameFromUrl(url: string): string {
  try {
    const pathname = new URL(url).pathname;
    const base = pathname.split("/").pop() ?? "unknown";
    return base.replace(/\.(glb|gltf)$/i, "") || "unknown";
  } catch {
    const base = url.split("/").pop() ?? "unknown";
    return base.replace(/\.(glb|gltf)$/i, "") || "unknown";
  }
}

export function allVersions(desc: ServerObjectDescriptor): VersionOption[] {
  const latest: VersionOption = {
    version: desc.version,
    hash: desc.hash,
    label: `v${desc.version} (latest)`,
  };
  const older = desc.versions.map((v) => ({
    version: v.version,
    hash: v.hash,
    label: `v${v.version}`,
  }));
  return [latest, ...older];
}

export async function resolveApiBaseUrl(): Promise<string | null> {
  const sett = await settings;
  for (const entry of sett.preload) {
    if (entry.startsWith("dev+") || entry.startsWith("dev ")) {
      try {
        const base = new URL(entry.slice(4).trim());
        return base.origin;
      } catch {
        continue;
      }
    }
  }
  const origin = window.location.origin;
  try {
    const eventsUrl = new URL("/api/events", origin);
    const response = await fetch(eventsUrl, { method: "HEAD" });
    const ct = response.headers.get("Content-Type") || "";
    if (response.ok && ct.startsWith("text/event-stream")) {
      return origin;
    }
  } catch {
    /* no backend on same origin */
  }
  return null;
}

export async function fetchObjectList(baseUrl: string): Promise<ServerObjectDescriptor[]> {
  const url = new URL("/api/object", baseUrl);
  const response = await fetch(url.toString(), {
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(`Failed to list objects: HTTP ${response.status}`);
  }
  const payload = (await response.json()) as { objects?: ServerObjectDescriptor[] };
  return payload.objects ?? [];
}

export async function importObjectFromUrl(
  baseUrl: string,
  name: string,
  sourceUrl: string,
): Promise<{ name: string; version: number; hash: string }> {
  const url = new URL(`/api/object/${encodeURIComponent(name)}`, baseUrl);
  const response = await fetch(url.toString(), {
    method: "PUT",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ url: sourceUrl }),
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Import failed: HTTP ${response.status}`);
  }
  return (await response.json()) as { name: string; version: number; hash: string };
}
