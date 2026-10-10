#!/usr/bin/env python3
"""Run a DAX query against a Power BI dataset using the service principal.
Headless (no sign-in) — works in scheduled jobs.
Usage:
  addons/powerbi/pbi_dax.py "EVALUATE ROW(\"n\", COUNTROWS('Sales'))"
  addons/powerbi/pbi_dax.py --dataset <id> --group <id> "<DAX>"
Creds: ~/.local/state/personal-agent/secrets/powerbi-sp.env (never print it) (PBI_TENANT_ID/CLIENT_ID/CLIENT_SECRET/DATASET_ID/GROUP_ID)
"""
import sys, os, json, urllib.request, urllib.parse

ENV = os.path.expanduser("~/.local/state/personal-agent/secrets/powerbi-sp.env")

def load_env(p):
    d = {}
    with open(p) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                d[k.strip()] = v.strip()
    return d

def token(cfg):
    body = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "client_id": cfg["PBI_CLIENT_ID"],
        "client_secret": cfg["PBI_CLIENT_SECRET"],
        "scope": "https://analysis.windows.net/powerbi/api/.default",
    }).encode()
    url = f"https://login.microsoftonline.com/{cfg['PBI_TENANT_ID']}/oauth2/v2.0/token"
    with urllib.request.urlopen(urllib.request.Request(url, body)) as r:
        return json.load(r)["access_token"]

def run_dax(dax, cfg=None, dataset=None, group=None):
    cfg = cfg or load_env(ENV)
    dataset = dataset or cfg["PBI_DATASET_ID"]
    group = group or cfg["PBI_GROUP_ID"]
    tok = token(cfg)
    url = f"https://api.powerbi.com/v1.0/myorg/groups/{group}/datasets/{dataset}/executeQueries"
    payload = json.dumps({"queries": [{"query": dax}],
                          "serializerSettings": {"includeNulls": True}}).encode()
    req = urllib.request.Request(url, payload, {
        "Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            d = json.load(r)
        return d["results"][0]["tables"][0]["rows"]
    except urllib.error.HTTPError as e:
        raise SystemExit(f"HTTP {e.code}: {e.read().decode()[:500]}")

if __name__ == "__main__":
    args = sys.argv[1:]
    ds = grp = None
    while args and args[0] in ("--dataset", "--group"):
        if args[0] == "--dataset": ds = args[1]
        else: grp = args[1]
        args = args[2:]
    if not args:
        raise SystemExit("usage: pbi_dax.py [--dataset ID] [--group ID] \"<DAX>\"")
    rows = run_dax(args[0], dataset=ds, group=grp)
    print(json.dumps(rows, indent=2, ensure_ascii=False))
