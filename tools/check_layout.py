#!/usr/bin/env python3
"""Check popup-storybook layouts in a real Chromium browser."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from _browser import (
    apply_state,
    browser_context,
    built_book,
    dispatch_key,
    entry_for_key,
    go_to,
    load_story,
    open_book,
    overlap_ratio,
    scene_for_page,
    set_final,
    set_half,
    set_start,
)

MEASURE_JS = r"""() => {
  const st=document.querySelector('.page.right .stage');
  const result={edge:[],underLesson:[],nan:[],pieces:[],proseScroll:false,textExpected:0,textChecked:0,textItems:[],unverifiedText:[]};
  const prose=document.querySelector('.page.left .prose.scrolls');
  result.proseScroll=!!prose;
  const parseRGB=(str)=>{
    const m=str&&str.match(/rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)(?:\s*,\s*([\d.]+))?\s*\)/);
    if(!m) return null;
    return [Number(m[1]),Number(m[2]),Number(m[3]),m[4]===undefined?1:Number(m[4])];
  };
  const blend=(fg,bg)=>{
    const a=fg[3]+bg[3]*(1-fg[3]);
    if(a<=0) return [246,238,219,0];
    return [
      (fg[0]*fg[3]+bg[0]*bg[3]*(1-fg[3]))/a,
      (fg[1]*fg[3]+bg[1]*bg[3]*(1-fg[3]))/a,
      (fg[2]*fg[3]+bg[2]*bg[3]*(1-fg[3]))/a,
      a
    ];
  };
  const isVisible=(el)=>{
    let cur=el;
    while(cur && cur.nodeType===1){
      if(cur.classList && (cur.classList.contains('leaf') || cur.id==='print')) return false;
      const cs=getComputedStyle(cur);
      if(cs.display==='none' || cs.visibility==='hidden' || Number(cs.opacity)<0.2) return false;
      cur=cur.parentElement;
    }
    const rect=el.getBoundingClientRect();
    return rect.width>=2 && rect.height>=2;
  };
  const parseHex=(str)=>{
    const s=(str||'').trim();
    const m6=s.match(/^#([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i);
    if(m6) return [parseInt(m6[1],16),parseInt(m6[2],16),parseInt(m6[3],16),1];
    const m3=s.match(/^#([0-9a-f])([0-9a-f])([0-9a-f])$/i);
    if(m3) return [parseInt(m3[1]+m3[1],16),parseInt(m3[2]+m3[2],16),parseInt(m3[3]+m3[3],16),1];
    return null;
  };
  const resolvePaper=(el)=>{
    const cs=getComputedStyle(el||document.documentElement);
    const v=cs.getPropertyValue('--paper');
    return parseRGB(v)||parseHex(v)||[246,238,219,1];
  };
  const effectiveBg=(el)=>{
    const layers=[];
    let cur=el;
    let foundBase=false;
    while(cur && cur.nodeType===1){
      const cs=getComputedStyle(cur);
      const c=parseRGB(cs.backgroundColor);
      const bgImg=cs.backgroundImage||'none';
      if(c && c[3]>0){
        layers.push(c);
        if(c[3]>=0.99){ foundBase=true; break; }
      } else if(cur.matches && cur.matches('.cover .outside')){
        const m=bgImg.match(/rgba?\([^)]+\)|#[0-9a-fA-F]{3,6}/g);
        const parsed=m&&m.length?(parseRGB(m[m.length-1])||parseHex(m[m.length-1])):null;
        if(!parsed) return null;
        layers.push(parsed);
        foundBase=true;
        break;
      } else if(cur.matches && cur.matches('.page, .finale-layer')){
        const paper=resolvePaper(cur);
        if(!paper) return null;
        layers.push(paper);
        foundBase=true;
        break;
      } else if(bgImg!=='none'){
        return null;
      }
      cur=cur.parentElement;
    }
    if(!foundBase) return null;
    let bg=layers[layers.length-1];
    for(let i=layers.length-2;i>=0;i--) bg=blend(layers[i],bg);
    return bg;
  };
  const selectorList=[
    '.page.left .title',
    '.page.left .prose p',
    '.slider .seg.trial',
    '.lesson-card .lesson-body',
    '.cover-card h1',
    '.cover-card .sub',
    '.cover:not(.open) .outside .sub',
    '.finale-banner-paper .title',
    '.finale-copy p'
  ];
  for(const sel of selectorList){
    document.querySelectorAll(sel).forEach(el=>{
      if(el.closest && el.closest('.leaf, #print, .book.closed .page')) return;
      const text=(el.textContent||'').trim();
      if(!text) return;
      if(sel==='.lesson-card .lesson-body'){
        const lesson=el.closest('.lesson');
        if(lesson && !lesson.classList.contains('up')) return;
      }
      if(sel.startsWith('.cover') && !document.querySelector('.book.closed')) return;
      result.textExpected+=1;
      if(!isVisible(el)) return;
      const cs=getComputedStyle(el);
      const fg=parseRGB(cs.color);
      const bg=effectiveBg(el);
      if(!fg || !bg){
        result.unverifiedText.push({selector:sel,text:text.slice(0,40)});
        return;
      }
      const blendedFg=blend(fg,bg);
      const size=parseFloat(cs.fontSize)||16;
      const weight=parseInt(cs.fontWeight,10)||400;
      result.textChecked+=1;
      result.textItems.push({
        selector:sel,
        fg:blendedFg.slice(0,3),
        bg:bg.slice(0,3),
        fontSize:size,
        fontWeight:weight,
        text:text.slice(0,40)
      });
    });
  }
  if(result.textExpected===0 && document.querySelector('.page.left, .cover .outside, .finale-layer')){
    result.textExpected=1;
  }
  if(!st) return result;
  const r=st.getBoundingClientRect();
  const les=document.querySelector('.lesson-card');
  const L=les?les.getBoundingClientRect():null;
  document.querySelectorAll('.page.right .piece').forEach((e,index)=>{
    const m=e.querySelector('.mech');
    const v=e.querySelector('.mech > .main')||e.querySelector('.mech > svg');
    const id=e.dataset.qaLabel || e.dataset.id || `piece-${index+1}`;
    const es=getComputedStyle(e);
    const ms=m?getComputedStyle(m):null;
    const numericStyles=[
      e.style.left, es.left, e.style.bottom, es.bottom,
      e.style.getPropertyValue('--grow'), es.getPropertyValue('--grow'),
      m?m.style.transform:'', ms?ms.transform:''
    ];
    if(numericStyles.some(value => /(?:NaN|Infinity)/.test(value||''))) result.nan.push(id);
    if(!m || +ms.opacity<0.2 || !v) return;
    const b=v.getBoundingClientRect();
    if(!b.width || !b.height) return;
    const box={id,left:b.left,top:b.top,right:b.right,bottom:b.bottom,width:b.width,height:b.height,active:e.dataset.qaActive==='true'};
    result.pieces.push(box);
    const left=b.left-r.left, right=r.right-b.right, top=b.top-r.top;
    if(left<r.width*0.03 || right<2 || top<0) {
      result.edge.push([id,Math.round(left),Math.round(right),Math.round(top)]);
    }
    if(L && b.top<L.bottom-2 && b.right>L.left && b.left<L.right) {
      result.underLesson.push([id,Math.round(L.bottom-b.top)]);
    }
  });
  return result;
}"""


def state_names(phone: bool = False) -> list[str]:
    """Return the layout states required for one viewport."""
    return ["start", "final"] if phone else ["start", "half", "pulled", "lifted"]


def relative_luminance(rgb: tuple[float, float, float] | list[float]) -> float:
    """Return WCAG 2.1 relative luminance for an sRGB triplet."""
    channels = []
    for value in rgb[:3]:
        channel = value / 255
        channels.append(channel / 12.92 if channel <= 0.03928 else ((channel + 0.055) / 1.055) ** 2.4)
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def contrast_ratio(
    foreground: tuple[float, float, float] | list[float],
    background: tuple[float, float, float] | list[float],
) -> float:
    """Return WCAG 2.1 contrast ratio between two sRGB colours."""
    left = relative_luminance(foreground)
    right = relative_luminance(background)
    return (max(left, right) + 0.05) / (min(left, right) + 0.05)


def required_contrast(font_size: float, font_weight: float) -> float:
    """Return WCAG AA contrast threshold for one CSS font size and weight."""
    return 3.0 if font_size >= 24 or (font_size >= 18.66 and font_weight >= 700) else 4.5


def read_allowlist(source: str | Path, extra: list[str] | None = None) -> set[str]:
    """Combine story-level and command-line offstage allowances."""
    story = load_story(source)
    values = story.get("qa", {}).get("allowOffstage", [])
    return {str(value) for value in values} | set(extra or [])


def piece_annotations(scene: dict, effects: list[dict]) -> list[dict]:
    """Name scene pieces and mark pieces that move or appear."""
    active_ids = {
        effect.get("piece")
        for effect in effects
        if effect.get("fx") in {"move", "show"} and effect.get("piece")
    }
    ordered = list(scene.get("wall", [])) + list(scene.get("pieces", []))
    return [
        {
            "label": piece.get("id") or f"{piece.get('sprite', 'piece')} (scene {index})",
            "active": piece.get("id") in active_ids,
        }
        for index, piece in enumerate(ordered, 1)
    ]


def annotate_scene(page, scene: dict, effects: list[dict]) -> None:
    """Attach stable QA names to the currently rendered scene pieces."""
    page.evaluate(
        """annotations => {
          const pieces=[...document.querySelectorAll('.page.right .stage .piece')];
          pieces.forEach((piece,index) => {
            const value=annotations[index] || {label:`piece (scene ${index+1})`,active:false};
            piece.dataset.qaLabel=value.label;
            piece.dataset.qaActive=String(value.active);
          });
        }""",
        piece_annotations(scene, effects),
    )


def check_measurement(measured: dict, allow: set[str], location: str) -> tuple[list[dict], list[dict]]:
    """Convert one browser measurement into errors and warnings."""
    errors: list[dict] = []
    warnings: list[dict] = []
    for item in measured["edge"]:
        if item[0] not in allow:
            errors.append({"type": "edge", "at": location, "piece": item[0], "offsets": item[1:]})
    for item in measured["underLesson"]:
        errors.append({"type": "under-lesson", "at": location, "piece": item[0], "pixels": item[1]})
    for piece in measured["nan"]:
        errors.append({"type": "nan-position", "at": location, "piece": piece})
    pieces = measured["pieces"]
    for index, left in enumerate(pieces):
        for right in pieces[index + 1 :]:
            ratio = overlap_ratio(left, right)
            if ratio > 0.12:
                warning = {
                    "type": "overlap",
                    "at": location,
                    "pieces": [left["id"], right["id"]],
                    "ratio": round(ratio, 3),
                }
                if ratio > 0.5 and (left.get("active") or right.get("active")):
                    warning["severity"] = "high"
                warnings.append(warning)
    if measured["proseScroll"]:
        warnings.append({"type": "prose-overflow", "at": location})
    for item in measured.get("textItems", []):
        raw_ratio = contrast_ratio(item["fg"], item["bg"])
        required = required_contrast(float(item["fontSize"]), float(item["fontWeight"]))
        if raw_ratio < required:
            errors.append(
                {
                    "type": "contrast",
                    "at": location,
                    "selector": item["selector"],
                    "ratio": round(raw_ratio, 2),
                    "required": required,
                    "text": item.get("text", ""),
                }
            )
    for item in measured.get("unverifiedText", []):
        errors.append(
            {
                "type": "contrast-coverage",
                "at": location,
                "selector": item["selector"],
                "problem": f"unverified background or colour on {item['selector']}",
            }
        )
    if measured.get("textExpected", 0) and measured.get("textChecked", 0) == 0:
        errors.append(
            {
                "type": "contrast-coverage",
                "at": location,
                "problem": "visible reader text was not checked",
            }
        )
    return errors, warnings


def drag_test(page, pages: list[str]) -> tuple[list[dict], list[dict]]:
    """Check one-to-one pull-tab tracking on every slider page."""
    results: list[dict] = []
    errors: list[dict] = []
    for index, key in enumerate(pages):
        go_to(page, index)
        if not page.locator(".slider .tab").count():
            continue
        set_start(page)
        page.wait_for_timeout(500)
        tab = page.locator(".slider .tab")
        strip = page.locator(".slider .strip")
        track = page.locator(".slider .track")
        tab_before = tab.bounding_box()
        strip_before = strip.bounding_box()
        track_box = track.bounding_box()
        if not tab_before or not strip_before or not track_box:
            errors.append(
                {"type": "drag-test", "at": key, "problem": "slider geometry is unavailable"}
            )
            continue
        drag_distance = min(100, track_box["width"] - tab_before["width"])
        x = tab_before["x"] + tab_before["width"] / 2
        y = tab_before["y"] + tab_before["height"] / 2
        page.mouse.move(x, y)
        page.mouse.down()
        page.mouse.move(x + drag_distance, y, steps=10)
        try:
            page.wait_for_function(
                "([before,distance]) => Math.abs(document.querySelector('.slider .tab').getBoundingClientRect().left - before - distance) <= 2",
                arg=[tab_before["x"], drag_distance],
                timeout=1000,
            )
        except Exception:
            pass
        tab_after = tab.bounding_box()
        strip_after = strip.bounding_box()
        page.mouse.up()
        value_after = tab.get_attribute("aria-valuenow")
        page.wait_for_timeout(500)
        value_later = tab.get_attribute("aria-valuenow")
        if not tab_after or not strip_after:
            errors.append(
                {"type": "drag-test", "at": key, "problem": "slider geometry disappeared"}
            )
            continue
        tab_delta = tab_after["x"] - tab_before["x"]
        strip_delta = strip_after["x"] - strip_before["x"]
        details = {
            "page": key,
            "requested_delta": round(drag_distance, 2),
            "tab_delta": round(tab_delta, 2),
            "strip_delta": round(strip_delta, 2),
            "aria_after": value_after,
            "aria_later": value_later,
        }
        results.append(details)
        problems = []
        if abs(tab_delta - drag_distance) > 2:
            problems.append(
                f"tab moved {tab_delta:.1f}px for a {drag_distance:.1f}px drag"
            )
        if abs(strip_delta - tab_delta) > 3:
            problems.append(
                f"strip moved {strip_delta:.1f}px while tab moved {tab_delta:.1f}px"
            )
        if value_after != value_later:
            problems.append("value changed after release")
        if problems:
            errors.append(
                {"type": "drag-test", "at": key, "problem": "; ".join(problems)}
            )
    return results, errors


def dedupe(items: list[dict]) -> list[dict]:
    """Remove exact duplicate findings while preserving their order."""
    seen = set()
    output = []
    for item in items:
        token = json.dumps(item, sort_keys=True)
        if token not in seen:
            seen.add(token)
            output.append(item)
    return output


def run(
    source: str | Path,
    phone: bool = False,
    allow_extra: list[str] | None = None,
    browser_name: str = "chromium",
) -> dict:
    """Run all required layout checks and return a serialisable report."""
    from playwright.sync_api import sync_playwright

    source = Path(source).expanduser().resolve()
    story = load_story(source)
    allow = read_allowlist(source, allow_extra)
    report = {
        "source": str(source),
        "browser": browser_name,
        "allowOffstage": sorted(allow),
        "checks": 0,
        "textChecks": 0,
        "errors": [],
        "warnings": [],
    }
    viewports = [("desktop", False)] + ([("phone", True)] if phone else [])
    with built_book(source) as html, sync_playwright() as playwright:
        for viewport_name, is_phone in viewports:
            browser, context = browser_context(
                playwright, phone=is_phone, browser_name=browser_name
            )
            page = context.new_page()
            browser_errors: list[dict] = []
            page.on(
                "console",
                lambda message, name=viewport_name: browser_errors.append(
                    {"type": "console", "at": name, "problem": message.text}
                )
                if message.type == "error"
                else None,
            )
            page.on(
                "pageerror",
                lambda error, name=viewport_name: browser_errors.append(
                    {"type": "page-error", "at": name, "problem": str(error)}
                ),
            )
            pages = open_book(page, html)
            for index, key in enumerate(pages):
                go_to(page, index)
                scene, effects = scene_for_page(story, key)
                annotate_scene(page, scene, effects)
                for state in state_names(phone=is_phone):
                    apply_state(page, state)
                    measured = page.evaluate(MEASURE_JS)
                    location = f"{viewport_name}/{key}/{state}"
                    errors, warnings = check_measurement(measured, allow, location)
                    report["errors"].extend(errors)
                    report["warnings"].extend(warnings)
                    report["checks"] += 1
                    report["textChecks"] += int(measured.get("textChecked", 0))
            if not is_phone:
                details, drag_errors = drag_test(page, pages)
                report["dragTests"] = details
                report["errors"].extend(drag_errors)
            report["errors"].extend(browser_errors)
            context.close()
            browser.close()
    report["errors"] = dedupe(report["errors"])
    report["warnings"] = dedupe(report["warnings"])
    if report["checks"] > 0 and report["textChecks"] == 0:
        report["errors"].append(
            {
                "type": "contrast-coverage",
                "at": "book",
                "problem": "zero text elements were checked across the book",
            }
        )
    report["passed"] = not report["errors"]
    return report


def print_summary(report: dict) -> None:
    """Print a short report suited to local use and continuous integration."""
    status = "PASS" if report["passed"] else "FAIL"
    text_checks = report.get("textChecks", 0)
    print(
        f"{status}: {report['checks']} page-state checks, {text_checks} text contrast checks, "
        f"{len(report['errors'])} errors, {len(report['warnings'])} warnings"
    )
    for item in report["errors"][:20]:
        subject = item.get("piece") or item.get("selector") or item.get("problem") or ""
        if item.get("type") == "contrast" and "ratio" in item and "required" in item:
            subject = f"{subject} {item['ratio']} < {item['required']}".strip()
        print(f"ERROR {item['type']} {item.get('at', '')} {subject}".rstrip())
    if len(report["errors"]) > 20:
        print(f"ERROR {len(report['errors']) - 20} more errors in the JSON report")
    for item in report["warnings"][:12]:
        subject = ", ".join(item.get("pieces", []))
        level = " HIGH" if item.get("severity") == "high" else ""
        print(f"WARN{level} {item['type']} {item.get('at', '')} {subject}".rstrip())
    if len(report["warnings"]) > 12:
        print(f"WARN  {len(report['warnings']) - 12} more warnings in the JSON report")
    for drag in report.get("dragTests", []):
        print(
            f"DRAG  {drag['page']}: tab {drag['tab_delta']}px, "
            f"strip {drag['strip_delta']}px, stable {drag['aria_later']}"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("book", help="story JSON or built HTML book")
    parser.add_argument("--phone", action="store_true", help="also check the phone layout")
    parser.add_argument(
        "--browser",
        choices=("chromium", "firefox", "webkit"),
        default="chromium",
        help="browser engine to use",
    )
    parser.add_argument("--allow", action="append", default=[], metavar="ID", help="allow one piece offstage")
    parser.add_argument("--json", dest="json_out", metavar="OUT", help="write the full JSON report")
    args = parser.parse_args(argv)
    try:
        report = run(
            args.book,
            phone=args.phone,
            allow_extra=args.allow,
            browser_name=args.browser,
        )
    except Exception as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print_summary(report)
    if args.json_out:
        output = Path(args.json_out)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"JSON  {output}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
