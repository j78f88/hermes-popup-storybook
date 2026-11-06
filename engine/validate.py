#!/usr/bin/env python3
"""Validate a popup-storybook story file.

Checks structure, sprite and source references, gadget effect targets,
reading length, and scans for secrets and private network details.

Usage: python3 engine/validate.py STORY.json [--deny FILE] [--strict]
Exit code 1 on errors (or on warnings with --strict).
"""
import argparse
import base64
import json
import math
import re
import sys
from pathlib import Path

ENGINE = Path(__file__).resolve().parent
VERSION = "1.0.0"
MAX_FLOOR_PIECES = 9
MAX_WALL_PIECES = 4
MAX_GADGET_EFFECTS = 6
MAX_IMAGE_BYTES = 180 * 1024
MAX_TOTAL_IMAGE_BYTES = 1500 * 1024
ACTIVE_FX = {"move", "hop", "rise", "flip", "wobble", "glow", "dim", "swap"}

# Shared with tools/release_check.py. Keep every privacy pattern in this list.
SECRET_PATTERNS = [
    ("OpenAI-style key", r"\bsk-[A-Za-z0-9_-]{20,}"),  # release-check: allow
    ("GitHub token", r"\b(?:(?:ghp|gho|ghs|ghu)_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"),  # release-check: allow
    ("Slack token", r"\bxox[abprs]-[A-Za-z0-9-]{10,}"),  # release-check: allow
    ("AWS key", r"\bAKIA[0-9A-Z]{16}\b"),  # release-check: allow
    ("Private key", r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),  # release-check: allow
    ("Bearer token", r"\bBearer\s+[A-Za-z0-9._-]{20,}"),  # release-check: allow
    ("Linear key", r"\blin_(?:api|oauth)_[A-Za-z0-9]{20,}"),  # release-check: allow
    ("Private IPv4", r"\b(?:10\.\d{1,3}|192\.168|172\.(?:1[6-9]|2\d|3[01]))\.\d{1,3}\.\d{1,3}\b"),  # release-check: allow
    ("CGNAT / tailnet IPv4", r"\b100\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7])\.\d{1,3}\.\d{1,3}\b"),  # release-check: allow
    ("Tailnet hostname", r"\b(?:[a-z0-9-]+\.)+ts\.net\b"),  # release-check: allow
    ("Email address", r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),  # release-check: allow
    ("Password assignment", r"(?i)\b(?:password|passwd|secret|api[_-]?key)\s*[:=]\s*[^\s\"',;]{6,}"),  # release-check: allow
    ("Home directory path", r"(?:/home/[a-z_][a-z0-9_-]*/|/Users/[A-Za-z0-9_-]+/|C:\\Users\\)"),  # release-check: allow
]

SKIES = {"dawn", "day", "dusk", "night", "storm", "indoor", "library", "workshop", "sea", "council"}
GROUNDS = {"paper", "wood", "grass", "water", "carpet", "desk", "road", "stone"}
FX = {"hop", "wobble", "flip", "dim", "glow", "rise", "hide", "show", "swap", "move"}


def load_library():
    sprites = json.loads((ENGINE / "library" / "sprites.json").read_text())
    font = json.loads((ENGINE / "library" / "font.json").read_text())
    return sprites, font


def words(paras):
    return sum(len(str(p).split()) for p in paras or [])


def validate(story, deny_terms=(), min_facts=3, max_words=320):
    errors, warnings = [], []
    lib, font = load_library()
    palette = dict(lib["palette"], **story.get("palette", {}))
    sprites = dict(lib["sprites"], **story.get("sprites", {}))
    glyphs = font["glyphs"]
    sources = story.get("sources", {})
    used_sources = set()

    def E(msg):
        errors.append(msg)

    def W(msg):
        warnings.append(msg)

    def finite_number(value):
        return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)

    for key in ("title", "chapters", "sources"):
        if key not in story:
            E(f"missing top-level '{key}'")
    if not isinstance(story.get("chapters", []), list) or not story.get("chapters"):
        E("'chapters' must be a non-empty list")
    if "sound" in story:
        sound = story["sound"]
        if not isinstance(sound, dict):
            E("'sound' must be an object with an optional 'volume'")
        elif "volume" in sound:
            volume = sound["volume"]
            if isinstance(volume, bool) or not isinstance(volume, (int, float)) or not 0 <= volume <= 1:
                E("'sound.volume' must be a number from 0 to 1")

    for name, rows in story.get("sprites", {}).items():
        if not rows or len({len(r) for r in rows}) != 1:
            E(f"sprite '{name}': rows must be the same length")
        for r in rows:
            bad = {c for c in r if c != "." and c not in palette}
            if bad:
                E(f"sprite '{name}': unknown palette keys {sorted(bad)}")
                break

    images = story.get("images", {})
    total_image_bytes = 0
    if images and not isinstance(images, dict):
        E("'images' must be an object mapping image ids to image definitions")
        images = {}
    for img_id, info in images.items():
        if not isinstance(info, dict):
            E(f"image '{img_id}': must be an object")
            continue
        src = str(info.get("src") or "")
        if not re.match(r"^data:image/(?:png|webp|jpeg);base64,[A-Za-z0-9+/=\s]+$", src):
            E(f"image '{img_id}': src must be an offline data:image/(png|webp|jpeg);base64 URI")
        else:
            b64_part = src.split(",", 1)[1]
            try:
                raw = base64.b64decode(b64_part, validate=False)
            except Exception:
                raw = b""
                E(f"image '{img_id}': invalid base64 payload")
            size = len(raw)
            total_image_bytes += size
            if size > MAX_IMAGE_BYTES:
                E(f"image '{img_id}': {size // 1024} KB exceeds 180 KB per-image limit")
            if b"Exif\x00\x00" in raw or b"GPSInfo" in raw:
                E(f"image '{img_id}': contains unstripped EXIF metadata; run tools/ingest_image.py")
        for dim in ("width", "height"):
            val = info.get(dim)
            if not finite_number(val) or val <= 0:
                E(f"image '{img_id}': '{dim}' must be a positive number")
        img_source = info.get("source")
        if not img_source or img_source not in sources:
            E(f"image '{img_id}': must cite a valid 'source' from sources")
        else:
            used_sources.add(img_source)
    if total_image_bytes > MAX_TOTAL_IMAGE_BYTES:
        E(f"images: total embedded size {total_image_bytes // 1024} KB exceeds 1500 KB book limit")

    def check_text_glyphs(where, text):
        missing = {c for c in str(text).upper() if c not in glyphs}
        if missing:
            W(f"{where}: pixel font has no glyph for {sorted(missing)}; '?' will be drawn")

    def check_scene(where, scene, need_pieces=True):
        if not scene:
            if need_pieces:
                E(f"{where}: missing scene")
            return set()
        ids = set()
        if scene.get("sky") and "(" not in scene["sky"] and scene["sky"] not in SKIES:
            E(f"{where}: unknown sky '{scene['sky']}'")
        g = scene.get("ground")
        if g and "(" not in g and not g.startswith("#") and g not in GROUNDS:
            E(f"{where}: unknown ground '{g}'")
        wings = scene.get("wings")
        if wings is not None and wings not in ("none", "low"):
            E(f"{where}: scene wings must be 'none' or 'low'")
        if not scene.get("alt"):
            W(f"{where}: scene has no alt text for screen readers")
        pieces = scene.get("pieces", [])
        if need_pieces and not pieces:
            E(f"{where}: scene has no pieces")
        wall = scene.get("wall", [])
        for i, p in enumerate(pieces + wall):
            if p.get("image"):
                img_ref = p["image"]
                if img_ref not in images:
                    E(f"{where}: piece {i} uses unknown image '{img_ref}'")
            for k in ("sprite", "alt"):
                nm = p.get(k)
                finale_engine_sprite = where == "finale" and nm == "finale_arch"
                if nm and nm not in sprites and not finale_engine_sprite:
                    E(f"{where}: piece {i} uses unknown sprite '{nm}'")
            if not p.get("sprite") and not p.get("image"):
                E(f"{where}: piece {i} needs 'sprite' or 'image'")
            if p.get("remap"):
                for a, b in p["remap"].items():
                    if b not in palette:
                        E(f"{where}: piece {i} remaps to unknown colour key '{b}'")
            x = p.get("x", 50)
            if not finite_number(x):
                E(f"{where}: piece {i} x must be a finite number")
            elif not 0 <= x <= 100:
                E(f"{where}: piece {i} x={x} outside 0..100")
            if i >= len(pieces):
                y = p.get("y", 20)
                if not finite_number(y):
                    E(f"{where}: wall piece {i - len(pieces)} y must be a finite number")
                elif not 0 <= y <= 100:
                    E(f"{where}: wall piece {i - len(pieces)} y={y} outside 0..100")
            if "depth" in p and (
                not finite_number(p["depth"]) or p["depth"] not in (1, 2, 3, 4)
            ):
                E(f"{where}: piece {i} depth must be 1..4")
            if where != "finale" and i < len(pieces) and p.get("mount") is not None:
                if p["mount"] not in ("flat", "box", "vfold"):
                    E(f"{where}: piece {i} mount must be one of ['box', 'flat', 'vfold']")
                elif p["mount"] == "vfold" and finite_number(x) and not 35 <= x <= 65:
                    E(f"{where}: piece {i} mount 'vfold' requires x between 35 and 65")
            if p.get("id"):
                if p["id"] in ids:
                    E(f"{where}: duplicate piece id '{p['id']}'")
                ids.add(p["id"])
        if where != "finale" and len(pieces) > MAX_FLOOR_PIECES:
            W(f"{where}: {len(pieces)} floor pieces exceeds {MAX_FLOOR_PIECES}; keep scenes uncluttered on phones")
        elif len(pieces) > 14:
            W(f"{where}: {len(pieces)} pieces may be slow on phones")
        if where != "finale" and len(wall) > MAX_WALL_PIECES:
            W(f"{where}: {len(wall)} wall pieces exceeds {MAX_WALL_PIECES}; keep walls uncluttered")
        return ids

    SUBSTITUTION_OVERLAP_TOLERANCE = 0.10

    def check_effects(where, effects, ids):
        for f in effects or []:
            if not isinstance(f, dict):
                E(f"{where}: effect must be an object")
                continue
            if f.get("piece") not in ids:
                E(f"{where}: effect targets unknown piece '{f.get('piece')}'")
            if f.get("fx") not in FX:
                E(f"{where}: unknown effect '{f.get('fx')}' (use one of {sorted(FX)})")
            if f.get("fx") == "move":
                to = f.get("to")
                if not isinstance(to, dict) or not to:
                    E(f"{where}: move effect on '{f.get('piece')}' needs a 'to' object")
                else:
                    unknown = sorted(set(to) - {"x", "grow", "z", "lift", "depth"})
                    if unknown:
                        E(f"{where}: move target has unknown fields {unknown}")
                    for field in ("x", "grow", "z", "lift", "depth"):
                        if field not in to:
                            continue
                        value = to[field]
                        if not finite_number(value):
                            E(f"{where}: move to {field} must be a finite number")
                        elif field == "x" and not 0 <= value <= 100:
                            E(f"{where}: move to x={value} outside 0..100")
                        elif field == "z" and not 0 <= value <= 1:
                            E(f"{where}: move to z={value} outside 0..1")
                        elif field == "depth" and value not in (1, 2, 3, 4):
                            E(f"{where}: move to depth must be 1..4")
                        elif field == "grow" and not value > 0:
                            E(f"{where}: move to grow must be greater than 0")
            at = f.get("at")
            if at is not None and not (isinstance(at, list) and len(at) == 2 and all(isinstance(n, (int, float)) for n in at) and 0 <= at[0] < at[1] <= 1):
                E(f"{where}: 'at' on '{f.get('piece')}' must be [start, end] with 0 <= start < end <= 1")

    def effect_window(effect):
        at = effect.get("at")
        if (
            isinstance(at, list)
            and len(at) == 2
            and all(finite_number(value) for value in at)
            and 0 <= at[0] < at[1] <= 1
        ):
            return float(at[0]), float(at[1])
        return None

    def check_substitution_overlap(where, effects, scene):
        scene_dict = scene if isinstance(scene, dict) else {}
        pieces = {
            piece.get("id"): piece
            for piece in scene_dict.get("pieces", [])
            if isinstance(piece, dict) and piece.get("id")
        }
        hides = []
        shows = []
        for effect in effects or []:
            if not isinstance(effect, dict):
                continue
            window = effect_window(effect)
            piece = pieces.get(effect.get("piece"))
            if not window or not piece:
                continue
            if effect.get("fx") == "hide":
                hides.append((effect["piece"], piece, window))
            elif effect.get("fx") == "show":
                shows.append((effect["piece"], piece, window))
        for hide_id, hide_piece, hide_win in hides:
            for show_id, show_piece, show_win in shows:
                if hide_id == show_id:
                    continue
                hx = hide_piece.get("x", 50)
                sx = show_piece.get("x", 50)
                if not (finite_number(hx) and finite_number(sx)):
                    continue
                same_spot = abs(hx - sx) <= 10 and hide_piece.get("depth", 2) == show_piece.get("depth", 2)
                overlap = min(hide_win[1], show_win[1]) - max(hide_win[0], show_win[0])
                if same_spot and overlap > SUBSTITUTION_OVERLAP_TOLERANCE:
                    W(f"{where}: stagger hide '{hide_id}' before show '{show_id}' so they do not overlap")

    numbers = []
    for idx, c in enumerate(story.get("chapters", [])):
        where = f"chapter {c.get('number', idx + 1)}"
        for key in ("number", "title"):
            if key not in c:
                E(f"{where}: missing '{key}'")
        numbers.append(c.get("number"))
        status = c.get("status", "written")
        if status not in ("written", "open"):
            E(f"{where}: status must be 'written' or 'open'")
        check_text_glyphs(f"{where} title", c.get("title", ""))
        ids = check_scene(where, c.get("scene"))
        if status == "written":
            if not c.get("text"):
                E(f"{where}: written chapter has no text")
            n = words(c.get("text"))
            if n > max_words:
                W(f"{where}: {n} words in main text; the page may scroll (aim for under {max_words})")
            if len(c.get("facts", [])) < min_facts:
                E(f"{where}: needs at least {min_facts} facts with sources")
        for gadget in ("tab", "flap"):
            g = c.get(gadget)
            if g:
                if not g.get("text"):
                    E(f"{where}: {gadget} has no text")
                effs = g.get("effects") or []
                check_effects(f"{where} {gadget}", effs, ids)
                check_substitution_overlap(f"{where} {gadget}", effs, c.get("scene"))
                if len(effs) > MAX_GADGET_EFFECTS:
                    W(f"{where}: {gadget} has {len(effs)} effects (max {MAX_GADGET_EFFECTS})")
                if status == "written" and effs and not any(isinstance(ef, dict) and ef.get("fx") in ACTIVE_FX for ef in effs):
                    W(f"{where}: {gadget} uses only static show/hide effects; add move, hop, rise, flip, wobble, glow or swap")
                if words([g.get("text", "")]) > 70:
                    W(f"{where}: {gadget} text over 70 words will be cramped")
                if gadget == "flap" and words([g.get("text", "")]) > 45:
                    W(f"{where}: the lesson flap sits on the picture; over 45 words will cover too much of it")
        for f in c.get("facts", []):
            s = f.get("source")
            if s not in sources:
                E(f"{where}: fact '{f.get('label')}' cites unknown source '{s}'")
            used_sources.add(s)
            if f.get("image") and f["image"] not in images:
                E(f"{where}: fact '{f.get('label')}' uses unknown image '{f['image']}'")
            if f.get("value") is None and not f.get("label"):
                E(f"{where}: empty fact")
    if numbers and numbers != list(range(1, len(numbers) + 1)):
        E(f"chapter numbers must run 1..{len(numbers)} in order, got {numbers}")

    character_sprites = {"robot", "robot_wave", "robot_happy", "robot_sleep", "robin", "owl", "person"}
    nature_wall_sprites = {"sun", "moon", "star", "cloud", "raincloud"}
    chapters_list = story.get("chapters", [])
    if isinstance(chapters_list, list) and len(chapters_list) >= 4:
        setting_pages: dict[str, list[int]] = {}
        wall_pages: dict[str, list[int]] = {}
        room_pages: dict[tuple[str, str], list[int]] = {}
        for idx, c in enumerate(chapters_list):
            if not isinstance(c, dict) or c.get("status", "written") != "written":
                continue
            num = c.get("number", idx + 1)
            scene = c.get("scene") if isinstance(c.get("scene"), dict) else {}
            sky_key = str(scene.get("sky") or "day")
            ground_key = str(scene.get("ground") or "paper")
            room_pages.setdefault((sky_key, ground_key), []).append(num)
            seen_on_page = set()
            for piece in scene.get("pieces", []):
                if not isinstance(piece, dict):
                    continue
                sp = piece.get("sprite")
                depth = piece.get("depth", 2)
                if sp and sp not in character_sprites and isinstance(depth, (int, float)) and depth >= 3:
                    seen_on_page.add(sp)
            for sp in seen_on_page:
                setting_pages.setdefault(sp, []).append(num)
            seen_wall = {
                w.get("sprite")
                for w in scene.get("wall", [])
                if isinstance(w, dict) and w.get("sprite") and w.get("sprite") not in nature_wall_sprites
            }
            for sp in seen_wall:
                wall_pages.setdefault(sp, []).append(num)
        for sp, nums in sorted(setting_pages.items()):
            if len(nums) > 2:
                W(f"setting sprite '{sp}' repeats at depth 3..4 on {len(nums)} chapters ({nums}); keep characters recurring, not the same setting")
        for sp, nums in sorted(wall_pages.items()):
            if len(nums) > 2:
                W(f"wall setting sprite '{sp}' repeats on {len(nums)} chapters ({nums}); vary the room details across chapters")
        for (sky_key, ground_key), nums in sorted(room_pages.items()):
            if len(nums) > 2:
                W(f"scene sky/ground pair ({sky_key!r}, {ground_key!r}) repeats on {len(nums)} chapters ({nums}); give chapters distinct settings")

    finale = story.get("finale")
    if finale is not None:
        if not isinstance(finale, dict):
            E("'finale' must be an object")
        else:
            for key in ("title", "text", "scene"):
                if not finale.get(key):
                    E(f"finale: missing '{key}'")
            if finale.get("text") and not isinstance(finale["text"], list):
                E("finale: 'text' must be a list of short paragraphs")
            elif words(finale.get("text")) > 80:
                W("finale: text over 80 words will crowd the paper card")
            ids = check_scene("finale", finale.get("scene"))
            finale_pieces = (finale.get("scene") or {}).get("pieces", [])
            roles = {"structure", "cast", "reveal", "scenery"}
            mounts = {"vfold", "wing-left", "wing-right", "platform"}
            structures = []
            cast_tiers = set()
            tier_lifts = {}
            for index, piece in enumerate(finale_pieces):
                role = piece.get("finaleRole", "cast")
                if role not in roles:
                    E(f"finale: piece {index} finaleRole must be one of {sorted(roles)}")
                if piece.get("mount") and piece["mount"] not in mounts:
                    E(f"finale: piece {index} mount must be one of {sorted(mounts)}")
                tier = piece.get("tier")
                if tier is not None and tier not in (1, 2, 3, 4):
                    E(f"finale: piece {index} tier must be 1..4")
                if role == "structure":
                    structures.append(piece)
                if role == "cast":
                    if not tier:
                        E(f"finale: cast piece {index} needs a tier so it stands on a platform")
                    elif piece.get("mount") not in {"wing-left", "wing-right", "platform"}:
                        E(f"finale: cast piece {index} needs a platform or wing mount")
                    else:
                        cast_tiers.add(tier)
                        tier_lifts.setdefault(tier, set()).add(piece.get("lift", 0))
            for tier, lifts in tier_lifts.items():
                if len(lifts) > 1:
                    E(f"finale: cast on tier {tier} must share one platform height")
            ordered_lifts = [next(iter(tier_lifts[tier])) for tier in sorted(tier_lifts)]
            if any(back <= front for front, back in zip(ordered_lifts, ordered_lifts[1:])):
                E("finale: higher cast tiers must use higher platform lifts")
            if not structures:
                E("finale: scene needs a central piece with finaleRole 'structure'")
            elif not any(40 <= piece.get("x", 50) <= 60 and piece.get("mount") == "vfold" for piece in structures):
                E("finale: central structure must use mount 'vfold' near x 50")
            if len(cast_tiers) < 3:
                E("finale: cast must use at least three tiers")
            for gadget in ("tab", "flap"):
                g = finale.get(gadget)
                if g:
                    if not g.get("text"):
                        E(f"finale: {gadget} has no text")
                    check_effects(f"finale {gadget}", g.get("effects"), ids)
                    check_substitution_overlap(f"finale {gadget}", g.get("effects"), finale.get("scene"))
                    if words([g.get("text", "")]) > 45:
                        W(f"finale: {gadget} text over 45 words will crowd the spread")
            for fact in finale.get("facts", []):
                source = fact.get("source")
                if source not in sources:
                    E(f"finale: fact '{fact.get('label')}' cites unknown source '{source}'")
                used_sources.add(source)
                if fact.get("value") is None and not fact.get("label"):
                    E("finale: empty fact")

    if story.get("contents", {}).get("scene"):
        check_scene("contents", story["contents"]["scene"])
    if story.get("back", {}).get("scene"):
        check_scene("back", story["back"]["scene"])
    if story.get("numbers"):
        for s in story["numbers"].get("stats", []):
            check_text_glyphs(f"stat '{s.get('label')}'", s.get("value", ""))
            if s.get("source"):
                if s["source"] not in sources:
                    E(f"stat '{s.get('label')}' cites unknown source '{s['source']}'")
                used_sources.add(s["source"])
        for m in story["numbers"].get("months", []):
            if m.get("source"):
                if m["source"] not in sources:
                    E(f"month '{m.get('label')}' cites unknown source '{m['source']}'")
                used_sources.add(m["source"])
    check_text_glyphs("title", story.get("title", ""))
    hero = story.get("cover", {}).get("hero")
    if hero and hero not in sprites:
        E(f"cover hero sprite '{hero}' not found")

    for sid, s in sources.items():
        if not s.get("kind") or not s.get("ref"):
            E(f"source '{sid}' needs 'kind' and 'ref'")
        if sid not in used_sources:
            W(f"source '{sid}' is never cited")

    image_meta = {
        k: {mk: mv for mk, mv in v.items() if mk != "src"}
        for k, v in images.items()
        if isinstance(v, dict)
    }
    blob = json.dumps(
        {k: (image_meta if k == "images" else v) for k, v in story.items() if k != "sprites"},
        ensure_ascii=False,
    )
    for label, pat in SECRET_PATTERNS:
        for m in re.finditer(pat, blob):
            E(f"possible {label} in story: '{m.group(0)[:40]}'")
    low = blob.lower()
    for term in deny_terms:
        if term and term.lower() in low:
            E(f"denied term present: '{term}'")
    return errors, warnings


def load_deny(path):
    """Read banned terms from a file, ignoring blank lines and comments."""
    if not path:
        return []
    words = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            words.append(line)
    return words


def main(argv=None):
    ap = argparse.ArgumentParser(description=(__doc__ or "").strip().split("\n")[0])
    ap.add_argument("story")
    ap.add_argument("--deny", help="file with one denied term per line (customer names, private projects)")
    ap.add_argument("--strict", action="store_true", help="treat warnings as errors")
    ap.add_argument("--min-facts", type=int, default=3)
    a = ap.parse_args(argv)
    try:
        story = json.loads(Path(a.story).read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"FAIL: story file not found: {a.story}")
        return 1
    except json.JSONDecodeError as e:
        print(f"FAIL: {a.story} is not valid JSON: line {e.lineno}, column {e.colno}: {e.msg}")
        return 1
    deny = []
    if a.deny:
        try:
            deny = load_deny(a.deny)
        except FileNotFoundError:
            print(f"FAIL: deny file not found: {a.deny}")
            return 1
    errors, warnings = validate(story, deny, a.min_facts)
    for w in warnings:
        print("WARN ", w)
    for e in errors:
        print("ERROR", e)
    n = len(story.get("chapters", []))
    nf = sum(len(c.get("facts", [])) for c in story.get("chapters", []))
    print(f"{'FAIL' if errors or (a.strict and warnings) else 'PASS'}: {n} chapters, {nf} facts, {len(story.get('sources', {}))} sources, {len(errors)} errors, {len(warnings)} warnings")
    return 1 if errors or (a.strict and warnings) else 0


if __name__ == "__main__":
    sys.exit(main())
