#!/usr/bin/env python3
"""Admin helper for SMS Classifier backend entitlements.

Requires ADMIN_API_TOKEN or SMS_ADMIN_TOKEN in the environment, matching the
Cloud Run backend's admin token.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def _token() -> str:
    token = (os.getenv("SMS_ADMIN_TOKEN") or os.getenv("ADMIN_API_TOKEN") or "").strip()
    if not token:
        raise SystemExit("Set SMS_ADMIN_TOKEN or ADMIN_API_TOKEN before running this command.")
    return token


def _request(base_url: str, method: str, path: str, token: str, body: dict[str, Any] | None = None, query: dict[str, str] | None = None) -> dict[str, Any]:
    url = base_url.rstrip("/") + path
    if query:
        url += "?" + urlencode({k: v for k, v in query.items() if v})
    data = None
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=30) as response:
            text = response.read().decode("utf-8")
            return json.loads(text) if text else {"ok": True}
    except HTTPError as exc:
        text = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code}: {text}") from exc
    except URLError as exc:
        raise SystemExit(f"Request failed: {exc}") from exc


def _print_json(data: dict[str, Any]) -> None:
    print(json.dumps(data, indent=2, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage SMS Classifier backend entitlements.")
    parser.add_argument(
        "--base-url",
        default=os.getenv("SMS_ADMIN_BASE_URL", "").strip(),
        help="Backend API base URL. Can also be set with SMS_ADMIN_BASE_URL.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    grant = sub.add_parser("grant-pro", help="Grant Pro as a gift for a fixed number of days.")
    grant.add_argument("--install-id", default="", help="App installId from the user's device.")
    grant.add_argument("--firebase-uid", default="", help="Firebase UID, usually from linked phone auth.")
    grant.add_argument("--days", type=int, default=365, help="Gift duration in days. Default: 365.")
    grant.add_argument("--reason", default="gift", help="Short audit reason. Default: gift.")
    grant.add_argument("--note", default="", help="Optional private audit note.")

    lookup = sub.add_parser("lookup", help="Lookup one user's entitlement.")
    lookup.add_argument("--install-id", default="", help="App installId from the user's device.")
    lookup.add_argument("--firebase-uid", default="", help="Firebase UID, usually from linked phone auth.")

    sub.add_parser("stats", help="Show backend entitlement counts and recent gift grants.")

    args = parser.parse_args()
    if not args.base_url:
        raise SystemExit("Set SMS_ADMIN_BASE_URL or pass --base-url before running this command.")
    token = _token()

    if args.command == "grant-pro":
        if not args.install_id and not args.firebase_uid:
            raise SystemExit("grant-pro requires --install-id or --firebase-uid.")
        payload: dict[str, Any] = {
            "durationDays": args.days,
            "reason": args.reason,
        }
        if args.install_id:
            payload["installId"] = args.install_id
        if args.firebase_uid:
            payload["firebaseUid"] = args.firebase_uid
        if args.note:
            payload["note"] = args.note
        _print_json(_request(args.base_url, "POST", "/admin/entitlements/grant-pro", token, body=payload))
        return 0

    if args.command == "lookup":
        if not args.install_id and not args.firebase_uid:
            raise SystemExit("lookup requires --install-id or --firebase-uid.")
        query = {
            "installId": args.install_id,
            "firebaseUid": args.firebase_uid,
        }
        _print_json(_request(args.base_url, "GET", "/admin/entitlements/lookup", token, query=query))
        return 0

    if args.command == "stats":
        _print_json(_request(args.base_url, "GET", "/admin/entitlements/stats", token))
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
