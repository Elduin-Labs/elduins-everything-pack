#!/usr/bin/env python3
"""Print the draft project's own fields so we can see what Modrinth wants.

Project metadata is not secret; the token is, and is never printed.
"""
import json, os, sys, urllib.error, urllib.request

TOKEN = os.environ["MODRINTH_TOKEN"]
UA = "Elduin-Labs/elduins-everything-pack (one kid, one mac)"
PID = "8FaPoo3x"
VID = "knws3Wk5"


def get(url):
    req = urllib.request.Request(url, headers={"Authorization": TOKEN, "User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        return {"_error": e.code, "_body": e.read().decode()[:400]}


def patch(url, body):
    req = urllib.request.Request(url, method="PATCH", data=json.dumps(body).encode(),
                                 headers={"Authorization": TOKEN, "User-Agent": UA,
                                          "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return {"_ok": r.status}
    except urllib.error.HTTPError as e:
        return {"_error": e.code, "_body": e.read().decode()[:400]}


p3 = get(f"https://api.modrinth.com/v3/project/{PID}")
print("v3 project keys:", sorted(p3.keys()) if "_error" not in p3 else p3)
for k in ("status", "environment", "project_types", "side_types_migration_review_status"):
    if k in p3:
        print(f"  {k} = {p3[k]!r}")

v3 = get(f"https://api.modrinth.com/v3/version/{VID}")
print("\nv3 version keys:", sorted(v3.keys()) if "_error" not in v3 else v3)
for k in ("status", "environment", "loaders"):
    if k in v3:
        print(f"  {k} = {v3[k]!r}")

for attempt in (
    {"environment": "client_and_server"},
    {"environment": ["client", "server"]},
):
    print(f"\nPATCH v3 version {attempt} ->",
          patch(f"https://api.modrinth.com/v3/version/{VID}", attempt))
    print(f"PATCH v3 project {attempt} ->",
          patch(f"https://api.modrinth.com/v3/project/{PID}", attempt))
