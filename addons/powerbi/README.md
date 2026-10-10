# Power BI add-on (optional)

Lets the agent **query** Power BI semantic models with DAX and **build dashboards as code** (PBIP/PBIR in a git
repo), then publish them to a *drafts-only* workspace for you to review. Moving a report to a live workspace stays
your job.

## Files
| File | What it does |
|---|---|
| `pbi_dax.py` | Runs a DAX query headlessly with a service principal (works in scheduled jobs). `pbi_dax.py "EVALUATE …"` |
| `publish-report.py` | Publishes a **thin** PBIR report (byConnection to a published model) to the workspace in `PBI_DRAFTS_WORKSPACE` — hard-locked, refuses any other workspace. Creates the first time, updates afterwards. Needs `powerbi-report-author` (for `pack`). |
| `powerbi-sp.env.example` | Settings/secrets template → `~/.local/state/personal-agent/secrets/powerbi-sp.env` (chmod 600). |
| `instructions-snippet.md` | Section to paste into your `CLAUDE.md`. |

## Setup
1. Azure / Entra ID: create an app registration (service principal) + client secret.
2. Power BI admin portal: allow service principals to use Power BI / Fabric APIs (tenant setting, ideally limited to a security group).
3. Create a workspace for drafts (e.g. "Agent Drafts") and add the service principal as **Contributor**.
   Give it **Viewer** (or Build) on the workspaces whose models it should read.
4. Fill `powerbi-sp.env` from the example. Test: `addons/powerbi/pbi_dax.py "EVALUATE ROW(\"ok\", 1)"`.
5. Optional, for richer authoring: Microsoft's Power BI Modeling MCP server and the Power BI agent skills
   (installed separately — not part of this repo, they have their own licenses).

## Safety
- Reading and DAX queries: anytime. **Any change to a model** (measures, tables, relationships, refreshes) needs the
  owner's explicit "yes" — never in scheduled jobs.
- Publishing: only to the drafts workspace. Never "Publish"/"Save a copy" anywhere else from the browser.
- Keep the secrets file out of git (the repo `.gitignore` already ignores `*.env`).
