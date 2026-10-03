#!/usr/bin/env python3
"""Create the Modrinth modpack project and upload a version.

Reads MODRINTH_TOKEN from the environment and never prints it. Creating a
project needs a token with the project-create scope; a CI token that can only
upload versions will fail at that step with a clear message, which is the point.
"""
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request

API = "https://api.modrinth.com/v2"
SLUG = "elduins-everything-pack"
TITLE = "Elduin's Everything Pack"
UA = "Elduin-Labs/elduins-everything-pack (one kid, one mac)"

TOKEN = os.environ.get("MODRINTH_TOKEN", "")
if not TOKEN:
    sys.exit("MODRINTH_TOKEN is not set. Refusing to run and pretend it worked.")
print("token fingerprint:", hashlib.sha256(TOKEN.encode()).hexdigest()[:12])

PACK = sys.argv[1] if len(sys.argv) > 1 else "elduins-everything-1.0.0.mrpack"
VERSION = os.environ.get("PACK_VERSION", "1.0.0")

BODY = """## Elduin's Everything Pack

Every mod Elduin has made, in one pack, with the optimization mods that play
nicely alongside them.

- 31 of Elduin's own mods, bundled in
- 13 other mods his mods need, linked from Modrinth
- 28 optimization mods

Mods tagged "optimization" that fight each other are left out on purpose.
VulkanMod cannot run beside Sodium, and Nvidium needs an Nvidia graphics card.

Minecraft 1.21.11, Fabric.
"""


def call(method, path, *, data=None, raw=None, ctype=None):
    url = path if path.startswith("http") else API + path
    req = urllib.request.Request(url, method=method)
    req.add_header("Authorization", TOKEN)
    req.add_header("User-Agent", UA)
    if raw is not None:
        req.data = raw
        if ctype:
            req.add_header("Content-Type", ctype)
    elif data is not None:
        req.data = json.dumps(data).encode()
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            text = r.read().decode()
            return json.loads(text) if text.strip() else {}
    except urllib.error.HTTPError as e:
        sys.exit(f"{method} {url} -> {e.code}\n{e.read().decode()[:600]}")


def multipart(fields, files):
    """fields: {name: str}. files: [(name, filename, bytes, content_type)]."""
    boundary = "----ElduinLabs" + hashlib.sha1(os.urandom(16)).hexdigest()
    out = bytearray()
    for name, value in fields.items():
        out += f"--{boundary}\r\n".encode()
        out += f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode()
        out += value.encode() + b"\r\n"
    for name, filename, blob, ct in files:
        out += f"--{boundary}\r\n".encode()
        out += (f'Content-Disposition: form-data; name="{name}"; '
                f'filename="{filename}"\r\n').encode()
        out += f"Content-Type: {ct}\r\n\r\n".encode()
        out += blob + b"\r\n"
    out += f"--{boundary}--\r\n".encode()
    return bytes(out), f"multipart/form-data; boundary={boundary}"


def find_project():
    req = urllib.request.Request(f"{API}/project/{SLUG}", headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


project = find_project()

if project is None:
    print("creating project", SLUG)
    data = {
        "slug": SLUG,
        "title": TITLE,
        "description": "Every mod Elduin has made, plus every optimization mod that works with them.",
        "body": BODY,
        "categories": ["kitchen-sink", "optimization"],
        "client_side": "required",
        "server_side": "optional",
        "license_id": "MIT",
        "project_type": "modpack",
        "is_draft": True,
        "initial_versions": [],
    }
    body, ctype = multipart({"data": json.dumps(data)}, [])
    project = call("POST", "/project", raw=body, ctype=ctype)
    print("created:", project["id"])
else:
    print("project already exists:", project["id"])

pid = project["id"]

# A new project reports both sides as "unknown" whatever the manifest said.
call("PATCH", f"/project/{pid}",
     data={"client_side": "required", "server_side": "optional"})
print("sides set")

if os.path.exists("icon.png"):
    call("PATCH", f"/project/{pid}/icon?ext=png",
         raw=open("icon.png", "rb").read(), ctype="image/png")
    print("icon uploaded")

existing = {v["version_number"] for v in call("GET", f"/project/{pid}/version")}
if VERSION in existing:
    print(f"version {VERSION} is already up — nothing to upload")
else:
    vdata = {
        "name": f"{TITLE} {VERSION}",
        "version_number": VERSION,
        "changelog": "Every mod Elduin has made, plus 28 optimization mods.",
        "dependencies": [],
        "game_versions": ["1.21.11"],
        "version_type": "release",
        "loaders": ["fabric"],
        "featured": True,
        "project_id": pid,
        "file_parts": ["file"],
        "primary_file": "file",
    }
    blob = open(PACK, "rb").read()
    body, ctype = multipart({"data": json.dumps(vdata)},
                            [("file", os.path.basename(PACK), blob,
                              "application/x-modrinth-modpack+zip")])
    v = call("POST", "/version", raw=body, ctype=ctype)
    print("uploaded version:", v["id"])

if project.get("status") == "draft":
    call("PATCH", f"/project/{pid}", data={"status": "processing"})
    print("submitted for review")

print(f"\nhttps://modrinth.com/modpack/{SLUG}")
print("New projects always wait in Modrinth's human review queue.")
