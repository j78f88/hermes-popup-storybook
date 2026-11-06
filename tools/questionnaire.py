#!/usr/bin/env python3
"""Optional intake questionnaire pathway for popup-storybook.

Exports an offline HTML questionnaire form (--html OUT.html) or compiles a
completed answers JSON file (--from ANSWERS.json --dir DIR) into a verified
story folder (brief.md, sources.md, outline.md, storyboard.md, research
ledgers and story.json) with recurring characters and non-repeating settings.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"
NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")

SETTING_PRESETS = {
    "map_room": {
        "sky": "library",
        "ground": "paper",
        "wings": "low",
        "wall": [
            {"sprite": "map_wall", "x": 50, "y": 26, "scale": 2.3},
            {"sprite": "calendar", "x": 82, "y": 24, "scale": 1.9},
        ],
        "backdrop": {"id": "bg_main", "sprite": "drafting_table", "x": 28, "depth": 4, "scale": 3.1, "mount": "box"},
        "secondary": {"id": "bg_sec", "sprite": "compass_rose", "x": 78, "depth": 3, "scale": 2.6},
        "prop": {"id": "focal", "sprite": "book_open", "x": 50, "depth": 2, "scale": 2.2},
    },
    "observatory": {
        "sky": "night",
        "ground": "carpet",
        "wings": "low",
        "wall": [
            {"sprite": "moon", "x": 80, "y": 22, "scale": 2.1},
            {"sprite": "star", "x": 22, "y": 20, "scale": 1.6, "twinkle": True, "cut": False},
        ],
        "backdrop": {"id": "bg_main", "sprite": "memory_dome", "x": 26, "depth": 4, "scale": 3.0},
        "secondary": {"id": "bg_sec", "sprite": "telescope", "x": 78, "depth": 3, "scale": 2.7},
        "prop": {"id": "focal", "sprite": "book_stack", "x": 50, "depth": 2, "scale": 2.2},
    },
    "watchtower": {
        "sky": "workshop",
        "ground": "stone",
        "wings": "none",
        "wall": [
            {"sprite": "radar_screen", "x": 50, "y": 24, "scale": 2.3},
            {"sprite": "star", "x": 20, "y": 20, "scale": 1.6, "twinkle": True, "cut": False},
        ],
        "backdrop": {"id": "bg_main", "sprite": "server_pair", "x": 32, "depth": 4, "scale": 2.9, "mount": "box"},
        "secondary": {"id": "bg_sec", "sprite": "nas", "x": 78, "depth": 4, "scale": 2.8},
        "prop": {"id": "focal", "sprite": "magnifier", "x": 50, "depth": 2, "scale": 2.2},
    },
    "mailroom": {
        "sky": "indoor",
        "ground": "wood",
        "wings": "low",
        "wall": [
            {"sprite": "window_night", "x": 24, "y": 24, "scale": 2.0},
            {"sprite": "lamp", "x": 78, "y": 24, "scale": 1.9},
        ],
        "backdrop": {"id": "bg_main", "sprite": "mail_chute", "x": 26, "depth": 4, "scale": 3.1},
        "secondary": {"id": "bg_sec", "sprite": "conveyor", "x": 74, "depth": 4, "scale": 2.8, "mount": "box"},
        "prop": {"id": "focal", "sprite": "video_card", "x": 52, "depth": 2, "scale": 2.2},
    },
    "boardroom": {
        "sky": "council",
        "ground": "carpet",
        "wings": "low",
        "wall": [
            {"sprite": "chandelier", "x": 50, "y": 20, "scale": 2.3},
            {"sprite": "star", "x": 20, "y": 22, "scale": 1.6, "twinkle": True, "cut": False},
        ],
        "backdrop": {"id": "bg_main", "sprite": "table_round", "x": 48, "depth": 3, "scale": 3.3, "mount": "box"},
        "secondary": {"id": "bg_sec", "sprite": "scales", "x": 24, "depth": 2, "scale": 2.3},
        "prop": {"id": "focal", "sprite": "book_open", "x": 52, "depth": 2, "scale": 2.2},
    },
    "gymnasium": {
        "sky": "day",
        "ground": "road",
        "wings": "none",
        "wall": [
            {"sprite": "scoreboard", "x": 50, "y": 24, "scale": 2.4},
        ],
        "backdrop": {"id": "bg_main", "sprite": "podium_steps", "x": 26, "depth": 4, "scale": 3.1, "mount": "box"},
        "secondary": {"id": "bg_sec", "sprite": "hurdle", "x": 54, "depth": 3, "scale": 2.6},
        "prop": {"id": "focal", "sprite": "trophy", "x": 26, "depth": 3, "scale": 2.2, "lift": 18},
    },
    "courtroom": {
        "sky": "storm",
        "ground": "desk",
        "wings": "low",
        "wall": [
            {"sprite": "raincloud", "x": 24, "y": 24, "scale": 2.2, "bob": True},
            {"sprite": "clock_wall", "x": 78, "y": 24, "scale": 2.1},
        ],
        "backdrop": {"id": "bg_main", "sprite": "gavel_bench", "x": 46, "depth": 4, "scale": 3.1, "mount": "box"},
        "secondary": {"id": "bg_sec", "sprite": "recycle_bin", "x": 82, "depth": 3, "scale": 2.6},
        "prop": {"id": "focal", "sprite": "magnifier", "x": 36, "depth": 2, "scale": 2.2},
    },
    "forge_bridge": {
        "sky": "workshop",
        "ground": "water",
        "wings": "none",
        "wall": [
            {"sprite": "spark", "x": 24, "y": 24, "scale": 2.2, "twinkle": True, "cut": False},
            {"sprite": "blueprint", "x": 76, "y": 24, "scale": 2.2},
        ],
        "backdrop": {"id": "bg_main", "sprite": "anvil_forge", "x": 24, "depth": 4, "scale": 3.0},
        "secondary": {"id": "bg_sec", "sprite": "bridge_arch", "x": 52, "depth": 3, "scale": 3.0, "mount": "vfold"},
        "prop": {"id": "focal", "sprite": "blueprint", "x": 42, "depth": 2, "scale": 2.2},
    },
    "parliament": {
        "sky": "dusk",
        "ground": "stone",
        "wings": "low",
        "wall": [
            {"sprite": "parliament_roof", "x": 50, "y": 24, "scale": 2.4},
            {"sprite": "cloud", "x": 20, "y": 20, "scale": 1.9, "bob": True},
        ],
        "backdrop": {"id": "bg_main", "sprite": "hansard_desk", "x": 48, "depth": 4, "scale": 3.1, "mount": "box"},
        "secondary": {"id": "bg_sec", "sprite": "megaphone", "x": 22, "depth": 2, "scale": 2.1},
        "prop": {"id": "focal", "sprite": "blueprint", "x": 60, "depth": 2, "scale": 2.2},
    },
    "timber_yard": {
        "sky": "day",
        "ground": "grass",
        "wings": "none",
        "wall": [
            {"sprite": "sun", "x": 80, "y": 24, "scale": 2.3},
            {"sprite": "cloud", "x": 24, "y": 22, "scale": 2.1, "bob": True},
        ],
        "backdrop": {"id": "bg_main", "sprite": "robot_arm", "x": 28, "depth": 4, "scale": 3.0},
        "secondary": {"id": "bg_sec", "sprite": "house", "x": 80, "depth": 4, "scale": 3.6},
        "prop": {"id": "focal", "sprite": "truck", "x": 26, "depth": 3, "scale": 2.2},
    },
    "harbour_veranda": {
        "sky": "sea",
        "ground": "wood",
        "wings": "none",
        "wall": [
            {"sprite": "sun", "x": 22, "y": 24, "scale": 2.1},
            {"sprite": "cloud", "x": 52, "y": 20, "scale": 1.9, "bob": True},
        ],
        "backdrop": {"id": "bg_main", "sprite": "weight_scale", "x": 30, "depth": 4, "scale": 3.0},
        "secondary": {"id": "bg_sec", "sprite": "portal_arch", "x": 54, "depth": 4, "scale": 3.1, "mount": "vfold"},
        "prop": {"id": "focal", "sprite": "magnifier", "x": 36, "depth": 2, "scale": 2.2},
    },
    "conservatory": {
        "sky": "dawn",
        "ground": "grass",
        "wings": "low",
        "wall": [
            {"sprite": "radio_dish", "x": 24, "y": 24, "scale": 2.2},
            {"sprite": "sun", "x": 80, "y": 24, "scale": 2.2},
        ],
        "backdrop": {"id": "bg_main", "sprite": "sandbox_pen", "x": 26, "depth": 4, "scale": 3.1, "mount": "box"},
        "secondary": {"id": "bg_sec", "sprite": "coffee_table", "x": 74, "depth": 4, "scale": 3.0, "mount": "box"},
        "prop": {"id": "focal", "sprite": "book_open", "x": 52, "depth": 2, "scale": 2.2},
    },
}

PRESET_ORDER = list(SETTING_PRESETS.keys())


def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")
    return s or "source-1"


def render_html_form() -> str:
    options = "".join(f'<option value="{k}">{k.replace("_", " ").title()}</option>' for k in PRESET_ORDER)
    return f"""<!doctype html>
<html lang="en-AU">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Pop-up book intake questionnaire</title>
<style>
  body {{ font-family: ui-rounded, system-ui, sans-serif; background: #f6eedb; color: #241f2e; margin: 0; padding: 32px; line-height: 1.45; }}
  main {{ max-width: 860px; margin: 0 auto; background: #fffaf0; border: 1px solid #cbb58a; border-radius: 10px; padding: 28px 32px; box-shadow: 0 8px 24px rgba(45,25,10,.12); }}
  h1, h2 {{ font-family: Georgia, serif; margin-top: 0; }}
  label {{ display: block; font-weight: 700; margin: 12px 0 4px; font-size: .92rem; }}
  input, textarea, select {{ width: 100%; padding: 8px 10px; border: 1px solid #bfae86; border-radius: 6px; background: #fffdf8; font: inherit; box-sizing: border-box; }}
  button {{ margin-top: 18px; padding: 10px 18px; border: 0; border-radius: 99px; background: #b45309; color: #fff; font-weight: 700; cursor: pointer; }}
  pre {{ background: #f3ead6; padding: 12px; border-radius: 6px; overflow: auto; font-size: .84rem; }}
</style>
</head>
<body>
<main>
  <h1>Pop-up book intake questionnaire</h1>
  <p>Fill out this optional intake form to generate a ready-to-build pop-up book folder with recurring characters and distinct settings.</p>
  <label>Folder name (lowercase letters, digits and hyphens)<input id="q-name" value="my-storybook"></label>
  <label>Book title<input id="q-title" value="My Storybook"></label>
  <label>Subtitle<input id="q-sub" value="Trials, lessons and sourced facts"></label>
  <label>Byline<input id="q-by" value="Curated for the team"></label>
  <label>Secret or out-of-scope terms to skip (comma-separated)<input id="q-skip" placeholder="client-name, internal-secret"></label>
  <label>First page setting preset<select id="q-setting">{options}</select></label>
  <label>First page title<input id="q-ch-title" value="First map"></label>
  <label>First page date or period<input id="q-ch-when" value="August 2026"></label>
  <label>First page main paragraphs (one per line)<textarea id="q-ch-sum" rows="3">On 1 August 2026 we mapped 4 questions across 2 notebooks.\nThe first draft hid the point until we put 1 recommendation at the top.</textarea></label>
  <label>The trial (what went wrong on the pull tab)<input id="q-ch-trial" value="The first draft repeated 3 sections before naming the decision."></label>
  <label>What I learned (the lesson under the top flap)<input id="q-ch-lesson" value="Put the recommendation at the top and keep the notes short."></label>
  <button type="button" id="q-export">Export answers.json</button>
  <pre id="q-out" hidden></pre>
</main>
<script>
document.getElementById("q-export").addEventListener("click", () => {{
  const data = {{
    name: document.getElementById("q-name").value.trim(),
    title: document.getElementById("q-title").value.trim(),
    subtitle: document.getElementById("q-sub").value.trim(),
    byline: document.getElementById("q-by").value.trim(),
    unit: "Page",
    skip_terms: document.getElementById("q-skip").value.split(",").map(s => s.trim()).filter(Boolean),
    cast: ["robot", "person", "owl", "robin"],
    chapters: [{{
      title: document.getElementById("q-ch-title").value.trim(),
      when: document.getElementById("q-ch-when").value.trim(),
      setting: document.getElementById("q-setting").value,
      summary: document.getElementById("q-ch-sum").value.split("\\n").map(s => s.trim()).filter(Boolean),
      trial: document.getElementById("q-ch-trial").value.trim(),
      lesson: document.getElementById("q-ch-lesson").value.trim(),
      facts: [
        {{label: "Questions mapped", value: "4", source_title: "Record A", ref: "record-a:1", excerpt: "Four questions mapped across two notebooks on 1 August 2026."}},
        {{label: "Notebooks used", value: "2", source_title: "Record A", ref: "record-a:2", excerpt: "Two notebooks held the first draft."}},
        {{label: "Sections repeated", value: "3", source_title: "Record B", ref: "record-b:4", excerpt: "Three sections repeated before 1 recommendation."}}
      ]
    }}]
  }};
  const pre = document.getElementById("q-out");
  pre.hidden = false;
  pre.textContent = JSON.stringify(data, null, 2);
}});
</script>
</body>
</html>
"""


def compile_answers(answers: dict, base_dir: Path) -> Path:
    name = str(answers.get("name") or "").strip()
    if not NAME_PATTERN.match(name):
        raise ValueError(f"Invalid folder name {name!r}; use lowercase letters, digits and hyphens")
    dest = base_dir / name
    if dest.exists():
        raise FileExistsError(f"Destination already exists: {dest}")
    (dest / "research").mkdir(parents=True)
    shutil.copy2(TEMPLATES / "fact-ledger.schema.json", dest / "research" / "fact-ledger.schema.json")
    for tpl in ("page-checklist.md", "owner-review.md", "qa-log.md"):
        shutil.copy2(TEMPLATES / tpl, dest / tpl)

    cast = answers.get("cast") or ["robot", "person", "owl", "robin"]
    skip_terms = answers.get("skip_terms") or []
    chapters_in = answers.get("chapters") or []
    if not chapters_in:
        raise ValueError("Questionnaire answers must include at least one chapter")

    sources: dict[str, dict] = {}
    ledger_facts: list[dict] = []
    story_chapters: list[dict] = []
    outline_lines = [f"# Outline for {answers['title']}", ""]
    board_lines = [f"# Storyboard for {answers['title']}", ""]

    for idx, ch in enumerate(chapters_in, start=1):
        preset_key = ch.get("setting")
        if preset_key not in SETTING_PRESETS:
            preset_key = PRESET_ORDER[(idx - 1) % len(PRESET_ORDER)]
        preset = json.loads(json.dumps(SETTING_PRESETS[preset_key]))
        companion_sprite = cast[idx % len(cast)] if len(cast) > 1 else "owl"
        if companion_sprite == "robot":
            companion_sprite = "person"

        ch_facts = []
        for f_idx, f in enumerate(ch.get("facts") or [], start=1):
            src_title = f.get("source_title") or f.get("ref") or f"Source {idx}"
            src_id = slugify(src_title)
            if src_id not in sources:
                sources[src_id] = {
                    "kind": "record",
                    "title": src_title,
                    "ref": f.get("ref") or src_id,
                    "excerpt": f.get("excerpt") or "",
                }
            else:
                if f.get("excerpt") and f["excerpt"] not in sources[src_id]["excerpt"]:
                    sources[src_id]["excerpt"] = (sources[src_id]["excerpt"] + " " + f["excerpt"]).strip()
            ch_facts.append({"label": f["label"], "value": str(f["value"]), "source": src_id})
            ledger_facts.append(
                {
                    "id": f"ch{idx:02d}-fact-{f_idx:03d}",
                    "claim": f"{f['label']}: {f['value']}. {f.get('excerpt', '')}".strip(),
                    "value": str(f["value"]),
                    "source": src_id,
                    "source_kind": "record",
                    "ref": str(f.get("ref") or src_id),
                    "excerpt": str(f.get("excerpt") or f["value"]),
                    "date": str(f.get("date") or ch.get("when") or "2026-10-30"),
                    "verified_by": "Questionnaire compiler",
                    "notes": f"Compiled from intake questionnaire for page {idx}.",
                }
            )

        pieces = [
            preset["backdrop"],
            preset["secondary"],
            {"id": "companion", "sprite": companion_sprite, "x": 18, "depth": 2, "scale": 2.5},
            preset["prop"],
            {"id": "trial_note", "sprite": "paper", "x": 14, "depth": 1, "scale": 1.9, "hidden": True},
            {"id": "hero", "sprite": "robot", "alt": "robot_happy", "x": 68, "depth": 1, "scale": 2.8, "bob": True},
        ]

        story_chapters.append(
            {
                "number": idx,
                "title": ch["title"],
                "when": ch.get("when") or f"Part {idx}",
                "status": "written",
                "text": list(ch.get("summary") or []),
                "tab": {
                    "label": "The trial",
                    "hint": "Pull to act out the trial",
                    "text": ch["trial"],
                    "effects": [
                        {"piece": "trial_note", "fx": "show", "at": [0.06, 0.45]},
                        {"piece": "trial_note", "fx": "move", "to": {"x": 36}, "at": [0.18, 0.85]},
                        {"piece": "hero", "fx": "hop", "at": [0.30, 0.90]},
                    ],
                },
                "flap": {
                    "label": "What I learned",
                    "cover": "Open",
                    "text": ch["lesson"],
                    "effects": [
                        {"piece": "trial_note", "fx": "hide", "at": [0.05, 0.42]},
                        {"piece": "focal", "fx": "move", "to": {"x": 28, "depth": 3, "lift": 18, "grow": 0.9}, "at": [0.18, 0.90]},
                        {"piece": "hero", "fx": "swap", "at": [0.38, 0.92]},
                    ],
                },
                "facts": ch_facts,
                "scene": {
                    "sky": preset["sky"],
                    "ground": preset["ground"],
                    "wings": preset["wings"],
                    "alt": f"{ch['title']} scene in the {preset_key.replace('_', ' ')}.",
                    "wall": preset["wall"],
                    "pieces": pieces,
                },
            }
        )
        outline_lines.extend(
            [
                f"## Page {idx}: {ch['title']}",
                f"- **Start:** {preset_key.replace('_', ' ')}",
                f"- **Hand action:** {ch['trial']}",
                f"- **Result:** {ch['lesson']}",
                "",
            ]
        )
        board_lines.extend(
            [
                f"## Page {idx}: {ch['title']}",
                f"- **Setting:** {preset_key}",
                f"- **Trial:** {ch['trial']}",
                f"- **Lesson:** {ch['lesson']}",
                "",
            ]
        )

    first_src = next(iter(sources.keys()))
    first_fact = ledger_facts[0]
    story = {
        "title": answers["title"],
        "subtitle": answers.get("subtitle") or "A sourced pop-up storybook",
        "byline": answers.get("byline") or "Curated with popup-storybook",
        "lang": "en-AU",
        "unit": answers.get("unit") or "Page",
        "colophon": "Compiled from verified intake questionnaire answers.",
        "cover": {"hero": "robot_wave", "button": "Open the book"},
        "contents": {
            "kicker": "Inside",
            "title": "Contents",
            "intro": answers.get("subtitle") or "Open each page, pull the tab and lift the lesson flap.",
            "scene": {
                "sky": "dawn",
                "ground": "grass",
                "alt": "The cast waves beside a signpost at dawn.",
                "wall": [{"sprite": "sun", "x": 78, "y": 26, "scale": 2.2}],
                "pieces": [
                    {"sprite": "hill", "x": 50, "depth": 4, "scale": 4.0},
                    {"sprite": "signpost", "x": 74, "depth": 3, "scale": 2.6},
                    {"sprite": "robot_wave", "x": 42, "depth": 1, "scale": 2.8, "bob": True},
                ],
            },
        },
        "chapters": story_chapters,
        "numbers": {
            "kicker": "By the numbers",
            "title": "The numbers",
            "intro": "Key figures from the record.",
            "wheelTitle": "Milestone",
            "stats": [{"label": first_fact["claim"].split(":")[0], "value": first_fact["value"], "source": first_src}],
            "months": [
                {
                    "label": f"P{c['number']}",
                    "lines": [c["title"][:24], f"{c['facts'][0]['value']} {c['facts'][0]['label'][:16]}"],
                    "source": c["facts"][0]["source"],
                }
                for c in story_chapters[:6]
            ],
        },
        "back": {
            "kicker": "The end",
            "title": "Thank you",
            "text": ["Every figure in this book points back to its recorded source."],
            "scene": {
                "sky": "dusk",
                "ground": "wood",
                "alt": "A closed book rests beside the robot at dusk.",
                "wall": [{"sprite": "moon", "x": 76, "y": 24, "scale": 2.0}],
                "pieces": [
                    {"sprite": "book_closed", "x": 62, "depth": 2, "scale": 2.4},
                    {"sprite": "robot_wave", "x": 38, "depth": 1, "scale": 2.7, "bob": True},
                ],
            },
        },
        "sources": sources,
    }

    (dest / "brief.md").write_text(
        f"# Brief for {answers['title']}\n\nCompiled via intake questionnaire.\n",
        encoding="utf-8",
    )
    (dest / "sources.md").write_text(
        "# Sources and skip list\n\n## Skip list\n"
        + ("\n".join(f"- `{t}`" for t in skip_terms) if skip_terms else "- None specified")
        + "\n",
        encoding="utf-8",
    )
    (dest / "outline.md").write_text("\n".join(outline_lines), encoding="utf-8")
    (dest / "storyboard.md").write_text("\n".join(board_lines), encoding="utf-8")
    (dest / "research" / "facts-01.json").write_text(
        json.dumps({"facts": ledger_facts}, indent=2) + "\n",
        encoding="utf-8",
    )
    (dest / "story.json").write_text(json.dumps(story, indent=2) + "\n", encoding="utf-8")
    return dest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--html", metavar="OUT.html", help="export a standalone offline HTML questionnaire form")
    parser.add_argument("--from", dest="from_file", metavar="ANSWERS.json", help="compile answers JSON into a story folder")
    parser.add_argument("--dir", default="stories", help="parent directory for the generated story folder")
    args = parser.parse_args(argv)

    if not args.html and not args.from_file:
        parser.error("Provide --html OUT.html or --from ANSWERS.json")

    if args.html:
        out_html = Path(args.html)
        out_html.parent.mkdir(parents=True, exist_ok=True)
        out_html.write_text(render_html_form(), encoding="utf-8")
        print(f"PASS: wrote questionnaire HTML form to {out_html}")

    if args.from_file:
        ans_path = Path(args.from_file)
        if not ans_path.exists():
            print(f"FAIL: answers file not found: {ans_path}", file=sys.stderr)
            return 1
        answers = json.loads(ans_path.read_text(encoding="utf-8"))
        dest = compile_answers(answers, Path(args.dir))
        print(f"PASS: compiled questionnaire into {dest}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
