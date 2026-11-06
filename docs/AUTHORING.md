# Writing a story

A story is one JSON file. Start with `python3 tools/new_story.py NAME`. The scaffold gives you one complete working page and every planning file. Use `stories/example/story.json` as the larger reference.

## Top level

| Field | Meaning |
|---|---|
| `title`, `subtitle`, `byline` | Cover text. The title is drawn in the pixel font, so keep it short. |
| `lang` | Page language, for example `en-AU` |
| `unit` | What to call each entry, for example `Page`. Defaults to `Chapter`. |
| `colophon` | Small print on the back page |
| `cover.hero` | Sprite on the cover |
| `contents` | `kicker`, `title`, `intro` and a `scene` for the contents spread |
| `chapters` | The chapters, numbered from 1 |
| `numbers` | Optional stats spread with a paper wheel |
| `finale` | Optional whole-book pop-up spread shown before the back page |
| `back` | Closing spread: `kicker`, `title`, `text` and a `scene` |
| `sources` | Every source the fact cards cite |
| `sprites`, `palette` | Optional extra sprites and colours for this story |

## A chapter

```json
{
  "number": 3, "title": "A board for everything", "when": "June 2026", "status": "written",
  "text": ["Short paragraphs.", "Aim for 100 to 230 words in total."],
  "tab":  { "label": "The trial", "hint": "Pull to fill the board", "text": "Under 60 words.",
            "effects": [ { "piece": "n1", "fx": "show" }, { "piece": "hero", "fx": "hop", "delay": 300 } ] },
  "flap": { "label": "What I learned", "cover": "LIFT", "text": "Under 45 words.",
            "effects": [ { "piece": "bell", "fx": "show" } ] },
  "facts": [ { "label": "Tickets created by 30 June", "value": "217", "source": "tracker-export" } ],
  "scene": { ... }
}
```

- `status` is `written` or `open`. An open chapter needs no facts and shows a `stamp`, such as "To be written after the test".
- Text may use `*emphasis*`. Nothing else is interpreted, and HTML is escaped.
- `tab` and `flap` are optional. Their `effects` act on stage pieces by `id`.

## A scene

```json
{
  "sky": "indoor", "ground": "carpet", "alt": "Describe the scene for screen readers.",
  "caption": "Optional line under the stage.",
  "wall": [ { "sprite": "calendar", "x": 84, "y": 26, "scale": 2 } ],
  "pieces": [
    { "sprite": "board", "x": 50, "depth": 4, "scale": 4.5 },
    { "id": "hero", "sprite": "robot", "alt": "robot_happy", "x": 30, "depth": 1, "scale": 3, "bob": true }
  ]
}
```

| Setting | Named options | Also accepts |
|---|---|---|
| `sky` | `dawn` `day` `dusk` `night` `storm` `indoor` `library` `workshop` `sea` `council` | any CSS gradient |
| `ground` | `paper` `wood` `grass` `water` `carpet` `desk` `road` `stone` | any CSS colour or gradient |

**Wall pieces** sit flat on the back wall. `x` and `y` are percentages of the visible wall, so `y: 0` is the top of the stage and `y: 100` is where the floor starts. Set `"cut": false` for tiny sprites such as stars, so they get no paper border.

**Floor pieces** stand up from the floor and fold flat when the page turns.

| Field | Meaning |
|---|---|
| `x` | Where the piece appears across the stage, 0 to 100. Deeper pieces are spread out for you, so `x` is what you see. |
| `depth` | 1 is the front, 4 is against the back wall. Use `z` (0 to 1) for finer control. |
| `scale` | Pixel size. Deeper pieces look smaller, so give them a bigger scale. |
| `lift` | Raise a piece off the floor, in pixel units. Use it to set a laptop on a bench, or a speech bubble above a head. Use the same `z` as the furniture, minus a little. |
| `alt` | A second sprite. The `swap` effect switches to it. |
| `remap` | Recolour a sprite, for example `{ "b": "l" }` turns the robot green. |
| `flip` | Mirror the sprite. |
| `hidden` | Start folded flat in view. The `show` effect stands it up. |
| `bob`, `twinkle` | Gentle idle motion |

| Effect | What it does |
|---|---|
| `show` | Reveals a hidden piece |
| `hide` | Hides a piece. Hide always beats show. |
| `swap` | Switches to the piece's `alt` sprite |
| `hop` | Jumps once across its window |
| `wobble` | Shakes |
| `glow` | Glows |
| `dim` | Darkens |
| `rise` | Grows taller from the bottom, like rising water |
| `flip` | Turns the piece around |
| `move` | Moves the piece to a new spot. Give `to` with any of `x`, `depth` or `z`, `lift` and `grow` (a size multiplier). Pushing the tab or closing the flap sends it home. |

Effects are tied to how far the tab or flap has travelled, from 0 to 1, like a real paper mechanism. Each effect plays over a window of that travel. By default the windows follow the effects' order, staggered by `delay` in milliseconds. At half travel, an early effect may be complete while a later effect has not started. Give `"at": [0.2, 0.6]` to set a window yourself. Add `"off": true` to undo an earlier effect, for example to lower water that the tab raised.

A hidden piece stays opaque and folded flat in view until its window passes. The tab then stands it up. `hop` and `wobble` play once across their window, so they run backwards when you push the tab in.

The lesson flap sits on the picture, hinged along the top of the scene. Keep its text under 45 words, since the card covers the top of the stage. Wall pieces are placed below the card for you, so `y` still runs 0 to 100.

Let the lesson resolve the scene. One clear movement and a calm final pose reads better than a glow. For example, papers move onto the shelf, or the chosen robot steps to the front.

```json
{ "piece": "p1", "fx": "move", "to": { "x": 20, "z": 0.6, "lift": 25, "grow": 0.65 }, "delay": 0 },
{ "piece": "waves", "fx": "rise", "off": true }
```

## Paper feel and sound

Standing pieces sit on glued paper feet with a tight contact shadow. Wide furniture gets a foot at each side. Lifted pieces have neither.

The nav has a Sound button, off by default. The choice is remembered. Web Audio starts only after the reader acts, and books still work when it is unavailable.

Sounds are made in the browser, so nothing is downloaded. Paper scrapes and air swishes follow drag speed. End stops tap, flaps flick and settle, pages whoosh and riffle, scenes pop up, booklets rustle, and wheel detents click.

Set an optional overall level at the top of the story. The default is `1`.

```json
"sound": { "volume": 0.65 }
```

`volume` must be from `0` to `1`. Use it to keep a book's whole sound design subtle. Sound remains off until the reader uses the nav button.

## Sources and facts

```json
"sources": {
  "tracker-export": { "kind": "tickets", "title": "Issue tracker export", "ref": "769 issues read 20 October 2026", "excerpt": "Optional short quote" }
}
```

Every fact names a source id. The fact card shows the label, the value, the source title, the reference and the quote. Collect facts first, in a separate ledger, and only write sentences you can point to.

## The numbers spread

```json
"numbers": {
  "title": "The numbers", "intro": "One line.", "wheelTitle": "That month",
  "stats":  [ { "label": "sessions", "value": "5,190", "source": "stats" } ],
  "months": [ { "label": "May", "lines": ["103 sessions", "10 commits"], "source": "stats" } ]
}
```

Stat values are drawn in the pixel font. It has capitals, digits and common punctuation. The validator warns about anything it can't draw.

## The centre-spread finale

Add one optional `finale` when the story needs a large closing scene before the back page.

```json
"finale": {
  "title": "Everyone comes home",
  "text": ["The whole cast rises together."],
  "tab": { "label": "Raise the last light", "text": "A paper star stands up.",
           "effects": [{ "piece": "light", "fx": "show" }] },
  "flap": { "label": "Inside the arch", "text": "The work belongs to everyone.", "effects": [] },
  "facts": [],
  "scene": {
    "sky": "dusk", "ground": "wood", "alt": "A tall arch and the cast rise across the spread.",
    "pieces": [
      { "id": "arch", "sprite": "finale_arch", "x": 50, "depth": 4, "scale": 2.25,
        "finaleRole": "structure", "mount": "vfold" },
      { "id": "friend", "sprite": "person", "x": 20, "depth": 3, "scale": 2,
        "finaleRole": "cast", "tier": 3, "mount": "wing-left" },
      { "id": "reader", "sprite": "robot_happy", "x": 75, "depth": 2, "scale": 2,
        "finaleRole": "cast", "tier": 2, "mount": "platform" },
      { "id": "hero", "sprite": "robot_wave", "x": 50, "depth": 1, "scale": 3,
        "finaleRole": "cast", "tier": 1, "mount": "platform" },
      { "id": "light", "sprite": "star", "x": 50, "z": 0.04, "scale": 2.4,
        "lift": 90, "hidden": true, "finaleRole": "reveal", "mount": "vfold" }
    ]
  }
}
```

The finale is one stage across both pages. It folds flat and rises with the spread.

- Add one central `structure` near `x: 50` on a `vfold` mount. Use the engine's `finale_arch` at a scale near `2.2` to fill the centre without clipping the crown.
- Put every cast member on tier `1`, `2`, `3` or `4`. Use at least three tiers.
- Give every cast member a `wing-left`, `wing-right` or `platform` mount.
- Cast on one tier must share one `lift`. Higher tier numbers need higher lifts.
- The engine draws a scored platform top, platform front, paper feet and a contact shadow for each tier.
- Keep the copy short. The engine glues its banner across the front row, below the arch.
- The pull tab should raise one last piece. Mark that piece with `finaleRole: "reveal"`.
- The lift flap sits inside the central structure. Keep its hidden message short.
- Check every face at folded, mid-rise and open states.
- Check the tall phone stage. Pull tabs and flaps stay at least 44 pixels high.
- Storyboard mode adds a finale card. The print edition adds one flat finale page.
- Finale facts are optional. Each fact still needs a source from `sources`.

Valid finale roles are `structure`, `cast`, `reveal` and `scenery`.

Valid mounts are `vfold`, `wing-left`, `wing-right` and `platform`.

Use the normal `delay` field when one cut-out needs to rise after another.

## Sprites

Use `python3 tools/list_sprites.py SEARCH` to find names, sizes and tags. The same searchable list is in [SPRITES.md](SPRITES.md). Keep [sprites.png](sprites.png) open when you need to compare the artwork.

To add or change a sprite, edit `tools/sprites_src.py` and run it. The test suite checks the generated library matches the source.

A story can also bring its own sprites. Rows are strings of palette keys and `.` is transparent:

```json
"sprites": { "flag": ["kkkk", "krrk", "kkkk", "k...", "k..."] }
```

## Composition tips

- Put the hero at depth 1, off-centre, so it doesn't hide the scene behind it.
- Keep big furniture at depth 3 or 4 and give it scale 4 or more.
- Put reveal pieces where nothing covers them. Lift speech bubbles above heads.
- Check every chapter in four states: default, tab half pulled, tab pulled, flap lifted. Half pulled catches pieces that cross each other on the way.
- Check a phone size as well as a desk size.
