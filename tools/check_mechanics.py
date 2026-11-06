#!/usr/bin/env python3
"""Measure the paper mechanics contract in a real browser."""

from __future__ import annotations

import argparse
import json
import math
import sys
import traceback
from pathlib import Path
from typing import Any

from _browser import (
    FREEZE_CSS,
    browser_context,
    built_book,
    entry_for_key,
    load_story,
    overlap_ratio,
)

POSITION_TOLERANCE = 2.0
ANGLE_TOLERANCE = 2.0
FRAME_TOLERANCE = 17.0
CLAUSES = (
    [f"S{i}" for i in range(1, 10)]
    + [f"F{i}" for i in range(1, 7)]
    + [f"T{i}" for i in range(1, 7)]
    + [f"B{i}" for i in range(1, 5)]
    + [f"W{i}" for i in range(1, 4)]
    + ["L1", "L2", "L3", "N1", "N2", "I1", "I3"]
)


def selected_clauses(values: list[str] | None) -> set[str]:
    """Expand --only values into checked clause ids."""
    if not values:
        return set(CLAUSES)
    chosen: set[str] = set()
    for raw in values:
        for token in raw.upper().split(","):
            token = token.strip()
            if not token:
                continue
            if len(token) == 1:
                chosen.update(clause for clause in CLAUSES if clause.startswith(token))
            elif token in CLAUSES:
                chosen.add(token)
            else:
                raise ValueError(f"unknown clause or family: {token}")
    return chosen


def rect_delta(left: dict, right: dict) -> float:
    return max(
        abs(float(left.get(name, 0)) - float(right.get(name, 0)))
        for name in ("x", "y", "width", "height")
    )


def signature_delta(left: list[dict], right: list[dict]) -> float:
    by_id = {item["id"]: item for item in right}
    delta = 0.0
    for item in left:
        other = by_id.get(item["id"])
        if not other:
            return 9999.0
        delta = max(delta, rect_delta(item, other))
        delta = max(delta, abs(float(item["opacity"]) - float(other["opacity"])) * 100)
    return delta


TURN_SAMPLE_JS = r"""() => {
  const turn = window.__book.turn();
  if (!turn) return null;
  const wide = !matchMedia('(max-width: 820px), (max-aspect-ratio: 1/1)').matches;
  const leaf = document.querySelector('.leaf');
  const degrees = (matrix, axis) => {
    if (!matrix || matrix === 'none') return 0;
    const m = new DOMMatrixReadOnly(matrix);
    if (axis === 'y') return Math.acos(Math.max(-1, Math.min(1, m.m11))) * 180 / Math.PI;
    return Math.abs(Math.atan2(m.m23, m.m22)) * 180 / Math.PI;
  };
  const describe = (stage) => {
    if (!stage) return null;
    const folds = [...stage.querySelectorAll('.piece:not(.wallpiece) .hinge, .finale-structure-piece .hinge')].map((el, i) => {
      const owner = el.closest('[data-id]');
      return { id: (owner && owner.dataset.id) || `hinge-${i}`, angle: degrees(getComputedStyle(el).transform, 'x'), max: 88, opacity: +getComputedStyle(el).opacity };
    });
    const finale = stage.classList.contains('finale-stage') ? [...stage.querySelectorAll('.finale-structure-piece .hinge, .finale-role-cast .hinge, .finale-wing, .finale-low-layer, .finale-platform-top, .finale-platform-front')].map((el, i) => {
      const owner = el.closest('[data-id], [data-tier]');
      const name = (owner && (owner.dataset.id || owner.dataset.tier)) || 'rig';
      return { id: `${name}:${el.className}:${i}`, opacity: +getComputedStyle(el).opacity, transform: getComputedStyle(el).transform };
    }) : [];
    return { stage: stage.dataset.stage || null, open: +getComputedStyle(stage).getPropertyValue('--spread-open'), folds, finale };
  };
  // What each surface carries: a stage id, else the page title, else nothing.
  const surface = (sel) => {
    const el = document.querySelector(sel);
    if (!el || !el.innerHTML.trim()) return null;
    const st = el.querySelector('.stage');
    // A finale is one spread split across two surfaces during a turn: count each half separately.
    const half = el.classList.contains('finale-half') ? (el.classList.contains('fh-left') ? ':left-half' : ':right-half') : '';
    if (st) return 'stage:' + (st.dataset.stage || '?') + half;
    const t = el.querySelector('.title');
    return t ? 'title:' + t.textContent.trim() : null;
  };
  // Physical model: forward (and every phone turn) the new picture lies under the leaf and the leaf
  // carries the old one; turning back on a desktop the base keeps the old picture and the leaf's back carries the new.
  const forwardish = (turn.dir != null ? turn.dir : turn.direction) > 0 || !wide;
  const base = document.querySelector('.page.right .stage');
  const leafF = document.querySelector('.leaf .face.f .stage'), leafB = document.querySelector('.leaf .face.b .stage');
  return {
    state: turn, wide,
    leaf: degrees(getComputedStyle(leaf).transform, 'y'), direction: leaf.dataset.direction || '',
    opening: describe(forwardish ? base : leafB),
    closing: describe(forwardish ? leafF : base),
    surfaces: { baseLeft: wide ? surface('.page.left') : null, baseRight: surface('.page.right'), leafFront: surface('.leaf .face.f'), leafBack: surface('.leaf .face.b') },
  };
}"""



class MechanicsCheck:
    def __init__(
        self,
        page,
        context,
        html: Path,
        story: dict,
        viewport: str,
        browser_name: str,
        reduced_motion: bool,
        only: set[str],
    ):
        self.page = page
        self.context = context
        self.html = html
        self.story = story
        self.viewport = viewport
        self.phone = viewport == "phone"
        self.browser_name = browser_name
        self.reduced_motion = reduced_motion
        self.only = only
        self.results: list[dict] = []
        self.sequence = 0
        self.pages: list[str] = []
        self.turn_samples: dict[str, list[dict]] = {}

    def add(self, clause: str, key: str, passed: bool, measured: str, expected: str) -> None:
        if clause not in self.only:
            return
        self.results.append(
            {
                "clause": clause,
                "page": key,
                "viewport": self.viewport,
                "status": "PASS" if passed else "FAIL",
                "measured": measured,
                "expected": expected,
            }
        )

    def fail_exception(self, clause: str, key: str, error: Exception) -> None:
        frames = traceback.extract_tb(error.__traceback__)
        own = [frame for frame in frames if frame.filename == __file__]
        frame = own[-1] if own else (frames[-1] if frames else None)
        where = f" at {frame.name}:{frame.lineno}" if frame else ""
        self.add(clause, key, False, f"checker error{where}: {type(error).__name__}: {error}", "measurement completes")

    def open(self, key: str) -> None:
        self.sequence += 1
        url = self.html.resolve().as_uri() + f"?mechanics={self.sequence}#{key}"
        self.page.goto(url, wait_until="load")
        self.page.wait_for_function("window.__book && window.__book.pages")
        self.page.add_style_tag(content=FREEZE_CSS)
        self.pages = self.page.evaluate("window.__book.pages()")
        wanted = self.pages.index(key)
        self.page.wait_for_function("i => window.__book.cur() === i", arg=wanted)
        if self.page.locator(".stage").count():
            self.page.wait_for_function("!document.querySelector('.stage').classList.contains('folded')")
            self.centre_eye()
            self.wait_stable(".stage")
        if self.page.locator(".finale-banner").count() and not self.reduced_motion:
            # Settled means no transform: 'none' or an identity matrix (both draw the banner unmoved).
            self.page.wait_for_function(
                "(() => { const t = getComputedStyle(document.querySelector('.finale-banner')).transform;"
                " if (t === 'none') return true; const m = new DOMMatrixReadOnly(t); return m.isIdentity; })()",
                timeout=4000,
            )
        for selector in (".slider .tab", ".lflap", ".booklet", ".wheel"):
            if self.page.locator(selector).count():
                self.wait_stable(selector)

    def centre_eye(self) -> None:
        stage = self.page.locator(".stage")
        if not stage.count():
            return
        box = stage.bounding_box()
        if box:
            self.page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)

    def wait_stable(self, selector: str) -> None:
        self.page.wait_for_function(
            """selector => new Promise((resolve, reject) => {
              const started=performance.now(); let last=null, stable=0;
              const tick=()=>{
                const el=document.querySelector(selector);
                if(!el) { reject(new Error(`missing ${selector}`)); return; }
                const r=el.getBoundingClientRect();
                const now=[r.x,r.y,r.width,r.height,getComputedStyle(el).transform,getComputedStyle(el).opacity];
                const same=last && now.every((v,i)=>typeof v==='number' ? Math.abs(v-last[i])<.15 : v===last[i]);
                stable=same?stable+1:0; last=now;
                if(stable>=4) resolve(true);
                else if(performance.now()-started>4000) reject(new Error(`unstable ${selector}`));
                else requestAnimationFrame(tick);
              }; requestAnimationFrame(tick);
            })""",
            arg=selector,
            timeout=5000,
        )

    def geom(self, selector: str) -> dict:
        return self.page.eval_on_selector(
            selector,
            """e => { const r=e.getBoundingClientRect(); const s=getComputedStyle(e); return {
              x:r.x,y:r.y,left:r.left,top:r.top,right:r.right,bottom:r.bottom,
              width:r.width,height:r.height,opacity:+s.opacity,transform:s.transform,
              pull:parseFloat(s.getPropertyValue('--pull')),
              flap:parseFloat(s.getPropertyValue('--flap')),
              value:e.getAttribute('aria-valuenow'),expanded:e.getAttribute('aria-expanded')
            }}""",
        )

    def scene_signature(self) -> list[dict]:
        return self.page.evaluate(
            """() => [...document.querySelectorAll('.stage .piece')].map((e,i)=>{
              const v=e.querySelector('.mech > .main')||e.querySelector('.mech > svg')||e;
              const r=v.getBoundingClientRect(), s=getComputedStyle(e.querySelector('.mech')||e);
              return {id:e.dataset.id||`piece-${i}`,x:r.x,y:r.y,width:r.width,height:r.height,opacity:+s.opacity,transform:s.transform};
            })"""
        )

    def mechanism_signature(self) -> list[dict]:
        """Read mechanism-owned state without look-around perspective movement."""
        return self.page.evaluate(
            """() => [...document.querySelectorAll('.stage .piece')].map((e,i)=>{
              const m=e.querySelector('.mech')||e, s=getComputedStyle(m), es=getComputedStyle(e);
              const nums=value=>(String(value).match(/-?\\d+(?:\\.\\d+)?/g)||[]).map(Number);
              return {id:e.dataset.id||`piece-${i}`,values:[
                +(e.dataset.x||0), +(e.dataset.z||0), +(e.dataset.lift||0),
                +(es.getPropertyValue('--grow')||1), +s.opacity,
                ...nums(m.style.transform||s.transform), ...nums(m.style.filter||s.filter)
              ]};
            })"""
        )

    @staticmethod
    def mechanism_delta(left: list[dict], right: list[dict]) -> float:
        by_id = {item["id"]: item for item in right}
        delta = 0.0
        for item in left:
            other = by_id.get(item["id"])
            if not other:
                return 9999.0
            if len(item["values"]) != len(other["values"]):
                return 9999.0
            delta = max(delta, *(abs(a - b) for a, b in zip(item["values"], other["values"])))
        return delta

    def slider_point(self) -> tuple[dict, float, float]:
        tab = self.geom(".slider .tab")
        track = self.geom(".slider .track")
        return tab, tab["x"] + tab["width"] / 2, tab["y"] + tab["height"] / 2

    def touch_or_mouse_drag(
        self,
        x0: float,
        y0: float,
        x1: float,
        y1: float,
        release: bool = True,
        steps: int = 14,
    ) -> Any:
        if self.phone and self.browser_name == "chromium":
            session = self.context.new_cdp_session(self.page)
            session.send(
                "Input.dispatchTouchEvent",
                {"type": "touchStart", "touchPoints": [{"x": x0, "y": y0, "id": 1}]},
            )
            for index in range(1, steps + 1):
                k = index / steps
                session.send(
                    "Input.dispatchTouchEvent",
                    {
                        "type": "touchMove",
                        "touchPoints": [
                            {"x": x0 + (x1 - x0) * k, "y": y0 + (y1 - y0) * k, "id": 1}
                        ],
                    },
                )
                self.page.evaluate("() => new Promise(resolve => requestAnimationFrame(resolve))")
            self.page.evaluate("() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))")
            if release:
                session.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
                session.detach()
                return None
            return session
        self.page.mouse.move(x0, y0)
        self.page.mouse.down()
        for index in range(1, steps + 1):
            k = index / steps
            self.page.mouse.move(x0 + (x1 - x0) * k, y0 + (y1 - y0) * k)
            self.page.evaluate("() => new Promise(resolve => requestAnimationFrame(resolve))")
        self.page.evaluate("() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))")
        if release:
            self.page.mouse.up()
            return None
        return "mouse"

    def release_drag(self, handle: Any) -> None:
        if handle == "mouse":
            self.page.mouse.up()
        elif handle is not None:
            handle.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
            handle.detach()

    def real_click(self, selector: str) -> None:
        # A printed phone cue may be absent on the page we have just turned to (numbers, finale):
        # fall back to the toolbar button with the same meaning.
        fallback = {"[data-stage-next]": "[data-next]", "[data-stage-prev]": "[data-prev]"}
        if selector in fallback and not self.page.locator(selector).count():
            selector = fallback[selector]
        locator = self.page.locator(selector)
        if self.phone:
            locator.scroll_into_view_if_needed()
        box = locator.bounding_box()
        if not box:
            raise RuntimeError(f"no clickable geometry for {selector}")
        x = box["x"] + box["width"] / 2
        y = box["y"] + box["height"] / 2
        if self.phone:
            self.page.touchscreen.tap(x, y)
        else:
            self.page.mouse.click(x, y)

    def wait_slider(self, value: int) -> None:
        self.page.wait_for_function(
            "v => +document.querySelector('.slider .tab').getAttribute('aria-valuenow') === v",
            arg=value,
            timeout=3000,
        )
        self.wait_stable(".slider .tab")

    def press_slider(self, key: str) -> None:
        self.page.locator(".slider .tab").focus()
        self.page.keyboard.press(key)

    def slider_checks(self, key: str) -> None:
        # S1, S2, S3 and S6 share one held diagonal pull.
        self.open(key)
        start_tab, x, y = self.slider_point()
        strip0 = self.geom(".slider .strip")
        track = self.geom(".slider .track")
        travel = track["width"] - start_tab["width"]
        requested = travel * 0.48
        handle = self.touch_or_mouse_drag(x, y, x + requested, y + 37, release=False)
        moved_tab = self.geom(".slider .tab")
        moved_track = self.geom(".slider .track")
        strip1 = self.geom(".slider .strip")
        axis_error = abs((moved_tab["y"] - moved_track["y"]) - (start_tab["y"] - track["y"]))
        hand_error = abs((moved_tab["x"] - start_tab["x"]) - requested)
        strip_error = abs((strip1["x"] - strip0["x"]) - (moved_tab["x"] - start_tab["x"]))
        self.add("S1", key, axis_error <= POSITION_TOLERANCE and moved_tab["x"] > start_tab["x"], f"x +{moved_tab['x']-start_tab['x']:.2f}px, y {axis_error:.2f}px", "rightward only; cross-axis <= 2px")
        self.add("S2", key, hand_error <= POSITION_TOLERANCE, f"hand {requested:.2f}px, tab {moved_tab['x']-start_tab['x']:.2f}px, error {hand_error:.2f}px", "one-to-one within 2px")
        self.add("S6", key, strip_error <= POSITION_TOLERANCE, f"tab {moved_tab['x']-start_tab['x']:.2f}px, strip {strip1['x']-strip0['x']:.2f}px, error {strip_error:.2f}px", "strip tracks tab within 2px")
        before_pause = {"tab": moved_tab, "scene": self.mechanism_signature()}
        timed = self.page.evaluate(
            """() => new Promise(resolve=>{const t0=performance.now(); const loop=t=>{if(t-t0>=100){resolve(t-t0);return;} requestAnimationFrame(loop)};requestAnimationFrame(loop)})"""
        )
        after_pause = {"tab": self.geom(".slider .tab"), "scene": self.mechanism_signature()}
        pause_delta = max(rect_delta(before_pause["tab"], after_pause["tab"]), self.mechanism_delta(before_pause["scene"], after_pause["scene"]))
        self.add("S3", key, pause_delta <= POSITION_TOLERANCE, f"hold {timed:.1f}ms, max movement {pause_delta:.2f}px", "no movement after 100ms; <= 2px")
        self.release_drag(handle)

        # Hard stops and exact return.
        self.open(key)
        initial = self.mechanism_signature()
        start_tab, x, y = self.slider_point()
        track = self.geom(".slider .track")
        travel = track["width"] - start_tab["width"]
        self.touch_or_mouse_drag(x, y, x + travel + 20, y)
        end_tab = self.geom(".slider .tab")
        hard_error = abs((end_tab["x"] - start_tab["x"]) - travel)
        self.add("S2", key, hard_error <= POSITION_TOLERANCE, f"travel {travel:.2f}px, beyond-end tab {end_tab['x']-start_tab['x']:.2f}px, error {hard_error:.2f}px", "hard end within 2px")
        _, xe, ye = self.slider_point()
        self.touch_or_mouse_drag(xe, ye, xe - travel - 20, ye)
        returned = self.mechanism_signature()
        return_delta = self.mechanism_delta(initial, returned)
        self.add("S5", key, return_delta <= POSITION_TOLERANCE, f"start-return max delta {return_delta:.2f}px", "scene returns within 2px")

        # Keyboard endpoints and steps.
        self.open(key)
        self.press_slider("ArrowRight")
        arrow = int(self.page.locator(".slider .tab").get_attribute("aria-valuenow") or -1)
        self.press_slider("End")
        self.wait_slider(100)
        end = int(self.page.locator(".slider .tab").get_attribute("aria-valuenow") or -1)
        self.press_slider("Home")
        self.wait_slider(0)
        home = int(self.page.locator(".slider .tab").get_attribute("aria-valuenow") or -1)
        self.add("S9", key, (arrow, end, home) == (10, 100, 0), f"ArrowRight {arrow}, End {end}, Home {home}", "10, 100, 0")

        # The same full travel must give the same scene by drag, keyboard and click.
        self.open(key)
        start_tab, x, y = self.slider_point()
        track = self.geom(".slider .track")
        travel = track["width"] - start_tab["width"]
        held = self.touch_or_mouse_drag(x, y, x + travel, y, release=False)
        pointer_sig = self.mechanism_signature()
        self.release_drag(held)
        self.open(key)
        self.press_slider("End")
        self.wait_slider(100)
        keyboard_sig = self.mechanism_signature()
        self.open(key)
        self.page.evaluate("""() => { window.__qaSliderSamples=[]; const tick=()=>{const e=document.querySelector('.slider .tab'); if(!e)return; const v=+e.getAttribute('aria-valuenow'); window.__qaSliderSamples.push(v); if(v<100)requestAnimationFrame(tick)}; requestAnimationFrame(tick) }""")
        self.real_click(".slider .tab")
        self.wait_slider(100)
        click_sig = self.mechanism_signature()
        samples = self.page.evaluate("window.__qaSliderSamples")
        state_delta = max(self.mechanism_delta(pointer_sig, keyboard_sig), self.mechanism_delta(pointer_sig, click_sig))
        middle = [value for value in samples if 5 < value < 95]
        max_step = max((abs(b - a) for a, b in zip(samples, samples[1:])), default=100)
        self.add("S4", key, state_delta <= POSITION_TOLERANCE, f"same full-travel state max delta {state_delta:.2f}", "drag, keyboard and click match within tolerance")
        if not self.reduced_motion:
            self.add("S8", key, len(set(middle)) >= 3 and max_step < 35, f"{len(set(middle))} middle values, largest frame step {max_step}%", "continuous travel through >= 3 middle values")

        # Hidden paper geometry and opacity. S7 covers pieces linked to this tab, not flap-only pieces.
        self.open(key)
        entry = entry_for_key(self.story, key)
        tab_piece_ids = [
            effect.get("piece")
            for effect in (entry.get("tab") or {}).get("effects", [])
            if effect.get("piece") and effect.get("fx") in {"show", "hide"}
        ]
        affected = self.page.evaluate(
            """ids => [...document.querySelectorAll('.stage .piece.hidden-until')]
              .filter(e=>ids.includes(e.dataset.id))
              .map((e,i)=>({id:e.dataset.id||`piece-${i}`,opacity:+getComputedStyle(e.querySelector('.mech')).opacity,transform:getComputedStyle(e.querySelector('.mech')).transform}))""",
            tab_piece_ids,
        )
        self.press_slider("End")
        self.wait_slider(100)
        upright = self.page.evaluate(
            """ids => [...document.querySelectorAll('.stage .piece.hidden-until')]
              .filter(e=>ids.includes(e.dataset.id))
              .map((e,i)=>({id:e.dataset.id||`piece-${i}`,opacity:+getComputedStyle(e.querySelector('.mech')).opacity,transform:getComputedStyle(e.querySelector('.mech')).transform}))""",
            tab_piece_ids,
        )
        if affected:
            min_opacity = min([item["opacity"] for item in affected + upright])
            changed = any(a["transform"] != b["transform"] for a, b in zip(affected, upright))
            self.add("S7", key, min_opacity >= 0.98 and changed, f"{len(affected)} hidden pieces, min opacity {min_opacity:.3f}, fold changed {changed}", "opacity 1 and flat-to-upright fold")
        else:
            self.add("S7", key, True, "no hidden tab-driven pieces", "no applicable hidden piece")

    def flap_value(self) -> float:
        return float(self.page.eval_on_selector(".lesson", "e => parseFloat(getComputedStyle(e).getPropertyValue('--flap'))"))

    def flap_drag(self, fraction: float, release: bool = True, reverse: bool = False) -> Any:
        flap = self.geom(".lflap")
        lesson = self.geom(".lesson")
        current = self.flap_value()
        target = max(0.0, min(1.0, current + fraction * (-1 if reverse else 1)))
        max_angle = math.radians(82)
        x = flap["x"] + flap["width"] / 2
        y = flap["y"] + flap["height"] * 0.82
        dy = lesson["height"] * (math.cos(target * max_angle) - math.cos(current * max_angle))
        return self.touch_or_mouse_drag(x, y, x, y + dy, release=release)

    def wait_flap(self, value: float) -> None:
        self.page.wait_for_function(
            "v => Math.abs(parseFloat(getComputedStyle(document.querySelector('.lesson')).getPropertyValue('--flap'))-v)<.01",
            arg=value,
            timeout=3000,
        )
        self.wait_stable(".lflap")

    def flap_checks(self, key: str) -> None:
        # Sample independent lifts. The hinge stays fixed and the bottom edge rises at every larger angle.
        samples: list[dict] = []
        for target in (0.0, 0.2, 0.4, 0.6, 0.8):
            self.open(key)
            if target:
                held = self.flap_drag(target, release=False)
                samples.append(self.geom(".lflap"))
                self.release_drag(held)
            else:
                samples.append(self.geom(".lflap"))
        shut = samples[0]
        top_error = max(abs(sample["top"] - shut["top"]) for sample in samples)
        bottoms = [sample["bottom"] for sample in samples]
        steady = all(after < before - 0.25 for before, after in zip(bottoms, bottoms[1:]))
        never_below = all(bottom <= shut["bottom"] + POSITION_TOLERANCE for bottom in bottoms)
        bottom_rise = shut["bottom"] - bottoms[-1]
        self.add("F1", key, top_error <= POSITION_TOLERANCE and steady and never_below, f"max top error {top_error:.2f}px, bottom rose {bottom_rise:.2f}px, steady {steady}, never below {never_below}", "top fixed within 2px; bottom rises steadily and never dips")

        self.open(key)
        self.page.locator(".lflap").focus()
        self.page.keyboard.press("Enter")
        self.wait_flap(1)
        lifted = self.geom(".lflap")
        self.add("F4", key, lifted["height"] > 1, f"visible projected height {lifted['height']:.2f}px", "visible height > 0px")

        # Contract direction: upward travel must lift; downward travel from shut must do nothing.
        self.open(key)
        up = self.flap_drag(0.25, release=False)
        upward_value = self.flap_value()
        self.release_drag(up)
        self.wait_flap(0)
        flap = self.geom(".lflap")
        lesson = self.geom(".lesson")
        x = flap["x"] + flap["width"] / 2
        y = flap["y"] + flap["height"] * 0.82
        down = self.touch_or_mouse_drag(x, y, x, y + lesson["height"] * 0.25, release=False)
        downward_value = self.flap_value()
        self.release_drag(down)
        self.wait_flap(0)
        self.add("F2", key, upward_value > 0.05 and downward_value <= 0.02, f"upward travel lift {upward_value:.3f}, downward-from-shut {downward_value:.3f}", "upward increases; downward from shut stays 0")

        self.open(key)
        self.flap_drag(0.25)
        self.wait_stable(".lflap")
        low = self.flap_value()
        self.flap_drag(0.45)
        self.wait_stable(".lflap")
        high = self.flap_value()
        self.add("F3", key, low <= 0.01 and high >= 0.99, f"release 25% -> {low:.2f}, 45% -> {high:.2f}", "0 and 1")

        # Reaching half travel from shut and open must give the same scene; closing restores start.
        self.open(key)
        initial = self.mechanism_signature()
        held = self.flap_drag(0.5, release=False)
        opening_value = self.flap_value()
        opening = self.mechanism_signature()
        self.release_drag(held)
        self.wait_stable(".lflap")
        opened_value = self.flap_value()
        held = self.flap_drag(1 - opening_value, release=False, reverse=True)
        closing_value = self.flap_value()
        closing = self.mechanism_signature()
        self.release_drag(held)
        self.wait_stable(".lflap")
        self.page.locator(".lflap").focus()
        self.page.keyboard.press("Escape")
        self.wait_stable(".lflap")
        returned = self.mechanism_signature()
        path_delta = self.mechanism_delta(opening, closing)
        return_delta = self.mechanism_delta(initial, returned)
        self.add("F5", key, opened_value >= 0.99 and path_delta <= POSITION_TOLERANCE and return_delta <= POSITION_TOLERANCE, f"opening {opening_value:.3f}, opened {opened_value:.2f}, closing {closing_value:.3f}, same-half delta {path_delta:.2f}, close-return {return_delta:.2f}", "open reaches 1 and both paths match within tolerance")

        self.open(key)
        self.real_click(".lflap")
        self.wait_stable(".lflap")
        click_open = self.page.locator(".lflap").get_attribute("aria-expanded")
        self.real_click(".lflap")
        self.wait_stable(".lflap")
        second_closed = self.page.locator(".lflap").get_attribute("aria-expanded")
        self.page.locator(".lflap").focus()
        self.page.keyboard.press("Enter")
        self.wait_stable(".lflap")
        enter_open = self.page.locator(".lflap").get_attribute("aria-expanded")
        self.page.keyboard.press("Escape")
        self.wait_stable(".lflap")
        escape_closed = self.page.locator(".lflap").get_attribute("aria-expanded")
        states = [click_open, second_closed, enter_open, escape_closed]
        self.add("F6", key, states == ["true", "false", "true", "false"], f"click/second/Enter/Escape {states}", "true, false, true, false")

    def next_direction(self, index: int) -> int:
        return 1 if index < len(self.pages) - 1 else -1

    def nav_selector(self, direction: int) -> str:
        if self.phone and self.page.locator("[data-stage-next]").count():
            return "[data-stage-next]" if direction > 0 else "[data-stage-prev]"
        return "[data-next]" if direction > 0 else "[data-prev]"

    def turn_and_wait(self, start_index: int, direction: int) -> None:
        self.real_click(self.nav_selector(direction))
        self.page.wait_for_function("i => window.__book.cur() === i", arg=start_index + direction, timeout=8000)
        self.page.wait_for_function("window.__book.turn() === null", timeout=8000)
        if self.reduced_motion:
            self.page.wait_for_timeout(130)
        if self.page.locator(".stage").count():
            self.page.wait_for_function("+getComputedStyle(document.querySelector('.stage')).getPropertyValue('--spread-open') >= .999")
            self.wait_stable(".stage")

    def capture_turn(self, start_index: int, direction: int) -> list[dict]:
        if self.reduced_motion:
            self.turn_and_wait(start_index, direction)
            return []
        self.page.evaluate(
            "sample => { window.__qaTurn=[]; window.__qaTurnDone=false; const take = eval('(' + sample + ')'); let seen=false;"
            " const tick=()=>{ const s=take(); if(s){ seen=true; window.__qaTurn.push(s); } else if(seen){ window.__qaTurnDone=true; return; }"
            " requestAnimationFrame(tick); }; requestAnimationFrame(tick); }",
            TURN_SAMPLE_JS,
        )
        self.real_click(self.nav_selector(direction))
        self.page.wait_for_function("window.__qaTurnDone === true", timeout=20000)
        self.page.wait_for_function("i => window.__book.cur() === i", arg=start_index + direction)
        return self.page.evaluate("window.__qaTurn")

    @staticmethod
    def coupling_result(samples: list[dict], index: int, direction: int, old_has_stage: bool, new_has_stage: bool) -> tuple[bool, str]:
        """Both spreads move at once, as in a codex: the closing pop-up folds as the leaf rises
        (fold = max * angle / 180) and the opening one rises with it (fold = max * (1 - angle / 180)).
        Every surface carries the page a real book would put there, and no page shows twice."""
        problems: list[str] = []
        counts: list[str] = []
        part = [item for item in samples if item and 4.0 <= item["state"]["angle"] <= 176.0]
        roles = [
            ("closing", old_has_stage, lambda angle, maximum: maximum * angle / 180),
            ("opening", new_has_stage, lambda angle, maximum: maximum * (1 - angle / 180)),
        ]
        for role, applicable, expected in roles:
            if not applicable:
                continue
            usable = [item for item in part if item.get(role) and item[role]["folds"]]
            counts.append(f"{role} {len(usable)}")
            if len(usable) < 3:
                problems.append(f"{role} has too few fold samples")
                continue
            ids = set.intersection(*(set(fold["id"] for fold in item[role]["folds"]) for item in usable))
            for fold_id in ids:
                records = []
                for item in usable:
                    fold = next(value for value in item[role]["folds"] if value["id"] == fold_id)
                    records.append((item["state"]["angle"], fold["angle"], fold["max"], fold["opacity"]))
                error = max(abs(fold_angle - expected(leaf_angle, maximum)) for leaf_angle, fold_angle, maximum, _ in records)
                held = any(abs(b[0] - a[0]) >= 1 and abs(b[1] - a[1]) < 0.15 for a, b in zip(records, records[1:]))
                faded = min(record[3] for record in records) < 0.99
                if error > 4 or held or faded:
                    problems.append(f"{role} {fold_id} error {error:.1f}°, held {held}, faded {faded}")
        # Surfaces: no page on two surfaces at once.
        dupes = set()
        for item in part:
            seen = [value for value in item["surfaces"].values() if value]
            for value in set(seen):
                if seen.count(value) > 1:
                    dupes.add(value)
        if dupes:
            problems.append("shown twice during the turn: " + ", ".join(sorted(dupes)))
        return not problems, "; ".join(counts + problems)

    def live_turn_sample(self) -> dict:
        return self.page.evaluate(TURN_SAMPLE_JS) or {}

    def capture_drag_turn(self, index: int, direction: int) -> list[dict]:
        page = self.geom(".page.right" if direction > 0 or self.phone else ".page.left")
        surface = self.geom(".stage") if self.phone else page
        y = surface["top"] + surface["height"] * 0.55
        if direction > 0:
            x0, x1 = surface["right"] - 8, surface["right"] - 8 - page["width"]
        else:
            x0, x1 = surface["left"] + 8, surface["left"] + 8 + page["width"]
        samples: list[dict] = []
        if self.phone and self.browser_name == "chromium":
            session = self.context.new_cdp_session(self.page)
            session.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": x0, "y": y, "id": 1}]})
            for step in range(1, 13):
                x = x0 + (x1 - x0) * step / 12
                session.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": x, "y": y, "id": 1}]})
                self.page.evaluate("() => new Promise(resolve => requestAnimationFrame(resolve))")
                samples.append(self.live_turn_sample())
            session.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
            session.detach()
        else:
            self.page.mouse.move(x0, y)
            self.page.mouse.down()
            for step in range(1, 13):
                x = x0 + (x1 - x0) * step / 12
                self.page.mouse.move(x, y)
                self.page.evaluate("() => new Promise(resolve => requestAnimationFrame(resolve))")
                samples.append(self.live_turn_sample())
            self.page.mouse.up()
        self.page.wait_for_function("window.__book.turn() === null", timeout=5000)
        self.page.wait_for_function("i => window.__book.cur() === i", arg=index + direction)
        return [sample for sample in samples if sample.get("state")]

    def page_drag(self, fraction: float) -> tuple[float, int]:
        page = self.geom(".page.right")
        surface = self.geom(".stage") if self.page.locator(".stage").count() else page
        x0 = surface["right"] - 8
        y = surface["top"] + surface["height"] * 0.55
        x1 = x0 - page["width"] * fraction
        handle = self.touch_or_mouse_drag(x0, y, x1, y, release=False, steps=18)
        state = self.page.evaluate("window.__book.turn()")
        angle = float(state["angle"]) if state else -1.0
        self.release_drag(handle)
        self.page.wait_for_function("window.__book.turn() === null", timeout=5000)
        return angle, int(self.page.evaluate("window.__book.cur()"))

    def page_turn_checks(self, key: str) -> None:
        self.open(key)
        index = self.pages.index(key)
        direction = self.next_direction(index)
        destination = self.pages[index + direction]
        samples = self.capture_turn(index, direction)
        moved = int(self.page.evaluate("window.__book.cur()")) - index
        if self.reduced_motion:
            stage_open = not self.page.locator(".stage").count() or float(self.page.eval_on_selector(".stage", "e => getComputedStyle(e).getPropertyValue('--spread-open')")) >= 0.999
            self.add("T1", key, moved == direction, f"reduced-motion cut moved {moved:+d}", f"{direction:+d}")
            self.add("T2", key, stage_open, f"reduced motion, destination open {stage_open}", "not timing-applicable; destination stands open")
        else:
            direction_name = "next" if direction > 0 else "previous"
            leaf_errors = [abs(float(item["leaf"]) - float(item["state"]["angle"])) for item in samples]
            direction_ok = bool(samples) and all(item["direction"] == direction_name and item["state"]["direction"] == direction for item in samples)
            turn_ok = moved == direction and direction_ok and max(leaf_errors, default=999) <= ANGLE_TOLERANCE
            self.add("T1", key, turn_ok, f"{len(samples)} samples, direction {direction_name}, leaf error {max(leaf_errors, default=999):.1f}°, moved {moved:+d}", "direction correct, leaf within 2°, one page")
            old_has_stage = key not in {"cover", "numbers"}
            new_has_stage = destination not in {"cover", "numbers"}
            coupled, detail = self.coupling_result(samples, index, direction, old_has_stage, new_has_stage)
            if not coupled and "too few" in detail:
                self.open(key)
                drag_samples = self.capture_drag_turn(index, direction)
                coupled, detail = self.coupling_result(drag_samples, index, direction, old_has_stage, new_has_stage)
                detail = "hand-sampled " + detail
            self.add("T2", key, coupled, detail, "every fold changes with the leaf; angle error <= 4°")
            self.turn_samples[key] = samples

        # Double input must remain locked until the first turn has finished.
        self.open(key)
        index = self.pages.index(key)
        direction = self.next_direction(index)
        selector = self.nav_selector(direction)
        if self.phone:
            self.real_click(selector)
            self.real_click(selector)
        else:
            box = self.page.locator(selector).bounding_box()
            if not box:
                raise RuntimeError("navigation button has no geometry")
            x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
            self.page.mouse.click(x, y, click_count=2, delay=5)
        self.page.wait_for_function("i => window.__book.cur() !== i", arg=index, timeout=5000)
        self.page.wait_for_function("window.__book.turn() === null", timeout=8000)
        self.page.wait_for_timeout(250)
        moved = abs(int(self.page.evaluate("window.__book.cur()")) - index)
        self.add("T5", key, moved <= 1, f"double press moved {moved} page", "at most 1 page after the turn finishes")

        if self.reduced_motion:
            self.add("T6", key, True, "reduced-motion page turns cut to the destination", "not timing-applicable")
        elif key not in {"numbers"} and index < len(self.pages) - 1:
            self.open(key)
            if self.page.locator(".stage").count():
                angle40, after40 = self.page_drag(0.4)
                self.open(key)
                angle60, after60 = self.page_drag(0.6)
                passed = abs(angle40 - 72) <= ANGLE_TOLERANCE and after40 == index and abs(angle60 - 108) <= ANGLE_TOLERANCE and after60 == index + 1
                self.add("T6", key, passed, f"40% angle {angle40:.1f}° -> {after40-index:+d}; 60% angle {angle60:.1f}° -> {after60-index:+d}", "72° returns; 108° turns one page")

        entry = entry_for_key(self.story, key)
        if entry.get("tab"):
            self.open(key)
            self.press_slider("End")
            self.wait_slider(100)
            index = self.pages.index(key)
            direction = self.next_direction(index)
            self.turn_and_wait(index, direction)
            other = index + direction
            self.turn_and_wait(other, -direction)
            value = int(self.page.locator(".slider .tab").get_attribute("aria-valuenow") or -1)
            self.add("T3", key, value == 100, f"tab after away/back {value}%", "100% retained")
        if entry.get("flap"):
            self.open(key)
            expected_tab = None
            if entry.get("tab"):
                for _ in range(5):
                    self.press_slider("ArrowRight")
                expected_tab = 50
            self.page.locator(".lflap").focus()
            self.page.keyboard.press("Enter")
            self.wait_flap(1)
            index = self.pages.index(key)
            direction = self.next_direction(index)
            self.turn_and_wait(index, direction)
            other = index + direction
            self.turn_and_wait(other, -direction)
            flap = self.page.locator(".lflap").get_attribute("aria-expanded")
            tab = int(self.page.locator(".slider .tab").get_attribute("aria-valuenow") or -1) if expected_tab is not None else None
            passed = flap == "false" and (expected_tab is None or tab == expected_tab)
            self.add("T4", key, passed, f"flap {flap}, tab {tab if tab is not None else 'n/a'}%", f"flap false, tab {expected_tab if expected_tab is not None else 'n/a'}%")

    def booklet_checks(self, key: str, entry: dict) -> None:
        self.open(key)
        facts = entry.get("facts") or []
        printed = int(self.page.locator(".booklet .bk-n").inner_text())
        self.add("B1", key, printed == len(facts), f"cover {printed}, story {len(facts)}", "equal")
        self.real_click(".booklet")
        self.page.wait_for_selector(".bk-wrap")
        wrap = self.geom(".bk-wrap")
        host_selector = ".page.left .text" if self.phone else ".page.left"
        host = self.geom(host_selector)
        inside = wrap["left"] >= host["left"] - POSITION_TOLERANCE and wrap["right"] <= host["right"] + POSITION_TOLERANCE and wrap["top"] >= host["top"] - POSITION_TOLERANCE and wrap["bottom"] <= host["bottom"] + POSITION_TOLERANCE
        self.add("B3", key, inside, f"booklet [{wrap['left']:.1f},{wrap['top']:.1f},{wrap['right']:.1f},{wrap['bottom']:.1f}], text page [{host['left']:.1f},{host['top']:.1f},{host['right']:.1f},{host['bottom']:.1f}]", "booklet rect inside text page within 2px")
        if len(facts) > 1:
            def turn_with_leaf(selector: str, prefix: str) -> tuple[str, bool]:
                self.page.evaluate(
                    """() => { window.__qaBookletLeaf=[]; clearInterval(window.__qaBookletTimer);
                    window.__qaBookletTimer=setInterval(()=>{const e=document.querySelector('.bk-leaf');if(e){const s=getComputedStyle(e);window.__qaBookletLeaf.push([s.animationName,s.transform,e.className])}},8) }"""
                )
                self.real_click(selector)
                self.page.wait_for_function(
                    "prefix => document.querySelector('.bk-where').textContent.startsWith(prefix)",
                    arg=prefix,
                )
                samples = self.page.evaluate("() => {clearInterval(window.__qaBookletTimer);return window.__qaBookletLeaf}")
                visible_turn = any(
                    animation not in {"", "none"} and transform not in {"", "none"}
                    for animation, transform, _ in samples
                )
                return self.page.locator(".bk-where").inner_text(), visible_turn

            forward, forward_leaf = turn_with_leaf("[data-bk='1']", "2 ")
            back, back_leaf = turn_with_leaf("[data-bk='-1']", "1 ")
            passed = forward.startswith("2 ") and back.startswith("1 ") and forward_leaf and back_leaf
            self.add("B2", key, passed, f"forward {forward}, leaf {forward_leaf}; back {back}, leaf {back_leaf}", "index +1 then -1, with a rotating leaf each way")
        else:
            self.add("B2", key, True, "one fact; no page change to animate", "one page at a time")
        self.page.keyboard.press("Escape")
        self.page.wait_for_function("!document.querySelector('.bk-wrap')")
        focused = self.page.evaluate("document.activeElement && document.activeElement.matches('[data-facts]')")
        self.add("B4", key, bool(focused), f"closed true, focus returned {focused}", "closed and booklet focused")

    def wheel_angle(self) -> float:
        value = self.page.eval_on_selector(".wheel", "e => getComputedStyle(e).transform")
        if value == "none":
            return 0.0
        numbers = value[value.find("(") + 1 : value.rfind(")")].split(",")
        return math.degrees(math.atan2(float(numbers[1]), float(numbers[0])))

    def wheel_checks(self, key: str, entry: dict) -> None:
        self.open(key)
        wheel = self.geom(".wheel")
        cx, cy = wheel["x"] + wheel["width"] / 2, wheel["y"] + wheel["height"] / 2
        radius = wheel["width"] * 0.38
        a0, a1, a2 = 0.0, 70.0, 25.0
        p = lambda angle: (cx + radius * math.cos(math.radians(angle)), cy + radius * math.sin(math.radians(angle)))
        x0, y0 = p(a0)
        x1, y1 = p(a1)
        held = self.touch_or_mouse_drag(x0, y0, x1, y1, release=False, steps=18)
        angle1 = self.wheel_angle()
        x2, y2 = p(a2)
        if held == "mouse":
            self.page.mouse.move(x2, y2, steps=12)
        else:
            held.send(
                "Input.dispatchTouchEvent",
                {"type": "touchMove", "touchPoints": [{"x": x2, "y": y2, "id": 1}]},
            )
            self.page.evaluate("() => new Promise(resolve => requestAnimationFrame(resolve))")
        angle2 = self.wheel_angle()
        self.release_drag(held)
        self.wait_stable(".wheel")
        snapped = self.wheel_angle()
        months = entry.get("months") or []
        step = 360 / max(1, len(months))
        idx = round(-snapped / step)
        expected = months[idx % len(months)] if months else {}
        readout = self.page.locator(".wheel-readout .v").inner_text()
        expected_text = "\n".join(expected.get("lines") or [])
        self.add("W1", key, abs(angle1 - a1) <= ANGLE_TOLERANCE, f"pointer +{a1:.1f}°, disc {angle1:.1f}°, error {abs(angle1-a1):.1f}°", "within 2°")
        self.add("W3", key, angle2 < angle1 and abs((angle1 - angle2) - (a1 - a2)) <= ANGLE_TOLERANCE, f"reverse pointer {a1-a2:.1f}°, disc {angle1-angle2:.1f}°", "equal reverse within 2°")
        detent_error = abs(snapped - round(snapped / step) * step)
        self.add("W2", key, detent_error <= ANGLE_TOLERANCE and readout == expected_text, f"angle {snapped:.1f}°, detent error {detent_error:.1f}°, readout {readout!r}", f"detent within 2° and {expected_text!r}")

    def look_checks(self, key: str) -> None:
        self.open(key)
        if self.page.locator(".slider .tab").count():
            tab = self.geom(".slider .tab")
            x = tab["x"] + tab["width"] / 2
            y = tab["y"] + tab["height"] / 2
            self.page.mouse.move(x, y)
            self.page.evaluate("() => new Promise(resolve=>{let n=0;const tick=()=>++n>=20?resolve():requestAnimationFrame(tick);requestAnimationFrame(tick)})")
            before_drag = self.page.eval_on_selector(".stage", "e => getComputedStyle(e).perspectiveOrigin")
            self.page.mouse.down()
            self.page.mouse.move(x + 60, y, steps=8)
            self.page.evaluate("() => new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))")
            after_drag = self.page.eval_on_selector(".stage", "e => getComputedStyle(e).perspectiveOrigin")
            self.page.mouse.up()
            def origin_point(value: str) -> tuple[float, float]:
                parts = value.replace("px", "").split()
                return float(parts[0]), float(parts[1])
            origin_delta = math.dist(origin_point(before_drag), origin_point(after_drag))
            self.add("L3", key, origin_delta <= POSITION_TOLERANCE, f"tab drag origin {before_drag!r} -> {after_drag!r}, delta {origin_delta:.2f}px", "unchanged within 2px while the text-page tab is held")
            self.open(key)
        if self.reduced_motion:
            before = self.page.eval_on_selector(".stage", "e => getComputedStyle(e).perspectiveOrigin")
            elapsed = self.page.evaluate(
                """() => new Promise(resolve=>{const t0=performance.now(); const loop=t=>{if(t-t0>=2700){resolve(t-t0);return}requestAnimationFrame(loop)};requestAnimationFrame(loop)})"""
            )
            after = self.page.eval_on_selector(".stage", "e => getComputedStyle(e).perspectiveOrigin")
            self.add("L2", key, before == after, f"idle {elapsed:.0f}ms, origin {before!r} -> {after!r}", "unchanged with reduced motion")
            return
        stage = self.geom(".stage")
        target_x = stage["left"] + stage["width"] * 0.8
        target_y = stage["top"] + stage["height"] * 0.35
        self.page.evaluate("window.__qaOrigins=[]")
        self.page.mouse.move(target_x, target_y)
        samples = self.page.evaluate(
            """() => new Promise(resolve=>{let n=0; const tick=()=>{window.__qaOrigins.push(getComputedStyle(document.querySelector('.stage')).perspectiveOrigin); if(++n>=8)resolve(window.__qaOrigins);else requestAnimationFrame(tick)};requestAnimationFrame(tick)})"""
        )
        def point(value: str) -> tuple[float, float]:
            parts = value.replace("px", "").split()
            return float(parts[0]), float(parts[1])
        points = [point(value) for value in samples]
        steps = [math.dist(a, b) for a, b in zip(points, points[1:])]
        changed = math.dist(points[0], points[-1]) > 0.5
        eased = bool(steps) and max(steps) < stage["width"] * 0.08
        self.add("L1", key, changed and eased, f"8 frames, total {math.dist(points[0],points[-1]):.2f}px, largest step {max(steps, default=0):.2f}px", "changes smoothly; no step over 8% stage width")

    @staticmethod
    def finale_coupling(samples: list[dict], current: int, closing: bool) -> tuple[bool, str]:
        role = "closing" if closing else "opening"
        part = [item for item in samples if item and 4 <= item["state"]["angle"] <= 176 and item.get(role) and item[role]["finale"]]
        if len(part) < 3:
            return False, f"{len(part)} usable samples"
        ids = set.intersection(*(set(piece["id"] for piece in item[role]["finale"]) for item in part))
        held: list[str] = []
        faded: list[str] = []
        for piece_id in ids:
            records = []
            for item in part:
                piece = next(value for value in item[role]["finale"] if value["id"] == piece_id)
                records.append((item["state"]["angle"], piece["transform"], piece["opacity"]))
            if any(abs(b[0] - a[0]) >= 1 and b[1] == a[1] for a, b in zip(records, records[1:])):
                held.append(piece_id)
            if min(record[2] for record in records) < 0.99:
                faded.append(piece_id)
        passed = bool(ids) and not held and not faded
        return passed, f"{len(part)} samples, {len(ids)} pieces, held {len(held)}, faded {len(faded)}"

    def finale_checks(self, key: str, entry: dict) -> None:
        self.open(key)
        index = self.pages.index(key)
        direction = self.next_direction(index)
        if self.reduced_motion:
            stage_open = float(self.page.eval_on_selector(".finale-stage", "e => getComputedStyle(e).getPropertyValue('--spread-open')")) >= 0.999
            self.add("N1", key, stage_open, f"reduced motion, finale open {stage_open}", "not timing-applicable; finale stands open")
        else:
            closing_samples = self.capture_turn(index, direction)
            opening_samples = self.capture_turn(index + direction, -direction)
            closing_ok, closing_detail = self.finale_coupling(closing_samples, index, closing=True)
            opening_ok, opening_detail = self.finale_coupling(opening_samples, index, closing=False)
            if not closing_ok and "usable samples" in closing_detail:
                self.open(key)
                closing_samples = self.capture_drag_turn(index, direction)
                closing_ok, closing_detail = self.finale_coupling(closing_samples, index, closing=True)
                closing_detail = "hand-sampled " + closing_detail
            if not opening_ok and "usable samples" in opening_detail:
                self.open(self.pages[index + direction])
                opening_samples = self.capture_drag_turn(index + direction, -direction)
                opening_ok, opening_detail = self.finale_coupling(opening_samples, index, closing=False)
                opening_detail = "hand-sampled " + opening_detail
            self.add("N1", key, closing_ok and opening_ok, f"closing {closing_detail}; opening {opening_detail}", "every structure, wing, platform and cast piece moves with the leaf and stays opaque")
        self.open(key)
        if entry.get("tab"):
            self.press_slider("End")
            self.wait_slider(100)
        if entry.get("flap"):
            self.page.locator(".lflap").focus()
            self.page.keyboard.press("Enter")
            self.wait_flap(1)
        stage = self.geom(".stage")
        cast = self.page.evaluate(
            """() => [...document.querySelectorAll('.finale-role-cast')].map((e,i)=>{const v=e.querySelector('.mech > .main')||e;const r=v.getBoundingClientRect();return{id:e.dataset.id||`cast-${i}`,left:r.left,top:r.top,right:r.right,bottom:r.bottom,width:r.width,height:r.height,mount:[...e.classList].find(x=>x.startsWith('finale-mount-'))||'',tier:[...e.classList].find(x=>x.startsWith('finale-tier-'))||''}})"""
        )
        platforms = set(self.page.eval_on_selector_all(".finale-tier-platform", "els => els.map(e=>e.dataset.tier)"))
        worst_edge = 0.0
        for item in cast:
            worst_edge = max(worst_edge, stage["left"] - item["left"], item["right"] - stage["right"], stage["top"] - item["top"], item["bottom"] - stage["bottom"])
        worst_overlap = max((overlap_ratio(a, b) for i, a in enumerate(cast) for b in cast[i + 1 :]), default=0.0)
        mounted = all(item["mount"] and (not item["tier"] or item["tier"].split("-")[-1] in platforms) for item in cast)
        self.add("N2", key, mounted and worst_edge <= POSITION_TOLERANCE and worst_overlap <= 0.5, f"cast {len(cast)}, mounted {mounted}, worst edge {worst_edge:.1f}px, worst overlap {worst_overlap:.3f}", "mounted, inside stage within 2px, overlap <= 0.5")

    def instruction_checks(self, key: str, entry: dict) -> None:
        self.open(key)
        text = self.page.evaluate(
            """() => [...document.querySelectorAll('.ink-cue, .lf-cue, .bk-cue, .wheel-btns, .phone-page-cues, .stage-hint')]
              .filter(e=>{const s=getComputedStyle(e);return s.display!=='none'&&s.visibility!=='hidden'})
              .map(e=>e.innerText).join(' ')"""
        )
        expected: list[str] = []
        if entry.get("tab"):
            expected.append("Slide the tab to the right" if self.phone else "Pull the tab towards the picture")
        if entry.get("flap"):
            expected.append("Lift the flap")
        if entry.get("facts"):
            expected.append("Open")
        if key == "numbers":
            expected.append(str(entry.get("wheelHint") or "Turn the wheel"))
        if self.phone and self.page.locator(".phone-page-cues").count():
            index = self.pages.index(key)
            if index > 0:
                expected.append("Previous page")
            if index < len(self.pages) - 1:
                expected.append("Next page")
        missing = [cue for cue in expected if cue not in text]
        self.add("I1", key, not missing, f"expected {expected}, missing {missing}", "all printed cues name measured action and direction")
        pointer_words = [word for word in ("pointer", "mouse", "hover") if word in text.lower()]
        self.add("I3", key, not self.phone or not pointer_words, f"device {'phone' if self.phone else 'desktop'}, pointer-only words {pointer_words}", "none on phone")

    def run(self) -> list[dict]:
        self.open("cover")
        pages = list(self.pages)
        for key in pages:
            entry = entry_for_key(self.story, key)
            families: list[tuple[list[str], Any]] = []
            if entry.get("tab"):
                families.append(([f"S{i}" for i in range(1, 10)], lambda k=key: self.slider_checks(k)))
            if entry.get("flap"):
                families.append(([f"F{i}" for i in range(1, 7)], lambda k=key: self.flap_checks(k)))
            if key != "cover":
                families.append(([f"T{i}" for i in range(1, 7)], lambda k=key: self.page_turn_checks(k)))
            if entry.get("facts"):
                families.append(([f"B{i}" for i in range(1, 5)], lambda k=key, e=entry: self.booklet_checks(k, e)))
            if key == "numbers" and entry.get("months"):
                families.append(([f"W{i}" for i in range(1, 4)], lambda k=key, e=entry: self.wheel_checks(k, e)))
            if key not in {"cover", "numbers"} and (not self.phone or self.reduced_motion):
                families.append((["L1", "L2", "L3"], lambda k=key: self.look_checks(k)))
            if key == "finale":
                families.append((["N1", "N2"], lambda k=key, e=entry: self.finale_checks(k, e)))
            if key != "cover":
                families.append((["I1", "I3"], lambda k=key, e=entry: self.instruction_checks(k, e)))
            for clauses, function in families:
                active = [clause for clause in clauses if clause in self.only]
                if not active:
                    continue
                try:
                    function()
                except Exception as error:
                    for clause in active:
                        self.fail_exception(clause, key, error)
        return self.results


def run(
    source: str | Path,
    phone: bool = False,
    browser_name: str = "chromium",
    reduced_motion: bool = False,
    only: list[str] | None = None,
) -> dict:
    """Build a story, measure all selected clauses and return a JSON-safe report."""
    from playwright.sync_api import sync_playwright

    source = Path(source).expanduser().resolve()
    story = load_story(source)
    chosen = selected_clauses(only)
    report = {
        "source": str(source),
        "browser": browser_name,
        "reduced_motion": reduced_motion,
        "clauses": sorted(chosen),
        "results": [],
    }
    viewports = [("phone", True)] if phone else [("desktop", False)]
    with built_book(source) as html, sync_playwright() as playwright:
        for viewport, is_phone in viewports:
            browser, context = browser_context(
                playwright,
                phone=is_phone,
                browser_name=browser_name,
                reduced_motion=reduced_motion,
            )
            page = context.new_page()
            page.set_default_timeout(5000)
            checker = MechanicsCheck(
                page,
                context,
                html,
                story,
                viewport,
                browser_name,
                reduced_motion,
                chosen,
            )
            report["results"].extend(checker.run())
            context.close()
            browser.close()
    report["failures"] = [item for item in report["results"] if item["status"] == "FAIL"]
    report["passed"] = not report["failures"]
    report["checks"] = len(report["results"])
    return report


def print_report(report: dict) -> None:
    for item in report["results"]:
        print(
            f"{item['status']} {item['clause']} {item['page']} {item['viewport']}: "
            f"{item['measured']}; expected {item['expected']}"
        )
    status = "PASS" if report["passed"] else "FAIL"
    print(f"{status}: {report['checks']} clause-page checks, {len(report['failures'])} failures")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("book", help="story JSON or built HTML book")
    parser.add_argument("--phone", action="store_true", help="check the 390 by 844 touch layout")
    parser.add_argument("--browser", choices=("chromium", "firefox"), default="chromium")
    parser.add_argument("--json", dest="json_out", metavar="OUT", help="write the full JSON report")
    parser.add_argument("--only", action="append", help="comma-separated clause ids or families")
    parser.add_argument("--reduced-motion", action="store_true", help="emulate reduced motion")
    args = parser.parse_args(argv)
    try:
        report = run(
            args.book,
            phone=args.phone,
            browser_name=args.browser,
            reduced_motion=args.reduced_motion,
            only=args.only,
        )
    except Exception as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print_report(report)
    if args.json_out:
        output = Path(args.json_out).expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"JSON {output}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
