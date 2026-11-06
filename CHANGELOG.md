# Changelog

## Unreleased

- Mechanics contract (`docs/MECHANICS.md`) and checker (`tools/check_mechanics.py`): every paper part measured with real mouse, touch and keyboard input.
- Page turns work like a real book. The leaf follows your hand, the leaf and both pop-ups move together, and each surface carries the right page. The finale splits at the spine.
- The lesson flap lifts upwards, as its arrow shows. Tabs remember where you left them. Turning a page presses a lifted flap shut.
- Hidden pieces stay opaque and lie flat until they stand up. Look-around only follows a pointer over the picture.
- Phone: drag the picture to turn a page, and booklet pages turn as visible leaves.
- Paper sound now follows each mechanism's movement, speed, detents and folds.
- Optional centre-spread finales rise across the whole open book, with phone, storyboard and print views.
- The method is written down in `docs/PROCESS.md`, with templates for every step.
- Storyboard mode: open a book with `#storyboard` for a planning sheet.
- `tools/new_story.py` starts a story with the templates.
- QA tools: `check_layout.py`, `shoot.py`, `export_pdf.py`, and a generic `visual_qa.py`.
- `tools/release_check.py` checks for private data before sharing.
- The example story shows every mechanism.
- Real books live in their own repos. The first book moved out.

## 0.6

- Real paper mechanisms. The pull tab is a slider that the picture follows. The lesson flap sits on the picture. Facts live in a taped booklet.
- Fixed a bug where pieces never moved sideways. SVG elements have no `offsetWidth`.

## 0.5

- The pop-up fills the whole right page. Entries can be called pages. No drop caps or page numbers.
- Every cut-out is kept inside the page.

## 0.4

- The lesson flap resolves the scene with a move. Paper feet, contact shadows and optional sounds.

## 0.1 to 0.3

- First engine, validator, build, sprite library, print edition and phone layout.
