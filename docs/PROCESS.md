# The process

This is how to make a pop-up storybook from a real history, from first idea to published edition. It is the method used for the first book, written down so anyone can repeat it.

Each step has a purpose, the work, what it produces and a check before you move on. Run `python3 tools/new_story.py NAME` first. It copies every template and adds one complete fictional page to replace.

The steps run in order the first time. After the first edition, steps 9 to 12 repeat as a loop until the owner is happy.

| Step | What you do | What you end with |
|---|---|---|
| 1. Brief | Agree what the book is for | `brief.md`, signed off |
| 2. Sources | Freeze the record | `sources.md` |
| 3. Fact ledgers | Collect facts before writing | `research/*.json` |
| 4. Outline | Shape the story into pages | `outline.md` |
| 5. Storyboard | Plan each page's scene and mechanisms | `storyboard.md` and a draft `story.json`, signed off |
| 6. Write | Write the pages | Finished text in `story.json` |
| 7. Lay out | Place the cut-outs and tune the mechanisms | Finished scenes in `story.json` |
| 8. Build | Validate and build | One HTML file |
| 9. Measure | Check the layout by machine | A clean `check_layout` report |
| 10. Look | Review screenshots, then get an outside review | `qa-log.md` entries |
| 11. Owner review | Show the owner and refine | `owner-review.md` entries, a new edition |
| 12. Publish | Export and store the edition | HTML, PDF, storyboard PDF and checksums |

The scaffold carries the safe intake, source rules and page-state questions. Complete those before opening broad source folders. The checks improve judgement. They do not replace source review or owner approval.

## 1. Brief

Purpose: agree what the book is for before anyone writes a word.

- Write down who the book is for and why it matters now. A shutdown, a launch or a handover are good reasons.
- Pick the narrator and the voice. First person from the subject reads warmly.
- Set the length. Ten to fourteen pages works well. Each page is one spread.
- Decide what must stay out. Secrets, private business plans, customer details and anyone who has not agreed to appear.
- Write the success test in one sentence. For example: "The owner reads it end to end and finds nothing wrong or missing."

Check: the owner has read `brief.md` and said yes.

## 2. Sources

Purpose: know exactly what the book is allowed to say.

- List every place the history lives. Code history, tickets, notes, chat records, photos, documents.
- Freeze them. Record the date and the exact version, such as a commit or an export file.
- Note what was lost or pruned, so the book does not pretend to be complete.
- Open records read-only. Never change a source while you research it.

Check: `sources.md` lists every source with a freeze date and a way to find it again.

## 3. Fact ledgers

Purpose: collect facts before prose, so the story rests on the record and not on memory.

- Split the history into date ranges and research each range separately. Parallel researchers work well here.
- Every fact needs a claim, a value and a source ID from the story's `sources` map. It also needs the source kind, exact reference and a short quote.
- The schema is in `templates/fact-ledger.schema.json`. Check the ledgers, source IDs and prose claims before writing:

```bash
python3 tools/check_ledger.py stories/NAME/research/*.json --story stories/NAME/story.json --claims strict
```

- Use `--claims report` on older books while you reconcile numbers and dates.
- Ask researchers to list gaps and doubts as well as facts.
- Re-check every fact the book will lean on yourself. Recount numbers from the raw source. Find each quote again at its exact reference. Researcher ledgers are evidence, not truth.

Check: the ledger command passes. Every number and quote has also been re-checked by someone other than its researcher.

## 4. Outline

Purpose: turn the facts into a story with a shape.

- Write the arc in three or four sentences. Where it starts, what went wrong, what changed, where it ends.
- Give each page one beat: what happened. Then its trial, the thing that went wrong or got hard. Then its lesson, what was learned.
- Tell failures in full. They are the best pages.
- If an event has not happened yet, keep a page for it and mark it open. Never write it from the plan.

Check: each page has a beat, a trial and a lesson, and each beat has facts behind it in the ledgers.

## 5. Storyboard

Purpose: plan what each page shows and does before you write it in full.

- For each page, sketch the scene. Who stands where, what furniture, what is on the wall.
- Plan the pull tab. What moves, stands up or changes as the reader pulls? It should act out the trial.
- Plan the lift flap. What one movement settles the scene? It should show the lesson.
- List the facts the page will cite.
- Put the scenes into a draft `story.json` with rough text. Open the build with `#storyboard` on the end of the address. Each page becomes a card with its start and final scenes, its mechanism plan and its word counts. See `docs/STORYBOARD.md`.
- Review the storyboard with the owner. This is the cheapest moment to change direction.

Check: the owner has approved the storyboard. Record what they changed in `owner-review.md`.

## 6. Write

Purpose: write pages people actually read.

- Put the point first. One idea per sentence, 12 to 18 words. Split anything over 25.
- Use plain words. Name things. Say "you" to the reader if the book is for one person.
- Keep to the budgets. Main text 100 to 230 words. Trial under 60. Lesson under 45, because it sits on the picture.
- Give every written page at least three facts, each pointing to a source.
- Read each page aloud. If you need a breath mid-sentence, split it.

Check: the validator passes and every page is within its word budgets.

## 7. Lay out

Purpose: make each scene read at a glance and each mechanism feel like paper.

The stage is a tunnel book. A back wall, a floor in perspective and cut-outs standing at four depths. The full reference is in `docs/AUTHORING.md`. The rules that matter most:

- Put the main character at the front, a little off centre.
- Put big furniture at the back, at depth 3 or 4. Keep its scale modest. The engine keeps every piece inside the page, and moving a wide shelf to fit will separate it from things standing on it.
- Things that sit on furniture use the furniture's depth minus a little, and a `lift` to raise them.
- Put pieces that appear where nothing covers them. Lift speech bubbles above heads.
- Keep the top band clear for the lesson card. Wall pieces are placed below it for you.
- The pull tab acts out the trial as you pull. Hidden pieces stand up from flat, and things move in the direction of the pull where it makes sense.
- The lift flap settles the scene with one clear movement and a calm final pose.
- Effects play over a window of the travel, in order. Use `"at": [start, end]` when the order needs help.

Check: the storyboard cards match what you meant, and the next step's measure is clean.

## 8. Build

```bash
python3 engine/validate.py stories/NAME/story.json --strict
python3 engine/build.py stories/NAME/story.json -o dist/NAME/index.html
```

The validator blocks unknown sprites, bad effects, missing sources and common secret patterns. Add `--deny FILE` with private names that must not appear.

Check: the build succeeds with no errors and no warnings.

## 9. Measure

Purpose: let the machine find layout bugs, because eyes miss them.

```bash
python3 tools/check_layout.py stories/NAME/story.json --phone
python3 tools/check_mechanics.py stories/NAME/story.json --phone
```

The layout check opens every page at desktop and phone sizes. It checks four states: at rest, tab half pulled, tab pulled, and flap lifted. Errors are pieces off the page, pieces under the lesson card, broken positions, unreadable text contrast, page errors and a pull tab that does not follow the hand. Overlaps and overflowing text are warnings to look at, not errors.

The mechanics check measures every checked rule in `docs/MECHANICS.md`.

Check: zero errors. Every warning has been looked at.

## 10. Look

Purpose: judge what the page looks like, which no measure can do.

1. Take screenshots with `python3 tools/shoot.py dist/NAME/index.html -o shots --phone`. It saves each page at rest, half pulled, fully pulled and flap lifted. It also saves contact sheets.
2. Save a settled desktop cover card with `python3 tools/shoot.py dist/NAME/index.html -o shots --poster-only --poster-page 1`. This image is private output, not public publication.
3. Look at the contact sheets yourself first. Check each page's final pose against the storyboard.
4. Send the screenshots to a strong vision model from another vendor with `tools/visual_qa.py` and the brief in `templates/qa-briefs/first-pass.md`. An outside eye catches what the builder has stopped seeing.
5. Fix what it finds. Confirm each finding in the browser before you change code. Models report animation frames and decoration as bugs.
6. Send back only the affected images with `templates/qa-briefs/recheck.md` and the open items.
7. Stop when the model signs off, or when only polish is left.
8. Log every pass in `qa-log.md`: images, score, findings, fixes and cost.

Check: the last pass has no major findings, and every fix since was measured clean.

## 11. Owner review

Purpose: get the book the owner actually wants. Each round of feedback is a new edition.

- Record the owner's words verbatim in `owner-review.md`.
- Classify each point. A bug, a design rule, content, or a mechanism that does not feel right.
- When the feedback is about realism, research the real thing first. The first book's flap and pull tab only felt right after looking at how real pop-up books build them.
- When the feedback changes direction, offer two or three options with a recommendation, and wait.
- Fix, then repeat steps 8 to 10 for what changed. A layout fix can move other pieces, so measure every page again.
- Write any new rule into `docs/DESIGN-RULES.md` or the story's notes, so the next book starts with it.
- Publish a new edition and keep the old ones.

Check: every point in the latest round is fixed, declined with a reason, or waiting on the owner.

## 12. Publish

```bash
python3 tools/export_pdf.py stories/NAME/story.json -o dist/NAME/book.pdf --storyboard dist/NAME/storyboard.pdf
sha256sum dist/NAME/* > dist/NAME/SHA256SUMS
```

- Store the HTML, the PDF and the checksums together, with a short readme naming the source commit.
- Keep every edition. Number them.
- Books are private by default. Sharing one outside the owner's own storage is the owner's decision.
- Before sharing the engine or a story publicly, run `python3 tools/release_check.py --history`. It scans tracked and untracked files.
- Add `--baseline FILE` only when you have a reviewed baseline for existing findings.

Check: a fresh build from the recorded commit matches the published HTML byte for byte.

## Keeping a book alive

- Open pages wait for their event. When it happens, collect the evidence, write the page and publish a new edition.
- Note each edition in the story's readme: date, commit and what changed.

## What it costs

The first book had 13 pages. It took about a day of agent time, across six editions. Fifteen outside review passes cost about US$2 in total.
