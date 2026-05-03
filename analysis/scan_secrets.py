"""Scan git history of both repos for leaked secrets.

Outputs a structured report. Secret values are REDACTED (only first 8 + last 4
characters shown) so the report itself doesn't propagate the leak.
"""
from __future__ import annotations
import re
import subprocess
from collections import defaultdict
from pathlib import Path

# Repos to scan
REPOS = {
    "android_sms_classifier": Path(r"d:\Projects\SMS datasets and project\android_sms_classifier"),
    "sms_datasets_parent":    Path(r"d:\Projects\SMS datasets and project"),
}

# (label, regex). Word-boundary aware where useful.
PATTERNS = [
    ("Groq",        re.compile(r"\bgsk_[A-Za-z0-9]{40,}\b")),
    ("OpenAI/DeepSeek", re.compile(r"\bsk-[A-Za-z0-9_\-]{20,}\b")),
    ("Google",      re.compile(r"\bAIza[A-Za-z0-9_\-]{35}\b")),
    ("AWS-AKID",    re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("Slack",       re.compile(r"\bxox[bpoa]-[0-9]+-[0-9]+-[A-Za-z0-9]+")),
    ("JWT",         re.compile(r"\beyJ[A-Za-z0-9_\-]{10,}\.eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\b")),
    ("GitHub PAT",  re.compile(r"\bghp_[A-Za-z0-9]{36}\b")),
    ("Generic API_KEY assignment", re.compile(
        r"(?i)(?:api[_\-]?key|secret[_\-]?key|access[_\-]?token|auth[_\-]?token|bearer)"
        r"\s*[=:]\s*['\"]?([A-Za-z0-9_\-]{20,})['\"]?"
    )),
]


def redact(value: str) -> str:
    if len(value) <= 14:
        return value[:2] + "***"
    return f"{value[:8]}...{value[-4:]}  (length {len(value)})"


def run(args: list[str], cwd: Path) -> str:
    try:
        out = subprocess.run(args, cwd=cwd, capture_output=True, text=True,
                             encoding="utf-8", errors="replace", check=False)
        return out.stdout + out.stderr
    except Exception as e:
        return f"<error: {e}>"


def scan_repo(name: str, path: Path):
    print(f"\n{'='*70}")
    print(f"SCANNING: {name}  ({path})")
    print('='*70)
    if not (path / ".git").exists():
        print(f"  NOT A GIT REPO — scanning working tree only")
        scan_working_tree(name, path)
        return

    # Get all commits + their patches
    print(f"  Fetching all-history patch (this may take a moment)...")
    log = run(["git", "log", "--all", "-p", "--no-color"], cwd=path)
    print(f"  History length: {len(log):,} chars")

    findings: dict[str, list[tuple]] = defaultdict(list)
    current_commit = "<unknown>"
    current_file = "<unknown>"

    for line in log.splitlines():
        if line.startswith("commit "):
            current_commit = line.split()[1][:8]
        elif line.startswith("diff --git "):
            # diff --git a/path b/path
            parts = line.split()
            if len(parts) >= 4:
                current_file = parts[3].lstrip("b/")
        elif line.startswith("+") and not line.startswith("+++"):
            for label, regex in PATTERNS:
                for m in regex.finditer(line):
                    val = m.group(0) if not m.groups() else m.group(1)
                    findings[label].append((current_commit, current_file, redact(val)))

    if not findings:
        print(f"\n  [CLEAN] No secrets matched in git history of {name}")
    else:
        print(f"\n  [LEAK] Found {sum(len(v) for v in findings.values())} matches in history:")
        for label, hits in findings.items():
            print(f"\n  -- {label} ({len(hits)} matches) --")
            unique_redacted = sorted({(c, f, r) for c, f, r in hits})
            for c, f, r in unique_redacted[:20]:
                print(f"     commit {c}  file {f}  value {r}")
            if len(unique_redacted) > 20:
                print(f"     ... and {len(unique_redacted) - 20} more")

    print(f"\n  Also scanning current working tree of {name}...")
    scan_working_tree(name, path)


def scan_working_tree(name: str, path: Path):
    findings: dict[str, list[tuple]] = defaultdict(list)
    for f in path.rglob("*"):
        try:
            if not f.is_file():
                continue
        except OSError:
            continue
        if any(part in {".git", "node_modules", ".gradle", "build",
                        "__pycache__", ".idea", ".venv", "venv",
                        "dist", "site-packages", ".gradle", ".pytest_cache"}
               for part in f.parts):
            continue
        # Skip symlinks / non-regular files (e.g. .venv/bin/python on Windows)
        try:
            if f.is_symlink():
                continue
        except OSError:
            continue
        if f.suffix in {".jks", ".keystore", ".pkl", ".onnx", ".aab", ".apk",
                        ".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip"}:
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if len(text) > 5_000_000:  # skip huge files
            continue
        for label, regex in PATTERNS:
            for m in regex.finditer(text):
                val = m.group(0) if not m.groups() else m.group(1)
                rel = f.relative_to(path).as_posix()
                findings[label].append((rel, redact(val)))

    if not findings:
        print(f"     [CLEAN] No secrets in working tree.")
        return
    print(f"     [LEAK] Working tree findings:")
    for label, hits in findings.items():
        unique = sorted(set(hits))
        for f, r in unique[:20]:
            print(f"       {label}: {f}  value {r}")
        if len(unique) > 20:
            print(f"       ... and {len(unique) - 20} more {label} hits")


def main():
    for name, path in REPOS.items():
        scan_repo(name, path)


if __name__ == "__main__":
    main()
