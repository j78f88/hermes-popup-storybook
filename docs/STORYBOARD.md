# Storyboard view

The storyboard view places every story entry on one page for quick review.

## Open the storyboard

Build the complete story before opening its storyboard view in your preferred browser.

```sh
python3 engine/build.py stories/example/story.json
```

After opening the book, add `#storyboard` to the end of its file address.

```text
dist/example/index.html#storyboard
```

Remove the fragment, or choose a book link, to resume normal reading.

## Review each card

The header shows entry, word, fact, and source totals for the complete story.

Cards follow story order through contents, pages, numbers, an optional finale, and the closing entry.

A finale card shows its short paper-card copy, mechanism plan, facts, and start and final scenes.

Each page card shows its title, date, status, and three word counts.

Coloured word labels flag main text, trial, or lesson outside their budgets.

Trial and lesson text appear beside the plain-language mechanism movement plan.

Fact labels identify the evidence that reviewers should check against frozen sources.

Start and final thumbnails reveal whether each paper movement resolves the scene cleanly.

Compare the start and final scenes first to confirm the hand action causes the planned result.

Open entries say “still to come”, so plans never appear as recorded history.

Review card order and start-to-final scene changes first, then inspect wording and evidence.

## Use the index and filters

The page index stays at the top while you review. Choose an entry to move straight to its card.

Choose **Open pages** to show only entries marked still to come.

Choose **Budget flags** to show only entries with copy outside its word budget.

The filters work together when both are selected. Clear them to restore the complete storyboard.

The index and filters stay out of the printed storyboard.

## Record owner review

Ask the owner to review the complete storyboard before beginning detailed visual polishing.

Copy every owner comment verbatim into `owner-review.md` before classifying the feedback.

Record each decision, required fix, and completed recheck within the same table line.

Keep unresolved owner questions visible until the owner makes a clear final decision.

## Print the storyboard

Open the complete storyboard view, then use the browser's standard print command.

Choose landscape page orientation whenever cards appear cramped within the print preview.

Enable background graphics so scene colours and review labels remain clear and meaningful.

Check every printed card for clipping, small text, and unwanted internal page breaks.

Save a PDF only after the printed order matches the complete browser storyboard.
