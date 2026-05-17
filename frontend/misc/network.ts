import {settings} from "./settings";

const batchTimeout = 250; // ms

type SceneEvent = {
    type: string;
    name?: string;
    hash?: string;
    version?: number;
    except_names?: string[];
};

export class NetworkUpdateEventModel {
    name: string;
    url: string | Blob;
    hash: string | null;
    isRemove: boolean | null;

    constructor(name: string, url: string | Blob, hash: string | null, isRemove: boolean | null) {
        this.name = name;
        this.url = url;
        this.hash = hash;
        this.isRemove = isRemove;
    }
}

export class NetworkUpdateEvent extends Event {
    models: NetworkUpdateEventModel[];
    disconnect: () => void;

    constructor(models: NetworkUpdateEventModel[], disconnect: () => void) {
        super("update");
        this.models = models;
        this.disconnect = disconnect;
    }
}

function versionFromObjectUrl(url: string | Blob): number | null {
    if (url instanceof Blob) return null;
    try {
        const raw = new URL(url).searchParams.get("version");
        if (raw == null) return null;
        const v = parseInt(raw, 10);
        return Number.isFinite(v) ? v : null;
    } catch {
        return null;
    }
}

/** Listens for updates and emits events when a model changes */
export class NetworkManager extends EventTarget {
    private knownObjectHashes: { [name: string]: string | null } = {};
    private knownObjectVersions: { [name: string]: number } = {};
    private knownObjectNames = new Set<string>();
    private bufferedUpdates: NetworkUpdateEventModel[] = [];
    private batchTimeout: number | null = null;

    async load(url: string | Blob) {
        if (!(url instanceof Blob) && (url.startsWith("dev+") || url.startsWith("dev "))) {
            let baseUrl = new URL(url.slice(4).trim());
            if (baseUrl.pathname.endsWith("/api/updates")) {
                baseUrl.pathname = baseUrl.pathname.replace(/\/api\/updates\/?$/, "/api/events");
            } else if (!baseUrl.pathname.endsWith("/api/events")) {
                baseUrl.pathname = baseUrl.pathname.replace(/\/?$/, "") + "/api/events";
            }
            baseUrl.search = "";
            await this.monitorDevServer(baseUrl);
        } else {
            let name;
            let hash = null;
            if (url instanceof Blob) {
                if (url instanceof File) name = (url as File).name
                else name = `blob-${Math.random()}`;
                name = name.replace('.glb', '').replace('.gltf', '');
            } else {
                let hashParams: URLSearchParams
                try {
                    let urlObj = new URL(url, window.location.href);
                    hashParams = new URLSearchParams(urlObj.hash.slice(1));
                } catch (e) {
                    hashParams = new URLSearchParams();
                }
                if (hashParams.has("name")) {
                    name = hashParams.get("name") || `unknown-${Math.random()}`;
                } else {
                    name = url.split("/").pop();
                }
                name = name?.split(".")[0] || `unknown-${Math.random()}`;
                let response = await fetch(url, {method: "HEAD"});
                hash = response.headers.get("etag");
            }
            this.foundModel(name, hash, url, false);
        }
    }

    private handleSceneEvent(data: SceneEvent, origin: string, disconnect: () => void) {
        switch (data.type) {
            case "server.shutdown":
                this.foundModel("", null, "", null, disconnect);
                break;
            case "scene.cleared": {
                const except = new Set(data.except_names || []);
                const removals: NetworkUpdateEventModel[] = [];
                for (const name of this.knownObjectNames) {
                    if (!except.has(name)) {
                        removals.push(
                            new NetworkUpdateEventModel(name, "", this.knownObjectHashes[name] ?? null, true),
                        );
                    }
                }
                for (const name of Object.keys(this.knownObjectHashes)) {
                    delete this.knownObjectHashes[name];
                }
                for (const name of Object.keys(this.knownObjectVersions)) {
                    delete this.knownObjectVersions[name];
                }
                for (const name of this.knownObjectNames) {
                    if (!except.has(name)) this.knownObjectNames.delete(name);
                }
                if (removals.length > 0) {
                    this.dispatchEvent(new NetworkUpdateEvent(removals, disconnect));
                }
                break;
            }
            case "object.removed":
                if (data.name) {
                    const objectUrl = new URL(
                        "/api/object/" + encodeURIComponent(data.name),
                        origin,
                    );
                    this.foundModel(data.name, data.hash ?? null, objectUrl.toString(), true, disconnect);
                }
                break;
            case "object.created":
            case "object.versioned":
                if (data.name) {
                    const objectUrl = new URL(
                        "/api/object/" + encodeURIComponent(data.name),
                        origin,
                    );
                    if (data.version != null) {
                        objectUrl.searchParams.set("version", String(data.version));
                    }
                    this.foundModel(data.name, data.hash ?? null, objectUrl.toString(), false, disconnect);
                }
                break;
            default:
                console.warn("Unknown scene event type", data);
        }
    }

    private async monitorDevServer(url: URL, stop: () => boolean = () => false) {
        while (!stop()) {
            let monitorEveryMs = (await settings).monitorEveryMs;
            try {
                const controller = new AbortController();
                let response = await fetch(url.toString(), {signal: controller.signal});
                if (response.status === 200) {
                    let lines = readLinesStreamings(response.body!.getReader());
                    for await (let line of lines) {
                        if (stop()) break;
                        if (!line || !line.startsWith("data:")) continue;
                        let data: SceneEvent = JSON.parse(line.slice(5).trim());
                        this.handleSceneEvent(data, url.origin, async () => {
                            controller.abort();
                        });
                    }
                } else {
                    await new Promise(resolve => setTimeout(resolve, 10 * monitorEveryMs));
                }
                controller.abort();
            } catch (e) {
            }
            await new Promise(resolve => setTimeout(resolve, monitorEveryMs));
        }
    }

    private foundModel(name: string, hash: string | null, url: string | Blob, isRemove: boolean | null, disconnect: () => void = () => {
    }) {
        if (isRemove === null) {
            this.bufferedUpdates = this.bufferedUpdates.filter(m => m.name !== name);
            let upd = new NetworkUpdateEventModel(name, url, hash, isRemove);
            this.bufferedUpdates.push(upd);
            this.dispatchEvent(new CustomEvent("update-early", {detail: this.bufferedUpdates}));
            if (this.batchTimeout !== null) clearTimeout(this.batchTimeout);
            this.batchTimeout = setTimeout(() => {
                this.dispatchEvent(new NetworkUpdateEvent(this.bufferedUpdates, disconnect));
                this.bufferedUpdates = [];
            }, batchTimeout);
            return;
        }

        this.bufferedUpdates = this.bufferedUpdates.filter(m => m.name !== name);

        let upd = new NetworkUpdateEventModel(name, url, hash, isRemove);
        this.bufferedUpdates.push(upd);
        this.dispatchEvent(new CustomEvent("update-early", {detail: this.bufferedUpdates}));

        if (this.batchTimeout !== null) clearTimeout(this.batchTimeout);
        this.batchTimeout = setTimeout(() => {
            for (let model of this.bufferedUpdates) {
                if (model.isRemove == false) {
                    const version = versionFromObjectUrl(model.url);
                    const sameHash =
                        model.hash != null && model.hash === this.knownObjectHashes[model.name];
                    const sameVersion =
                        version != null && version === this.knownObjectVersions[model.name];
                    if (sameHash && (version == null || sameVersion)) {
                        let foundFirst = false;
                        this.bufferedUpdates = this.bufferedUpdates.filter(m => {
                            if (m === model) {
                                if (!foundFirst) {
                                    foundFirst = true;
                                    return false;
                                }
                            }
                            return true;
                        });
                        continue;
                    }
                }
                if (model.isRemove == true) {
                    delete this.knownObjectHashes[model.name];
                    delete this.knownObjectVersions[model.name];
                    this.knownObjectNames.delete(model.name);
                } else if (model.isRemove == false) {
                    this.knownObjectHashes[model.name] = model.hash;
                    const version = versionFromObjectUrl(model.url);
                    if (version != null) this.knownObjectVersions[model.name] = version;
                    else delete this.knownObjectVersions[model.name];
                    this.knownObjectNames.add(model.name);
                }
            }

            this.dispatchEvent(new NetworkUpdateEvent(this.bufferedUpdates, disconnect));
            this.bufferedUpdates = [];
        }, batchTimeout);
    }
}

async function* readLinesStreamings(reader: ReadableStreamDefaultReader<Uint8Array>) {
    const decoder = new TextDecoder();
    let pending = "";
    while (true) {
        const {value, done} = await reader.read();
        if (done) break;
        if (!value?.length) continue;
        pending += decoder.decode(value, {stream: true});
        let newlineAt = pending.indexOf("\n");
        while (newlineAt !== -1) {
            yield pending.slice(0, newlineAt);
            pending = pending.slice(newlineAt + 1);
            newlineAt = pending.indexOf("\n");
        }
    }
    pending += decoder.decode();
    if (pending.length > 0) {
        yield pending;
    }
}
