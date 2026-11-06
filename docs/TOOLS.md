# QA tools

These commands run from repository root and accept either story JSON or built HTML.

## `check_ledger.py`

This tool checks fact ledgers, story source IDs and numeric claims in story prose.

```bash
python3 tools/check_ledger.py LEDGER.json [...] [--story STORY.json] [--claims off|report|strict]
```

Use `--claims report` to print warnings for unsupported numbers and dates without failing.

Use `--claims strict` on new stories so unsupported numeric claims return a non-zero exit status.

Pre-template Edition 1 ledgers with a top-level `lane` key and object `source` fields remain supported for regression checks.

Written number words and narrative claims without digits still need human review.

## `check_layout.py`

This tool checks every required desktop or phone state for measurable layout and contrast defects.

```bash
python3 tools/check_layout.py STORY.json|BOOK.html [--phone] [--browser chromium|firefox|webkit] [--allow ID] [--json OUT]
```

A successful run prints PASS with the page-state count and the text contrast count.

Use `--json` when automated systems need structured findings and exact element identifiers.

Contrast failures report reader text below 4.5 to 1, or below 3.0 to 1 for large or bold text.

The check inspects the fixed selector list `.page.left .title`, `.page.left .prose p`, `.slider .seg.trial`, `.lesson-card .lesson-body`, `.cover-card h1`, `.cover-card .sub`, `.cover:not(.open) .outside .sub`, `.finale-banner-paper .title`, and `.finale-copy p`.

Zero checked text elements on a visible text spread also fails the run.

Offstage failures identify pieces outside safe boundaries during one or more interaction states.

Move those pieces inward, or allow intentional exceptions with repeated `--allow` options.

Lesson failures mean visible pieces sit beneath the lesson card on the picture.

Lower or resize those pieces until every tested state clears the card.

NaN failures cover left, bottom, growth and mechanism transforms.

Correct the reported piece values, then rebuild the book before checking again.

Drag failures show that a pull tab and paper strip no longer track together.

The drag check covers every page with a slider.

Overlap warnings name each piece by id or by sprite and scene index.

A high overlap warning covers more than half of a moving or appearing piece.

Review every warning visually. Intentional paper stacking remains a warning.

Browser launch failures usually mean the selected browser or Playwright is missing.

Install Playwright and the selected browser using the commands shown in continuous integration.

## `check_mechanics.py`

This tool measures every checked rule in the paper mechanics contract.

```bash
python3 tools/check_mechanics.py STORY.json [--phone] [--browser chromium|firefox] [--only S,F,T] [--json OUT]
```

It prints one PASS or FAIL line for each applicable rule and page.

Use `--phone` for the touch layout. Use `--only` to check named rules or whole rule families.

## `shoot.py`

This tool captures repeatable screenshots for every chapter state, including dedicated phone views.

```bash
python3 tools/shoot.py STORY.json|BOOK.html -o DIR [--phone] [--poster] [--poster-only] [--poster-page N]
```

A successful run fills the output directory with consistently named PNG screenshots.

Each chapter has start, half-pulled, fully pulled and lifted states.

Contact sheets show those four states in four columns.

Use `--phone` to capture the narrow layout required for responsive visual review.

Use `--poster` with `--poster-page N` on desktop to save `cover-card.jpg` at 1440 by 900 in the lifted final state.

Use `--poster-only` when you want only `cover-card.jpg` without re-shooting every desktop state.

The cover card is private output for owner review, not public publication.

Combining `--poster` and `--phone` fails before launching the browser.

Missing screenshots often indicate a browser launch failure or an invalid story path.

Check Chromium installation, confirm the input exists, then remove any incomplete output before retrying.

## `export_pdf.py`

This tool exports the flat print edition, with an optional storyboard companion document.

```bash
python3 tools/export_pdf.py STORY.json|BOOK.html -o OUT.pdf [--storyboard OUT2.pdf]
```

A successful run creates a readable PDF at the requested output path.

Supplying `--storyboard` also creates a second PDF containing visual planning reference pages.

Blank pages usually mean Chromium could not finish loading the built book.

Validate the story, confirm Chromium works, then rerun after clearing the partial PDF.

Missing storyboard output means the built book did not render storyboard mode.

Add storyboard support to the engine, then rebuild and repeat the export.

## `visual_qa.py`

This tool sends prepared screenshots and a review brief to a selected vision model.

```bash
python3 tools/visual_qa.py --model MODEL --images DIR --brief FILE [--var key=value] [--recheck PREV_RAW.json] --out DIR [--dry-run]
```

A successful run writes structured review files inside the specified output directory.

Dry runs verify image discovery, prompt rendering and payload size without sending requests.

The output lists every resolved variable. The full brief is saved as `qa-dry-run-brief.md`.

Provide every required brief template value with repeated `--var key=value` command arguments.

Authentication failures mean `OPENROUTER_API_KEY` is missing, invalid, or unavailable to the process.

Set a valid environment value, then repeat the same command without changing inputs.

Empty image failures mean the directory contains no supported screenshots for review.

Generate screenshots first, then confirm their extensions and directory permissions before retrying.

Rechecks should reference the previous raw JSON and include only affected images.

## `release_check.py`

This tool scans the repository before it leaves its owner.

```bash
python3 tools/release_check.py [--deny FILE] [--allow-story NAME]
python3 tools/release_check.py --history [--baseline FILE]
```

The default scan covers tracked files and untracked files not ignored by Git.

The result prints separate tracked and untracked file counts.

Use `--history` before preparing a public copy.

A history finding includes a twelve-character id.

After review, place accepted ids in the baseline file, one per line.

New history findings still fail the check.

Do not rewrite Git history to clear findings. Make a fresh public export without repository history.

## `ingest_image.py`

This tool brings a user photo or stock image into `story.json` for offline use.

```bash
python3 tools/ingest_image.py IMAGE_PATH --story STORY.json --id ID [--mode cutout|polaroid|pixel] [--source SOURCE_ID]
```

It strips EXIF and GPS metadata before saving.

Use `--mode cutout` to create a die-cut stage piece with a white paper border.

Use `--mode polaroid` to add a framed photo inside a fact card or on a wall.

Use `--mode pixel` to convert an image into a 20-colour pixel sprite grid.

## `questionnaire.py`

This tool provides an optional questionnaire pathway to create a new story folder.

```bash
python3 tools/questionnaire.py --html intake.html
python3 tools/questionnaire.py --from answers.json --dir stories
```

Use `--html` to save an offline HTML questionnaire form.

Use `--from` to compile an answers file into a complete story folder with recurring characters and distinct settings.

## `build_and_check.py`

This tool runs validation, ledger checks, HTML build, layout checks and mechanics checks in one command.

```bash
python3 tools/build_and_check.py STORY.json [-o dist/index.html] [--fast] [--json receipt.json]
```

Use `--fast` during iteration to run the quick mechanics rules before the full page-turn pass.
