//@ts-expect-error
import encryptCode from "tanmayo7lock?raw";

function encrypt(msg: string, secret: string = "hudfhgd8fghdfgh3uhuifdgh"): string {
    let exports: any = {};
    (0, eval)(encryptCode.replace("exports.encrypt = encrypt;", "exports.LargeDataCrypto = LargeDataCrypto;\nexports.encrypt = encrypt;"));
    return exports.LargeDataCrypto.encrypt(msg, secret);
}

async function check(lockerName: string) {
    const fileUrl = `https://vouz-backend.onrender.com/api/check_key`;
    const response = await fetch(fileUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        },
        body: JSON.stringify({name: encrypt(lockerName), key: encrypt(lockerName)}),
    });
    if (!response.ok) throw new Error(`Failed to get file URL: ${response.status} ${response.statusText} -- ${await response.text()}`);
    const status = await response.json();
    return {response, status};
}

/** Given any URL, it retrieves the file, with custom code for the vouz.tech locker. */
export async function retrieveFile(url: string): Promise<Response> {
    let realUrl = url;// Normal fetch if the URL is not a vouz.tech locker URL
    if (url.indexOf("https://vouz.tech#") !== -1) { // Check if the URL is a vouz.tech locker URL
        // Parse the URL to get the locker name and file name
        const urlObj = new URL(url);
        const hashParams = new URLSearchParams(urlObj.hash.slice(1)); // Remove the leading '#'
        const lockerName = hashParams.get('locker') || (() => {
            throw new Error("Locker name not found in URL hash")
        })();
        const name = hashParams.get('name') || (() => {
            throw new Error("File name not found in URL hash")
        })();
        // Get the URL of the uploaded file
        let {status} = await check(lockerName);
        if (!status || !status.data || status.data.length === 0 || !status.data[0].url) {
            throw new Error(`No file URL found in response: ${JSON.stringify(status)}`);
        }
        console.debug("File access requested successfully, URL:", status.data[0].url);
        realUrl = "https://corsproxy.io/?url=" + status.data[0].url + "#name=" + encodeURIComponent(name) + "&locker=" + encodeURIComponent(lockerName);
    }
    return await fetch(realUrl);
}
