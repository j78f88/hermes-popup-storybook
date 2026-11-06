#!/usr/bin/env python3
"""List shared sprites by name, pixel size and plain tag."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LIBRARY = ROOT / "engine" / "library" / "sprites.json"
GROUPS = {
    "character": {"robot", "robot_wave", "robot_happy", "robot_sleep", "robin", "owl", "person"},
    "book and office": {"shelf", "shelf_full", "book_stack", "book_open", "book_closed", "paper", "sticky_y", "sticky_p", "sticky_b", "sticky_l", "board", "table_round", "blueprint", "workbench", "scorecard_9", "scorecard_7", "trophy", "trophy_cutout", "magnifier", "map_wall", "drafting_table", "compass_rose", "mail_chute", "conveyor", "video_card", "scales", "gavel_bench", "recycle_bin", "clock_wall", "hansard_desk"},
    "room and technology": {"server", "nas", "laptop", "plant", "lamp", "lamp_off", "window_night", "mug", "telescope", "memory_dome", "radar_screen", "server_pair", "chandelier", "scoreboard", "podium_steps", "hurdle", "anvil_forge", "robot_arm", "weight_scale", "radio_dish", "sandbox_pen", "coffee_table"},
    "signal": {"megaphone", "bubble_alert", "bubble_ok", "bell", "heart", "spark"},
    "place and travel": {"box", "truck", "house", "mirror", "signpost", "calendar", "bridge_arch", "parliament_roof", "timber_frame", "portal_arch"},
    "sky and nature": {"sun", "moon", "star", "cloud", "raincloud", "tree", "waves", "hill"},
}


def tag_for(name):
    for tag, names in GROUPS.items():
        if name in names:
            return tag
    return "general"


def rows(search=""):
    sprites = json.loads(LIBRARY.read_text())["sprites"]
    needle = search.casefold()
    found = []
    for name, pixels in sprites.items():
        tag = tag_for(name)
        if needle and needle not in name.casefold() and needle not in tag.casefold():
            continue
        found.append((name, len(pixels[0]), len(pixels), tag))
    return found


def markdown(items):
    lines = [
        "# Sprite list",
        "",
        "Use `python3 tools/list_sprites.py SEARCH` to filter this list.",
        "",
        "Keep `docs/sprites.png` open when you need to compare the artwork.",
        "",
        "| Name | Size | Tag |",
        "|---|---:|---|",
    ]
    lines.extend(f"| `{name}` | {width} by {height} | {tag} |" for name, width, height, tag in items)
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("search", nargs="?", default="", help="name or tag to find")
    parser.add_argument("--markdown", metavar="FILE", help="write the full list as Markdown")
    args = parser.parse_args(argv)
    items = rows(args.search)
    if args.markdown:
        if args.search:
            parser.error("--markdown writes the full list and cannot be combined with SEARCH")
        destination = Path(args.markdown)
        destination.write_text(markdown(items))
        print(f"Wrote {destination} with {len(items)} sprites.")
        return 0
    print("name\tsize\ttag")
    for name, width, height, tag in items:
        print(f"{name}\t{width}x{height}\t{tag}")
    print(f"{len(items)} sprites")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
