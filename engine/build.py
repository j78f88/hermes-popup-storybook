#!/usr/bin/env python3
"""Build a popup-storybook story into one self-contained HTML file.

Usage: python3 engine/build.py STORY.json [-o dist/NAME/index.html] [--deny FILE] [--no-validate]
The output works offline: no fonts, images or scripts are fetched.
"""
import argparse
import hashlib
import html as html_module
import json
import sys
from pathlib import Path

ENGINE = Path(__file__).resolve().parent
sys.path.insert(0, str(ENGINE))
import validate as V  # noqa: E402


def render(story):
    lib, font = V.load_library()
    data = dict(story)
    data["__library"] = {"palette": lib["palette"], "sprites": lib["sprites"], "font": font}
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    payload = payload.replace("</", "<\\/").replace("<!--", "<\\!--")
    html = (ENGINE / "template.html").read_text()
    css = (ENGINE / "book.css").read_text()
    js = (ENGINE / "book.js").read_text()
    title = html_module.escape(str(story.get("title", "Storybook")), quote=True)
    lang = html_module.escape(str(story.get("lang", "en")), quote=True)
    for k, v in {"{{lang}}": lang, "{{version}}": V.VERSION, "{{title}}": title}.items():
        html = html.replace(k, v)
    # Insert the large blocks last so their contents are never re-scanned for placeholders.
    head, rest = html.split("{{css}}")
    mid, rest = rest.split("{{story}}")
    mid2, tail = rest.split("{{js}}")
    return head + css + mid + payload + mid2 + js + tail


def main(argv=None):
    ap = argparse.ArgumentParser(description=(__doc__ or "").strip().split("\n")[0])
    ap.add_argument("story")
    ap.add_argument("-o", "--out")
    ap.add_argument("--deny")
    ap.add_argument("--no-validate", action="store_true")
    a = ap.parse_args(argv)
    sp = Path(a.story)
    story = json.loads(sp.read_text())
    if not a.no_validate:
        deny = V.load_deny(a.deny) if a.deny else []
        errors, warnings = V.validate(story, deny)
        for w in warnings:
            print("WARN ", w)
        if errors:
            for e in errors:
                print("ERROR", e)
            print(f"FAIL: {len(errors)} errors; nothing built")
            return 1
    out = Path(a.out) if a.out else Path("dist") / sp.parent.name / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    html = render(story)
    out.write_text(html)
    digest = hashlib.sha256(html.encode()).hexdigest()
    print(f"built {out} ({len(html) // 1024} KB) sha256 {digest[:16]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
