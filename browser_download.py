#!/usr/bin/env python3
"""Save the original giza ZIP through the already-open XDA browser page."""
import base64
import hashlib
import json
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent
URL = "https://xdaforums.com/attachments/amonet-giza-v1-3-zip.5551753/"
DESTINATION = ROOT / "prepared/unlock/amonet-giza-v1.3.zip"
PAGE_ID = "2"  # Returned by Chrome DevTools when this task opened the XDA page.


def evaluate(function):
    result = subprocess.run(
        ["npx", "-y", "--package=chrome-devtools-mcp@1.10.1", "chrome-devtools",
         "evaluate_script", function, "--pageId", PAGE_ID, "--output-format=json"],
        capture_output=True, text=True, check=True, timeout=40,
    )
    envelope = json.loads(result.stdout)
    message = envelope.get("message", "")
    if "```json\n" not in message:
        raise RuntimeError("Browser did not return a JSON result")
    return json.loads(message.split("```json\n", 1)[1].rsplit("\n```", 1)[0])


def main():
    state = evaluate("async () => {"
                     f"const r=await fetch({json.dumps(URL)});"
                     "if(!r.ok) throw new Error('Download failed: '+r.status);"
                     "const bytes=new Uint8Array(await r.arrayBuffer());"
                     "globalThis.__gizaFilePreparationDownload=bytes;"
                     "const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)))"
                     ".map(x=>x.toString(16).padStart(2,'0')).join('');"
                     "return {bytes:bytes.length,magic:Array.from(bytes.slice(0,4)),sha256:hash};}")
    if state["bytes"] != 30829874 or state["magic"] != [80, 75, 3, 4]:
        raise RuntimeError("Unexpected attachment size or ZIP header")
    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    temporary = DESTINATION.with_suffix(".zip.partial")
    chunk_size = 2 * 1024 * 1024
    digest = hashlib.sha256()
    with temporary.open("wb") as output:
        for offset in range(0, state["bytes"], chunk_size):
            limit = min(state["bytes"], offset + chunk_size)
            result = evaluate("() => {const b=globalThis.__gizaFilePreparationDownload;"
                              f"const offset={offset},limit={limit};let raw='';"
                              "for(let p=offset;p<limit;p+=32768)"
                              "raw+=String.fromCharCode(...b.slice(p,Math.min(limit,p+32768)));"
                              "return {offset,base64:btoa(raw)};}")
            data = base64.b64decode(result["base64"], validate=True)
            if result["offset"] != offset or len(data) != limit - offset:
                raise RuntimeError("Unexpected browser chunk")
            output.write(data)
            digest.update(data)
    if digest.hexdigest() != state["sha256"]:
        raise RuntimeError("Browser-to-host digest mismatch")
    temporary.replace(DESTINATION)
    evaluate("() => {delete globalThis.__gizaFilePreparationDownload;return {cleared:true};}")
    print(f"Saved original attachment: {DESTINATION.name}; {state['bytes']:,} bytes")
    print(f"SHA256: {digest.hexdigest()}")


if __name__ == "__main__":
    main()
