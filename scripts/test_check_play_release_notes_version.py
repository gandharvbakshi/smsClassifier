from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_play_release_notes_version import (  # noqa: E402
    ReleaseNotesVersionError,
    check_release_notes_version,
    extract_version_name,
    main,
    validate_release_notes_text,
)


def write_fixture_tree(
    base: Path,
    *,
    build_gradle_text: str,
    release_notes_text: str | None = None,
) -> dict[str, Path]:
    build_gradle_path = base / "app/build.gradle.kts"
    release_notes_path = base / "app/src/main/play/release-notes/en-US/default.txt"
    build_gradle_path.parent.mkdir(parents=True, exist_ok=True)
    release_notes_path.parent.mkdir(parents=True, exist_ok=True)
    build_gradle_path.write_text(build_gradle_text, encoding="utf-8")
    if release_notes_text is not None:
        release_notes_path.write_text(release_notes_text, encoding="utf-8")
    return {"build_gradle": build_gradle_path, "release_notes": release_notes_path}


class PlayReleaseNotesVersionTests(unittest.TestCase):
    def test_current_style_release_notes_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            files = write_fixture_tree(
                root,
                build_gradle_text='versionName = "1.2.27"\n',
                release_notes_text="v1.2.27 - More reliable Pro trial setup\n",
            )

            version_name = check_release_notes_version(
                root,
                build_gradle_path=files["build_gradle"],
                release_notes_path=files["release_notes"],
            )

            self.assertEqual(version_name, "1.2.27")

    def test_stale_release_notes_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            files = write_fixture_tree(
                root,
                build_gradle_text='versionName = "1.2.27"\n',
                release_notes_text="v1.2.26 - Stale notes\n",
            )

            with self.assertRaises(ReleaseNotesVersionError) as ctx:
                check_release_notes_version(
                    root,
                    build_gradle_path=files["build_gradle"],
                    release_notes_path=files["release_notes"],
                )

            self.assertIn("v1.2.27", str(ctx.exception))

    def test_missing_release_notes_file_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            files = write_fixture_tree(
                root,
                build_gradle_text='versionName = "1.2.27"\n',
                release_notes_text=None,
            )

            with self.assertRaises(ReleaseNotesVersionError) as ctx:
                check_release_notes_version(
                    root,
                    build_gradle_path=files["build_gradle"],
                    release_notes_path=files["release_notes"],
                )

            self.assertIn("Missing release notes file", str(ctx.exception))

    def test_ambiguous_version_name_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            files = write_fixture_tree(
                root,
                build_gradle_text=(
                    'versionName = "1.2.27"\n'
                    'versionName = "1.2.28"\n'
                ),
                release_notes_text="v1.2.27 - More reliable Pro trial setup\n",
            )

            with self.assertRaises(ReleaseNotesVersionError) as ctx:
                check_release_notes_version(
                    root,
                    build_gradle_path=files["build_gradle"],
                    release_notes_path=files["release_notes"],
                )

            self.assertIn("Ambiguous versionName declarations", str(ctx.exception))

    def test_prefix_collision_rejects_longer_semver(self) -> None:
        with self.assertRaises(ReleaseNotesVersionError):
            validate_release_notes_text("1.2.2", "v1.2.20 - wrong release\n")

    def test_extract_version_name_requires_single_declaration(self) -> None:
        with self.assertRaises(ReleaseNotesVersionError):
            extract_version_name('versionName = "1.2.27"\nversionName = "1.2.28"\n')

    def test_cli_returns_nonzero_for_stale_release_notes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            files = write_fixture_tree(
                root,
                build_gradle_text='versionName = "1.2.27"\n',
                release_notes_text="v1.2.26 - Stale notes\n",
            )
            stderr = io.StringIO()

            with contextlib.redirect_stderr(stderr):
                exit_code = main(
                    [
                        "--build-gradle-path",
                        str(files["build_gradle"]),
                        "--release-notes-path",
                        str(files["release_notes"]),
                    ]
                )

            self.assertEqual(exit_code, 1)
            self.assertIn("RELEASE NOTES VERSION CHECK FAILED", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
