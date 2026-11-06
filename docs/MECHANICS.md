# Mechanics contract

Every moving part in the book copies a real paper mechanism. This page says how each one must behave, in terms a script can measure. `docs/DESIGN-RULES.md` says why. `tools/check_mechanics.py` checks the clauses marked **checked**. The others are checked by eye during the review step in `docs/PROCESS.md`.

A real pop-up book has no motors. Paper moves only because a hand moves it, or because gravity or a spring of folded card pulls it back. So:

- Nothing moves without a hand, except falling, settling and the slow look-around drift.
- Every state is a function of where the hand put the paper, not of how it got there.
- Pushing a part back undoes exactly what pulling it did.

Tolerances: 2 px for position, 2 degrees for angle, one animation frame (about 17 ms) for timing.

With reduced motion, parts the hand drives still follow it one to one. Motion the hand does not drive is removed: a click sends the tab straight to its end (S8 applies only with motion on), and a page turn cuts to the open spread with its pop-up already standing (T2 and N1 apply only with motion on). Every other clause still applies.

## Pull tab (slider)

The real thing: a card strip in a slot, with a tab on the end. Pulling the strip moves pieces linked to it.

| Id | Rule | How it is measured |
|---|---|---|
| S1 | The tab moves only along its slot, towards the picture. On a phone it moves to the right. The tab sits on the text page by owner choice; its strip reads as passing through the spine. | Drag diagonally. Only the slot axis changes. **checked** |
| S2 | The tab follows the hand one to one inside its travel and stops hard at both ends. | Tab offset equals pointer offset within 2 px; beyond the ends it stays at the end. **checked** |
| S3 | The tab stops when the hand stops. No glide, no spring back. | 100 ms after the pointer stops, the tab and every driven piece have not moved. **checked** |
| S4 | The scene depends only on how far the tab is pulled. The same travel gives the same scene, whether reached by pulling, pushing, keyboard or a click. | Compare piece positions at the same travel reached three ways. **checked** |
| S5 | Pulling all the way and pushing all the way back returns the scene exactly to its start. | Every piece rect and visibility matches the start within 2 px. **checked** |
| S6 | The trial strip moves with the tab, one to one, behind its window. | Strip offset tracks tab offset within 2 px. **checked** |
| S7 | Hidden pieces lie flat and stand up as the tab pulls them. They stay opaque. | Opacity stays 1; the fold angle runs from flat to upright across the effect window. **checked** |
| S8 | A click without a drag pushes the tab all the way, in one continuous travel, like a quick shove. | Travel passes through middle values, not a jump. **checked** |
| S9 | Keyboard: arrow keys step the tab, Home and End go to the ends. | **checked** |

## Lesson flap

The real thing: a card hinged along its top edge, glued over the picture. You lift its bottom edge.

| Id | Rule | How it is measured |
|---|---|---|
| F1 | The flap turns about its top edge only. As it lifts, its bottom edge moves towards the hinge on screen and never dips below its shut position. | The top edge stays fixed; the bottom edge's screen position rises steadily with lift. **checked** |
| F2 | You lift it by its bottom edge, upwards towards the hinge, as the printed arrow shows. The bottom edge follows the hand. Moving back lowers it. | Lift rises with upward travel and falls when the hand reverses. A downward drag from shut does nothing. **checked** |
| F3 | Let go below about a third and it falls shut. Let go above that and it stays up. | Release at 25% gives shut, release at 45% gives open. **checked** |
| F4 | When lifted, a strip of the flap stays visible, so it reads as raised paper. | The lifted flap has a visible height above zero. **checked** |
| F5 | Anything the flap moves depends only on how far it is lifted, and closing it reverses the move. | As S4 and S5, with the flap as the control. **checked** |
| F6 | Click or Enter lifts it. Escape or a second click closes it. | **checked** |

## Page turn

The real thing: a leaf turning about the spine. Pop-ups fold flat as the spread closes and stand up as it opens.

| Id | Rule | How it is measured |
|---|---|---|
| T1 | Next turns the right-hand leaf to the left; previous turns it back. On a phone, swiping left goes forward. | Leaf rotation direction and page index. **checked** |
| T2 | Both spreads move at once, as in a real book. Turning forward, the leaf carries the old picture on its front, folding shut as the leaf rises, and the new text page on its back. The new picture lies under the leaf and rises as the leaf opens away from it. The old text page stays put until the leaf lands on it. Turning back is the mirror image. No page shows on two surfaces at once, and nothing waits for the leaf to start or land. | Sample through a real turn: the closing pop-up's fold is 88° × angle / 180 and the opening one's 88° × (1 − angle / 180), within 4°, with no held stretch; every surface carries a different page. **checked** |
| T3 | A tab stays where you left it. Come back to a page and the tab is still pulled. | Pull, turn away, turn back: same travel. **checked** |
| T4 | Turning a page presses a lifted flap shut, as the facing page would. | Lift, turn away, turn back: flap shut, scene as the tab left it. **checked** |
| T5 | One turn at a time. A second press during a turn waits or is ignored; it never skips a page or tears the animation. | Double-press: the page index moves by at most one per finished turn. **checked** |
| T6 | The leaf follows the hand. On a desktop, drag a page edge. On a phone, drag across the picture. Let go before halfway and it falls back. Let go after halfway and it turns. | Drag to 40% and release: the spread returns. Drag to 60% and release: one page turns. **checked** |

## Fact booklet

The real thing: a small booklet taped by one corner to the text page.

| Id | Rule | How it is measured |
|---|---|---|
| B1 | The count on the cover equals the number of facts inside. | **checked** |
| B2 | It opens where it is taped and turns one page at a time, forward and back, with a visible leaf turn on every layout. | Page index changes by one per turn, in the pressed direction, and a leaf rotates during the change. **checked** |
| B3 | It never covers more than the text page. On a desktop it may lift towards the reader from its taped corner. On a phone it opens in place on the text page. | Its rect stays inside the text page. **checked** |
| B4 | Escape closes it and focus goes back to the booklet. | **checked** |

## Paper wheel (volvelle)

The real thing: a disc on a pivot behind a window.

| Id | Rule | How it is measured |
|---|---|---|
| W1 | The disc turns with the hand around its pivot, one to one in angle. | Disc angle change equals pointer angle change within 2 degrees. **checked** |
| W2 | It settles at detents, and the window shows exactly one entry at each. | Readout matches the detent index. **checked** |
| W3 | Turning back reverses it. | **checked** |

## Look-around

| Id | Rule | How it is measured |
|---|---|---|
| L1 | The eye moves smoothly, eased each frame, with no snap when the pointer enters or leaves. | Perspective origin changes by a small step per frame. **checked** |
| L2 | With reduced motion, the idle drift stops. Hand-driven mechanisms still work one to one. | **checked** |
| L3 | Only a pointer over the picture moves the eye. While a tab, flap or wheel is held, the eye holds still, so the scene stops when the hand stops. | Drag a tab on the text page: perspective origin does not change. **checked** |

## Finale

The finale follows the tab, flap and page-turn rules. Also:

| Id | Rule | How it is measured |
|---|---|---|
| N1 | The central structure rises out of the fold as the spread opens and folds flat when it closes. | Fold angles at the start and end of the turn. **checked** |
| N2 | Every cast piece stands on a platform and stays fully visible in the final state. | Rects inside the stage, no piece more than half covered. **checked** |

## Printed instructions

| Id | Rule | How it is measured |
|---|---|---|
| I1 | Every printed cue names the action that works, in the direction that works, for the current layout. | Cue text against the measured direction, per layout. **checked** |
| I2 | A tab's hint says what visibly happens when you pull it. | Read the hint, pull, and look. Review by eye. |
| I3 | No cue mentions an input the device does not have, such as a pointer on a phone. | **checked** |
