## Power BI data (semantic models)
For numbers from Power BI models prefer DAX over clicking through reports:
`addons/powerbi/pbi_dax.py "<DAX>"` (default model from the secrets file; `--group <id> --dataset <id>` for others).
Reading and DAX queries are fine anytime; every change to a model follows safety rule 1 (exact change → my "yes" → do it),
and say which model/workspace it affects. Never make model changes in scheduled jobs.
Use the WORK browser when I want to *see* a report page or need a screenshot/PDF.

## Power BI dashboards (built as code — I review and publish myself)
1. **Brief first.** Send a short design brief (purpose, pages, KPIs, visuals per page, slicers, which model) with
   `bin/tg-buttons.sh … "✅ Build it" "✏️ Change brief"`. Build only after ✅.
2. **Repo:** `workspace/powerbi-repo` (git). One PBIP project per dashboard in `dashboards/<Name>/`. If the data already
   exists in a published model → thin report (`definition.pbir` byConnection to `<workspace>;Initial Catalog=<model>`).
3. **Check before pushing:** validate the project (0 errors); every field exists in the model; key numbers verified
   with DAX; visuals inside the page and not overlapping. Say in your message what you checked.
4. **Push:** commit + push in `workspace/powerbi-repo` (pre-approved for this repo only).
5. **Publish to Drafts + screenshot:** `addons/powerbi/publish-report.py "workspace/powerbi-repo/dashboards/<Name>"`
   (drafts workspace only, hard-locked) → open the URL in the WORK browser, wait for visuals, screenshot every page,
   fix blank/broken visuals → publish again → send me screenshots + link + checks.
   **Never publish anywhere else** — moving a draft to a live workspace is my job.
6. Feedback rounds: apply → validate → push → list what changed. Keep learnings in `memory/sites/powerbi-dashboards.md`.
