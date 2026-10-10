#!/usr/bin/env python3
"""Publishes a thin PBIR report to the owner's DRAFTS workspace only.

  addons/powerbi/publish-report.py "<project dir or .Report dir>"

- Uses the Power BI service principal (Fabric REST API). Creates the report the first time, updates it afterwards
  (matched by display name = the .Report folder name).
- Hard-locked to the workspace named in DRAFTS_WORKSPACE; it refuses anything else, so live workspaces are never touched.
- Thin reports only (definition.pbir byConnection "Data Source=powerbi://…/myorg/<workspace>;Initial Catalog=<model>").
  The connection is rewritten to "semanticmodelid=<id>" in the uploaded copy only (files on disk are not changed).
- Prints the report URL. Open it in the WORK browser to screenshot the pages.
"""
import json, os, re, shutil, subprocess, sys, tempfile, time, urllib.error, urllib.parse, urllib.request
from pathlib import Path

DRAFTS_WORKSPACE = ""  # read from PBI_DRAFTS_WORKSPACE in the secrets file (e.g. "Agent Drafts")
SECRETS = Path.home() / ".local/state/personal-agent/secrets/powerbi-sp.env"
FABRIC = "https://api.fabric.microsoft.com/v1"


def die(msg):
    sys.exit(f"publish-report: {msg}")


def env():
    vals = {}
    for line in SECRETS.read_text().splitlines():
        m = re.match(r"\s*([A-Z_]+)\s*=\s*\"?([^\"#]*)\"?", line)
        if m:
            vals[m[1]] = m[2].strip()
    return vals


def token(e):
    body = urllib.parse.urlencode({"grant_type": "client_credentials", "client_id": e["PBI_CLIENT_ID"],
                                   "client_secret": e["PBI_CLIENT_SECRET"],
                                   "scope": "https://api.fabric.microsoft.com/.default"}).encode()
    url = f"https://login.microsoftonline.com/{e['PBI_TENANT_ID']}/oauth2/v2.0/token"
    return json.load(urllib.request.urlopen(url, body, timeout=30))["access_token"]


def call(tok, method, url, body=None):
    req = urllib.request.Request(url if url.startswith("http") else FABRIC + url, method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
    try:
        r = urllib.request.urlopen(req, timeout=120)
        raw = r.read()
        return r.status, dict(r.headers), (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as err:
        die(f"{method} {url} -> HTTP {err.code}: {err.read().decode()[:500]}")


def wait(tok, status, headers, body):
    """Follows a 202 long-running operation until it finishes; returns the final result (if any)."""
    if status != 202:
        return body
    op = headers.get("x-ms-operation-id") or headers.get("X-Ms-Operation-Id")
    loc = headers.get("Location") or headers.get("location") or f"{FABRIC}/operations/{op}"
    for _ in range(60):
        time.sleep(int(headers.get("Retry-After", 3) or 3))
        _, _, st = call(tok, "GET", loc)
        if st.get("status") == "Succeeded":
            if op:
                s, _, res = call(tok, "GET", f"/operations/{op}/result")
                return res
            return st
        if st.get("status") in ("Failed", "Cancelled"):
            die(f"operation {st.get('status')}: {json.dumps(st.get('error', st))[:500]}")
    die("operation timed out")


def find(items, name):
    return next((i for i in items if i["displayName"].lower() == name.lower()), None)


def main():
    if len(sys.argv) != 2:
        die('usage: publish-report.py "<project dir or .Report dir>"')
    src = Path(sys.argv[1]).resolve()
    report_dir = src if src.name.endswith(".Report") else next(src.glob("*.Report"), None)
    if not report_dir or not (report_dir / "definition.pbir").exists():
        die(f"no .Report folder with definition.pbir in {src}")
    name = report_dir.name[: -len(".Report")]

    pbir = json.loads((report_dir / "definition.pbir").read_text())
    conn = pbir.get("datasetReference", {}).get("byConnection", {}).get("connectionString", "")
    m = re.search(r"myorg/([^;]+);\s*Initial Catalog=([^;]+)", conn)
    if not m:
        die("only thin reports are supported (definition.pbir byConnection to a published model)")
    model_ws_name, model_name = urllib.parse.unquote(m[1]).strip(), m[2].strip()

    e = env()
    global DRAFTS_WORKSPACE
    DRAFTS_WORKSPACE = e.get("PBI_DRAFTS_WORKSPACE", "").strip()
    if not DRAFTS_WORKSPACE:
        die("set PBI_DRAFTS_WORKSPACE (your drafts-only workspace name) in " + str(SECRETS))
    tok = token(e)
    _, _, wss = call(tok, "GET", "/workspaces")
    drafts = find(wss.get("value", []), DRAFTS_WORKSPACE)
    if not drafts:
        die(f'workspace "{DRAFTS_WORKSPACE}" not found or the service principal has no access to it '
            "(create it and add the service principal as Contributor)")
    model_ws = find(wss["value"], model_ws_name)
    if not model_ws:
        die(f'model workspace "{model_ws_name}" not visible to the service principal')
    _, _, models = call(tok, "GET", f"/workspaces/{model_ws['id']}/items?type=SemanticModel")
    model = find(models.get("value", []), model_name)
    if not model:
        die(f'semantic model "{model_name}" not found in "{model_ws_name}"')

    _, _, reports = call(tok, "GET", f"/workspaces/{drafts['id']}/items?type=Report")
    existing = find(reports.get("value", []), name)

    with tempfile.TemporaryDirectory() as tmp:
        copy = Path(tmp) / report_dir.name
        shutil.copytree(report_dir, copy, ignore=shutil.ignore_patterns(".pbi"))
        pbir["datasetReference"] = {"byConnection": {"connectionString": f"semanticmodelid={model['id']}"}}
        (copy / "definition.pbir").write_text(json.dumps(pbir, indent=2))
        mode = ["--mode", "update"] if existing else ["--mode", "create", "--display-name", name]
        out = subprocess.run(["powerbi-report-author", "pack", str(copy), *mode, "--raw"],
                             capture_output=True, text=True)
        if out.returncode:
            die(f"pack failed: {out.stderr or out.stdout}")
        payload = json.loads(out.stdout)
        payload = payload.get("body", payload)

    if existing:
        res = wait(tok, *call(tok, "POST", f"/workspaces/{drafts['id']}/reports/{existing['id']}/updateDefinition",
                              {"definition": payload["definition"]}))
        rid, action = existing["id"], "updated"
    else:
        payload.setdefault("displayName", name)
        res = wait(tok, *call(tok, "POST", f"/workspaces/{drafts['id']}/reports", payload))
        rid, action = (res or {}).get("id"), "created"
        if not rid:
            _, _, reports = call(tok, "GET", f"/workspaces/{drafts['id']}/items?type=Report")
            rid = (find(reports.get("value", []), name) or {}).get("id")
    print(json.dumps({"action": action, "report": name, "workspace": DRAFTS_WORKSPACE, "model": model_name,
                      "url": f"https://app.powerbi.com/groups/{drafts['id']}/reports/{rid}?experience=power-bi"}))


main()
