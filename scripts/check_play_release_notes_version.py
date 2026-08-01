"""Validate Play release notes against the app versionName."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Sequence


class ReleaseNotesVersionError(RuntimeError):
    """Raised when the release notes version contract is broken."""


_VERSION_NAME_RE = re.compile(r'^\s*versionName\s*=\s*"([^"]+)"\s*$')


def default_repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def extract_version_name(build_gradle_text: str) -> str:
    matches: list[str] = []
    for line in build_gradle_text.splitlines():
        stripped = line.split("//", 1)[0].strip()
        if not stripped:
            continue
        match = _VERSION_NAME_RE.match(stripped)
        if match:
            matches.append(match.group(1))

    if not matches:
        raise ReleaseNotesVersionError("Missing versionName declaration in app/build.gradle.kts")
    if len(matches) > 1:
        raise ReleaseNotesVersionError(
            f"Ambiguous versionName declarations in app/build.gradle.kts: {matches}"
        )
    return matches[0]


def load_version_name(build_gradle_path: Path) -> str:
    try:
        text = build_gradle_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ReleaseNotesVersionError(f"Missing Gradle file: {build_gradle_path}") from exc
    return extract_version_name(text)


def validate_release_notes_text(version_name: str, notes_text: str) -> None:
    expected_prefix = f"v{version_name}"
    if not notes_text.startswith(expected_prefix):
        raise ReleaseNotesVersionError(
            f"Release notes must start with {expected_prefix!r} for version {version_name!r}"
        )

    remainder = notes_text[len(expected_prefix) :]
    if not remainder:
        return

    first = remainder[0]
    if first in {" ", "\t", "\n", "\r"}:
        return
    if first in {"-", ":", "–", "—"}:
        return

    raise ReleaseNotesVersionError(
        "Release notes version prefix must be followed by a separator or end of file"
    )


def validate_release_notes_file(version_name: str, notes_path: Path) -> None:
    try:
        notes_text = notes_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ReleaseNotesVersionError(f"Missing release notes file: {notes_path}") from exc

    validate_release_notes_text(version_name, notes_text)


def check_release_notes_version(
    repo_root: Path | None = None,
    *,
    build_gradle_path: Path | None = None,
    release_notes_path: Path | None = None,
) -> str:
    root = repo_root or default_repo_root()
    build_gradle_path = build_gradle_path or root / "app/build.gradle.kts"
    release_notes_path = release_notes_path or root / "app/src/main/play/release-notes/en-US/default.txt"

    version_name = load_version_name(build_gradle_path)
    validate_release_notes_file(version_name, release_notes_path)
    return version_name


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate Play release notes version prefix.")
    parser.add_argument("--repo-root", type=Path, default=default_repo_root())
    parser.add_argument("--build-gradle-path", type=Path)
    parser.add_argument("--release-notes-path", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        version_name = check_release_notes_version(
            args.repo_root,
            build_gradle_path=args.build_gradle_path,
            release_notes_path=args.release_notes_path,
        )
    except ReleaseNotesVersionError as exc:
        print(f"RELEASE NOTES VERSION CHECK FAILED: {exc}", file=sys.stderr)
        return 1

    print(f"RELEASE NOTES VERSION CHECK OK: v{version_name}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
