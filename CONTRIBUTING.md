# Contributing

Thanks for helping. This is a small engine with a strong point of view, so a few rules keep it that way.

## Ground rules

- The engine stays zero-dependency. A built book is one HTML file that works offline.
- QA tools may use Playwright and Pillow. Nothing else without a good reason.
- Every change to `engine/` must keep book mode working on every page, at desktop and phone sizes.
- Write docs in plain short sentences. Point first, one idea per sentence, no jargon.

## Before you open a pull request

```bash
python3 engine/validate.py stories/example/story.json --strict
python3 tools/check_ledger.py templates/ledger-template.json --story stories/example/story.json --claims strict
python3 -m unittest discover -s tests
python3 tools/check_layout.py stories/example/story.json --phone
python3 tools/check_mechanics.py stories/example/story.json --phone
python3 tools/release_check.py
```

If you change how anything looks, attach a contact sheet from `tools/shoot.py` showing the example before and after.

## Design changes

Read `docs/DESIGN-RULES.md` first. Each rule came from real feedback. If you want to change one, explain what readers will get instead.

## New sprites

Edit `tools/sprites_src.py`, then run it to rebuild `engine/library/sprites.json`. Regenerate the text list with `python3 tools/list_sprites.py --markdown docs/SPRITES.md`. A test fails if the library or list drifts from its source.

## Stories

Do not add real books to this repo. Keep each book in its own repo and build it with this engine.
