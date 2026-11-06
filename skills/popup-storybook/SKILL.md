---
name: popup-storybook
description: Use when building a sourced pop-up storybook or keepsake.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [storybook, pop-up, retrospective, pixel-art, html, keepsake]
    related_skills: []
---

# Pop-up Storybook

## Overview

Turn a real project history into a virtual pop-up book. One story JSON file builds into one offline HTML file. It includes tunnel-book scenes, a pull tab, a lift flap, a taped fact booklet, a paper wheel, a storyboard mode, and a print edition.

This repository (`hermes-popup-storybook`) holds the zero-dependency Python engine, validator, sprite library, templates, and QA tools. Read `docs/PROCESS.md` for the twelve-step method, `docs/ADR.md` for architecture decisions, and `docs/DESIGN-RULES.md` for layout defaults. Keep real books in their own separate repositories so private project history never mixes with the engine.

## When to Use

- The user wants a storybook, memoir, retrospective, or keepsake of a project, team, or milestone.
- A handover, launch, or retrospective needs an interactive offline record where every fact cites a source.

Do not use for:

- Routine status reports, sprint plans, or slide decks.

## Twelve-Step Method

Follow `docs/PROCESS.md` in order from brief to publication. Start a new book with `python3 tools/new_story.py my-book --title "My Book"`. The owner signs off the brief and the `#storyboard` view before the full build.

1. **Freeze the sources and skip list.** Complete the nine safe-intake sections in `brief.md` and the secret skip list in `sources.md` before scanning repositories or notes. List where the history lives, such as git logs, issue tracker exports, read-only session logs, project notes, and evidence folders.
2. **Build fact ledgers first, prose second.** Collect one JSON ledger per chapter range under `stories/<name>/research/`. Each fact needs a claim, value, source kind, exact reference, and short verbatim excerpt. Run `python3 tools/check_ledger.py stories/<name>/research/*.json --story stories/<name>/story.json --claims strict` so prose numbers and dates match the record.
3. **Verify load-bearing facts directly.** Recount key numbers from the primary source, such as `git rev-list --count HEAD` or an issue tracker export. Check every quoted excerpt at its exact reference.
4. **Plan paper state changes and write in plain prose.** In `outline.md` and `storyboard.md`, record each page's start state, hand-driven action, and settled result state before layout. Keep main text to 100 to 230 words per page, trial text under 60 words, and lesson text under 45 words.
5. **Design scenes.** Keep recurring characters across the book while varying each chapter's setting. No depth 3-4 backdrop piece or sky and ground pair may repeat on more than two chapters (`engine/validate.py --strict` checks this). Combine `move`, `hop`, `rise`, `flip`, `glow`, and `swap` on tabs and flaps. Place the hero at depth 1 and off-centre, and large furniture at depth 3 or 4 with scale 3 or more. Stagger `hide` and `show` windows when swapping pieces in the same spot.
6. **Validate and build.** Run `python3 tools/build_and_check.py STORY.json --fast` for validation, ledger checks, build, layout, and mechanics in one pass. Drop `--fast` before final review. Or run `python3 engine/validate.py STORY.json --strict` and `python3 engine/build.py STORY.json` directly.
7. **Measure every change.** Run `python3 tools/check_layout.py STORY.json --phone` and `python3 tools/check_mechanics.py STORY.json --phone`. `check_layout.py` fails on off-page pieces, items under the lesson card, `NaN` positions, low WCAG AA contrast, page errors, and broken tabs.
8. **Capture and inspect states.** Run `python3 tools/shoot.py STORY.json -o DIR --phone` to save four states per page and contact sheets. Run `python3 tools/shoot.py STORY.json -o DIR --poster --poster-page N` on desktop to export a settled 1440x900 `cover-card.jpg` preview.
9. **Optional vision QA.** Run `python3 tools/visual_qa.py --model MODEL --images DIR --brief templates/qa-briefs/first-pass.md --var book=... --out DIR` with `--dry-run` first. Confirm any vision findings in the browser DOM before changing layout values.
10. **Export and check privacy.** Run `python3 tools/export_pdf.py STORY.json -o book.pdf --storyboard storyboard.pdf`. Before sharing a book or engine changes, run `python3 tools/release_check.py --history --deny FILE` with a deny list kept outside the repository.

## Common Pitfalls

1. **Idle sway and bob animations shift screenshots.** Inject `.set{animation:none!important}.piece.bob .mech>svg,.piece.twinkle .mech>svg{animation:none!important}` before manual QA screenshots.
2. **Vision review overclaims.** Vision models can flag decorative tape and intentional dissolves as bugs. Confirm with DOM readback (`getBoundingClientRect` and computed styles) before changing code.
3. **Text overflow.** At 1440x900 about 230 words fit beside the gadgets. Check `.prose.scrolls` on every spread and trim prose rather than shrinking the font.
4. **SVG width measurement.** SVG elements have no `offsetWidth`, so read `parseFloat(getComputedStyle(svg).width)` to avoid `NaN` layout values.
5. **Sprite edits.** Edit sprites only in `tools/sprites_src.py` and run it to regenerate `engine/library/sprites.json` and `docs/sprites.png`. Then run `python3 tools/list_sprites.py --markdown docs/SPRITES.md`.

## Verification Checklist

- [ ] `python3 engine/validate.py STORY.json --strict` passes with zero errors.
- [ ] `python3 tools/check_ledger.py ... --claims strict` passes with zero unmatched numeric/date claims.
- [ ] `python3 tools/check_layout.py STORY.json --phone` and `python3 tools/check_mechanics.py STORY.json --phone` pass.
- [ ] `python3 -m unittest discover -s tests` passes.
- [ ] `python3 tools/release_check.py --history` passes with zero findings.
