# Architecture decisions

These eight decisions record how the engine and its workflow stay simple while adding safer intake, claim checks, contrast checks, and cover-card previews.

## ADR-001: Guard source selection before prose exists

- **Status:** accepted
- **Date:** 2026-10-29
- **Decision:** Put the read and skip policy in the scaffolded `brief.md` and `sources.md`. Keep `SECRET_PATTERNS` as the later build-time backstop.
- **Reason:** A late validator can stop a leak from the finished story. It cannot stop an agent from reading a credential file during research.
- **Rejected:** Crawling the whole project and cleaning up afterwards.

## ADR-002: Describe every page as a state transition

- **Status:** accepted
- **Date:** 2026-10-29
- **Decision:** Add `Start`, `Hand action`, and `Result` fields to the outline and storyboard templates. Keep `Beat`, `Trial`, and `Lesson` for the story meaning.
- **Reason:** Pop-up paper is clearest when the hand causes a visible change. The new fields improve planning without changing `story.json`.
- **Rejected:** Adding a second storyboard schema or a timed video model.

## ADR-003: Stage deterministic claim checks before strict enforcement

- **Status:** accepted
- **Date:** 2026-10-29
- **Decision:** Add `--claims report|strict|off` to `tools/check_ledger.py` with `report` as default. The scaffold work order uses `strict` for new stories. Existing books can run `report` until their page facts are aligned. Pre-template Edition 1 ledgers remain supported for regression checks.
- **Reason:** Numeric checks are valuable, but old books may cite the supporting source elsewhere in the research ledgers. A staged mode protects compatibility and prevents silent omission.
- **Rejected:** Breaking existing books immediately or claiming that number matching proves every sentence.

## ADR-004: Measure contrast in the browser and fail zero coverage

- **Status:** accepted
- **Date:** 2026-10-29
- **Decision:** Extend `tools/check_layout.py` with a browser-side contrast check for a fixed list of reader-facing selectors. Fail below WCAG AA and fail when an expected page checks zero visible text nodes.
- **Reason:** Computed styles and final visibility only exist in the browser. Zero coverage is not a pass.
- **Rejected:** Static CSS parsing or a whole-page text crawl over hidden turn faces.

## ADR-005: Keep paper motion controlled by hand position

- **Status:** accepted
- **Date:** 2026-10-29
- **Decision:** Add static warnings for ambiguous hide and show overlap windows. Keep effects as pure functions of tab or flap travel.
- **Reason:** Staggering avoids muddy substitutions while preserving the paper mechanics rules.
- **Rejected:** Timers, beat grids, or canned transition sequences.

## ADR-006: Shape synthesized sound instead of importing assets

- **Status:** accepted
- **Date:** 2026-10-29
- **Decision:** Define named frequency ceilings for one-shot rustles, repeated clicks, and continuous movement. Enforce them in `engine/book.js` and browser tests.
- **Reason:** The built book remains one offline file. Frequency ceilings reduce ear fatigue without an audio library or licence burden.
- **Rejected:** Sampled SFX, music tracks, bundled CC BY audio, or external audio tools.

## ADR-007: Export one explicit settled cover card

- **Status:** accepted
- **Date:** 2026-10-29
- **Decision:** Add `--poster` and `--poster-page` to `tools/shoot.py`. Capture the requested spread after `set_final()` and save `cover-card.jpg` at the desktop viewport.
- **Reason:** Authors need one stable image for private previews and owner review. The normal contact sheets remain unchanged.
- **Rejected:** Automatic scene scoring, frame-zero video tricks, or publishing the image.

## ADR-008: Use one source for privacy patterns

- **Status:** accepted
- **Date:** 2026-10-29
- **Decision:** `engine/validate.py` remains the sole definition of `SECRET_PATTERNS`. `tools/release_check.py` imports it. A unit test protects both rule names and regex strings.
- **Reason:** One list prevents drift between build-time and release-time privacy scans.
- **Rejected:** Duplicating regex lists across multiple files.

## Non-goals

- Do not turn books into MP4 launch videos or time-based autoplay animations.
- Do not add FFmpeg, npm packages, external audio files, sampled sound effects, or voiceover.
- Do not make a hosted publishing service or hosted intake form.
- Do not change the core paper controls, page-turn rules, story JSON runtime shape, pixel-art style, or private-by-default policy.
- Do not use OCR, language models, or network calls for claim checking.
- Do not promise complete semantic fact checking. The fixed-rule check covers numeric and date-like claims only.
- Do not make a passing contrast check proof that all accessibility requirements are met.
- Do not make preview images public. They stay in the selected output folder.
