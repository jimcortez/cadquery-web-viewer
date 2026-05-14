// These are the default values for the settings, which are overridden below

const firstTimeNames: Array<string> = []; // Needed for array values, which clear the array when overridden
export const settings = (async () => {
    let settings = {
        preload: [
            // @ts-ignore
            // new URL('../../assets/fox.glb', import.meta.url).href,
            // @ts-ignore
            // new URL('../../assets/logo_build/base.glb', import.meta.url).href,
            // @ts-ignore
            // new URL('../../assets/logo_build/location.glb', import.meta.url).href,
            // @ts-ignore
            // new URL('../../assets/logo_build/img.glb', import.meta.url).href,
            // Websocket URLs automatically listen for new models from the python backend
            '<auto>', // Get the default preload URL if not overridden
        ],
        loadHelpers: true,
        edgeWidth: 0, /* The default line size for edges, set to 0 to use basic gl.LINEs */
        displayLoadingEveryMs: 1000, /* How often to display partially loaded models */
        monitorEveryMs: 100,
        monitorOpenTimeoutMs: 1000,
        // ModelViewer settings
        autoplay: true, // Global animation toggle
        arModes: 'webxr scene-viewer quick-look',
        zoomSensitivity: 0.25,
        orbitSensitivity: 1,
        panSensitivity: 1,
        exposure: 1,
        shadowIntensity: 0,
        // Nice low-res outdoor/high-contrast HDRI image (CC0 licensed) for lighting
        environment: new URL('../../assets/qwantani_afternoon_1k_hdr.jpg', import.meta.url).href,
        environmentIntensity: 1.0,
        // Uniform (1x1 pixel) medium gray background for visibility (following dark/light mode)
        skybox: (window.matchMedia("(prefers-color-scheme: dark)").matches ?
            "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABAQMAAAAl21bKAAAAA1BMVEU4ODiyn42XAAAACklEQVQI" +
            "12NgAAAAAgAB4iG8MwAAAABJRU5ErkJggg==" :
            "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABAQMAAAAl21bKAAAAA1BMVEW6urpaLVq8AAAACklEQVQI" +
            "12NgAAAAAgAB4iG8MwAAAABJRU5ErkJggg=="),
    };

    // Auto-override any settings from the URL (either GET parameters or hash)
    const url = new URL(window.location.href);
    url.searchParams.forEach((value, key) => {
        if (key in settings) (settings as any)[key] = parseSetting(key, value, settings);
    })
    if (url.hash.length > 0) { // Hash has bigger limits as it is not sent to the server
        const hash = url.hash.slice(1);
        const hashParams = new URLSearchParams(hash);
        hashParams.forEach((value, key) => {
            if (key in settings) (settings as any)[key] = parseSetting(key, value, settings);
        });
    }

    // Get the default preload URL if not overridden (requires a fetch that is avoided if possible)
    for (let i = 0; i < settings.preload.length; i++) {
        let url = settings.preload[i];
        // Ignore empty preload URLs to allow overriding default auto behavior
        if (url === '') {
            settings.preload = settings.preload.slice(0, i).concat(settings.preload.slice(i + 1));
            continue; // Skip this preload URL
        }
        // Handle special <auto> preload URL
        if (url === '<auto>') {
            const possibleBackend = new URL("/api/updates", window.location.origin)
            await fetch(possibleBackend, {method: "HEAD"}).then((response) => {
                const ct = response.headers.get("Content-Type") || "";
                if (response.ok && ct.startsWith("text/event-stream")) {
                    // Frontend served by the backend: default to this URL for updates
                    url = "dev+" + possibleBackend.href;
                }
            }).catch((error) => console.error("Failed to check for backend:", error));
            if (url === '<auto>') { // Fallback to the default preload URL of localhost
                url = "dev+http://localhost:32323";
            }
        }
        settings.preload[i] = url ?? "";
    }

    return settings;
})()

function parseSetting(name: string, value: string, settings: any): any {
    let arrayElem = name.endsWith(".0")
    if (arrayElem) name = name.slice(0, -2);
    let prevValue = (settings as any)[name];
    if (prevValue === undefined) throw new Error(`Unknown setting: ${name}`);
    if (Array.isArray(prevValue)) {
        if (!arrayElem) {
            let toExtend = []
            if (!firstTimeNames.includes(name)) {
                firstTimeNames.push(name);
            } else {
                toExtend = prevValue;
            }
            toExtend.push(parseSetting(name + ".0", value, settings));
            return toExtend;
        } else {
            prevValue = prevValue[0];
        }
    }
    switch (typeof prevValue) {
        case 'boolean':
            return value === 'true';
        case 'number':
            return Number(value);
        case 'string':
            return value;
        default:
            throw new Error(`Unknown setting type: ${typeof prevValue} -- ${prevValue}`);
    }
}
