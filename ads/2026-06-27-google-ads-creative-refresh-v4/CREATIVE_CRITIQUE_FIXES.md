# Creative Critique Fixes

This v2 run is built against the Codex + Claude critique of v1.

| V1 critique | V2 fix | Evidence |
|---|---|---|
| Blank logo placeholder | Real app icon copied to `inputs/logo-primary.png`; every static layout has a logo lockup. | `brand_kit.yaml`, `layout_specs.json` |
| Static set was homogeneous | Three concept systems: warm scam-link warning, dark OTP-account contradiction, and mint OTP-inbox organizer. | `creative_matrix.csv`, rendered assets |
| Synthetic proof was too dense/tiny | Rebuilt ad-scale proof screenshots with 2 visible rows, 52px+ important text, and <=3 proof text blocks. | `screenshots/`, `proof_specs.yaml` |
| Video was mostly one repeated static card | Video uses 3 distinct proof screens and captions that advance setup -> reason -> payoff. | `storyboard.yaml`, `slideshow_scam_prize_9x16.json` |
| Video VO/caption parity was weak | VO adds context and does not simply read captions. | `voiceover_scripts.csv` |
| Search plan was stale/low-volume | New Search pack uses the high-volume Keyword Planner source and two RSAs per launch group. | `keyword_research.csv`, `keyword_clusters.yaml`, `google_search_copy.yaml` |
| Publish set not tied to eval | `exports/launch_ready` should be populated only after eval decisions are `ship`. | `launch_ready_assets.csv` after eval |
