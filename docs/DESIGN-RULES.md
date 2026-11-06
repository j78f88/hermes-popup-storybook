# Design rules

These are the defaults the engine and the process start from. Each one came from real feedback on the first book. Change them for your own book if you have a reason, and write the reason down.

## Pages

- Call entries what they are. A memoir has pages, a report has chapters. Set `"unit"` in the story.
- No drop caps. A large first letter throws the left edge out of line.
- No page numbers on the spread. They clash with the entry numbers.
- Sentence case for titles and labels. Keep the pixel font for the cover title and big numbers only.
- Turn off hyphenation. Split words make short lines look broken.

## The picture

- The pop-up fills the whole right page, edge to edge. A frame makes it look like a box on a page instead of a book.
- Every cut-out stays inside the page, clear of the fold shadow and the outer edge. The engine enforces this.
- Standing pieces sit on small paper feet with a tight shadow and a warm cardstock edge. Pieces lifted into the air have neither foot nor floor shadow.
- Keep recurring characters, not the same setting. Readers follow the cast from page to page, so characters (`robot`, `person`, `owl`, `robin`) should recur across the book while each page moves to a fresh setting with new story-supporting props. The validator warns when a backdrop piece, wall fixture or sky-and-ground pair repeats on more than two chapters.
- Make the joy of the pop-up the point. Every pull tab, flap and stage piece should surprise the hand with playful physical movement: hops, flips, rises, glows, swaps, sliding tracks and direct tap bounces on stage pieces.
- Look-around moves the viewer's eye only while the pointer is over the picture. It pauses while a control is held and eases back after the pointer leaves. Never tilt the whole set or snap when the pointer enters or leaves.

## Mechanisms

Real paper does not play animations. It moves because your hand moves it. Copy that.

- The pull tab is a slider in a slot on the text page, with a visible paper tongue bridging toward the spine. It pulls towards the picture.
- Pieces that slide across the floor ride in visible cut floor slots between their start and end positions.
- Every page's pull tab and flap should act out that page's specific story through travel, swaps, wobbles or lifted placements, not repeat a single reveal template.
- The picture follows the tab one to one. It stops when you stop, and runs back when you push.
- The tab stays where you leave it, including after a page turn. A click without a drag pulls it all the way, or pushes it back. With reduced motion, the click goes straight to the end.
- The trial shows through a window cut above the slot, on a strip that moves with the tab.
- The lesson flap is part of the picture, hinged along the top of the scene with a scored fold line, a thick cardstock lip and a moving cast shadow over the recessed card underneath. Lift its bottom edge upwards towards the hinge. The lesson is printed on the card underneath.
- A flap lifted past about a third stays up. Let go below that and it falls shut.
- When lifted, a strip of the flap stays visible, so it reads as raised paper and not as a panel that vanished.
- The lesson flap settles the scene with one movement into a calm final pose.
- Hidden pieces lie flat and stand up as the tab pulls them. They stay opaque, like paper, and never fade.
- Stagger hide and show windows when one piece replaces another in the same spot. Finish hiding the old piece before showing the new one.
- A page leaf and its pop-up folds share one angle. The old scene folds while the leaf closes. The new scene rises while the leaf opens.
- Drag a desktop page edge or drag across a phone picture to turn the leaf by hand. Releasing before halfway returns it. Releasing after halfway completes one turn.
- Every mechanism also works by keyboard. Escape closes an open flap or booklet.

## Facts

- Facts live in a compact note pouch taped to the corner of the text page, with stacked note cards peeking out of the top lip and the number of facts printed on its cover.
- It opens where it is taped, sized to the corner (`68%` width on desktop) so the story title and page remain visible around it, with one fact and its source per spread.
- On phones, it opens as a vertical mini book at the taped corner, pushes the text down and turns a visible leaf for each fact.
- Never hide facts in a thin ribbon or a pop-up window.

## Cues

- Print short instructions on the page in ink, such as "Pull the tab towards the picture" and "Lift the flap".
- Match the cue to the layout. On a phone, where the picture is above the text, the cue says "Slide the tab to the right".
- Phones print previous and next cues along the picture edge. The first spread also gives one swipe hint.
- Pointer look-around wording appears only when the device has a precise pointer.

## Sound

- Sound is optional and off by default.
- Make it in the browser so the book stays one offline file.
- Keep it warm, quiet and recognisably paper. Avoid cartoon effects.
- Sound follows the hand. Drag speed controls scrape, swish, loudness and brightness.
- Keep frequency ceilings warm: 2800 Hz for one-shot rustles, 2200 Hz for repeated clicks and riffles, and 2600 Hz for continuous drag movement.
- Reduced motion removes movement only. It does not change the reader's sound choice.
- A stopped hand becomes silent within 150 milliseconds.
- Paper contacts sound at their real point. End stops tap and folded pieces snap upright.
- Page and booklet sounds follow their visible movement instead of playing as a generic cue.
- Start or resume Web Audio only after a reader gesture. Missing Web Audio must not break the book.
- Use the story-level volume only as an overall trim. It never turns sound on.

## Things that went wrong in the first book

- Canned animations felt fake. Readers expect paper to follow their hand.
- A lifted flap seen from above shows its front face. Hiding the front made it vanish. Show its paper with the print hidden.
- SVG elements have no `offsetWidth`. Reading it froze every piece in place without an error. Measure layout after every engine change.
- Fixed-position overlays break inside anything with perspective or filters. Put phone overlays on the page body.
- Screenshots taken in a new browser call can lose the window size. Set it every time and check it before you crop.
