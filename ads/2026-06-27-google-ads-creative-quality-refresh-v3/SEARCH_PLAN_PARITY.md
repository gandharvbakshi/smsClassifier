# Search Plan Parity Note

Do not enable the old paused Search campaign as the main launch plan.

The v1 Google Ads account contains an earlier paused low-volume Search campaign. This v2 folder is the source of truth for the next Search publish candidate. It uses the same-day high-volume Keyword Planner data and a two-RSA-per-group copy structure.

Before any Google Ads mutate/publish step, compare the campaign plan fingerprint against:

- `keyword_clusters.yaml`
- `google_search_copy.yaml`
- `search_copy_eval_results.json`

No Search campaign should be enabled unless the plan matches these evaluated artifacts and the user has explicitly approved serving/spend.
