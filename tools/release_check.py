#!/usr/bin/env python3
"""Check the repo for private data before it is shared outside its owner.

Usage: python3 tools/release_check.py [--history] [--baseline FILE] [--deny FILE]

The default scan covers tracked files and untracked files that Git does not
ignore. With --history it also scans every file in every commit. A reviewed
history baseline contains one finding id per line. Keep deny and baseline files
outside a public export.
"""

import argparse
import hashlib
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENGINE = ROOT / "engine"
sys.path.insert(0, str(ENGINE))
import validate as V  # noqa: E402

# The validator owns the shared privacy patterns.
RULES = [(name, re.compile(pattern)) for name, pattern in V.SECRET_PATTERNS]

# Addresses that are fine to publish.
ALLOWED_EMAILS = re.compile(r"@(?:example\.(?:com|org|net)|users\.noreply\.github\.com)$")

# A line carrying this mark is a deliberate test fixture.
ALLOW_MARK = "release-check: allow"

# Exact fake values in older validator tests that predate the line marker.
ALLOWED_TEST_FIXTURES = {
    ("tests/test_engine.py", "Tailnet hostname", "box.tail1234." + "ts.net"),
    ("tests/test_engine.py", "Password assignment", "password: hunter2hunter2"),  # release-check: allow
}

# Files that are binary or generated and safe to skip line scanning.
SKIP_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".ico", ".woff", ".woff2"}


def git(*args):
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout


def load_deny(path):
    return V.load_deny(path)


def load_baseline(path):
    """Read reviewed history finding ids, one id per line."""
    if not path:
        return set()
    ids = set()
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        token = line.split(maxsplit=1)[0].strip("[]")
        if not re.fullmatch(r"[0-9a-f]{12}", token):
            raise ValueError(f"invalid baseline finding id: {token}")
        ids.add(token)
    return ids


def scan_text(name, text, deny):
    """Return (file, line, rule, excerpt) findings for one text file."""
    found = []
    deny_res = [
        (word, re.compile(r"(?<![A-Za-z0-9])" + re.escape(word) + r"(?![a-z0-9])"))
        for word in deny
    ]
    for number, line in enumerate(text.splitlines(), 1):
        if ALLOW_MARK in line:
            continue
        for rule, regex in RULES:
            for match in regex.finditer(line):
                hit = match.group(0)
                if rule.lower() == "email address" and ALLOWED_EMAILS.search(hit):
                    continue
                if (name, rule, hit) in ALLOWED_TEST_FIXTURES:
                    continue
                found.append((name, number, rule, hit[:60]))
        for word, regex in deny_res:
            if regex.search(line):
                found.append((name, number, "deny word", word))
    return found


def structure_findings(files, allow_stories):
    out = []
    for filename in files:
        parts = Path(filename).parts
        if parts and parts[0] == "dist":
            out.append((filename, 0, "built output in git", "remove dist/ from the repo"))
        if (
            len(parts) > 1
            and parts[0] == "stories"
            and parts[1] not in {"example", *allow_stories}
        ):
            out.append((filename, 0, "story other than the example", parts[1]))
    seen, unique = set(), []
    for item in out:
        key = (item[2], item[3])
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


def tracked_files():
    return [name for name in git("ls-files").splitlines() if name]


def untracked_files():
    return [
        name
        for name in git("ls-files", "--others", "--exclude-standard").splitlines()
        if name
    ]


def scan_tree(files, deny):
    findings = []
    for filename in files:
        path = ROOT / filename
        if path.suffix.lower() in SKIP_SUFFIXES or not path.is_file() or path.is_symlink():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        findings += scan_text(filename, text, deny)
    return findings


def scan_history(deny):
    """Scan every distinct text blob in every commit."""
    findings, seen = [], set()
    for line in git("rev-list", "--all", "--objects").splitlines():
        sha, _, name = line.partition(" ")
        if not name or sha in seen or Path(name).suffix.lower() in SKIP_SUFFIXES:
            continue
        seen.add(sha)
        if git("cat-file", "-t", sha).strip() != "blob":
            continue
        try:
            text = subprocess.run(
                ["git", "cat-file", "-p", sha],
                cwd=ROOT,
                capture_output=True,
                check=True,
            ).stdout.decode("utf-8")
        except UnicodeDecodeError:
            continue
        scanned = scan_text(name, text, deny)
        findings += [
            (f"{filename} (history {sha[:8]})", number, rule, hit)
            for filename, number, rule, hit in scanned
        ]
    return findings


def finding_id(finding):
    """Return a stable, non-secret id for one historical finding."""
    payload = "\0".join(str(part) for part in finding)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


def filter_history(findings, baseline):
    ids = {finding_id(item) for item in findings}
    remaining = [item for item in findings if finding_id(item) not in baseline]
    return remaining, len(findings) - len(remaining), baseline - ids


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Check the repo for private data before sharing it."
    )
    parser.add_argument("--history", action="store_true", help="also scan every file in every commit")
    parser.add_argument(
        "--baseline",
        help="reviewed history finding ids, one per line; requires --history",
    )
    parser.add_argument(
        "--deny", help="file of private names or words, one per line, kept outside the repo"
    )
    parser.add_argument(
        "--allow-story", action="append", default=[], help="a story folder that may be shared"
    )
    args = parser.parse_args(argv)
    if args.baseline and not args.history:
        parser.error("--baseline requires --history")

    try:
        deny = load_deny(args.deny)
        baseline = load_baseline(args.baseline)
    except (OSError, ValueError) as error:
        parser.error(str(error))

    tracked = tracked_files()
    untracked = untracked_files()
    current_files = tracked + untracked
    findings = structure_findings(current_files, set(args.allow_story))
    findings += scan_tree(current_files, deny)

    history_known = 0
    stale_baseline = set()
    history_findings = []
    if args.history:
        history_findings, history_known, stale_baseline = filter_history(
            scan_history(deny), baseline
        )
        findings += history_findings

    print(f"Scanned {len(tracked)} tracked files and {len(untracked)} untracked files.")
    if args.history:
        print(
            f"History baseline ignored {history_known} reviewed findings; "
            f"{len(stale_baseline)} baseline ids were not found."
        )

    if not findings:
        scope = " and full history" if args.history else ""
        print(f"PASS: current tree{scope}, nothing private found.")
        return 0

    history_set = set(history_findings)
    for finding in findings:
        filename, number, rule, hit = finding
        where = f"{filename}:{number}" if number else filename
        prefix = f"[{finding_id(finding)}] " if finding in history_set else ""
        print(f"FAIL {prefix}{rule}: {where}: {hit}")

    print(f"\n{len(findings)} unreviewed finding(s).")
    if args.history:
        print("Do not rewrite Git history. A public copy should be a fresh export without repository history.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
