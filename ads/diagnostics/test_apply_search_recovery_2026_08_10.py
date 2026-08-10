from __future__ import annotations

import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("apply_search_recovery_2026_08_10.py")
SPEC = importlib.util.spec_from_file_location("search_recovery", MODULE_PATH)
assert SPEC and SPEC.loader
SEARCH_RECOVERY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SEARCH_RECOVERY)


class CanonicalTextBytesTest(unittest.TestCase):
    def test_hash_is_stable_across_git_line_endings(self) -> None:
        lf_content = b"metadata:\n  campaign_id: 23973905019\n"
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "plan.yaml"
            path.write_bytes(lf_content.replace(b"\n", b"\r\n"))

            actual = hashlib.sha256(SEARCH_RECOVERY.canonical_text_bytes(path)).hexdigest()
            expected = hashlib.sha256(lf_content).hexdigest()

        self.assertEqual(expected, actual)


if __name__ == "__main__":
    unittest.main()
