/* popup-storybook engine.
   Reads the story JSON embedded in the page and builds a virtual pop-up book:
   a cover, a contents spread, chapter spreads with tunnel-book pop-up scenes,
   paper gadgets (pull tab, lift flap, fact pocket), a numbers spread with a
   paper wheel, a back cover and a flat print edition. No dependencies. */
(() => {
  "use strict";

  const story = JSON.parse(document.getElementById("story").textContent);
  const LIB = story.__library || { palette: {}, sprites: {}, font: { glyphs: {} } };
  const PAL = Object.assign({}, LIB.palette, story.palette || {});
  const SPR = Object.assign({}, LIB.sprites, story.sprites || {});
  const IMG = story.images || {};
  // The finale arch is engine scenery rather than a general authoring sprite.
  if (story.finale && !SPR.finale_arch) SPR.finale_arch = [
    ".............................",
    ".............................",
    "............kkkkk............",
    "..........kzzzzzzzk..........",
    ".........kzzzzzzzzzk.........",
    "........kzzzzzzzzzzzk........",
    ".k.k.k.kzzzzzzzzzzzzzkk.k.k..",
    ".akakakzzzzzzzzzzzzzzzkakaka.",
    ".kkkkkzzzzkzzzzzzzkzzzzkkkkk.",
    ".kaakzzzzkzzzzzzzzzkzzzzkaak.",
    ".kaakzzzkzzzzzzzzzzzkzzzkaak.",
    ".kakzzzkzzzzzzzzzzzzzkzzzkak.",
    ".kakzzzk.............kzzzkak.",
    ".kakzzzk.............kzzzkak.",
    ".kakzzzk.............kzzzkak.",
    ".kakzzzk.............kzzzkak.",
    ".kakzzzk.............kzzzkak.",
    ".kakzzzkkkkkkkkkkkkkkkzzzkak.",
    ".kakzzzkaaaaaaaaaaaaakzzzkak.",
    ".kakzzzkkkkkkkkkkkkkkkzzzkak.",
    ".kakzzzk.............kzzzkak.",
    ".kakzzzk.............kzzzkak.",
    ".kakzzzk.............kzzzkak.",
    ".kakzyzk.............kzyzkak.",
    ".kakzzzk.............kzzzkak.",
    ".kakzzzk.............kzzzkak.",
    ".kakzzzk.............kzzzkak.",
    ".kakzzzk.............kzzzkak.",
    ".kakzzzk.............kzzzkak.",
    ".kakzzzk.............kzzzkak.",
    ".kakzzzk.............kzzzkak.",
    ".kakzzzk.............kzzzkak.",
    ".kakzzzk.............kzzzkak.",
    ".kakzyzk.............kzyzkak.",
    ".kakzzzk.............kzzzkak.",
    ".kakzzzk.............kzzzkak.",
    ".kakzzzk.............kzzzkak.",
    ".kakzzzk.............kzzzkak.",
    ".kakzzzk.............kzzzkak.",
    ".kakzzzk.............kzzzkak.",
    ".kakzzzk.............kzzzkak.",
    ".kkkzzzk.............kzzzkkk.",
  ];
  const FONT = LIB.font.glyphs;
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => Array.from(el.querySelectorAll(s));
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const inline = (s) => esc(s).replace(/\*([^*]+)\*/g, "<em>$1</em>");

  const SKIES = {
    dawn: "radial-gradient(circle at 76% 28%,rgba(255,244,214,.55) 0 18%,transparent 48%),linear-gradient(180deg,#ffad84 0%,#ffd6ab 54%,#fff2de 100%)",
    day: "radial-gradient(circle at 78% 22%,rgba(255,252,235,.55) 0 16%,transparent 46%),linear-gradient(180deg,#74c2fc 0%,#b8e3ff 62%,#e8f7ff 100%)",
    dusk: "radial-gradient(circle at 50% 42%,rgba(255,186,120,.35) 0 22%,transparent 55%),linear-gradient(180deg,#35336e 0%,#9e4d70 52%,#ff9868 100%)",
    night: "radial-gradient(ellipse at 72% 18%,#3f5299 0%,#1f2e59 48%,#131930 100%)",
    storm: "radial-gradient(ellipse at 30% 20%,#495066 0%,transparent 55%),linear-gradient(180deg,#555c72 0%,#8d94a8 68%,#b8bfce 100%)",
    indoor: "linear-gradient(180deg,#e5cfa6 0 4%,#f6e9ce 4% 68%,#c7a270 68% 71%,#dfc69a 71% 100%)",
    library: "radial-gradient(ellipse at 50% 32%,#f6e7c8 0%,#e5CFA4 66%,#caa874 100%)",
    workshop: "radial-gradient(ellipse at 68% 26%,#5c4973 0%,#3c2f50 58%,#261e36 100%)",
    sea: "linear-gradient(180deg,#8ed0ff 0%,#c7eaff 64%,#eef9ff 100%)",
    council: "radial-gradient(ellipse at 50% 28%,#8a2b5c 0%,#441f42 58%,#241328 100%)",
  };
  const GROUNDS = {
    paper: "linear-gradient(180deg,#d8c49b 0 4%,#ede0c2 4% 48%,#e2d1ab 100%)",
    wood: "repeating-linear-gradient(0deg,rgba(72,42,16,.13) 0 2px,transparent 2px 26px),linear-gradient(180deg,#9e6e3c 0%,#bf8f58 55%,#ad7d49 100%)",
    grass: "radial-gradient(ellipse at 50% 25%,rgba(125,214,110,.35) 0%,transparent 65%),linear-gradient(180deg,#3d9444 0%,#56b854 62%,#4ba84b 100%)",
    water: "repeating-linear-gradient(0deg,rgba(255,255,255,.16) 0 2px,transparent 2px 24px),linear-gradient(180deg,#1a66ab 0%,#289be6 62%,#4bbdf7 100%)",
    carpet: "linear-gradient(180deg,#5e1b3d 0 9%,#c99755 9% 12%,#7c2551 12% 84%,#c99755 84% 87%,#5e1b3d 87% 100%)",
    desk: "linear-gradient(180deg,#59321c 0 6%,#7c4a2d 6% 82%,#5e361f 82% 100%)",
    road: "repeating-linear-gradient(0deg,rgba(255,255,255,.05) 0 2px,transparent 2px 32px),linear-gradient(180deg,#4c4742 0%,#66605a 58%,#57524c 100%)",
    stone: "repeating-linear-gradient(0deg,rgba(45,40,35,.16) 0 2px,transparent 2px 28px),linear-gradient(180deg,#878176 0%,#a19b8f 65%,#918b7f 100%)",
  };
  const sky = (k) => (k && k.includes("(") ? k : SKIES[k] || SKIES.day);
  const ground = (k) => (k && (k.includes("(") || k.startsWith("#")) ? k : GROUNDS[k] || GROUNDS.paper);

  /* ---------- Pixel rendering ---------- */

  // One <path> per colour. Shared edges inside a path rasterise without seams,
  // which separate <rect>s do not (visible hairlines in print and at odd zooms).
  function runs(rows, keyFn) {
    const paths = new Map();
    rows.forEach((row, y) => {
      let x = 0;
      while (x < row.length) {
        const fill = keyFn(row[x]);
        if (!fill) { x++; continue; }
        let x2 = x;
        while (x2 + 1 < row.length && keyFn(row[x2 + 1]) === fill) x2++;
        paths.set(fill, (paths.get(fill) || "") + `M${x} ${y}h${x2 - x + 1}v1h${-(x2 - x + 1)}z`);
        x = x2 + 1;
      }
    });
    let out = "";
    paths.forEach((d, fill) => { out += `<path fill="${fill}" d="${d}"/>`; });
    return out;
  }

  function dilate(rows) {
    const h = rows.length, w = rows[0].length, out = [];
    for (let y = -1; y <= h; y++) {
      let r = "";
      for (let x = -1; x <= w; x++) {
        let on = false;
        for (let dy = -1; dy <= 1 && !on; dy++)
          for (let dx = -1; dx <= 1 && !on; dx++) {
            const yy = y + dy, xx = x + dx;
            if (yy >= 0 && yy < h && xx >= 0 && xx < w && rows[yy][xx] !== ".") on = true;
          }
        r += on ? "#" : ".";
      }
      out.push(r);
    }
    return out;
  }

  const outlineCache = {};
  function spriteSVG(name, opts = {}) {
    const rows = SPR[name];
    if (!rows) { console.warn("missing sprite", name); return ""; }
    const { scale = 3, remap = null, flip = false, cut = true, cls = "" } = opts;
    const w = rows[0].length, h = rows.length;
    const key = (c) => (c === "." ? null : PAL[(remap && remap[c]) || c] || null);
    let body = runs(rows, key);
    let vb = `0 0 ${w} ${h}`, ow = w, oh = h;
    if (cut) {
      const ol = outlineCache[name] || (outlineCache[name] = dilate(rows));
      body = `<g transform="translate(1 1)">${body}</g>`;
      body = runs(ol, (c) => (c === "#" ? "#fffaf0" : null)) + body;
      vb = `0 0 ${w + 2} ${h + 2}`; ow = w + 2; oh = h + 2;
    }
    if (flip) body = `<g transform="translate(${ow} 0) scale(-1 1)">${body}</g>`;
    return `<svg class="px ${cls}" viewBox="${vb}" style="width:calc(var(--u) * ${ow * scale});height:calc(var(--u) * ${oh * scale})" shape-rendering="crispEdges" aria-hidden="true">${body}</svg>`;
  }

  function imageSVG(id, opts = {}) {
    const info = IMG[id];
    if (!info || !info.src) { console.warn("missing image", id); return ""; }
    const { scale = 3, flip = false, cut = true, cls = "" } = opts;
    const aspect = (info.width || 1) / Math.max(1, info.height || 1);
    const baseH = 14, baseW = Math.max(8, Math.min(28, Math.round(baseH * aspect)));
    const pad = cut ? 1.4 : 0;
    const ow = baseW + pad * 2, oh = baseH + pad * 2;
    const frame = cut ? `<rect x="0.3" y="0.3" width="${ow - 0.6}" height="${oh - 0.6}" rx="1.4" fill="#fffaf0" stroke="#cbb58a" stroke-width="0.45"/>` : "";
    const inner = `<image href="${esc(info.src)}" x="${pad}" y="${pad}" width="${baseW}" height="${baseH}" preserveAspectRatio="xMidYMid slice"/>`;
    const body = flip ? `<g transform="translate(${ow} 0) scale(-1 1)">${frame}${inner}</g>` : `${frame}${inner}`;
    return `<svg class="px img-cutout ${cls}" viewBox="0 0 ${ow} ${oh}" style="width:calc(var(--u) * ${(ow * scale).toFixed(2)});height:calc(var(--u) * ${(oh * scale).toFixed(2)})" aria-hidden="true">${body}</svg>`;
  }

  function pieceVisualSVG(p, opts = {}) {
    if (p.image) return imageSVG(p.image, opts);
    return spriteSVG(p.sprite, opts);
  }

  function pieceGridWidth(p) {
    if (p.image && IMG[p.image]) {
      const aspect = (IMG[p.image].width || 1) / Math.max(1, IMG[p.image].height || 1);
      return Math.max(8, Math.min(28, Math.round(14 * aspect)));
    }
    const rows = SPR[p.sprite] || [[""]];
    return rows[0].length;
  }

  function textSVG(str, color = "currentColor", label = true) {
    const s = String(str).toUpperCase();
    let x = 0, rects = "";
    for (const ch of s) {
      const g = FONT[ch] || FONT["?"];
      g.forEach((row, y) => {
        for (let i = 0; i < row.length; i++) if (row[i] === "#") rects += `<rect x="${x + i}" y="${y}" width="1" height="1"/>`;
      });
      x += g[0].length + 1;
    }
    const w = Math.max(1, x - 1);
    const aria = label ? `role="img" aria-label="${esc(str)}"` : `aria-hidden="true"`;
    return `<svg class="ptxt" viewBox="0 0 ${w} 7" style="aspect-ratio:${w}/7" fill="${color}" shape-rendering="crispEdges" ${aria}>${rects}</svg>`;
  }

  /* ---------- Pages ---------- */

  const chapters = story.chapters || [];
  const pages = [{ kind: "cover" }, { kind: "contents" }];
  chapters.forEach((c) => pages.push({ kind: "chapter", c }));
  if (story.numbers) pages.push({ kind: "numbers" });
  if (story.finale) pages.push({ kind: "finale", c: story.finale });
  pages.push({ kind: "back" });
  const sources = story.sources || {};
  const UNIT = story.unit || "Chapter";

  let cur = 0, busy = false, wide = true, stageObserver = null;
  const pageState = new Map();
  let turnState = null, dragTurn = null;
  let swipeHintSeen = false;
  try { swipeHintSeen = localStorage.getItem("popup-storybook-swipe-hint") === "seen"; } catch (e) { /* storage blocked */ }
  function markSwipeHintSeen() {
    swipeHintSeen = true;
    try { localStorage.setItem("popup-storybook-swipe-hint", "seen"); } catch (e) { /* storage blocked */ }
  }

  /* ---------- Stage ---------- */

  function stageHTML(scene, id, lesson, extraClass = "") {
    if (!scene) return "";
    const pcs = (scene.pieces || []).map((p, i) => pieceHTML(p, i)).join("");
    const wallPcs = (scene.wall || []).map((p, i) => wallPieceHTML(p, i)).join("");
    const wingsCls = scene.wings === "low" ? " stage-wings-low" : "";
    const wingsHTML = scene.wings === "low" ? `<div class="stage-wing left" aria-hidden="true"></div><div class="stage-wing right" aria-hidden="true"></div>` : "";
    const surface = `--sky:${esc(sky(scene.sky))};--ground:${esc(ground(scene.ground))}`;
    return `<div class="stage-page"><div class="stage folded ${esc(extraClass)}${wingsCls}" data-stage="${esc(id)}" style="${surface}" role="img" aria-label="${esc(scene.alt || "")}">
      <div class="set">
        <div class="wall-hinge"><div class="wall">${wallPcs}</div></div>
        <div class="floor"></div>
        ${wingsHTML}
        ${pcs}
      </div>
      <div class="proscenium"></div>
      ${lesson ? lessonHTML(lesson) : ""}
      <div class="stage-hint">Move your pointer to look around</div>
    </div>${scene.caption ? `<div class="caption">${esc(scene.caption)}</div>` : ""}
      <div class="phone-page-cues" aria-label="Printed page turns"><button data-stage-prev>‹ Previous page</button><span data-swipe-hint hidden>Swipe the picture to turn the page</span><button data-stage-next>Next page ›</button></div>
    </div>`;
  }

  /* The lesson flap is part of the picture: a paper flap hinged along the top
     of the scene. Lift it and it swings up towards you; the lesson is printed
     on the card underneath. */
  function lessonHTML(f) {
    const label = f.label || "What I learned";
    const cover = f.cover && f.cover !== "LIFT" ? f.cover : label;
    return `<div class="lesson" data-lesson style="--flap:0">
      <div class="lesson-card" id="lesson-card"><span class="lesson-label">${esc(label)}</span><span class="lesson-text">${inline(f.text)}</span></div>
      <div class="lflap" role="button" tabindex="0" aria-expanded="false" aria-controls="lesson-card" aria-label="Lift the flap: ${esc(label)}">
        <div class="lf-front"><span class="lf-title">${esc(cover)}</span><span class="lf-cue" aria-hidden="true">Lift the flap <span class="up">↑</span></span></div>
        <div class="lf-back" aria-hidden="true"></div>
      </div></div>`;
  }

  function pieceHTML(p, i) {
    const depth = p.depth ?? 2;
    const z = p.z ?? (depth - 0.5) / 4;
    const scale = p.scale ?? 3;
    const gw = pieceGridWidth(p);
    const gh = p.image && IMG[p.image] ? 14 : (SPR[p.sprite] || [[""]]).length;
    const sw = (gw + 2) * scale;
    const sh = (gh + 2) * scale;
    const mountCls = p.mount === "box" ? "mount-box" : (p.mount === "vfold" ? "mount-vfold" : "");
    const cls = ["piece", p.bob ? "bob" : "", p.hidden ? "hidden-until" : "", mountCls].filter(Boolean).join(" ");
    const alt = p.alt ? spriteSVG(p.alt, { scale, remap: p.remap, flip: p.flip, cls: "alt" }) : "";
    const boxTop = p.mount === "box" ? `<div class="box-top" aria-hidden="true" style="width:calc(var(--u) * ${(sw * 0.92).toFixed(1)});height:calc(var(--u) * ${Math.max(6, scale * 3.2).toFixed(1)});bottom:calc(var(--u) * ${(sh * 0.82).toFixed(1)})"></div>` : "";
    const vfoldCrease = p.mount === "vfold" ? `<div class="vfold-crease" aria-hidden="true" style="height:calc(var(--u) * ${(sh * 0.92).toFixed(1)})"></div>` : "";
    const delay = p.delay ?? 80 + i * 90 + (1 - z) * 160;
    return `<div class="${cls}${p.lift ? " lifted" : ""}" data-id="${esc(p.id || "")}" data-z="${z}" data-x="${p.x ?? 50}" data-lift="${p.lift ?? 0}" style="left:${p.x ?? 50}%;bottom:calc(var(--u) * ${p.lift ?? 0});--delay:${Math.round(delay)}ms;--bobdelay:${(i * 0.37) % 2}s">
      <div class="shadow" style="width:calc(var(--u) * ${sw * 0.8});height:calc(var(--u) * ${Math.max(4, scale * 3)})"></div>
      ${feet(gw, sw, scale)}
      <div class="hinge">${boxTop}${vfoldCrease}<div class="mech">${pieceVisualSVG(p, { scale, remap: p.remap, flip: p.flip, cls: "main" })}${alt}</div></div>
    </div>`;
  }

  // Standing pieces sit on glued fold tabs. Wide furniture gets one under each side.
  function feet(w, sw, scale) {
    const h = `height:calc(var(--u) * ${Math.max(2.4, scale * 1.1)})`;
    if (w <= 20) return `<div class="foot" style="width:calc(var(--u) * ${Math.max(6, sw * 0.42)});${h}"></div>`;
    const fw = `width:calc(var(--u) * ${Math.max(6, sw * 0.18)});${h}`;
    return `<div class="foot" style="${fw};left:calc(var(--u) * ${-sw * 0.33})"></div><div class="foot" style="${fw};left:calc(var(--u) * ${sw * 0.33})"></div>`;
  }

  function wallPieceHTML(p, i) {
    const scale = p.scale ?? 2;
    const cls = ["piece", "wallpiece", p.twinkle ? "twinkle" : "", p.bob ? "bob" : "", p.hidden ? "hidden-until" : ""].join(" ");
    const alt = p.alt ? spriteSVG(p.alt, { scale, remap: p.remap, flip: p.flip, cut: p.cut !== false, cls: "alt" }) : "";
    return `<div class="${cls}" data-id="${esc(p.id || "")}" data-x="${p.x ?? 50}" data-y="${p.y ?? 20}" style="left:${(((p.x ?? 50) + 22) / 1.44).toFixed(2)}%;top:${p.y ?? 20}%;bottom:auto;--delay:${60 + i * 70}ms;--bobdelay:${(i * 0.53) % 2.4}s">
      <div class="hinge" style="translate:-50% -50%"><div class="mech">${pieceVisualSVG(p, { scale, remap: p.remap, flip: p.flip, cut: p.cut !== false, cls: "main" })}${alt}</div></div></div>`;
  }

  function layoutStage(stage) {
    const H = stage.clientHeight, W = stage.clientWidth;
    if (!H) return;
    const P = H * 1.7, D = H * 0.95, s = (P + D) / P;
    const finale = stage.classList.contains("finale-stage");
    stage.style.setProperty("--u", (H / (finale ? 126 : 150)).toFixed(3) + "px");
    stage.style.setProperty("--uw", (H / (finale ? 170 : 200)).toFixed(3) + "px");
    stage.style.perspective = P + "px";
    const y0 = -0.4 * H;
    stage.dataset.y0 = y0;
    stage.style.perspectiveOrigin = `50% ${y0}px`;
    const set = $(".set", stage);
    // On a phone the lesson card is tall next to the small picture. Shrink the whole set
    // into the space below the card, so nothing stands behind it.
    const lesP = $(".lesson", stage);
    const lessonBottom = lesP ? lesP.offsetTop + lesP.offsetHeight : 0;
    const lessonGap = H * 0.05;
    // The finale is a tall theatre rather than a picture under a lesson card.
    // Keep its V-fold and tiers large on phones, while leaving the normal pages unchanged.
    const fit = !wide && finale ? 0.9 : (!wide && lesP ? Math.max(0.25, 1 - (lessonBottom + lessonGap) / H) : 1);
    set.style.transformOrigin = "50% 100%";
    set.style.transform = fit < 1 ? `scale(${fit.toFixed(4)})` : "";
    stage.classList.toggle("fitted", fit < 1);
    const fl = $(".floor", stage);
    fl.style.height = D + "px";
    fl.style.left = (-(s - 1) / 2 - 0.3) * W + "px";
    fl.style.right = (-(s - 1) / 2 - 0.3) * W + "px";
    fl.style.transform = "rotateX(90deg)";
    const wz = `translateZ(${-D}px) scale(${s})`;
    const wh = $(".wall-hinge", stage);
    wh.style.setProperty("--wall-z", wz);
    wh.style.transform = stage.classList.contains("folded") ? "" : wz;
    wh.dataset.wz = wz;
    $$(".piece:not(.wallpiece)", stage).forEach((el) => {
      // x is given in screen space: spread deeper pieces outwards so perspective does not crowd them to the centre.
      const z = parseFloat(el.dataset.z), k = (P + z * D) / P;
      // Keep the whole cut-out on the page: clear of the gutter shade on the left and the page edge on the right.
      const half = (pieceWidth(el, H) * parseFloat(el.style.getPropertyValue("--grow") || 1)) / 2 / k / W * 100;
      const lo = 5 + half, hi = 98 - half;
      let x = parseFloat(el.dataset.x);
      x = lo > hi ? (lo + hi) / 2 : Math.min(hi, Math.max(lo, x));
      el.style.left = (50 + (x - 50) * k).toFixed(2) + "%";
      const lift = parseFloat(el.dataset.lift || 0);
      el.style.bottom = `calc(var(--u) * ${lift + (finale ? 7 : 0)})`;
      el.style.transform = `translateZ(${-z * D}px)`;
      el.classList.toggle("lifted", lift > 0);
      if (el.dataset.slotToX != null && !finale) {
        const hx = Math.min(hi, Math.max(lo, parseFloat(el.dataset.homeX ?? x)));
        const tx = Math.min(hi, Math.max(lo, parseFloat(el.dataset.slotToX)));
        const sx1 = 50 + (hx - 50) * k, sx2 = 50 + (tx - 50) * k;
        let slot = el._slot || (el.dataset.id && $(`[data-slot-for="${el.dataset.id}"]`, set));
        if (!slot) {
          slot = document.createElement("div");
          slot.className = "floor-slot";
          if (el.dataset.id) slot.dataset.slotFor = el.dataset.id;
          slot.setAttribute("aria-hidden", "true");
          set.insertBefore(slot, el);
        }
        el._slot = slot;
        const leftPct = Math.min(sx1, sx2) - 1.2, widthPct = Math.abs(sx2 - sx1) + 2.4;
        slot.style.left = leftPct.toFixed(2) + "%";
        slot.style.width = widthPct.toFixed(2) + "%";
        slot.style.transform = `translateY(50%) translateZ(${(-z * D).toFixed(1)}px) rotateX(90deg)`;
      }
    });
    $$(".finale-tier-platform", stage).forEach((platform) => {
      const z = parseFloat(platform.dataset.z || 0);
      const lift = parseFloat(platform.dataset.lift || 0);
      platform.style.bottom = `calc(var(--u) * ${lift + 7})`;
      platform.style.transform = `translateX(-50%) translateZ(${-z * D}px)`;
    });
    // Wall pieces: y is a fraction of the visible wall (stage top to the far edge of the floor).
    const far = y0 + (H - y0) / s;
    const les = $(".lesson", stage);
    const band = les ? Math.min(0.45, (les.offsetHeight + H * 0.03) / far) : 0;
    if (les) {
      // Perspective is scaled to the card and centred on the hinge. The bottom edge then follows
      // the paper projection instead of dipping below its shut line.
      const lh = les.offsetHeight;
      les.style.perspective = (10 * lh).toFixed(0) + "px";
      les.style.perspectiveOrigin = "50% 0px";
      stage.dataset.band = band;
    }
    $$(".piece.wallpiece", stage).forEach((el) => {
      const half = pieceWidth(el, H) / 2 / W * 100;
      let wx = parseFloat(el.dataset.x);
      wx = Math.min(98 - half, Math.max(5 + half, wx));
      el.style.left = ((wx + 22) / 1.44).toFixed(2) + "%";
      const t = band + (1 - band) * parseFloat(el.dataset.y) / 100;
      let Y = y0 + (t * far - y0) * s;
      // Never let a wall piece reach up behind the lesson card, whatever its size.
      if (lesP) {
        // Allow for the look-around: the eye moves up to 10% of the height, which shifts the wall by this much.
        const L = lesP.offsetTop + lesP.offsetHeight + 2 + 0.1 * H * (1 - 1 / s);
        // Y is the wall height before perspective. The phone fit scales it about the stage bottom,
        // then perspective puts the centre on screen at y0 + (H - (H - Y) * fit - y0) / s.
        const need = L + (pieceHeight(el, H) / 2) * fit;
        Y = Math.max(Y, H - (H - y0 - (need - y0) * s) / fit);
      }
      el.style.top = ((H - (H - Y) / s) / H * 100).toFixed(2) + "%";
    });
    void W;
  }

  function pieceHeight(el, H) {
    if (el._hH !== H) { const v = $(".mech > .main", el) || $(".mech > svg", el); el._h = v ? parseFloat(getComputedStyle(v).height) || 0 : 0; el._hH = H; }
    return el._h;
  }

  function pieceWidth(el, H) {
    // SVG elements have no offsetWidth. Read the laid-out width, which ignores transforms.
    if (el._wH !== H) { const v = $(".mech > .main", el) || $(".mech > svg", el); el._w = v ? parseFloat(getComputedStyle(v).width) || 0 : 0; el._wH = H; }
    return el._w;
  }

  function setStageOpen(stage, openness) {
    if (!stage) return;
    const open = clamp01(openness);
    stage.classList.add("turn-coupled");
    stage.classList.toggle("folded", open <= 0.001);
    stage.style.setProperty("--spread-open", open.toFixed(4));
    const finaleLayer = stage.closest(".finale-layer");
    if (finaleLayer) finaleLayer.style.setProperty("--spread-open", open.toFixed(4));
    stage.style.setProperty("--fold-angle", ((1 - open) * 88).toFixed(2) + "deg");
    stage.style.setProperty("--wall-fold-angle", ((1 - open) * 84).toFixed(2) + "deg");
  }

  function raise(stage) {
    if (!stage) return;
    layoutStage(stage);
    setStageOpen(stage, 1);
  }

  function fold(stage) {
    setStageOpen(stage, 0);
  }

  /* Look around: the mouse moves the viewer's eye, not the set. Moving the
     perspective origin gives true parallax, so near pieces slide more than far
     ones and nothing tilts or jumps. The eye eases toward its target every frame
     and drifts slowly on its own when the mouse is still or away. */
  const eye = { tx: 0, ty: 0, x: 0, y: 0, last: 0, raf: 0, held: false };
  const eyeControl = (target) => target && target.closest && target.closest(".tab, .lflap, .wheel");
  document.addEventListener("pointerdown", (e) => { if (eyeControl(e.target)) eye.held = true; }, true);
  document.addEventListener("pointerup", () => { eye.held = false; }, true);
  document.addEventListener("pointercancel", () => { eye.held = false; }, true);
  addEventListener("pointermove", (e) => {
    if (e.pointerType === "touch" || eye.held) return;
    const active = $(".page.right .stage");
    const st = e.target && e.target.closest ? e.target.closest(".stage") : null;
    if (!active || st !== active) {
      eye.tx = 0; eye.ty = 0; eye.last = performance.now();
      return;
    }
    const r = st.getBoundingClientRect();
    const nx = ((e.clientX - (r.left + r.width / 2)) / (r.width * 0.9));
    const ny = ((e.clientY - (r.top + r.height / 2)) / (r.height * 0.9));
    eye.tx = Math.max(-1, Math.min(1, nx));
    eye.ty = Math.max(-1, Math.min(1, ny));
    eye.last = performance.now();
  });
  document.addEventListener("pointerleave", () => {
    if (!eye.held) { eye.tx = 0; eye.ty = 0; eye.last = performance.now(); }
  });

  function parallax(stage) {
    if (reduce) return;
    cancelAnimationFrame(eye.raf);
    eye.tx = 0; eye.ty = 0; eye.x = 0; eye.y = 0; eye.last = 0; eye.held = false;
    const tick = (t) => {
      if (!stage.isConnected) return;
      if (!eye.held) {
        const idle = t - eye.last > 2500;
        const gx = idle ? Math.sin(t / 3100) * 0.28 : eye.tx;
        const gy = idle ? Math.sin(t / 4300) * 0.2 : eye.ty;
        eye.x += (gx - eye.x) * (idle ? 0.02 : 0.08);
        eye.y += (gy - eye.y) * (idle ? 0.02 : 0.08);
        const H = stage.clientHeight, y0 = parseFloat(stage.dataset.y0 || 0);
        const ox = 50 + eye.x * 18, oy = y0 + eye.y * H * 0.1;
        stage.style.perspectiveOrigin = `${ox.toFixed(2)}% ${oy.toFixed(1)}px`;
      }
      eye.raf = requestAnimationFrame(tick);
    };
    eye.raf = requestAnimationFrame(tick);
  }

  /* Paper mechanisms. A pull tab or flap has a travel from 0 to 1. Every effect
     on the page is a function of that travel, so the picture moves while you
     pull, stops when you stop, and runs backwards when you push. Effects take
     a window of the travel, from their order (or an explicit "at": [a, b]). */
  const clamp01 = (x) => Math.max(0, Math.min(1, x));
  const smooth = (x) => { x = clamp01(x); return x * x * (3 - 2 * x); };
  function windows(list) {
    const L = (list || []).map((f, k) => Object.assign({}, f, { d: f.delay ?? k * 120 }));
    const max = Math.max(0, ...L.map((f) => f.d));
    L.forEach((f) => {
      if (Array.isArray(f.at)) { f.a = f.at[0]; f.b = f.at[1]; }
      else { f.a = 0.06 + (max ? 0.5 * f.d / max : 0); f.b = Math.min(1, f.a + 0.42); }
      if (!(f.b > f.a)) f.b = f.a + 0.01;
    });
    return L;
  }
  function makeMech(stage, c) {
    const recs = [], byId = {};
    $$(".piece", stage).forEach((el) => {
      const r = { el, wall: el.classList.contains("wallpiece"), hidden: el.classList.contains("hidden-until"), upright: false, rendered: false, mech: $(".mech", el),
        main: $(".mech > .main", el), alt: $(".mech > .alt", el), home: { x: +el.dataset.x, z: +(el.dataset.z || 0), lift: +(el.dataset.lift || 0) } };
      recs.push(r);
      if (el.dataset.id) byId[el.dataset.id] = r;
    });
    const lists = { tab: windows((c.tab || {}).effects), flap: windows((c.flap || {}).effects) };
    ["tab", "flap"].forEach((k) => lists[k].forEach((f) => {
      const r = byId[f.piece];
      if (r && !r.wall && f.fx === "move" && f.to && f.to.x != null && Math.abs(f.to.x - r.home.x) >= 6 && !r.home.lift && !f.to.lift && f.to.depth == null && f.to.z == null) {
        r.el.dataset.homeX = r.home.x;
        r.el.dataset.slotToX = f.to.x;
      }
    }));
    const v = { tab: 0, flap: 0 };
    const CH = ["dim", "rise", "glow", "flip", "swap"];
    function render() {
      recs.forEach((r) => { r.s = { vis: r.hidden ? 0 : 1, hop: 0, wob: 0, x: r.home.x, z: r.home.z, lift: r.home.lift, grow: 1 }; CH.forEach((k) => { r.s[k] = 0; }); });
      ["tab", "flap"].forEach((k) => lists[k].forEach((f) => {
        const r = byId[f.piece];
        if (!r) return;
        const s = r.s, p = smooth((v[k] - f.a) / (f.b - f.a)), sg = f.off ? -1 : 1;
        if (f.fx === "show") s.vis += sg * p;
        else if (f.fx === "hide") s.vis -= sg * p;
        else if (f.fx === "hop") s.hop += Math.sin(p * Math.PI);
        else if (f.fx === "wobble") s.wob += Math.sin(p * Math.PI * 3) * Math.sin(p * Math.PI);
        else if (f.fx === "move" && f.to) {
          const t = f.to, tz = t.z ?? (t.depth != null ? (t.depth - 0.5) / 4 : null);
          if (t.x != null) s.x += (t.x - s.x) * p;
          if (tz != null) s.z += (tz - s.z) * p;
          if (t.lift != null) s.lift += (t.lift - s.lift) * p;
          if (t.grow != null) s.grow += (t.grow - s.grow) * p;
        } else if (CH.includes(f.fx)) s[f.fx] += sg * p;
      }));
      recs.forEach((r) => {
        const s = r.s, vis = clamp01(s.vis), dim = clamp01(s.dim), glow = clamp01(s.glow), swap = clamp01(s.swap);
        if (r.hidden && !r.wall) {
          const upright = vis >= 0.875;
          if (r.rendered && upright !== r.upright) sfx("piece-snap");
          r.upright = upright;
        }
        r.rendered = true;
        r.el.style.setProperty("--vis", vis.toFixed(3));
        if (!r.wall) {
          r.el.dataset.x = s.x; r.el.dataset.z = s.z; r.el.dataset.lift = s.lift;
          r.el.style.setProperty("--grow", s.grow.toFixed(3));
        }
        // Hidden paper stays opaque. Floor pieces lie on the floor; wall pieces lie against the wall until their window stands them up.
        const unfold = r.wall ? `rotateY(${((1 - vis) * 90).toFixed(1)}deg)` : `rotateX(${((1 - vis) * 90).toFixed(1)}deg)`;
        r.mech.style.transform = `translateY(calc(var(--u) * ${(-6 * s.hop).toFixed(2)})) rotate(${(8 * s.wob).toFixed(2)}deg) ${unfold} rotateY(${(180 * clamp01(s.flip)).toFixed(1)}deg) scaleY(${(1 + 0.2 * clamp01(s.rise)).toFixed(3)})`;
        r.mech.style.opacity = "1";
        r.mech.style.filter = dim || glow ? `brightness(${(1 - 0.36 * dim + 0.12 * glow).toFixed(3)}) saturate(${(1 - 0.45 * dim).toFixed(3)})${glow ? ` drop-shadow(0 0 calc(var(--u) * ${(4 * glow).toFixed(2)}) rgba(255,176,0,${(0.9 * glow).toFixed(2)}))` : ""}` : "";
        if (r.alt) { r.alt.style.opacity = swap.toFixed(3); r.main.style.opacity = (1 - swap).toFixed(3); }
      });
      layoutStage(stage);
    }
    render();
    return { set(k, x) { v[k] = clamp01(x); render(); }, get: (k) => v[k] };
  }
  // Move a control smoothly to a target, as if your finger did it.
  const anims = {};
  function animateTo(key, get, set, to, ms = 850, done = null) {
    cancelAnimationFrame(anims[key]);
    const from = get();
    if (reduce || from === to) { set(to); if (done) done(); return; }
    const t0 = performance.now(), dur = ms * Math.max(0.35, Math.abs(to - from));
    const step = (t) => {
      const k = Math.min(1, (t - t0) / dur), e = k < 0.5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2;
      set(from + (to - from) * e);
      if (k < 1) anims[key] = requestAnimationFrame(step);
      else if (done) done();
    };
    anims[key] = requestAnimationFrame(step);
  }

  /* ---------- Sound: synthesised paper noises, off by default ---------- */

  const SOUND_LIMITS = {
    oneShotHz: 2800,
    repeatedHz: 2200,
    movementHz: 2600,
  };
  const configuredVolume = Number((story.sound || {}).volume ?? 1);
  const soundVolume = Number.isFinite(configuredVolume) ? clamp01(configuredVolume) : 1;
  const audio = { on: false, gestureUntil: 0, ctx: null, master: null, noise: null, streams: {}, riseTimers: [] };
  try { audio.on = localStorage.getItem("popup-storybook-sound") === "on"; } catch (e) { /* storage blocked */ }

  function markAudioGesture() {
    audio.gestureUntil = performance.now() + 1000;
    if (audio.on && audio.ctx && audio.ctx.state === "suspended") {
      try { const p = audio.ctx.resume(); if (p && p.catch) p.catch(() => {}); } catch (e) { /* Web Audio unavailable */ }
    }
  }
  document.addEventListener("pointerdown", markAudioGesture, true);
  document.addEventListener("keydown", markAudioGesture, true);
  document.addEventListener("touchstart", markAudioGesture, { capture: true, passive: true });

  function audioContext() {
    if (!audio.on || soundVolume <= 0) return null;
    try {
      const mayResume = performance.now() <= audio.gestureUntil;
      if (!audio.ctx) {
        if (!mayResume) return null;
        const Audio = window.AudioContext || window.webkitAudioContext;
        if (!Audio) return null;
        audio.ctx = new Audio();
        audio.master = audio.ctx.createGain();
        audio.master.gain.value = soundVolume;
        audio.master.connect(audio.ctx.destination);
      }
      if (audio.ctx.state === "suspended" && mayResume) {
        const p = audio.ctx.resume(); if (p && p.catch) p.catch(() => {});
      }
      if (audio.ctx.state === "suspended" && !mayResume) return null;
      if (!audio.noise) {
        const b = audio.ctx.createBuffer(1, audio.ctx.sampleRate * 0.8, audio.ctx.sampleRate), d = b.getChannelData(0);
        for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
        audio.noise = b;
      }
      return audio.ctx;
    } catch (e) { return null; }
  }

  function sfx(kind, level = 1) {
    const ctx = audioContext();
    if (!ctx) return;
    try {
      const t = ctx.currentTime;
      const env = (node, peak, attack, len, delay = 0) => {
        const g = ctx.createGain(), at = t + delay;
        g.gain.setValueAtTime(0.0001, at);
        g.gain.linearRampToValueAtTime(Math.max(0.0001, peak * level), at + attack);
        g.gain.exponentialRampToValueAtTime(0.0001, at + len);
        node.connect(g); g.connect(audio.master); return g;
      };
      const rustle = (freq, q, peak, len, rate = 1, delay = 0, ceiling = SOUND_LIMITS.oneShotHz) => {
        const src = ctx.createBufferSource(); src.buffer = audio.noise; src.playbackRate.value = rate;
        const f = ctx.createBiquadFilter(); f.type = "bandpass"; f.frequency.value = Math.min(freq, ceiling); f.Q.value = q;
        src.connect(f); env(f, peak, 0.012, len, delay); src.start(t + delay); src.stop(t + delay + len + 0.04);
      };
      const pop = (from, to, peak, len, delay = 0) => {
        const o = ctx.createOscillator(); o.type = "triangle"; o.frequency.setValueAtTime(from, t + delay);
        o.frequency.exponentialRampToValueAtTime(to, t + delay + len); env(o, peak, 0.004, len, delay);
        o.start(t + delay); o.stop(t + delay + len + 0.04);
      };
      if (kind === "page-turn") {
        rustle(1250, 0.65, 0.11, 0.46, 0.78);
        rustle(2700, 1.1, 0.045, 0.12, 1.2, 0.08);
        rustle(2200, 1.2, 0.035, 0.1, 1.35, 0.17);
      }
      if (kind === "slider-click") rustle(2500, 1.25, 0.045, 0.22, 1.05, 0, SOUND_LIMITS.repeatedHz);
      if (kind === "card-tap") pop(145, 92, 0.035, 0.075);
      if (kind === "flap-open") { rustle(1750, 1.1, 0.05, 0.12, 1.15); pop(230, 310, 0.022, 0.065); }
      if (kind === "flap-close") { rustle(900, 0.7, 0.045, 0.15, 0.8); pop(125, 72, 0.04, 0.1); }
      if (kind === "rise-pop") pop(190, 260, 0.011, 0.065);
      if (kind === "book-open") { rustle(1150, 0.8, 0.055, 0.2, 0.82); pop(170, 120, 0.022, 0.08); }
      if (kind === "book-riffle") {
        rustle(2400, 1.2, 0.04, 0.1, 1.3, 0, SOUND_LIMITS.repeatedHz);
        rustle(1900, 1, 0.025, 0.08, 1.5, 0.055, SOUND_LIMITS.repeatedHz);
      }
      if (kind === "book-close") { rustle(850, 0.75, 0.04, 0.16, 0.75); pop(120, 78, 0.03, 0.09); }
      if (kind === "wheel-click") { rustle(3900, 3.2, 0.026, 0.038, 1.4, 0, SOUND_LIMITS.repeatedHz); pop(260, 205, 0.012, 0.035); }
      if (kind === "piece-snap") pop(210, 285, 0.012, 0.055);
    } catch (e) { /* A failed sound must never stop the book. */ }
  }

  function movementSound(kind, speed) {
    const ctx = audioContext();
    if (!ctx) return;
    try {
      let stream = audio.streams[kind];
      if (!stream) {
        const src = ctx.createBufferSource(), filter = ctx.createBiquadFilter(), gain = ctx.createGain();
        src.buffer = audio.noise; src.loop = true; src.playbackRate.value = kind === "slider" ? 0.82 : 0.68;
        filter.type = "bandpass"; filter.Q.value = kind === "slider" ? 1.2 : 0.72;
        gain.gain.value = 0.0001; src.connect(filter); filter.connect(gain); gain.connect(audio.master); src.start();
        stream = audio.streams[kind] = { src, filter, gain, timer: 0 };
      }
      const v = Math.min(1, Math.max(0, speed));
      const peak = kind === "slider" ? 0.008 + v * 0.052 : 0.004 + v * 0.024;
      const rawFreq = kind === "slider" ? 900 + v * 3100 : 650 + v * 1700;
      const freq = Math.min(SOUND_LIMITS.movementHz, rawFreq);
      stream.gain.gain.cancelScheduledValues(ctx.currentTime);
      stream.gain.gain.setTargetAtTime(peak, ctx.currentTime, 0.018);
      stream.filter.frequency.setTargetAtTime(freq, ctx.currentTime, 0.025);
      clearTimeout(stream.timer);
      stream.timer = setTimeout(() => silenceMovement(kind), 82);
    } catch (e) { /* keep the paper mechanism working */ }
  }

  function silenceMovement(kind, immediate = false) {
    const stream = audio.streams[kind];
    if (!stream || !audio.ctx) return;
    clearTimeout(stream.timer);
    try {
      const t = audio.ctx.currentTime;
      stream.gain.gain.cancelScheduledValues(t);
      stream.gain.gain.setTargetAtTime(0.0001, t, immediate ? 0.001 : 0.018);
    } catch (e) { /* ignore */ }
  }

  function riseSounds(stage) {
    audio.riseTimers.forEach(clearTimeout); audio.riseTimers = [];
    if (!stage) return;
    $$(".piece:not(.wallpiece):not(.hidden-until)", stage).forEach((piece) => {
      const delay = parseFloat(piece.style.getPropertyValue("--delay")) || 0;
      audio.riseTimers.push(setTimeout(() => sfx("rise-pop"), delay));
    });
  }

  function setSound(on) {
    audio.on = !!on;
    try { localStorage.setItem("popup-storybook-sound", audio.on ? "on" : "off"); } catch (e) { /* ignore */ }
    const b = $("[data-sound]");
    if (b) { b.setAttribute("aria-pressed", String(audio.on)); b.textContent = audio.on ? "Sound on" : "Sound off"; }
    if (!audio.on) {
      silenceMovement("slider", true); silenceMovement("flap", true);
      audio.riseTimers.forEach(clearTimeout); audio.riseTimers = [];
      if (audio.master && audio.ctx) {
        try { audio.master.gain.setValueAtTime(0, audio.ctx.currentTime); } catch (e) { /* ignore */ }
      }
    } else if (audio.master && audio.ctx) {
      try { audio.master.gain.setValueAtTime(soundVolume, audio.ctx.currentTime); } catch (e) { /* ignore */ }
    }
  }

  /* ---------- Left pages ---------- */

  const head = (kicker, title, when = "") => `<div class="kicker"><span>${esc(kicker)}</span>${when ? `<span class="when">${esc(when)}</span>` : ""}</div>
      <h2 class="title">${esc(title)}</h2>`;

  function tabHTML(c, key) {
    if (!c.tab) return "";
    const label = esc(c.tab.label || "The trial");
    return `<div class="slider" data-pull style="--pull:0">
      <div class="window" aria-live="polite"><div class="strip" id="strip-${esc(key)}">
        <div class="seg trial"><span class="strip-label">${label}</span><span>${inline(c.tab.text)}</span></div>
        <div class="seg lead" aria-hidden="true"><span class="strip-label">${label}</span><span class="lead-hint">${esc(c.tab.hint || "Pull the tab")}</span></div>
      </div></div>
      <div class="track"><span class="groove" aria-hidden="true"></span>
        <button class="tab" role="slider" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0" aria-controls="strip-${esc(key)}" aria-label="Pull tab: ${label}"><span class="grip" aria-hidden="true"></span>Pull</button></div>
      <div class="ink-cue" aria-hidden="true"><span class="wide-only">Pull the tab towards the picture</span><span class="narrow-only">Slide the tab to the right</span> <span class="arrow">→</span></div>
    </div>`;
  }

  function bookletHTML(c) {
    const count = (c.facts || []).length;
    return count ? `<button class="booklet" data-facts aria-haspopup="dialog" aria-label="Open the fact booklet: ${count} ${count === 1 ? "fact" : "facts"} with sources">
      <span class="bk-cover"><span class="bk-n">${count}</span><span class="bk-t">${count === 1 ? "fact" : "facts"} from the record</span><span class="bk-cue">Open</span></span></button>` : "";
  }

  function chapterLeft(c, n) {
    const open = c.status === "open";
    const prose = (c.text || []).map((p) => `<p>${inline(p)}</p>`).join("");
    const nfacts = (c.facts || []).length;
    return `<div class="text${open ? " open" : ""}${nfacts ? " has-booklet" : ""}">${bookletHTML(c)}
      ${head(UNIT + " " + c.number, c.title, c.when)}
      <div class="prose${open ? "" : " lead"}">${prose}${open && c.stamp ? `<span class="stamp">${esc(c.stamp)}</span>` : ""}</div>
      <div class="gadgets">${tabHTML(c, c.number)}</div>
    </div>`;
  }

  function finalePieceHTML(piece, index) {
    const token = (value) => String(value || "").toLowerCase().replace(/[^a-z0-9_-]/g, "");
    const classes = [
      piece.finaleRole ? `finale-role-${token(piece.finaleRole)}` : "finale-role-cast",
      piece.mount ? `finale-mount-${token(piece.mount)}` : "",
      piece.tier ? `finale-tier-${token(piece.tier)}` : "",
    ].filter(Boolean).join(" ");
    return pieceHTML(piece, index).replace('class="piece', `class="piece ${classes}`);
  }

  function finaleStructureHTML(piece) {
    if (!piece) return "";
    const scale = piece.scale ?? 2.2;
    return `<div class="finale-structure-piece finale-role-structure finale-mount-vfold" data-id="${esc(piece.id || "finale_structure")}" style="left:${piece.x ?? 50}%;--delay:${piece.delay ?? 40}ms">
      <div class="hinge"><div class="mech">${spriteSVG(piece.sprite, { scale, remap: piece.remap, flip: piece.flip, cls: "main" })}</div></div>
    </div>`;
  }

  function finalePlatformsHTML(scene) {
    const byTier = new Map();
    (scene.pieces || []).filter((piece) => piece.finaleRole === "cast" && piece.tier).forEach((piece) => {
      if (!byTier.has(piece.tier)) byTier.set(piece.tier, []);
      byTier.get(piece.tier).push(piece);
    });
    const tiers = [...byTier.keys()].sort((a, b) => b - a);
    const count = tiers.length;
    return tiers.map((tier, index) => {
      const pieces = byTier.get(tier);
      const lift = pieces.reduce((sum, piece) => sum + (piece.lift || 0), 0) / pieces.length;
      const z = pieces.reduce((sum, piece) => sum + (piece.z ?? ((piece.depth ?? 2) - 0.5) / 4), 0) / pieces.length;
      const span = count > 1 ? 62 + (34 * index) / (count - 1) : 90;
      return `<div class="finale-platform finale-tier-platform finale-tier-platform-${tier}" data-tier="${tier}" data-lift="${lift}" data-z="${z}" style="--platform-span:${span.toFixed(1)}%;--delay:${260 + index * 170}ms">
        <span class="finale-platform-top"></span><span class="finale-platform-front"></span>
      </div>`;
    }).join("");
  }

  function finaleLessonHTML(f) {
    const label = f.label || "Inside the structure";
    const cover = f.cover && f.cover !== "LIFT" ? f.cover : label;
    return `<div class="lesson finale-lesson" data-lesson style="--flap:0">
      <div class="finale-message-card" id="finale-message-card"><span class="lesson-label">${esc(label)}</span><span class="lesson-text">${inline(f.text)}</span></div>
      <div class="lflap" role="button" tabindex="0" aria-expanded="false" aria-controls="finale-message-card" aria-label="Lift the flap: ${esc(label)}">
        <div class="lf-front"><span class="lf-title">${esc(cover)}</span><span class="lf-cue" aria-hidden="true">Lift the flap <span class="up">↑</span></span></div>
        <div class="lf-back" aria-hidden="true"></div>
      </div></div>`;
  }

  function finaleStageHTML(finale) {
    const scene = finale.scene || {};
    const structure = (scene.pieces || []).find((piece) => piece.finaleRole === "structure");
    const pieces = (scene.pieces || []).filter((piece) => piece !== structure).map((piece, index) => finalePieceHTML(piece, index)).join("");
    const wallPieces = (scene.wall || []).map((piece, index) => wallPieceHTML(piece, index)).join("");
    return `<div class="stage-page"><div class="stage folded finale-stage" data-stage="finale" style="--sky:${sky(scene.sky)};--ground:${ground(scene.ground)}" role="group" aria-label="${esc(scene.alt || "Finale pop-up scene")}">
      <div class="set">
        <div class="wall-hinge"><div class="wall">${wallPieces}</div></div>
        <div class="floor"></div>
        <div class="finale-paper-rig" aria-hidden="true">
          <div class="finale-wing finale-wing-left"></div><div class="finale-wing finale-wing-right"></div>
          <div class="finale-low-layer finale-low-layer-left"></div><div class="finale-low-layer finale-low-layer-right"></div>
          ${finalePlatformsHTML(scene)}
        </div>
        ${finaleStructureHTML(structure)}
        ${pieces}
      </div>
      <div class="proscenium"></div>
      ${finale.flap ? finaleLessonHTML(finale.flap) : ""}
      <div class="stage-hint">move to look around</div>
    </div>${scene.caption ? `<div class="caption">${esc(scene.caption)}</div>` : ""}</div>`;
  }

  function finaleHTML(finale) {
    const prose = (finale.text || []).map((p) => `<p>${inline(p)}</p>`).join("");
    return `<div class="finale-layer" data-finale>
      ${finaleStageHTML(finale)}
      <section class="finale-banner${(finale.facts || []).length ? " has-booklet" : ""}">
        <span class="finale-banner-tail left" aria-hidden="true"></span><span class="finale-banner-tail right" aria-hidden="true"></span>
        <div class="finale-banner-paper">${bookletHTML(finale)}
          ${head(finale.kicker || "Finale", finale.title)}
          <div class="finale-copy">${prose}</div>
          <div class="gadgets">${tabHTML(finale, "finale")}</div>
        </div>
      </section>
      <div class="finale-fold" aria-hidden="true"></div>
    </div>`;
  }

  function contentsLeft() {
    const t = story.contents || {};
    const items = chapters.map((c, i) => `<li class="${c.status === "open" ? "open" : ""}"><button data-go="${i + 2}"><span class="n">${c.number}</span><span class="t">${esc(c.title)}</span><span class="w">${esc(c.when || "")}</span></button></li>`).join("");
    const extras = [];
    if (story.numbers) extras.push(`<li><button data-go="${pages.findIndex((p) => p.kind === "numbers")}"><span class="n">#</span><span class="t">${esc(story.numbers.title || "The numbers")}</span><span class="w"></span></button></li>`);
    if (story.finale) extras.push(`<li><button data-go="${pages.findIndex((p) => p.kind === "finale")}"><span class="n">★</span><span class="t">${esc(story.finale.title || "Finale")}</span><span class="w"></span></button></li>`);
    return `<div class="text">${head(t.kicker || "Inside", t.title || "Contents")}
      ${t.intro ? `<div class="prose" style="flex:none"><p>${inline(t.intro)}</p></div>` : ""}
      <ol class="toc">${items}${extras.join("")}</ol></div>`;
  }

  function numbersLeft() {
    const nb = story.numbers;
    const st = (nb.stats || []).map((s) => `<div class="stat">${textSVG(s.value, "#c2410c")}<div class="l">${esc(s.label)}</div></div>`).join("");
    return `<div class="text">${head(nb.kicker || "By the numbers", nb.title || "The numbers")}
      ${nb.intro ? `<div class="prose" style="flex:none"><p>${inline(nb.intro)}</p></div>` : ""}
      <div class="stats">${st}</div></div>`;
  }

  function backLeft() {
    const b = story.back || {};
    return `<div class="text">${head(b.kicker || "The end", b.title || "Thank you")}
      <div class="prose">${(b.text || []).map((p) => `<p>${inline(p)}</p>`).join("")}
      <p style="font-family:var(--ui);font-size:.7em;color:var(--ink-soft)">${esc(story.colophon || "")}</p></div></div>`;
  }

  /* ---------- Volvelle ---------- */

  function volvelleHTML() {
    const months = story.numbers.months || [];
    const N = months.length || 1, step = 360 / N;
    const cols = ["#ffd9b0", "#cfeeff", "#ffe3ef", "#d9f5d0", "#efe3c6", "#e6dcf5"];
    const sect = months.map((m, i) => {
      const a0 = (i - 0.5) * step, a1 = (i + 0.5) * step;
      const p = (a, r) => [50 + r * Math.sin((a * Math.PI) / 180), 50 - r * Math.cos((a * Math.PI) / 180)];
      const [x0, y0] = p(a0, 48), [x1, y1] = p(a1, 48);
      const lab = `<text x="50" y="8.6" text-anchor="middle" font-family="Iowan Old Style, Palatino, Georgia, serif" font-size="5.2" font-weight="700" fill="#241f2e">${esc(m.label)}</text>`;
      return `<path d="M50 50 L${x0.toFixed(2)} ${y0.toFixed(2)} A48 48 0 0 1 ${x1.toFixed(2)} ${y1.toFixed(2)} Z" fill="${cols[i % cols.length]}" stroke="#d9c9a3" stroke-width=".4"/>
        <g transform="rotate(${i * step} 50 50)">${lab}</g>`;
    }).join("");
    const a = step * 0.42, r1 = 39.5, r2 = 48.5;
    const pt = (ang, r) => `${(50 + r * Math.sin((ang * Math.PI) / 180)).toFixed(2)} ${(50 - r * Math.cos((ang * Math.PI) / 180)).toFixed(2)}`;
    const cover = `<path fill-rule="evenodd" fill="#2f9e8f" d="M50 1.5 A48.5 48.5 0 1 1 49.99 1.5 Z M${pt(-a, r1)} A${r1} ${r1} 0 0 1 ${pt(a, r1)} L${pt(a, r2)} A${r2} ${r2} 0 0 0 ${pt(-a, r2)} Z"/>
      <circle cx="50" cy="50" r="35" fill="#fffaf0"/><circle cx="50" cy="50" r="2.2" fill="#c2410c"/><circle cx="50" cy="50" r="33.5" fill="none" stroke="#d9c9a3" stroke-dasharray="1.2 1.2" stroke-width=".5"/>`;
    const notches = Array.from({ length: 12 }, (_, k) => {
      const ang = (k * 30 * Math.PI) / 180;
      const nx = (50 + 49.2 * Math.cos(ang)).toFixed(2), ny = (50 + 49.2 * Math.sin(ang)).toFixed(2);
      return `<circle cx="${nx}" cy="${ny}" r="2.6" fill="black"/>`;
    }).join("");
    return `<div class="volvelle"><div class="wheel-wrap wheel-notch-rim">
        <div class="wheel" data-wheel style="transform:rotate(0deg)"><svg viewBox="0 0 100 100" aria-hidden="true"><defs><mask id="wheel-rim-notch"><rect width="100" height="100" fill="white"/>${notches}</mask></defs><g mask="url(#wheel-rim-notch)"><circle cx="50" cy="50" r="49.5" fill="#fffaf0" stroke="#bfae86" stroke-width=".8"/>${sect}</g></svg></div>
        <div class="wheel-cover"><svg viewBox="0 0 100 100" aria-hidden="true">${cover}</svg></div>
        <div class="wheel-readout" aria-live="polite" style="top:30%"></div>
      </div>
      <div class="wheel-btns"><button data-spin="-1" aria-label="Previous month">↺</button><span>${esc(story.numbers.wheelHint || "Turn the wheel")}</span><button data-spin="1" aria-label="Next month">↻</button></div></div>`;
  }

  function bindWheel(root) {
    const wheel = $("[data-wheel]", root);
    if (!wheel) return;
    const months = story.numbers.months || [];
    const N = months.length || 1, step = 360 / N;
    let idx = 0, angle = 0;
    const out = $(".wheel-readout", root);
    const show = () => {
      const m = months[((idx % N) + N) % N] || {};
      out.innerHTML = `<div class="m" style="font-size:.7em;opacity:.6">${esc(story.numbers.wheelTitle || "")}</div><div class="v">${(m.lines || []).map(esc).join("<br>")}</div>`;
    };
    const setA = (a, anim = true) => { wheel.style.transition = anim ? "" : "none"; wheel.style.transform = `rotate(${a}deg)`; };
    const snap = () => { idx = Math.round(-angle / step); angle = -idx * step; setA(angle); show(); };
    $$("[data-spin]", root).forEach((b) => b.addEventListener("click", () => { idx += +b.dataset.spin; angle = -idx * step; setA(angle); show(); sfx("wheel-click"); }));
    let drag = null;
    wheel.addEventListener("pointerdown", (e) => {
      const r = wheel.getBoundingClientRect();
      const c = [r.left + r.width / 2, r.top + r.height / 2];
      drag = { c, lastA: Math.atan2(e.clientY - c[1], e.clientX - c[0]), detent: Math.round(-angle / step) };
      try { wheel.setPointerCapture(e.pointerId); } catch (err) { /* synthetic pointer */ }
    });
    wheel.addEventListener("pointermove", (e) => {
      if (!drag) return;
      const a = Math.atan2(e.clientY - drag.c[1], e.clientX - drag.c[0]);
      let delta = a - drag.lastA;
      if (delta > Math.PI) delta -= Math.PI * 2;
      if (delta < -Math.PI) delta += Math.PI * 2;
      angle += (delta * 180) / Math.PI; drag.lastA = a; setA(angle, false);
      const detent = Math.round(-angle / step);
      for (let i = 0; i < Math.abs(detent - drag.detent); i++) sfx("wheel-click");
      drag.detent = detent;
    });
    const end = () => { if (drag) { drag = null; snap(); } };
    wheel.addEventListener("pointerup", end); wheel.addEventListener("pointercancel", end);
    show();
  }

  /* ---------- Gadgets ---------- */

  function bindGadgets(book, c, mech) {
    const slider = $(".page.left [data-pull], .finale-layer [data-pull]", book);
    if (slider && mech) {
      const tab = $(".tab", slider), track = $(".track", slider);
      const state = pageState.get(cur) || { tab: 0 };
      pageState.set(cur, state);
      const set = (x) => {
        x = clamp01(x); mech.set("tab", x); state.tab = x;
        slider.style.setProperty("--pull", x.toFixed(4));
        tab.setAttribute("aria-valuenow", Math.round(x * 100));
        tab.setAttribute("aria-valuetext", x > 0.98 ? "Pulled all the way" : x < 0.02 ? "Pushed in" : `${Math.round(x * 100)}% pulled`);
      };
      const get = () => mech.get("tab");
      let start = null, moved = false, atEnd = false;
      const travel = () => Math.max(1, track.clientWidth - tab.offsetWidth);
      const pointerValue = (e) => start.v + (e.clientX - start.x) / travel();
      set(state.tab || 0);
      tab.addEventListener("pointerdown", (e) => {
        cancelAnimationFrame(anims.tab);
        start = { x: e.clientX, v: get(), lastX: e.clientX, lastT: e.timeStamp || performance.now() };
        moved = false; atEnd = start.v <= 0.001 || start.v >= 0.999; slider.classList.add("dragging");
        try { tab.setPointerCapture(e.pointerId); } catch (err) { /* synthetic pointer */ }
      });
      tab.addEventListener("pointermove", (e) => {
        if (!start) return;
        const raw = pointerValue(e);
        const now = e.timeStamp || performance.now(), dt = Math.max(1, now - start.lastT);
        movementSound("slider", Math.abs(e.clientX - start.lastX) / dt / 1.2);
        start.lastX = e.clientX; start.lastT = now;
        if (!moved && Math.abs(e.clientX - start.x) > 3) moved = true;
        const end = raw >= 1 || raw <= 0;
        if (end && !atEnd && moved) sfx("card-tap");
        atEnd = end;
        set(raw);
      });
      const up = (e) => {
        if (!start) return;
        if (moved && Number.isFinite(e.clientX)) set(pointerValue(e));
        slider.classList.remove("dragging"); start = null; silenceMovement("slider");
        if (!moved) {
          const target = get() < 0.5 ? 1 : 0;
          sfx("slider-click"); animateTo("tab", get, set, target, 1100, () => sfx("card-tap"));
        }
      };
      tab.addEventListener("pointerup", up); tab.addEventListener("pointercancel", up);
      tab.addEventListener("keydown", (e) => {
        const k = e.key, step = { ArrowRight: 0.1, ArrowUp: 0.1, ArrowLeft: -0.1, ArrowDown: -0.1 }[k];
        if (step) {
          e.preventDefault(); const before = get(); sfx("slider-click", 0.55); set(before + step);
          if (before > 0 && before < 1 && (get() <= 0 || get() >= 1)) sfx("card-tap");
        }
        else if (k === "Home" || k === "End") { e.preventDefault(); cancelAnimationFrame(anims.tab); sfx("slider-click"); set(k === "End" ? 1 : 0); sfx("card-tap"); }
        else if (k === "Enter" || k === " ") { e.preventDefault(); const target = get() < 0.5 ? 1 : 0; sfx("slider-click"); animateTo("tab", get, set, target, 1100, () => sfx("card-tap")); }
      });
    }
    const lesson = $(".page.right [data-lesson]", book);
    if (lesson && mech) {
      const flap = $(".lflap", lesson);
      const maxFlapAngle = 82 * Math.PI / 180;
      const minProjection = Math.cos(maxFlapAngle);
      const set = (x) => { x = clamp01(x); mech.set("flap", x); lesson.style.setProperty("--flap", x.toFixed(4)); flap.setAttribute("aria-expanded", String(x > 0.5)); lesson.classList.toggle("up", x > 0.02); lesson.classList.toggle("past", x > 0.93); };
      const get = () => mech.get("flap");
      let start = null, moved = false;
      const pointerValue = (clientY) => {
        const projection = Math.max(minProjection, Math.min(1, start.projection + (clientY - start.y) / start.length));
        return clamp01(Math.acos(projection) / maxFlapAngle);
      };
      flap.addEventListener("pointerdown", (e) => {
        cancelAnimationFrame(anims.flap);
        const value = get();
        start = { y: e.clientY, v: value, projection: Math.cos(value * maxFlapAngle), length: Math.max(1, flap.offsetHeight), lastY: e.clientY, lastT: e.timeStamp || performance.now() };
        moved = false; lesson.classList.add("dragging");
        try { flap.setPointerCapture(e.pointerId); } catch (err) { /* synthetic pointer */ }
      });
      flap.addEventListener("pointermove", (e) => {
        if (!start) return;
        const dy = e.clientY - start.y, now = e.timeStamp || performance.now(), dt = Math.max(1, now - start.lastT);
        const next = pointerValue(e.clientY);
        movementSound("flap", Math.abs(e.clientY - start.lastY) / dt / 1.1);
        start.lastY = e.clientY; start.lastT = now;
        if (!moved && Math.abs(dy) > 3) { moved = true; if (next > start.v) sfx("flap-open"); }
        set(next);
      });
      const up = () => {
        if (!start) return;
        lesson.classList.remove("dragging"); const was = start.v; start = null; silenceMovement("flap");
        // A flap lifted past its balance point stays up. Below it, it falls shut.
        const target = moved ? (get() > 0.35 ? 1 : 0) : (was < 0.5 ? 1 : 0);
        if (!moved && target === 1) sfx("flap-open");
        animateTo("flap", get, set, target, moved ? 600 : 850, target === 0 ? () => sfx("flap-close") : null);
      };
      flap.addEventListener("pointerup", up); flap.addEventListener("pointercancel", up);
      flap.addEventListener("keydown", (e) => {
        if (e.key === "Escape") {
          if (get() > 0) {
            e.preventDefault();
            animateTo("flap", get, set, 0, 850, () => sfx("flap-close"));
          }
        } else if (e.key === "Enter" || e.key === " ") {
          e.preventDefault(); const target = get() < 0.5 ? 1 : 0;
          if (target === 1) sfx("flap-open");
          animateTo("flap", get, set, target, 850, target === 0 ? () => sfx("flap-close") : null);
        }
      });
      $(".lesson-card, .finale-message-card", lesson).addEventListener("click", () => { if (get() > 0.5) animateTo("flap", get, set, 0, 850, () => sfx("flap-close")); });
    }
    const bk = $("[data-facts]", book);
    if (bk && c) bk.addEventListener("click", () => openBooklet(c, bk.closest(".finale-layer") || $(".page.left", book)));
    $$(".stage .piece:not(.wallpiece)", book).forEach((p) => {
      p.addEventListener("click", (e) => {
        if (e.target && e.target.closest && e.target.closest(".lesson, .phone-page-cues, button")) return;
        p.classList.remove("popped");
        void p.offsetWidth;
        p.classList.add("popped");
        sfx("card-tap", 0.55);
      });
      p.addEventListener("animationend", () => p.classList.remove("popped"));
    });
    $$("[data-go]", book).forEach((b) => b.addEventListener("click", () => go(+b.dataset.go)));
    $$("[data-stage-prev]", book).forEach((b) => b.addEventListener("click", () => go(cur - 1)));
    $$("[data-stage-next]", book).forEach((b) => b.addEventListener("click", () => go(cur + 1)));
  }

  /* ---------- Fact booklet: a small booklet glued to the text page ---------- */

  const bkState = { c: null, i: 0, busy: false, trigger: null };
  function factFaces(c, i) {
    const f = (c.facts || [])[i] || {}, s = sources[f.source] || {}, n = (c.facts || []).length;
    const imgInfo = f.image && IMG[f.image] ? IMG[f.image] : null;
    const photo = imgInfo ? `<img class="bk-photo" src="${esc(imgInfo.src)}" alt=""/>` : "";
    return {
      l: `<div class="bk-fact"><span class="bk-k">Fact ${i + 1} of ${n}</span><span class="bk-label">${inline(f.label)}</span>${f.value != null && f.value !== "" ? `<span class="bk-value">${esc(f.value)}</span>` : ""}${photo}</div>`,
      r: `<div class="bk-src"><span class="bk-k">Where it comes from</span><span class="bk-st">${esc(s.title || s.kind || "The record")}</span><code>${esc(s.ref || f.source)}</code>${s.excerpt ? `<span class="bk-q">“${esc(s.excerpt)}”</span>` : ""}</div>`,
    };
  }
  function openBooklet(c, host = $(".page.left")) {
    const page = host, bk = $("[data-facts]", page);
    closeBooklet(true);
    bkState.c = c; bkState.i = 0; bkState.trigger = bk;
    const w = document.createElement("div");
    w.className = "bk-wrap"; w.setAttribute("role", "dialog"); w.setAttribute("aria-modal", "true"); w.setAttribute("aria-label", `Fact booklet for ${UNIT.toLowerCase()} ${c.number}`);
    const f = factFaces(c, 0), n = (c.facts || []).length;
    w.innerHTML = `<div class="bk-book"><div class="bk-page l">${f.l}</div><div class="bk-page r">${f.r}</div><div class="bk-spine" aria-hidden="true"></div>
      <div class="bk-leaf" aria-hidden="true"><div class="bk-face f"></div><div class="bk-face b"></div></div>
      <div class="bk-coverleaf" aria-hidden="true"><div class="bk-face f">${bk ? bk.querySelector(".bk-cover").outerHTML : ""}</div><div class="bk-face b"></div></div>
      <div class="bk-nav"><button data-bk="-1" aria-label="Previous fact">‹</button><span class="bk-where" aria-live="polite">1 of ${n}</span><button data-bk="1" aria-label="Next fact">›</button><button class="bk-close">Close the booklet</button></div></div>`;
    if (wide) page.appendChild(w);
    else {
      const textPage = bk ? bk.closest(".text, .finale-card") : page;
      const copy = $(".prose, .finale-copy", textPage);
      if (copy) textPage.insertBefore(w, copy); else textPage.appendChild(w);
      textPage.classList.add("booklet-open");
    }
    if (bk) bk.classList.add("lifted-off");
    requestAnimationFrame(() => requestAnimationFrame(() => w.classList.add("on")));
    setTimeout(() => w.classList.add("done"), reduce ? 0 : 680);
    sfx("book-open");
    $$("[data-bk]", w).forEach((b) => b.addEventListener("click", () => turnBooklet(+b.dataset.bk)));
    $(".bk-page.r", w).addEventListener("click", () => turnBooklet(1));
    $(".bk-page.l", w).addEventListener("click", () => turnBooklet(-1));
    $(".bk-close", w).addEventListener("click", () => closeBooklet());
    w.addEventListener("click", (e) => { if (e.target === w) closeBooklet(); });
    w.addEventListener("keydown", (e) => {
      if (e.key !== "Tab") return;
      const focusable = $$("button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex='-1'])", w).filter((el) => !el.hidden);
      if (!focusable.length) { e.preventDefault(); return; }
      const first = focusable[0], last = focusable[focusable.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    });
    syncBooklet();
    $("[data-bk='1']", w).focus({ preventScroll: true });
  }
  function syncBooklet() {
    const w = $(".bk-wrap"), n = (bkState.c.facts || []).length;
    if (!w) return;
    $(".bk-where", w).textContent = `${bkState.i + 1} of ${n}`;
    $("[data-bk='-1']", w).disabled = bkState.i === 0;
    $("[data-bk='1']", w).disabled = bkState.i >= n - 1;
  }
  async function turnBooklet(d) {
    const w = $(".bk-wrap"), c = bkState.c;
    if (!w || bkState.busy) return;
    const j = bkState.i + d, n = (c.facts || []).length;
    if (j < 0 || j >= n) return;
    const now = factFaces(c, bkState.i), next = factFaces(c, j);
    const leaf = $(".bk-leaf", w), L = $(".bk-page.l", w), Rt = $(".bk-page.r", w);
    bkState.busy = true; sfx("book-riffle");
    // Forward: the right leaf turns over to the left. Back: the left leaf turns over to the right.
    leaf.className = "bk-leaf " + (d > 0 ? "fwd" : "bwd");
    $(".bk-face.f", leaf).innerHTML = d > 0 ? now.r : now.l;
    $(".bk-face.b", leaf).innerHTML = d > 0 ? next.l : next.r;
    if (d > 0) Rt.innerHTML = next.r; else L.innerHTML = next.l;
    void leaf.offsetWidth; leaf.classList.add("go");
    await wait(reduce ? 80 : 520);
    if (d > 0) L.innerHTML = next.l; else Rt.innerHTML = next.r;
    leaf.className = "bk-leaf";
    bkState.i = j; bkState.busy = false; syncBooklet();
  }
  function closeBooklet(quiet) {
    const w = $(".bk-wrap");
    if (!w) return;
    const trigger = bkState.trigger;
    const textPage = w.closest(".text, .finale-card");
    if (textPage) textPage.classList.remove("booklet-open");
    w.remove(); bkState.c = null; bkState.trigger = null;
    $$("[data-facts]").forEach((b) => b.classList.remove("lifted-off"));
    if (!quiet) { sfx("book-close"); if (trigger && trigger.isConnected) trigger.focus(); }
  }

  /* ---------- Painting ---------- */

  function spreadFor(i) {
    const pg = pages[i];
    if (pg.kind === "contents") return { left: contentsLeft(), right: stageHTML((story.contents || {}).scene, "contents") };
    if (pg.kind === "chapter") return { left: chapterLeft(pg.c, i * 2 - 1), right: stageHTML(pg.c.scene, "ch" + pg.c.number, pg.c.flap) };
    if (pg.kind === "numbers") return { left: numbersLeft(), right: volvelleHTML() };
    if (pg.kind === "finale") return { left: "", right: finaleHTML(pg.c) };
    return { left: backLeft(), right: stageHTML((story.back || {}).scene, "back") };
  }

  function paint() {
    const book = $(".book");
    const pg = pages[cur];
    if (stageObserver) { stageObserver.disconnect(); stageObserver = null; }
    book.classList.toggle("finale-open", pg.kind === "finale");
    if (pg.kind === "cover") {
      book.classList.add("closed");
      $(".cover").classList.remove("open");
      $(".page.left").innerHTML = ""; $(".page.right").innerHTML = "";
    } else {
      book.classList.remove("closed");
      $(".cover").classList.add("open");
      const s = spreadFor(cur);
      $(".page.left").innerHTML = s.left;
      $(".page.right").innerHTML = s.right;
      bindWheel($(".page.right"));
      $(".page.right").classList.toggle("has-wheel", !!$(".page.right .volvelle"));
      const st = $(".page.right .stage");
      const mech = st ? makeMech(st, pg.c || {}) : null;
      bindGadgets(book, pg.c, mech);
      if (st) {
        parallax(st); layoutStage(st);
        if (typeof ResizeObserver !== "undefined") {
          stageObserver = new ResizeObserver(() => layoutStage(st));
          stageObserver.observe(st);
        }
      }
    }
    $(".nav .where").textContent = label(cur);
    $("[data-prev]").disabled = cur === 0;
    $("[data-next]").disabled = cur === pages.length - 1;
    $("[data-toc]").disabled = pg.kind === "contents";
    $$("[data-stage-prev]").forEach((b) => { b.disabled = cur === 0; });
    $$("[data-stage-next]").forEach((b) => { b.disabled = cur === pages.length - 1; });
    $$("[data-swipe-hint]").forEach((hint) => { hint.hidden = cur !== 1 || swipeHintSeen; });
    fitText();
    $(".progress").style.width = (cur / (pages.length - 1)) * 100 + "%";
    const h = "#" + (pg.kind === "chapter" ? "ch" + pg.c.number : pg.kind);
    if (location.hash !== h) history.replaceState(null, "", h);
    const pageTitle = pg.kind === "chapter" || pg.kind === "finale" ? pg.c.title + " · " : "";
    document.title = pageTitle + (story.title || "Storybook");
  }

  function fitText() {
    const tx = $(".page.left .text");
    if (!tx) return;
    tx.style.fontSize = "";
    const pr = $(".prose", tx);
    if (wide && pr) {
      let k = 1;
      while (pr.scrollHeight > pr.clientHeight + 2 && k > 0.86) { k -= 0.02; tx.style.fontSize = k + "em"; }
    }
    const bk = $(".booklet", tx);
    if (bk && pr && wide) {
      let sp = $(".bk-space", pr);
      if (!sp) { sp = document.createElement("span"); sp.className = "bk-space"; sp.setAttribute("aria-hidden", "true"); pr.prepend(sp); }
      sp.style.height = "0px";
      const need = bk.getBoundingClientRect().bottom - pr.getBoundingClientRect().top + 6;
      sp.style.width = (tx.getBoundingClientRect().right - bk.getBoundingClientRect().left - parseFloat(getComputedStyle(tx).paddingRight) + 8) + "px";
      sp.style.height = Math.max(0, need) + "px";
    }
    $$(".prose").forEach((p) => p.classList.toggle("scrolls", p.scrollHeight > p.clientHeight + 4));
  }

  function label(i) {
    const pg = pages[i];
    if (pg.kind === "cover") return "Cover";
    if (pg.kind === "contents") return "Contents";
    if (pg.kind === "chapter") return `${UNIT} ${pg.c.number} of ${chapters.length}`;
    if (pg.kind === "numbers") return "The numbers";
    if (pg.kind === "finale") return "Finale";
    return "The end";
  }

  function nextPaint() {
    return new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
  }

  function prepareLeaf(state) {
    const leaf = $(".leaf");
    leaf.className = "leaf go controlled" + (state.dir < 0 && wide ? " back" : "");
    leaf.dataset.direction = state.dir > 0 ? "next" : "previous";
    const front = $(".face.f", leaf), back = $(".face.b", leaf);
    const destination = spreadFor(state.to);
    if (!wide) {
      // Phone: one page shows. The old picture lifts away and the new one rises under it.
      front.innerHTML = $(".page.right").innerHTML;
      back.innerHTML = "";
    } else if (state.dir > 0) {
      front.innerHTML = $(".page.right").innerHTML;   // the old picture, folding shut as the leaf rises
      back.innerHTML = destination.left;             // the new text page, landing on the left
    } else {
      front.innerHTML = $(".page.left").innerHTML;    // the old text page, lifting off the left
      back.innerHTML = destination.right;            // the new picture, opening as the leaf lands
    }
    $$("[id]", leaf).forEach((element) => element.removeAttribute("id"));
    // Page-turn cues and other screen controls are not printed on the paper: keep them off the leaf,
    // so they never show twice while it turns.
    $$(".phone-page-cues, .stage-hint, [data-stage-prev], [data-stage-next]", leaf).forEach((element) => element.remove());
    $$(".stage", leaf).forEach((stage) => layoutStage(stage));
    if (!wide) {
      const page = $(".page.right");
      const book = $(".book");
      const pageRect = page.getBoundingClientRect();
      const bookRect = book.getBoundingClientRect();
      leaf.style.top = (pageRect.top - bookRect.top) + "px";
      leaf.style.bottom = "auto";
      leaf.style.left = "0";
      leaf.style.width = "100%";
      leaf.style.height = pageRect.height + "px";
      leaf.style.transformOrigin = state.dir > 0 ? "0 50%" : "100% 50%";
    }
    return leaf;
  }

  /* The finale spans both pages, so a turn into or out of it splits it like any spread:
     its left half sits on whichever surface carries that spread's left page, and its right
     half on whichever carries its right page. Each surface shows one half of the same layer. */
  function dressFinaleHalves(state) {
    if (!wide) return null;
    const into = pages[state.to].kind === "finale", out = pages[state.from].kind === "finale";
    if (!into && !out) return null;
    const spread = into ? "B" : "A";
    const surfaces = state.dir > 0
      ? { "A-left": ".page.left", "A-right": ".leaf .face.f", "B-left": ".leaf .face.b", "B-right": ".page.right" }
      : { "A-left": ".leaf .face.f", "A-right": ".page.right", "B-left": ".page.left", "B-right": ".leaf .face.b" };
    const html = spreadFor(into ? state.to : state.from).right;
    for (const half of ["left", "right"]) {
      const surface = $(surfaces[`${spread}-${half}`]);
      if (!surface) continue;
      const live = surface.matches(".page.right") && $(".finale-layer", surface);
      if (!live) {
        surface.innerHTML = html;
        $$("[id]", surface).forEach((element) => element.removeAttribute("id"));
        $$(".stage", surface).forEach((stage) => layoutStage(stage));
      }
      surface.classList.add("finale-half", `fh-${half}`);
    }
    return { opening: into };
  }

  function undressFinaleHalves() {
    $$(".finale-half").forEach((element) => element.classList.remove("finale-half", "fh-left", "fh-right"));
  }

  /* Lay the base pages for a turn, under the leaf prepared above. */
  function prepareBase(state) {
    const destination = spreadFor(state.to);
    if (!wide || state.dir > 0) {
      // The new picture lies under the leaf. Forward on a desktop, the old text page stays on the left.
      const oldLeft = $(".page.left").innerHTML;
      cur = state.to;
      paint();
      if (wide) $(".page.left").innerHTML = oldLeft;
    } else {
      // Back on a desktop: the old picture stays on the right; the new text page is under the leaf on the left.
      $(".page.left").innerHTML = destination.left;
    }
    $$(".page.left [id]").forEach((element) => { if (wide) element.removeAttribute("id"); });
  }

  function resetLeaf() {
    const leaf = $(".leaf");
    leaf.className = "leaf";
    leaf.removeAttribute("data-angle");
    leaf.removeAttribute("data-direction");
    leaf.removeAttribute("style");
    $$(".face", leaf).forEach((face) => { face.innerHTML = ""; });
  }

  /* One value drives a turn: the leaf angle, 0 to 180 degrees. As in a real codex,
     both spreads move at once. The spread the leaf is leaving closes as the leaf
     rises (its pop-up folds flat), and the spread the leaf is opening rises with it.
     Turning forward, the leaf carries the old picture on its front and the new
     text page on its back, the new picture lies under it, and the old text page
     stays put until the leaf lands on it. Turning back is the mirror image. */
  function turnStages(state) {
    const base = $(".page.right .stage");
    const leafStage = $(state.dir > 0 || !wide ? ".leaf .face.f .stage" : ".leaf .face.b .stage");
    // Forward (and every phone turn): the base picture is the new spread, the leaf carries the old one.
    // Back on a desktop: the base picture is the old spread, the leaf's back carries the new one.
    return state.dir > 0 || !wide ? { opening: base, closing: leafStage } : { opening: leafStage, closing: base };
  }

  function applyTurnAngle(value) {
    if (!turnState) return;
    const state = turnState;
    const angle = Math.max(0, Math.min(180, value));
    state.angle = angle;
    const leaf = $(".leaf");
    leaf.dataset.angle = angle.toFixed(2);
    leaf.style.transform = `rotateY(${(state.dir > 0 ? -angle : angle).toFixed(2)}deg)`;
    const t = angle / 180;
    const { opening, closing } = turnStages(state);
    if (opening) setStageOpen(opening, t);
    if (closing) setStageOpen(closing, 1 - t);
    if (state.finale) $$(".finale-half .finale-stage").forEach((stage) => setStageOpen(stage, state.finale.opening ? t : 1 - t));
  }

  function animateTurn(target, duration) {
    if (!turnState) return Promise.resolve();
    const start = turnState.angle;
    const distance = target - start;
    if (!duration || Math.abs(distance) < 0.01) {
      applyTurnAngle(target);
      return Promise.resolve();
    }
    return new Promise((resolve) => {
      const started = performance.now();
      const tick = (now) => {
        const raw = Math.min(1, (now - started) / duration);
        const eased = raw * raw * (3 - 2 * raw);
        applyTurnAngle(start + distance * eased);
        if (raw < 1) requestAnimationFrame(tick);
        else resolve();
      };
      requestAnimationFrame(tick);
    });
  }

  function beginTurn(to) {
    const from = cur;
    const dir = to > from ? 1 : -1;
    turnState = { from, to, dir, angle: 0 };
    busy = true;
    if (from === 1) markSwipeHintSeen();
    size();
    prepareLeaf(turnState);
    prepareBase(turnState);
    turnState.finale = dressFinaleHalves(turnState);
    $(".book").classList.add("turning");
    applyTurnAngle(0);
    sfx("page-turn");
    const { opening } = turnStages(turnState);
    if (opening && pages[to].kind !== "cover") riseSounds(opening);
  }

  async function endTurn(commit, duration = null) {
    if (!turnState) return;
    const target = commit ? 180 : 0;
    const remaining = Math.abs(target - turnState.angle);
    const settle = duration == null ? Math.max(120, 300 * remaining / 180) : duration;
    await animateTurn(target, settle);
    const destination = commit ? turnState.to : turnState.from;
    // The leaf has landed (or fallen back). Lay the settled spread properly, live and bound.
    cur = destination;
    undressFinaleHalves();
    paint();
    $(".book").classList.remove("turning");
    raise($(".page.right .stage"));
    if (!wide) {
      window.scrollTo({ top: 0, behavior: "auto" });
      size();
    }
    if (duration === 0) await wait(120);
    else await nextPaint();
    resetLeaf();
    turnState = null;
    busy = false;
  }

  async function go(i) {
    if (busy || i < 0 || i >= pages.length || i === cur) return;
    const fromCover = pages[cur].kind === "cover";
    const toCover = pages[i].kind === "cover";
    if (fromCover || toCover) {
      busy = true;
      if (cur === 1) markSwipeHintSeen();
      sfx("page-turn");
      cur = i;
      paint();
      if (fromCover && wide && !reduce) {
        $(".cover").classList.remove("open");
        void $(".cover").offsetWidth;
        $(".cover").classList.add("open");
        await wait(700);
      }
      raise($(".page.right .stage"));
      await nextPaint();
      busy = false;
      return;
    }
    beginTurn(i);
    if (reduce) await endTurn(true, 0);
    else await endTurn(true, 620);
  }

  /* ---------- Print edition ---------- */

  function finalScene(c) {
    // Print shows each chapter after its tab is pulled and its flap lifted.
    const scene = JSON.parse(JSON.stringify(c.scene || {}));
    const fx = [...((c.tab || {}).effects || []), ...((c.flap || {}).effects || [])];
    const all = [...(scene.pieces || []), ...(scene.wall || [])];
    fx.forEach((f) => {
      const p = all.find((x) => x.id === f.piece);
      if (!p) return;
      if (f.fx === "show") p.hidden = false;
      if (f.fx === "hide") p.gone = true;
      if (f.fx === "swap" && p.alt) { const a = p.sprite; p.sprite = p.alt; p.alt = a; }
      if (f.fx === "move" && f.to) {
        if (f.to.x != null) p.x = f.to.x;
        if (f.to.depth != null) { p.depth = f.to.depth; delete p.z; }
        if (f.to.z != null) p.z = f.to.z;
        if (f.to.lift != null) p.lift = f.to.lift;
        if (f.to.grow != null) p.scale = (p.scale ?? 3) * f.to.grow;
      }
    });
    scene.pieces = (scene.pieces || []).filter((p) => !p.gone);
    scene.wall = (scene.wall || []).filter((p) => !p.gone);
    return scene;
  }

  function flatStage(scene) {
    if (!scene) return "";
    const wall = (scene.wall || []).filter((p) => !p.hidden).map((p) => { const w = (pieceGridWidth(p) + 2) * (p.scale ?? 2) * 0.6; const x = Math.min(100 - w / 2 - 2, Math.max(w / 2 + 2, p.x ?? 50)); return `<div class="fp" style="left:${x}%;top:${Math.max(8, (p.y ?? 20) * 0.5)}%;transform:translate(-50%,-50%);width:${w}%">${pieceVisualSVG(p, { scale: 1, remap: p.remap, flip: p.flip, cut: p.cut !== false }).replace(/style="[^"]*"/, "")}</div>`; }).join("");
    const pcs = (scene.pieces || []).filter((p) => !p.hidden).slice().sort((a, b) => (b.depth ?? 2) - (a.depth ?? 2)).map((p) => {
      const z = p.z ?? ((p.depth ?? 2) - 0.5) / 4;
      const k = 1 / (1 + z * 0.56);
      const w = (pieceGridWidth(p) + 2) * (p.scale ?? 3) * 0.86 * k;
      const xx = Math.min(100 - w / 2 - 1, Math.max(w / 2 + 1, p.x ?? 50));
      return `<div class="fp" style="left:${xx}%;bottom:calc(${3 + z * 46}% + ${(p.lift ?? 0) * 0.62 * k}%);width:${w}%">${pieceVisualSVG(p, { scale: 1, remap: p.remap, flip: p.flip }).replace(/style="[^"]*"/, "")}</div>`;
    }).join("");
    return `<div class="flatstage" style="--sky:${esc(sky(scene.sky))};--ground:${esc(ground(scene.ground))}"><div class="fground"></div>${wall}${pcs}</div>`;
  }

  /* ---------- Storyboard review document (#storyboard) ---------- */

  const wordCount = (value) => String(value || "").trim().split(/\s+/).filter(Boolean).length;
  const proseWords = (paras) => wordCount((paras || []).join(" "));

  function budgetHTML(label, count, low, high) {
    const state = count < low ? "under" : count > high ? "over" : "ok";
    const range = low === 0 ? `up to ${high}` : `${low} to ${high}`;
    const flag = state === "under" ? ", short" : state === "over" ? ", too long" : "";
    return `<span class="storyboard-budget ${state}"><b>${esc(label)}</b> ${count} words${flag} <small>${range}</small></span>`;
  }

  function pieceName(piece, id) {
    const sprite = piece ? String(piece.sprite || "piece").replace(/_/g, " ") : "unknown piece";
    return `${sprite} (${id || "no id"})`;
  }

  function effectSentence(effect, pieces) {
    const piece = pieces.get(effect.piece);
    const name = pieceName(piece, effect.piece);
    const reverse = effect.off ? " returns to its starting state" : "";
    if (effect.off) return name + reverse;
    if (effect.fx === "show") return `${name} stands up`;
    if (effect.fx === "hide") return `${name} folds away`;
    if (effect.fx === "swap") return `${name} changes to ${String((piece || {}).alt || "its alternate sprite").replace(/_/g, " ")}`;
    if (effect.fx === "hop") return `${name} hops`;
    if (effect.fx === "wobble") return `${name} wobbles`;
    if (effect.fx === "glow") return `${name} glows`;
    if (effect.fx === "dim") return `${name} dims`;
    if (effect.fx === "rise") return `${name} rises`;
    if (effect.fx === "flip") return `${name} turns around`;
    if (effect.fx === "move") {
      // Say it in directions an owner can picture, relative to where the piece starts.
      const to = effect.to || {}, p = piece || {}, parts = [];
      const z0 = p.z ?? ((p.depth ?? 2) - 0.5) / 4;
      const z1 = to.z ?? (to.depth != null ? (to.depth - 0.5) / 4 : z0);
      if (to.x != null && Math.abs(to.x - (p.x ?? 50)) >= 3) parts.push(to.x > (p.x ?? 50) ? "right" : "left");
      if (Math.abs(z1 - z0) >= 0.05) parts.push(z1 < z0 ? "forward" : "back");
      if (to.lift != null && Math.abs(to.lift - (p.lift ?? 0)) >= 2) parts.push(to.lift > (p.lift ?? 0) ? "up" : "down");
      const dir = parts.length ? `moves ${parts.join(" and ")}` : "moves into place";
      const size = to.grow != null && to.grow !== 1 ? (to.grow < 1 ? " and gets smaller" : " and gets bigger") : "";
      return `${name} ${dir}${size}`;
    }
    return `${name} uses ${effect.fx || "an effect"}`;
  }

  function mechanismPlan(c) {
    const scene = c.scene || {};
    const pieces = new Map([...(scene.wall || []), ...(scene.pieces || [])].filter((p) => p.id).map((p) => [p.id, p]));
    const plan = (label, gadget) => {
      const effects = ((gadget || {}).effects || []).map((effect) => effectSentence(effect, pieces));
      return effects.length ? `<p><b>${label}:</b> ${effects.map(esc).join("; ")}.</p>` : "";
    };
    return plan("Pull", c.tab) + plan("Lift", c.flap) || "<p>No mechanism is planned yet.</p>";
  }

  function thumbnailHTML(label, scene) {
    return `<figure><figcaption>${esc(label)}</figcaption>${flatStage(scene) || '<div class="storyboard-empty">No scene</div>'}</figure>`;
  }

  function chapterStoryboard(c) {
    const open = c.status === "open";
    const mainWords = proseWords(c.text);
    const trialWords = wordCount((c.tab || {}).text);
    const lessonWords = wordCount((c.flap || {}).text);
    const facts = (c.facts || []).map((fact) => `<li>${esc(fact.label || fact.value || "Untitled fact")}</li>`).join("");
    return `<article class="storyboard-card chapter-card ${open ? "open" : "written"}" data-entry="chapter-${esc(c.number)}">
      <header><div><span class="storyboard-kicker">${esc(UNIT)} ${esc(c.number)}</span><h2>${esc(c.title)}</h2></div><div class="storyboard-status ${open ? "open" : "written"}">${open ? "Still to come" : "Written"}</div></header>
      <p class="storyboard-when">${esc(c.when || "Date not set")}</p>
      <div class="storyboard-budgets">${budgetHTML("Main", mainWords, 100, 230)}${budgetHTML("Trial", trialWords, 0, 59)}${budgetHTML("Lesson", lessonWords, 0, 44)}</div>
      <div class="storyboard-copy"><section><h3>Trial</h3><p>${inline((c.tab || {}).text || "No trial written yet.")}</p></section><section><h3>Lesson</h3><p>${inline((c.flap || {}).text || "No lesson written yet.")}</p></section></div>
      <section class="storyboard-plan"><h3>Mechanism plan</h3>${mechanismPlan(c)}</section>
      <section class="storyboard-facts"><h3>Fact labels</h3>${facts ? `<ul>${facts}</ul>` : "<p>No facts recorded yet.</p>"}</section>
      <div class="storyboard-thumbnails">${thumbnailHTML("Start scene", c.scene)}${thumbnailHTML("Final scene", finalScene(c))}</div>
    </article>`;
  }

  function finaleStoryboard(finale) {
    const copy = (finale.text || []).map((p) => `<p>${inline(p)}</p>`).join("");
    const facts = (finale.facts || []).map((fact) => `<li>${esc(fact.label || fact.value || "Untitled fact")}</li>`).join("");
    return `<article class="storyboard-card finale-card-review" data-entry="finale">
      <header><div><span class="storyboard-kicker">Finale</span><h2>${esc(finale.title)}</h2></div></header>
      <div class="storyboard-budgets">${budgetHTML("Card", proseWords(finale.text), 1, 80)}${budgetHTML("Pull", wordCount((finale.tab || {}).text), 0, 45)}${budgetHTML("Flap", wordCount((finale.flap || {}).text), 0, 45)}</div>
      <div class="storyboard-summary">${copy}</div>
      <section class="storyboard-plan"><h3>Mechanism plan</h3>${mechanismPlan(finale)}</section>
      ${facts ? `<section class="storyboard-facts"><h3>Fact labels</h3><ul>${facts}</ul></section>` : ""}
      <div class="storyboard-thumbnails">${thumbnailHTML("Closed plan", finale.scene)}${thumbnailHTML("Final scene", finalScene(finale))}</div>
    </article>`;
  }

  function simpleStoryboard(kind, kicker, title, copy, scene, extra = "") {
    const thumbs = scene ? `<div class="storyboard-thumbnails single">${thumbnailHTML("Scene", scene)}</div>` : "";
    return `<article class="storyboard-card ${kind}-card" data-entry="${kind}"><header><div><span class="storyboard-kicker">${esc(kicker)}</span><h2>${esc(title)}</h2></div></header>${copy ? `<div class="storyboard-summary">${copy}</div>` : ""}${extra}${thumbs}</article>`;
  }

  function storyboardEntries() {
    const contents = story.contents || {};
    const cards = [simpleStoryboard("contents", contents.kicker || "Inside", contents.title || "Contents", contents.intro ? `<p>${inline(contents.intro)}</p>` : "", contents.scene)];
    chapters.forEach((c) => cards.push(chapterStoryboard(c)));
    if (story.numbers) {
      const nb = story.numbers;
      const stats = (nb.stats || []).map((s) => `<li><b>${esc(s.value)}</b> ${esc(s.label)}</li>`).join("");
      const months = (nb.months || []).map((m) => `<li><b>${esc(m.label)}</b> ${(m.lines || []).map(esc).join(", ")}</li>`).join("");
      cards.push(simpleStoryboard("numbers", nb.kicker || "By the numbers", nb.title || "The numbers", nb.intro ? `<p>${inline(nb.intro)}</p>` : "", null, `<div class="storyboard-numbers"><section><h3>Stats</h3><ul>${stats}</ul></section><section><h3>Wheel</h3><ul>${months}</ul></section></div>`));
    }
    if (story.finale) cards.push(finaleStoryboard(story.finale));
    const back = story.back || {};
    cards.push(simpleStoryboard("back", back.kicker || "The end", back.title || "Thank you", (back.text || []).map((p) => `<p>${inline(p)}</p>`).join(""), back.scene));
    return cards;
  }

  function buildStoryboard() {
    const cards = storyboardEntries();
    const chapterWords = chapters.reduce((sum, c) => sum + proseWords(c.text) + wordCount((c.tab || {}).text) + wordCount((c.flap || {}).text), 0);
    const finaleWords = story.finale ? proseWords(story.finale.text) + wordCount((story.finale.tab || {}).text) + wordCount((story.finale.flap || {}).text) : 0;
    const totalWords = chapterWords + finaleWords + wordCount((story.contents || {}).intro) + wordCount((story.numbers || {}).intro) + proseWords((story.back || {}).text);
    const totalFacts = chapters.reduce((sum, c) => sum + (c.facts || []).length, 0) + ((story.finale || {}).facts || []).length;
    document.body.classList.add("storyboard-mode");
    document.getElementById("app").innerHTML = `<main class="storyboard">
      <header class="storyboard-header"><div><span class="storyboard-kicker">Storyboard review</span><h1>${esc(story.title || "Untitled story")}</h1><p>${esc(story.subtitle || "")}</p></div>
      <dl><div><dt>Entries</dt><dd>${cards.length}</dd></div><div><dt>Total words</dt><dd>${totalWords}</dd></div><div><dt>Total facts</dt><dd>${totalFacts}</dd></div><div><dt>Sources</dt><dd>${Object.keys(sources).length}</dd></div></dl></header>
      <section class="storyboard-tools" aria-label="Storyboard index and filters"><div class="storyboard-filters"><span>Show</span><button type="button" data-story-filter="open" aria-pressed="false">Open pages</button><button type="button" data-story-filter="budget" aria-pressed="false">Budget flags</button></div><nav class="storyboard-index" aria-label="Page index"></nav></section>
      <div class="storyboard-cards">${cards.join("")}</div></main>`;
    const cardNodes = $$(".storyboard-card");
    const index = $(".storyboard-index");
    cardNodes.forEach((card, i) => {
      card.id = `storyboard-entry-${i + 1}`;
      const button = document.createElement("button");
      button.type = "button";
      button.dataset.storyTarget = card.id;
      button.textContent = ($(".storyboard-kicker", card) || $("h2", card)).textContent;
      button.addEventListener("click", () => card.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" }));
      index.appendChild(button);
    });
    const filters = { open: false, budget: false };
    const applyFilters = () => {
      cardNodes.forEach((card, i) => {
        const matchesOpen = !filters.open || card.classList.contains("open");
        const matchesBudget = !filters.budget || !!$(".storyboard-budget.under, .storyboard-budget.over", card);
        card.hidden = !(matchesOpen && matchesBudget);
        index.children[i].hidden = card.hidden;
      });
    };
    $$("[data-story-filter]").forEach((button) => button.addEventListener("click", () => {
      const key = button.dataset.storyFilter;
      filters[key] = !filters[key];
      button.setAttribute("aria-pressed", String(filters[key]));
      applyFilters();
    }));
    document.title = `Storyboard · ${story.title || "Storybook"}`;
    window.__storyboard = { cards: cards.length, words: totalWords, facts: totalFacts };
  }

  function buildPrint() {
    const el = $("#print");
    let html = `<section class="pcover">${textSVG(story.title || "", "#1d2b53")}<div style="font-style:italic;font-size:14pt">${esc(story.subtitle || "")}</div><div style="width:40mm">${spriteSVG((story.cover || {}).hero || "robot", { scale: 1 }).replace(/style="[^"]*"/, 'style="width:100%;height:auto"')}</div><div style="font-family:var(--ui);font-size:9pt">${esc(story.byline || "")}</div></section>`;
    chapters.forEach((c) => {
      const facts = (c.facts || []).map((f) => { const s = sources[f.source] || {}; return `<li>${esc(f.label)}: <b>${esc(f.value ?? "")}</b> (${esc(s.kind || "")}: ${esc(s.ref || f.source)})</li>`; }).join("");
      html += `<section class="pp"><div class="ptext"><div class="kick">${esc(UNIT)} ${esc(c.number)}, ${esc(c.when || "")}</div><h2>${esc(c.title)}</h2>
        ${(c.text || []).map((p) => `<p>${inline(p)}</p>`).join("")}
        ${c.tab ? `<div class="box"><b>${esc(c.tab.label || "The trial")}</b><br>${inline(c.tab.text)}</div>` : ""}
        ${c.flap ? `<div class="box"><b>${esc(c.flap.label || "What I learned")}</b><br>${inline(c.flap.text)}</div>` : ""}
        ${facts ? `<ul class="pfacts">${facts}</ul>` : ""}</div>${flatStage(finalScene(c))}</section>`;
    });
    if (story.numbers) {
      html += `<section class="pp"><div class="ptext"><h2>${esc(story.numbers.title || "The numbers")}</h2>${(story.numbers.stats || []).map((s) => `<p><b>${esc(s.value)}</b> ${esc(s.label)}</p>`).join("")}</div>
        <div class="ptext">${(story.numbers.months || []).map((m) => `<p><b>${esc(m.label)}</b><br>${(m.lines || []).map(esc).join("<br>")}</p>`).join("")}</div></section>`;
    }
    if (story.finale) {
      const finale = story.finale;
      const facts = (finale.facts || []).map((f) => { const s = sources[f.source] || {}; return `<li>${esc(f.label)}: <b>${esc(f.value ?? "")}</b> (${esc(s.kind || "")}: ${esc(s.ref || f.source)})</li>`; }).join("");
      html += `<section class="pfin">${flatStage(finalScene(finale))}<div class="pfin-card"><div class="kick">Finale</div><h2>${esc(finale.title)}</h2>${(finale.text || []).map((p) => `<p>${inline(p)}</p>`).join("")}${finale.tab ? `<div class="box"><b>${esc(finale.tab.label || "Pull tab")}</b><br>${inline(finale.tab.text)}</div>` : ""}${finale.flap ? `<div class="box"><b>${esc(finale.flap.label || "Lift flap")}</b><br>${inline(finale.flap.text)}</div>` : ""}${facts ? `<ul class="pfacts">${facts}</ul>` : ""}</div></section>`;
    }
    el.innerHTML = html;
  }

  /* ---------- Hand-driven page turns ---------- */

  function pageTurnControl(target) {
    return target.closest("button, .slider, .lesson, .wheel, .booklet, .bk-wrap, [data-pull], [data-facts]");
  }

  function pageTurnPointerDown(e) {
    if (busy || reduce || e.button !== 0 || pageTurnControl(e.target)) return;
    const page = e.target.closest(".page.right, .page.left");
    if (!page) return;
    let rect = page.getBoundingClientRect();
    let dir = 0;
    if (wide) {
      // Decide the edge by where the hand is on the open book, not by which element was hit:
      // the finale's layer belongs to the right page but covers both.
      const left = $(".page.left").getBoundingClientRect(), right = $(".page.right").getBoundingClientRect();
      const grab = Math.min(110, right.width * 0.22);
      if (e.clientX >= right.right - grab && e.clientX <= right.right) { dir = 1; rect = right; }
      else if (e.clientX <= left.left + grab && e.clientX >= left.left) { dir = -1; rect = left; }
      if (!dir) return;
    } else if (!e.target.closest(".stage")) {
      return;
    }
    if ((dir > 0 && cur >= pages.length - 1) || (dir < 0 && cur <= 0)) return;
    dragTurn = {
      pointerId: e.pointerId,
      startX: e.clientX,
      startY: e.clientY,
      width: rect.width,
      dir,
      active: false,
      host: e.currentTarget,
    };
    try { e.currentTarget.setPointerCapture(e.pointerId); } catch (error) { /* synthetic pointer */ }
    if (dir) {
      beginTurn(cur + dir);
      dragTurn.active = true;
      e.preventDefault();
    }
  }

  function pageTurnPointerMove(e) {
    if (!dragTurn || e.pointerId !== dragTurn.pointerId) return;
    const dx = e.clientX - dragTurn.startX;
    const dy = e.clientY - dragTurn.startY;
    if (!dragTurn.active) {
      if (Math.abs(dy) > Math.abs(dx) && Math.abs(dy) > 8) {
        dragTurn = null;
        return;
      }
      if (Math.abs(dx) < 5) return;
      dragTurn.dir = dx < 0 ? 1 : -1;
      if ((dragTurn.dir > 0 && cur >= pages.length - 1) || (dragTurn.dir < 0 && cur <= 0)) {
        dragTurn = null;
        return;
      }
      beginTurn(cur + dragTurn.dir);
      dragTurn.active = true;
    }
    const travel = dragTurn.dir > 0 ? -dx : dx;
    applyTurnAngle(180 * Math.max(0, Math.min(1, travel / dragTurn.width)));
    e.preventDefault();
  }

  function pageTurnPointerUp(e) {
    if (!dragTurn || e.pointerId !== dragTurn.pointerId) return;
    const active = dragTurn.active;
    dragTurn = null;
    if (active && turnState) void endTurn(turnState.angle >= 90);
  }

  function bindPageTurns(book) {
    book.addEventListener("pointerdown", pageTurnPointerDown);
    book.addEventListener("pointermove", pageTurnPointerMove);
    book.addEventListener("pointerup", pageTurnPointerUp);
    book.addEventListener("pointercancel", pageTurnPointerUp);
  }

  /* ---------- Shell ---------- */

  function shell() {
    const cv = story.cover || {};
    document.getElementById("app").innerHTML = `
      <div class="progress"></div>
      <div class="desk"><div class="book closed">
        <section class="page left" aria-label="Left page"></section>
        <section class="page right" aria-label="Right page"></section>
        <div class="gutter"></div>
        <div class="leaf"><div class="face f"></div><div class="face b"></div></div>
        <div class="cover"><div class="face outside">
            <div class="byline">${esc(story.byline || "")}</div>
            ${textSVG(story.title || "", "#fff1e8")}
            <div class="hero">${spriteSVG(cv.hero || "robot", { scale: 1 }).replace(/style="[^"]*"/, 'style="width:100%;height:auto"')}</div>
            <div class="sub">${esc(story.subtitle || "")}</div>
            <button class="open-btn" data-open>${esc(cv.button || "Open the book")}</button>
          </div><div class="face inside"></div></div>
      </div></div>
      <nav class="nav" aria-label="Book navigation"><button data-prev aria-label="Previous page">‹</button><button data-toc>Contents</button><span class="where" aria-live="polite" aria-atomic="true"></span><button data-next aria-label="Next page">›</button><button data-sound aria-pressed="false" title="Paper sounds">Sound off</button></nav>`;
    const pr = document.createElement("div"); pr.id = "print"; document.body.appendChild(pr);
    bindPageTurns($(".book"));
    $("[data-prev]").addEventListener("click", () => go(cur - 1));
    $("[data-next]").addEventListener("click", () => go(cur + 1));
    $("[data-toc]").addEventListener("click", () => go(1));
    $("[data-sound]").addEventListener("click", () => setSound(!audio.on));
    setSound(audio.on);
    $("[data-open]").addEventListener("click", () => go(1));
    $(".cover .outside").addEventListener("click", (e) => { if (!e.target.closest("button")) go(1); });
    document.addEventListener("keydown", (e) => {
      if ($(".bk-wrap")) {
        if (e.key === "Escape") closeBooklet();
        if (e.key === "ArrowRight") turnBooklet(1);
        if (e.key === "ArrowLeft") turnBooklet(-1);
        return;
      }
      if (e.target.closest && e.target.closest(".tab, .lflap")) return;
      if (e.key === "ArrowRight" || e.key === "PageDown") go(cur + 1);
      if (e.key === "ArrowLeft" || e.key === "PageUp") go(cur - 1);
      if (e.key === "Home") go(0);
      if (e.key === "End") go(pages.length - 1);
    });
    /* Flick swipe: fallback for reduced motion and stage-less right pages. */
    let swipe = null;
    document.addEventListener("touchstart", (e) => {
      const picture = e.target.closest && e.target.closest(".page.right");
      const ownControl = e.target.closest && e.target.closest(".lflap, .tab, button, .wheel, .slider, .booklet, .bk-wrap");
      // The hand-driven turn owns drags over a stage when motion is on. This flick swipe covers
      // reduced motion and right pages without a stage, so one gesture never turns twice.
      const dragTurnOwns = !reduce && e.target.closest && e.target.closest(".stage");
      if (picture && !ownControl && !dragTurnOwns) swipe = { x: e.touches[0].clientX, y: e.touches[0].clientY, maxY: 0 };
    }, { passive: true });
    document.addEventListener("touchmove", (e) => {
      if (swipe) swipe.maxY = Math.max(swipe.maxY, Math.abs(e.touches[0].clientY - swipe.y));
    }, { passive: true });
    document.addEventListener("touchend", (e) => {
      if (!swipe) return;
      const dx = e.changedTouches[0].clientX - swipe.x, dy = e.changedTouches[0].clientY - swipe.y;
      const straight = swipe.maxY < 28;
      swipe = null;
      if (straight && Math.abs(dx) > 60 && Math.abs(dx) > Math.abs(dy) * 1.25) go(cur + (dx < 0 ? 1 : -1));
    });
  }

  function size() {
    const vw = innerWidth, vh = innerHeight;
    wide = !(vw <= 820 || vw / vh <= 1);
    const navH = 64;
    let bw = Math.min(vw * 0.94, 1480), bh = bw * 0.64;
    if (bh > vh - navH - 30) { bh = vh - navH - 30; bw = bh / 0.64; }
    const root = document.documentElement;
    root.style.setProperty("--bw", bw + "px");
    root.style.setProperty("--bh", bh + "px");
    root.style.setProperty("--fs", wide ? Math.max(12, Math.min(19, bw / 64)) + "px" : "17px");
    const st = $(".page.right .stage");
    if (st) layoutStage(st);
    fitText();
  }


  function start() {
    if (location.hash === "#storyboard") {
      buildStoryboard();
      return;
    }
    shell(); size(); buildPrint();
    const h = location.hash.slice(1);
    let i = 0;
    if (h.startsWith("ch")) i = pages.findIndex((p) => p.kind === "chapter" && "ch" + p.c.number === h);
    else if (h) i = pages.findIndex((p) => p.kind === h);
    cur = Math.max(0, i);
    paint();
    raise($(".page.right .stage"));
    addEventListener("resize", () => { size(); });
    let lastY = scrollY;
    addEventListener("scroll", () => {
      const nav = $(".nav"), y = scrollY, end = y + innerHeight >= document.documentElement.scrollHeight - 40;
      nav.classList.toggle("away", !wide && y > lastY + 4 && !end);
      if (y < lastY - 4 || end) nav.classList.remove("away");
      lastY = y;
    }, { passive: true });
    window.__book = {
      go,
      pages: () => pages.map((p) => p.kind === "chapter" ? "ch" + p.c.number : p.kind),
      cur: () => turnState ? turnState.from : cur,
      turn: () => turnState ? { angle: turnState.angle, direction: turnState.dir, from: turnState.from, to: turnState.to } : null,
    };
  }
  start();
})();
