#!/usr/bin/env python3
"""Create a new popup-storybook working folder from process templates."""

import argparse
import json
import re
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"
NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")
COPIES = {
    "brief.md": "brief.md",
    "sources.md": "sources.md",
    "outline.md": "outline.md",
    "storyboard.md": "storyboard.md",
    "fact-ledger.schema.json": "research/fact-ledger.schema.json",
    "ledger-template.json": "research/ledger-template.json",
    "page-checklist.md": "page-checklist.md",
    "owner-review.md": "owner-review.md",
    "qa-log.md": "qa-log.md",
}


def positive_page_count(value):
    count = int(value)
    if count < 1:
        raise argparse.ArgumentTypeError("pages must be at least 1")
    return count


def example_chapter():
    """Return one complete page that demonstrates the authoring pattern."""
    return {
        "number": 1,
        "title": "A careful first step",
        "when": "Starter example",
        "status": "written",
        "text": [
            "A small team found an empty corner and planned a quiet reading place. "
            "They counted the shelf, box and plant before moving anything. The simple "
            "record gave the page a clear starting point.",
            "The first arrangement blocked the path. Pull the tab to move Pip aside and "
            "make room. Lift the lesson flap to place the box safely on the shelf. This "
            "fictional page is ready to replace with your own verified story.",
        ],
        "tab": {
            "label": "The trial",
            "hint": "Pull to clear the path",
            "text": "Pip moves aside so the team can reach the shelf.",
            "effects": [
                {
                    "piece": "hero",
                    "fx": "move",
                    "to": {"x": 64},
                    "at": [0.05, 0.95],
                }
            ],
        },
        "flap": {
            "label": "What I learned",
            "cover": "LIFT",
            "text": "Count first, then give each object a safe place.",
            "effects": [
                {
                    "piece": "box",
                    "fx": "move",
                    "to": {"x": 24, "depth": 4, "lift": 22, "grow": 0.75},
                    "at": [0.08, 0.92],
                }
            ],
        },
        "facts": [
            {"label": "Shelves checked", "value": "1", "source": "arrival-example"},
            {"label": "Boxes moved", "value": "1", "source": "rain-example"},
            {"label": "Plants kept", "value": "1", "source": "opening-example"},
        ],
        "scene": {
            "sky": "library",
            "ground": "wood",
            "alt": "Pip stands between a shelf and a box.",
            "wall": [
                {"sprite": "calendar", "x": 76, "y": 42, "scale": 1.5}
            ],
            "pieces": [
                {"id": "shelf", "sprite": "shelf", "x": 22, "depth": 4, "scale": 2.4},
                {"id": "box", "sprite": "box", "x": 88, "depth": 2, "scale": 1.5},
                {"id": "hero", "sprite": "robot", "alt": "robot_happy", "x": 42, "depth": 1, "scale": 2.5},
            ],
        },
    }


def story_data(title, pages):
    chapters = [example_chapter()]
    for number in range(2, pages + 1):
        chapters.append(
            {
                "number": number,
                "title": f"Page {number}",
                "status": "open",
                "stamp": "To be written",
                "scene": {
                    "sky": "day",
                    "ground": "paper",
                    "alt": f"A placeholder scene for page {number}.",
                    "pieces": [
                        {"id": "hero", "sprite": "robot", "x": 40, "depth": 1, "scale": 3}
                    ],
                },
            }
        )
    return {
        "title": title,
        "subtitle": "A story ready to research and make your own",
        "byline": "Starter book",
        "lang": "en-AU",
        "unit": "Page",
        "colophon": "The first page and its sources are fictional starter material.",
        "cover": {"hero": "robot_wave", "button": "Open the book"},
        "contents": {
            "kicker": "Inside",
            "title": "Contents",
            "intro": "The first page demonstrates the complete pattern. Replace its example facts with your own record.",
            "scene": {
                "sky": "dawn",
                "ground": "grass",
                "alt": "Pip waves beside a signpost and a small plant at dawn.",
                "wall": [{"sprite": "sun", "x": 78, "y": 28, "scale": 1.8}],
                "pieces": [
                    {"sprite": "signpost", "x": 66, "depth": 3, "scale": 2.0},
                    {"sprite": "robot_wave", "x": 38, "depth": 1, "scale": 2.5},
                    {"sprite": "plant", "x": 84, "depth": 2, "scale": 1.4},
                ],
            },
        },
        "chapters": chapters,
        "numbers": {
            "kicker": "By the numbers",
            "title": "Starter numbers",
            "intro": "Turn the wheel to review the fictional starter facts.",
            "wheelTitle": "Starter fact",
            "stats": [
                {"label": "example facts", "value": "3", "source": "arrival-example"}
            ],
            "months": [
                {"label": "Plan", "lines": ["1 shelf checked"], "source": "arrival-example"},
                {"label": "Move", "lines": ["1 box moved"], "source": "rain-example"},
                {"label": "Keep", "lines": ["1 plant kept"], "source": "opening-example"},
            ],
        },
        "back": {
            "kicker": "Your turn",
            "title": "Make the story yours",
            "text": ["Replace the starter facts, words and scene with your verified history."],
            "scene": {
                "sky": "dusk",
                "ground": "wood",
                "alt": "A closed book rests beside a plant at dusk.",
                "pieces": [
                    {"sprite": "book_closed", "x": 44, "depth": 1, "scale": 3.0},
                    {"sprite": "plant", "x": 68, "depth": 2, "scale": 1.7},
                ],
            },
        },
        "sources": {
            "arrival-example": {"kind": "example", "title": "Example room plan", "ref": "Starter record A", "excerpt": "One shelf was checked."},
            "rain-example": {"kind": "example", "title": "Example move count", "ref": "Starter record B", "excerpt": "One box was moved."},
            "opening-example": {"kind": "example", "title": "Example garden note", "ref": "Starter record C", "excerpt": "One plant was kept."},
        },
    }


def work_order(story_path, name):
    build_path = Path("dist") / name / "index.html"
    shots_path = Path("shots") / name
    return f"""1. Brief: complete {story_path.parent / 'brief.md'}, settle the skip list in {story_path.parent / 'sources.md'} before research, and get owner approval.
2. Sources: freeze the record in {story_path.parent / 'sources.md'}.
3. Fact ledgers: replace the example facts, then run:
   python3 tools/check_ledger.py {story_path.parent / 'research'}/*.json --story {story_path} --claims strict
4. Outline: shape the pages in {story_path.parent / 'outline.md'}.
5. Storyboard: plan every scene in {story_path.parent / 'storyboard.md'}, then run:
   python3 engine/build.py {story_path} -o {build_path}
   Open {build_path}#storyboard and record the owner decision.
6. Write: replace the starter prose and facts in {story_path}.
7. Lay out: place the pieces and tune both paper mechanisms in {story_path}.
8. Build: run both commands:
   python3 engine/validate.py {story_path} --strict
   python3 engine/build.py {story_path} -o {build_path}
9. Measure: run both checks:
   python3 tools/check_layout.py {build_path} --phone
   python3 tools/check_mechanics.py {build_path} --phone
10. Look: capture all four states and the cover card:
   python3 tools/shoot.py {build_path} -o {shots_path} --phone
   python3 tools/shoot.py {build_path} -o {shots_path} --poster-only --poster-page 1
11. Owner review: record each decision in {story_path.parent / 'owner-review.md'}, then repeat steps 8 to 10.
12. Publish: export, checksum and scan the finished edition:
   python3 tools/export_pdf.py {build_path} -o dist/{name}/book.pdf --storyboard dist/{name}/storyboard.pdf
   sha256sum dist/{name}/* > dist/{name}/SHA256SUMS
   python3 tools/release_check.py --history
"""


def readme_text(title, story_path, name):
    return f"""# {title}

This folder holds the research, plan, review notes and source story data.

The first page is a complete fictional example. Replace it with verified material.

## Work order

{work_order(story_path, name)}
"""


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name", help="folder name using lowercase letters, numbers, and hyphens")
    parser.add_argument("--dir", default="stories", help="parent folder for the new story")
    parser.add_argument("--title", help="story title shown on the cover")
    parser.add_argument("--pages", type=positive_page_count, default=3, help="number of open pages")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    if not NAME_PATTERN.fullmatch(args.name):
        print(
            "error: NAME must use lowercase letters, numbers, and hyphens",
            file=sys.stderr,
        )
        return 2

    parent = Path(args.dir)
    target = parent / args.name
    if target.exists():
        print(f"error: {target} already exists", file=sys.stderr)
        return 1

    title = args.title or args.name.replace("-", " ").title()
    target.mkdir(parents=True)
    for template, destination in COPIES.items():
        output = target / destination
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(TEMPLATES / template, output)

    story_path = target / "story.json"
    story_path.write_text(json.dumps(story_data(title, args.pages), indent=2) + "\n")
    readme_path = target / "README.md"
    readme_path.write_text(readme_text(title, story_path, args.name))

    open_count = args.pages - 1
    suffix = "page" if open_count == 1 else "pages"
    print(f"Created {target} with 1 written example page and {open_count} open {suffix}.")
    print("Work order:")
    print(work_order(story_path, args.name), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
