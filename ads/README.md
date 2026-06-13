# SMS Classifier Ad Workspace

This folder separates reusable advertising inputs from dated campaign runs.

## Folder Map

- `_shared/`: reusable brand, product, monetization, icon, and approved demo-screen inputs for future runs.
- `YYYY-MM-DD-<campaign-slug>/`: one dated generation run with its own manifest, strategy, matrix, generated assets, evals, and summary.
- `icon-assets/`: older icon export bundle retained for compatibility; new runs should prefer `_shared/icons/`.

## Run Hygiene

Keep reusable app facts in `_shared/`. Keep campaign-specific copy, matrices, generated PNG/MP4 assets, eval reports, and client summaries inside the dated run folder. Do not place secrets, raw private SMS data, credentials, or unredacted user messages in either location.
