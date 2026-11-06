#!/usr/bin/env python3
"""Run strict validation, ledger checks, HTML build, layout checks and mechanics checks in one command."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATE = ROOT / "engine" / "validate.py"
BUILD = ROOT / "engine" / "build.py"
CHECK_LEDGER = ROOT / "tools" / "check_ledger.py"
CHECK_LAYOUT = ROOT / "tools" / "check_layout.py"
CHECK_MECHANICS = ROOT / "tools" / "check_mechanics.py"


def run_step(label: str, cmd: list[str]) -> tuple[bool, str]:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    out = (proc.stdout + proc.stderr).strip()
    return proc.returncode == 0, out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("story", help="path to story.json")
    parser.add_argument("-o", "--out", help="output HTML path (default: dist/<name>/index.html)")
    parser.add_argument("--deny", help="optional deny list file")
    parser.add_argument("--fast", action="store_true", help="run B,W,N,I mechanics clauses for fast iteration")
    parser.add_argument("--skip-mechanics", action="store_true", help="run validation, ledger, build and layout checks only")
    parser.add_argument("--json", dest="json_out", help="write summary JSON receipt to path")
    args = parser.parse_args(argv)

    story_path = Path(args.story).expanduser().resolve()
    if not story_path.exists():
        print(f"FAIL: story file not found: {story_path}", file=sys.stderr)
        return 1

    out_html = Path(args.out).expanduser().resolve() if args.out else story_path.parent / "dist" / "index.html"
    steps: list[dict] = []

    val_cmd = [sys.executable, str(VALIDATE), str(story_path), "--strict"]
    if args.deny:
        val_cmd.extend(["--deny", args.deny])
    ok, out = run_step("validate", val_cmd)
    steps.append({"step": "validate", "passed": ok, "output": out})
    print(f"[validate] {'PASS' if ok else 'FAIL'}: {out.splitlines()[-1] if out else ''}")

    research_dir = story_path.parent / "research"
    ledgers = sorted(
        p for p in research_dir.glob("*.json")
        if p.name not in ("fact-ledger.schema.json", "ledger-template.json")
    ) if research_dir.is_dir() else []
    if ledgers:
        led_cmd = [sys.executable, str(CHECK_LEDGER), *map(str, ledgers), "--story", str(story_path), "--claims", "strict"]
        l_ok, l_out = run_step("check_ledger", led_cmd)
        steps.append({"step": "check_ledger", "passed": l_ok, "output": l_out})
        print(f"[check_ledger] {'PASS' if l_ok else 'FAIL'}: {l_out.splitlines()[-1] if l_out else ''}")

    build_cmd = [sys.executable, str(BUILD), str(story_path), "-o", str(out_html)]
    if args.deny:
        build_cmd.extend(["--deny", args.deny])
    b_ok, b_out = run_step("build", build_cmd)
    steps.append({"step": "build", "passed": b_ok, "output": b_out})
    print(f"[build] {'PASS' if b_ok else 'FAIL'}: {b_out.splitlines()[-1] if b_out else ''}")

    if b_ok:
        lay_cmd = [sys.executable, str(CHECK_LAYOUT), str(out_html), "--phone"]
        lay_ok, lay_out = run_step("check_layout", lay_cmd)
        steps.append({"step": "check_layout", "passed": lay_ok, "output": lay_out})
        first_line = lay_out.splitlines()[0] if lay_out else ""
        print(f"[check_layout] {'PASS' if lay_ok else 'FAIL'}: {first_line}")

        if not args.skip_mechanics:
            mech_cmd = [sys.executable, str(CHECK_MECHANICS), str(out_html)]
            if args.fast:
                mech_cmd.extend(["--only", "B,W,N,I"])
            m_ok, m_out = run_step("check_mechanics", mech_cmd)
            steps.append({"step": "check_mechanics", "passed": m_ok, "output": m_out})
            print(f"[check_mechanics] {'PASS' if m_ok else 'FAIL'}: {m_out.splitlines()[-1] if m_out else ''}")

    all_passed = all(s["passed"] for s in steps)
    sha = hashlib.sha256(out_html.read_bytes()).hexdigest() if out_html.is_file() else ""
    receipt = {
        "story": str(story_path),
        "html": str(out_html),
        "sha256": sha,
        "passed": all_passed,
        "steps": steps,
    }
    if args.json_out:
        jp = Path(args.json_out).expanduser().resolve()
        jp.parent.mkdir(parents=True, exist_ok=True)
        jp.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        print(f"JSON {jp}")

    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
