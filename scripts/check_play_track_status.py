"""Read rollout status per track via Android Publisher API (service account).

Run from repo root:
  python scripts/check_play_track_status.py

Does not publish anything; opens a throwaway Edit, reads tracks, deletes edit.
"""

from __future__ import annotations

import pathlib

from google.oauth2 import service_account
from googleapiclient.discovery import build

ROOT = pathlib.Path(__file__).resolve().parent.parent
APP_DIR = ROOT / "app"
SCOPE = "https://www.googleapis.com/auth/androidpublisher"
PACKAGE = "com.smsclassifier.app"


def resolve_credentials_path() -> pathlib.Path:
    preferred = APP_DIR / "play-publisher.json"
    if preferred.is_file():
        return preferred
    for p in sorted(APP_DIR.glob("*.json")):
        if not p.is_file():
            continue
        try:
            txt = p.read_text(encoding="utf-8")
        except OSError:
            continue
        if '"service_account"' in txt and '"client_email"' in txt:
            return p
    raise SystemExit(f"No Play service-account JSON under {APP_DIR}")


def main() -> None:
    json_path = resolve_credentials_path()
    creds = service_account.Credentials.from_service_account_file(
        str(json_path), scopes=[SCOPE]
    )
    pub = build("androidpublisher", "v3", credentials=creds)

    edit = pub.edits().insert(packageName=PACKAGE, body={}).execute()
    edit_id = edit["id"]

    try:
        for track_name in ("internal", "alpha", "beta", "production"):
            try:
                t = pub.edits().tracks().get(
                    packageName=PACKAGE, editId=edit_id, track=track_name
                ).execute()
            except Exception as e:
                print(f"\n=== track={track_name!r} READ ERROR {type(e).__name__}: {e}")
                continue
            releases = t.get("releases") or []
            print(f"\n=== track={track_name!r} — {len(releases)} rolling release block(s)")
            if not releases:
                print("  (no releases)")
                continue
            for r in releases:
                print(
                    f"  status={r.get('status')!r}  "
                    f"versionCodes={r.get('versionCodes')}  "
                    f"fraction={r.get('userFraction')}"
                )
    finally:
        pub.edits().delete(packageName=PACKAGE, editId=edit_id).execute()


if __name__ == "__main__":
    main()
