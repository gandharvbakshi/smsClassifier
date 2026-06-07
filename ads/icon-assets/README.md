# SMS Classifier — App Icon Assets

A message bubble holding a verified check, on the brand's calm light‑blue plate.
It says, at a glance: **your messages, sorted and safe.** Built for elderly users —
one bold shape, high contrast, an unmistakable "this is OK" check. A subtle seat
edge keeps the light plate readable on any wallpaper, including pure white.

**Colors:** BrandBlue `#0067C0` · Plate `#E3F0FB` · Seat edge `#BBD7F2` · Check `#FFFFFF`

---

## What's inside

### `android/` — drop straight into `app/src/main/res/`
- `mipmap-anydpi-v26/ic_launcher.xml` + `ic_launcher_round.xml` — adaptive icon descriptors
- `mipmap-<density>/`
  - `ic_launcher.png` — legacy square icon (API < 26)
  - `ic_launcher_round.png` — legacy round icon
  - `ic_launcher_foreground.png` — adaptive foreground (mark only, transparent)
  - `ic_launcher_background.png` — adaptive background (solid plate)
- Densities: mdpi, hdpi, xhdpi, xxhdpi, xxxhdpi

> Replace the existing `mipmap-*` folders, sync, and run. The launcher will use the
> adaptive icon on Android 8+ and fall back to the legacy PNGs on older devices.

### `play-store/`
- `icon-512.png` — 512×512 hi‑res store icon (full‑bleed; Google rounds + shadows it)
- `feature-graphic-1024x500.png` — store listing feature graphic

### `ads/`
- `google-square-1200.png` (1200×1200)
- `google-landscape-1200x628.png` (1200×628)
- `meta-square-1080.png` (1080×1080)
- `meta-landscape-1200x628.png` (1200×628)

### `master/`
- `icon.svg` — scalable vector master (rebuild any size from this)
- `icon-1024-rounded.png` — rounded master (in‑app splash / marketing)
- `icon-1024-square.png` — full‑bleed square master
- `mark-only-1024-transparent.png` — the bubble mark alone, transparent

---

## Regenerating

`icon-draw.js` is the single source of truth — every PNG was drawn from it, so the
mark is identical at every size. Edit that file to tweak the geometry, then re‑export.
