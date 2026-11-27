"use strict";
// Legend of Link tracker: items, triforce and shrines, cards, upgrades, the overworld's 71 entrances and a room grid
// per level and shrine. Everything is kept in localStorage (one key), so a refresh keeps the run.

const KEY = "lol-tracker-v1";
const VER = (new URL(document.currentScript.src).searchParams.get("v")) || "";   // (the page's ?v=: the build's version)
const $ = (id) => document.getElementById(id);
const el = (tag, props = {}, kids = []) => { const e = Object.assign(document.createElement(tag), props); e.append(...kids); return e; };

// ---------------------------------------------------------------- data
const ITEMS = [   // id, steps (null = not owned), name
  ["sword", ["sword1", "sword2", "sword3"], ["Wood sword", "White sword", "Magical sword"]],
  ["boom", ["boom1", "boom2"], ["Boomerang", "Magical boomerang"]],
  ["bow", ["bow"], ["Bow"]],
  ["arrow", ["arrow1", "arrow2"], ["Arrows", "Silver arrows"]],
  ["candle", ["candle1", "candle2"], ["Blue candle", "Red candle"]],
  ["recorder", ["recorder"], ["Recorder"]],
  ["bait", ["bait"], ["Bait"]],
  ["letter", ["letter"], ["Letter"]],
  ["potion", ["potion1", "potion2"], ["Blue potion", "Red potion"]],
  ["wand", ["wand"], ["Wand"]],
  ["raft", ["raft"], ["Raft"]],
  ["book", ["book1", "book2"], ["Red book", "Blue book"]],
  ["ring", ["ring1", "ring2"], ["Blue ring", "Red ring"]],
  ["ladder", ["ladder"], ["Ladder"]],
  ["magickey", ["magickey"], ["Magic key"]],
  ["bracelet", ["bracelet"], ["Power bracelet"]],
  ["shield", ["shield"], ["Magical shield"]],
];
const UPGRADES = ["Sword Beams", "Boomstick", "Regeneration", "Skull Ring", "Sword Mastery", "Fairy in a Bottle",
  "Blue Like Likes", "Rupee Speed", "Ganon Boomerang", "Critter Crusher", "Statue Jammer", "Bombsmith", "Potion Pouch",
  "Bat Potion", "Bow Mastery", "Ganon Visible", "Slow Fireballs", "Key Hoarder", "Unlimited Blue Candle", "Miser's Bow",
  "Refilling Bomb Bag", "Map Master", "Spider Bomber", "Bow of Greed", "Holy Fire", "XP Boost", "Ghost Hunter",
  "Healerang", "Shield Breaker", "Membership Card", "Poison Bait", "Heart Snubber", "Divining Rod", "Song of Chaos",
  "Zombie Link", "Brain Potion", "X-ray Glasses", "Boomerang Mastery", "Bookworm"];   // (lol_uptable's order: the icons up_00..up_36)
const PRICE = [50, 100, 125, 50, 100, 150, 50, 100, 150, 50, 100, 150, 50, 125, 150, 25, 50, 50, 50, 50, 50, 50, 75,
  100, 100, 100, 125, 150, 150, 200, 50, 200, 100, 25, 75, 50, 200, 75, 200];
// overworld screens (row * 16 + column) with a randomized entrance; the wood sword cave and the Any Road stairs
const ENTRANCES = [1, 3, 4, 5, 7, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 25, 26, 27, 28, 30, 31, 33, 34, 37, 38,
  39, 40, 44, 45, 47, 51, 52, 55, 60, 61, 66, 68, 69, 70, 71, 72, 74, 75, 77, 78, 81, 86, 88, 91, 94, 98, 99, 100, 102,
  103, 104, 106, 107, 109, 111, 112, 113, 116, 117, 118, 120, 123, 124, 125];
const FIXED = { 119: ["SWORD", "fixed"], 29: ["ROAD", "road"], 35: ["ROAD", "road"], 73: ["ROAD", "road"], 121: ["ROAD", "road"] };
const MARKS = [   // value, label on the map, class, picker text
  ...[1, 2, 3, 4, 5, 6, 7, 8, 9].map((n) => [`L${n}`, `${n}`, "lvl", `Level ${n}`]),
  ...["A", "B", "C", "D"].map((c) => [`S${c}`, c, "shr", `Shrine ${c}`]),
  ["shop", "SHOP", "shop", "Shop"], ["up", "UPG", "up", "Upgrade cave"], ["hint", "HINT", "hint", "Hint"],
  ["gamble", "BET", "misc", "Gambling"], ["rupee", "$", "misc", "Secret rupees"],
  ["tri4", "4▲", "tri", "4-triforce cave"], ["tri8", "8▲", "tri", "8-triforce cave"],
];
const DUNGEONS = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "A", "B", "C", "D"];
// a mark's box; (owner 2026-11-27) the 4 and 8 triforce caves: an orange box, a triangle, the number in bold black
function markTag(cls, label) {
  const t = el("span", { className: "tag " + cls });
  if (cls !== "tri") { t.textContent = label; return t; }
  t.innerHTML = '<svg viewBox="0 0 20 18" aria-hidden="true"><path d="M10 1 L19 17 H1 Z"/></svg>';
  t.append(el("b", { textContent: label.replace("▲", "") }));
  t.title = label.replace("▲", "") + "-triforce cave";
  return t;
}
const BRUSHES = [   // id, label, title
  ["room", "", "Room: right-click for its kind (moats, old man, stairs, numbers); click: a room, again cleared"],
  ["E", "↑", "Entrance (the first room you click; one per map)"], ["S", "S", "Stairs"], ["O", "O", "Old man"], ["B", "B", "Boss"],
  ["T", "▲", "Triforce or prize"], ["I", "★", "Item"], ["K", "K", "Locked door"], ["X", "✸", "Bomb wall"],
  ["?", "?", "Something to check"], ["erase", "✕", "Remove: click a room to clear it"],
];
const NICKNAMES = ["The Serpent", "The Bell", "The Face", "The Rook", "The Bat", "The Stallion", "The Giraffe",
  "The Unicorn", "The Pompadour", "The Whale", "The Ghost", "The Gecko", "The Balloon", "The Anteater", "The Robber",
  "The Sock Puppet", "The Vice", "The Elephant", "The Cactus", "The Poodle", "The Piranha", "The Hero", "The Hellhound",
  "The Broken Reticle", "The Bomb", "The Candle", "The Guillotine", "The Bird", "The Ladle", "The Notes",
  "The Question Mark", "The Pyramids", "The Heart", "The Bull", "The Periscope",
  "The Eagle", "The Moon", "The Manji", "The Snake", "The Lizard", "The Dragon", "The Demon", "The Lion", "The Skull",
  "The E", "The A", "The L", "The D", "The Z", "The Cap", "The Flail", "The Whip", "The Pig",
  "The Sword", "The Kite", "The Islands", "The Crane", "The Dancer", "The Lock Picks", "The Vire",
  "The Bow and Arrow", "The Rabbit", "The Broken Boomerang", "The Whirlwind", "The Hammer", "The Scorpion",
  "The Armos", "The Crown", "The Swiss Cheese"];

// ---------------------------------------------------------------- state
// the dungeon old men's choices (odds/old_men.csv), and a red potion when there's nothing to offer
const OM_ITEMS = [["boom1", "Boomerang"], ["candle1", "Blue candle"], ["raft", "Raft"], ["recorder", "Recorder"],
  ["bracelet", "Power bracelet"], ["ladder", "Ladder"], ["arrow1", "Arrows"], ["bombs", "Bomb upgrade"],
  ["sword2", "White sword"], ["wand", "Wand"], ["bow", "Bow"], ["arrow2", "Silver arrows"], ["shield", "Magical shield"],
  ["candle2", "Red candle"], ["sword3", "Magical sword"], ["potion2", "Red potion"]];
const fresh = () => ({ side: {}, items: {}, hearts: 3, om: {}, bombups: 0, tri: [], shrines: [], cards: { S: 0, D: 0, X: 0 }, ups: {},
  ow: {}, owDone: {}, owX: {}, owBuy: {}, dun: {}, cur: "1", notes: "", timer: { acc: 0, start: null } });
let S = fresh();
try { const raw = localStorage.getItem(KEY); if (raw) S = Object.assign(fresh(), JSON.parse(raw)); } catch (e) { /* new run */ }
let upQueued = false;
function save() {
  try { localStorage.setItem(KEY, JSON.stringify(S)); } catch (e) { /* storage unavailable: still works */ }
  if (!upQueued && typeof renderUps === "function") {
    upQueued = true;
    queueMicrotask(() => { upQueued = false; renderUps(); renderTri(); renderItems(); renderCounters(); renderSide(); renderDTabs(); });
  }
}

// a click advances, a right-click or a long press goes back
function stepper(node, fn) {
  let held = null, longed = false;
  node.addEventListener("click", (e) => { if (longed) { longed = false; return; } fn(+1, e); });
  node.addEventListener("contextmenu", (e) => { e.preventDefault(); fn(-1, e); });
  node.addEventListener("touchstart", () => { longed = false; held = setTimeout(() => { longed = true; fn(-1); }, 450); }, { passive: true });
  ["touchend", "touchmove", "touchcancel"].forEach((t) => node.addEventListener(t, () => clearTimeout(held)));
}
// (an upgrade pick, "up:N": its picture from the manual's)
const UPI = (v) => /^up:(\d+)$/.exec(v || "");
const icon = (name, cls = "") => {
  const m = UPI(name);
  return el("img", { src: m ? `../manual/img/up_${m[1].padStart(2, "0")}.png` : `img/${name}.png`, className: `px ${cls}`, alt: "", draggable: false });
};
const optName = (list, v) => { const m = UPI(v); if (m) return UPGRADES[+m[1]]; const f = list.find((x) => x[0] === v); return f ? f[1] : v; };

// ---------------------------------------------------------------- items, counters, triforce, cards
function renderItems() {
  const box = $("items"); box.replaceChildren();
  for (const [id, steps, names] of ITEMS) {
    const v = S.items[id] || 0;
    const b = el("button", { type: "button", className: "item" + (v ? " on" : ""), title: v ? names[v - 1] : names[0] });
    b.append(icon(steps[Math.max(0, v - 1)]));
    if (steps.length > 1 && v) b.append(el("span", { className: "tier", textContent: v }));
    stepper(b, (d) => { S.items[id] = (v + d + steps.length + 1) % (steps.length + 1); save(); renderItems(); });
    box.append(b);
  }
}
function counter(id, img, label, get, set, lo, hi) {
  const box = $(id); box.replaceChildren();
  const minus = el("button", { type: "button", className: "pm", textContent: "−", ariaLabel: `Fewer ${label}` });
  const plus = el("button", { type: "button", className: "pm", textContent: "+", ariaLabel: `More ${label}` });
  const val = el("b", { textContent: get() });
  minus.onclick = () => { set(Math.max(lo, get() - 1)); save(); val.textContent = get(); };
  plus.onclick = () => { set(Math.min(hi, get() + 1)); save(); val.textContent = get(); };
  box.append(icon(img), el("span", { className: "clabel", textContent: label }), minus, val, plus);
}
function renderTri() {
  const t = $("triforce"); t.replaceChildren();
  for (let n = 1; n <= 8; n++) {
    const on = S.tri.includes(n);
    const found = Object.values(S.ow).includes(`L${n}`);            // its level marked on the overworld
    const b = el("button", { type: "button", className: "tpiece" + (on ? " on" : "") + (found ? " found" : "") + (sideDone(String(n)) ? " all" : ""),
      title: `Triforce piece ${n}` + (found ? " (level found)" : "") });
    b.append(icon("triforce"), el("span", { textContent: n }));
    b.onclick = () => { S.tri = on ? S.tri.filter((x) => x !== n) : [...S.tri, n]; save(); renderTri(); };
    t.append(b);
  }
  const s = $("shrines"); s.replaceChildren();
  for (const c of ["A", "B", "C", "D"]) {
    const on = S.shrines.includes(c);
    const found = Object.values(S.ow).includes(`S${c}`);
    const b = el("button", { type: "button", className: "shrine" + (on ? " on" : "") + (found ? " found" : "") + (sideDone(c) ? " all" : ""), textContent: c,
      title: `Shrine ${c} prize taken` + (found ? " (found)" : "") });
    b.onclick = () => { S.shrines = on ? S.shrines.filter((x) => x !== c) : [...S.shrines, c]; save(); renderTri(); };
    s.append(b);
  }
  renderOM();
  const k = $("cards"); k.replaceChildren();
  for (const [c, name] of [["S", "Shop"], ["D", "Dungeon"], ["X", "Shrine"]]) {
    const b = el("button", { type: "button", className: "card" + (S.cards[c] ? " on" : ""), title: `${name} cards (up to 3)` });
    b.append(icon("card" + c), el("span", { textContent: `${c} ×${S.cards[c]}` }));
    stepper(b, (d) => { S.cards[c] = (S.cards[c] + d + 4) % 4; save(); renderTri(); });
    k.append(b);
  }
}

// ---------------------------------------------------------------- old men (levels 1-8)
// the shops' wares (lol_choice SHOP_ITEMS, the bookworm's red book, the potion shop's potions): icon, name, gives
const SHOP_WARES = [["key", "Key", null], ["bombs", "Bombs", null], ["bait", "Bait", "bait"], ["candle1", "Blue candle", "candle1"],
  ["boom1", "Boomerang", "boom1"], ["arrow1", "Arrows", "arrow1"], ["heart", "Heart", null], ["raft", "Raft", "raft"],
  ["recorder", "Recorder", "recorder"], ["bracelet", "Power bracelet", "bracelet"], ["bow", "Bow", "bow"],
  ["ladder", "Ladder", "ladder"], ["candle2", "Red candle", "candle2"], ["boom2", "Magical boomerang", "boom2"],
  ["shield", "Magical shield", "shield"], ["book1", "Red book", "book1"], ["potion1", "Blue potion", "potion1"],
  ["potion2", "Red potion", "potion2"]];
// an item picked in a shop or from an old man: into the inventory (a higher tier only; "bombs": a bomb upgrade)
function giveItem(img) {
  if (img === "bombs") { S.bombups = Math.min(3, (S.bombups || 0) + 1); return; }
  for (const [id, steps] of ITEMS) {
    const k = steps.indexOf(img);
    if (k >= 0) { S.items[id] = Math.max(S.items[id] || 0, k + 1); return; }
  }
}
// what each pick gave (S.grants: where it was picked -> {img, prev}), so a pick changed or cleared takes back what
// the wrong one gave (the item back to where it was, a card or bomb upgrade off) and the upgrades follow
function grant(src, img, lit) {
  S.grants = S.grants || {};
  if (S.grants[src] && S.grants[src].img === img && !!S.grants[src].lit === !!lit) return;
  revoke(src);
  const u = UPI(img);
  if (u) {                                         // an upgrade: its picture only; right-clicked: bought too
    S.grants[src] = { img, lit: !!lit, prevUp: S.ups[+u[1]] || 0 };
    if (lit) S.ups[+u[1]] = 2;
    return;
  }
  const it = ITEMS.find(([, steps]) => steps.includes(img));
  S.grants[src] = { img, prev: it ? S.items[it[0]] || 0 : null };
  if (/^card[SDX]$/.test(img)) S.cards[img[4]] = Math.min(3, (S.cards[img[4]] || 0) + 1); else giveItem(img);
}
function revoke(src) {
  const g = (S.grants || {})[src]; if (!g) return;
  delete S.grants[src];
  const u = UPI(g.img);
  if (u) { if (g.lit) S.ups[+u[1]] = g.prevUp || 0; return; }
  const m = /^card([SDX])$/.exec(g.img);
  if (m) { S.cards[m[1]] = Math.max(0, (S.cards[m[1]] || 0) - 1); return; }
  if (g.img === "bombs") { S.bombups = Math.max(0, (S.bombups || 0) - 1); return; }
  const it = ITEMS.find(([, steps]) => steps.includes(g.img)); if (!it) return;
  const [id, steps] = it, lvl = steps.indexOf(g.img) + 1;
  if ((S.items[id] || 0) !== lvl) return;                 // (changed by hand since: left as it is)
  const others = Object.values(S.grants).filter((x) => steps.includes(x.img)).map((x) => steps.indexOf(x.img) + 1);
  S.items[id] = Math.max(g.prev || 0, ...others);
}
const omDrawn = (n) => Object.values((S.dun[String(n)] || {}).cells || {}).some((c) => c.m === "O");
let omOpen = null;
function renderOM() {
  S.om = S.om || {};
  const box = $("oldmen"); box.replaceChildren();
  for (let n = 1; n <= 8; n++) {
    const o = S.om[n] || {};
    const auto = omDrawn(n), lit = auto || o.found || o.item;
    const name = o.item ? optName(OM_ITEMS, o.item) : null;
    const b = el("button", { type: "button", className: "om" + (lit ? " on" : "") + (o.item ? " took" : ""),
      title: `Level ${n} old man` + (name ? `: took ${name}` : lit ? ": found" : ": not found yet") });
    b.append(el("span", { className: "n", textContent: n }), icon(o.item || "cardD", o.item ? "it" : "man"));
    b.onclick = (e) => { e.stopPropagation(); openOM(n, b); };
    box.append(b);
  }
}
function openOM(n, btn) {
  const p = $("ompick"); omOpen = n; p.replaceChildren();
  const o = (S.om[n] = S.om[n] || {});
  p.append(el("div", { className: "ptitle", textContent: `Level ${n} old man: what did you take?` }));
  const g = el("div", { className: "omgrid" });
  for (const [img, name] of OM_ITEMS) {
    const b = el("button", { type: "button", className: "omi" + (o.item === img ? " sel" : ""), title: name }, [icon(img)]);
    b.onclick = () => { o.item = img; o.found = true; grant("om:" + n, img); save(); closeOM(); renderAll(); };
    g.append(b);
  }
  const found = el("button", { type: "button", className: "wide", textContent: o.found && !o.item ? "Not found" : "Found, nothing taken" });
  found.onclick = () => { o.found = !(o.found && !o.item); o.item = null; revoke("om:" + n); save(); closeOM(); renderAll(); };
  const clear = el("button", { type: "button", className: "wide quiet", textContent: "Clear" });
  clear.onclick = () => { delete S.om[n]; revoke("om:" + n); save(); closeOM(); renderAll(); };
  p.append(g, el("div", { className: "prow" }, [found, clear]));
  p.hidden = false;
  const r = btn.getBoundingClientRect(), host = p.parentElement.getBoundingClientRect();
  const w = Math.min(300, host.width - 16);
  p.style.width = w + "px";
  p.style.left = Math.max(8, Math.min(r.left - host.left, host.width - w - 8)) + "px";
  p.style.top = (r.bottom - host.top + 4) + "px";
}
function closeOM() { $("ompick").hidden = true; omOpen = null; }
document.addEventListener("click", (e) => { if (omOpen !== null && !$("ompick").contains(e.target)) closeOM(); });
document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeOM(); });

// ---------------------------------------------------------------- upgrades: none -> seen -> bought
console.assert(UPGRADES.length === PRICE.length);
// what each upgrade needs to be offered (lol_uptable's conditions, as far as the tracker knows them; "the first /
// second upgrade cave" ones are left out). An upgrade seen or bought always shows.
const own = (i) => (S.ups[i] || 0) === 2;
const has = (id, n = 1) => (S.items[id] || 0) >= n;
const UP_NEEDS = {
  0: () => has("sword") && !own(31), 1: () => has("wand") && !own(32), 2: () => !own(34), 4: () => has("sword") && !own(31),
  11: () => S.bombups >= 1, 12: () => has("potion"), 13: () => has("potion") && !own(35), 14: () => has("bow") && has("arrow"),
  18: () => (S.items.candle || 0) === 1, 19: () => has("bow") && !own(23), 20: () => S.bombups >= 1, 22: () => S.bombups >= 1,
  23: () => has("bow") && !own(19), 24: () => has("candle"), 25: () => S.hearts <= 3, 27: () => has("boom"),
  30: () => has("bait"), 31: () => has("sword") && S.hearts <= 3, 32: () => has("wand") && !own(1),
  33: () => has("recorder") && S.tri.length >= 1, 34: () => S.hearts === 3 && !has("ring") && !own(2),
  35: () => own(34) && has("potion") && !own(13), 37: () => has("boom"), 38: () => S.hearts >= 8,
};
const TIERS = [["Tier 1", "25-50"], ["Tier 2", "75-125"], ["Tier 3", "150-200"]];
const tierOf = (i) => (PRICE[i] <= 50 ? 0 : PRICE[i] <= 125 ? 1 : 2);
function renderUps() {
  const box = $("upgrades"); box.replaceChildren();
  const all = $("up-all").checked;
  TIERS.forEach(([tname, range], t) => {
    const row = el("div", { className: "upgrid" });
    let hidden = 0;
    UPGRADES.forEach((name, i) => {
      if (tierOf(i) !== t) return;
      const v = S.ups[i] || 0;
      const ok = !UP_NEEDS[i] || UP_NEEDS[i]();
      if (!ok && !v && !all) { hidden++; return; }
      const b = el("button", { type: "button", className: "up " + ["", "seen", "own"][v] + (ok ? "" : " locked"),
        title: `${name} (${PRICE[i]})` + (ok ? "" : ": not offered yet") });
      b.append(el("img", { src: `../manual/img/up_${String(i).padStart(2, "0")}.png`, className: "px", alt: name, draggable: false }));
      b.onmouseenter = () => { $("up-name").textContent = `${name} · ${PRICE[i]} rupees` + (ok ? "" : " · not offered yet"); };
      stepper(b, (d) => { S.ups[i] = (v + d + 3) % 3; save(); renderUps(); $("up-name").textContent = `${name} · ${["not seen", "seen", "bought"][S.ups[i]]}`; });
      row.append(b);
    });
    // (owner 2026-11-27) the hidden ones keep their room, as blank squares after the shown ones: the bar's size never
    // changes as more are offered (in Stream the whole page rescales when it does)
    for (let k = 0; k < hidden; k++) row.append(el("div", { className: "up ghost" }));
    const head = el("div", { className: "tierhead", textContent: `${tname} · ${range} rupees` + (hidden ? ` · ${hidden} hidden` : "") });
    head.dataset.short = `Tier ${t + 1}`;
    head.dataset.tn = `${t + 1}`;                         // (Stream + One map: just the number)                // (the Stream layout's bar shows this)
    box.append(head, row);
  });
}
$("up-all").addEventListener("change", renderUps);

// ---------------------------------------------------------------- overworld
const MARK = Object.fromEntries(MARKS.map((m) => [m[0], m]));
let picking = null;
function renderMap() {
  const map = $("map");
  map.querySelectorAll(".cell, .dim").forEach((c) => c.remove());
  // screens with nothing to find: greyed out
  const has = new Set([...ENTRANCES, ...Object.keys(FIXED).map(Number)]);
  for (let s = 0; s < 128; s++) {
    if (has.has(s)) continue;
    const d = el("div", { className: "dim" });
    d.style.left = `${(s & 15) * 6.25}%`; d.style.top = `${(s >> 4) * 12.5}%`;
    map.append(d);
  }
  const all = [...ENTRANCES, ...Object.keys(FIXED).map(Number)];
  for (const s of all) {
    const row = s >> 4, col = s & 15;
    const cell = el("button", { type: "button", className: "cell", title: "ABCDEFGH"[row] + (col + 1) });
    cell.dataset.s = s;
    cell.style.left = `${col * 6.25}%`; cell.style.top = `${row * 12.5}%`;
    if (FIXED[s]) { cell.classList.add("fixed"); cell.append(el("span", { className: "tag " + FIXED[s][1], textContent: FIXED[s][0] })); cell.disabled = true; }
    else {
      const m = MARK[S.ow[s]];
      if (m) cell.append(markTag(m[2], m[1]));
      else cell.classList.add("open");
      if (S.owDone[s]) cell.append(el("span", { className: "check", textContent: "✓" }));
      if (S.owBuy[s]) cell.title += ": bought " + SHOP_WARES.find((x) => x[0] === S.owBuy[s])[1];
      if (S.owX[s]) { cell.classList.add("xd"); cell.append(el("span", { className: "xmark", textContent: "✕" })); }
      // left click: what's here; right-click / long press: an X ("don't need it"), again to take it off
      const menu = () => (S.ow[s] === "shop" ? openShop(s, cell) : openPicker(s, cell));
      const xout = () => { if (S.owX[s]) delete S.owX[s]; else S.owX[s] = 1; save(); renderMap(); };
      cell.onclick = (e) => { e.stopPropagation(); menu(); };
      cell.oncontextmenu = (e) => { e.preventDefault(); e.stopPropagation(); xout(); };
      longPress(cell, xout);
    }
    map.append(cell);
  }
  $("spots").textContent = ENTRANCES.filter((s) => !S.ow[s] && !S.owX[s]).length;
  if (typeof showAccess === "function" && accShown) showAccess(accShown);
}
// (owner 2026-11-27; test page) what opens which entrance: point at (or tap) an icon under the overworld and the
// entrances that need it light up. The screens by how they open (ZORA's model of the overworld: both quests' secrets)
const B_ = [0x01, 0x03, 0x05, 0x07, 0x0D, 0x10, 0x12, 0x13, 0x14, 0x16, 0x1E, 0x26, 0x27, 0x2C, 0x2D, 0x33, 0x67, 0x71,
  0x76, 0x7B, 0x7C, 0x7D, 0x19];
const CANDLE_ = [0x28, 0x46, 0x47, 0x48, 0x4B, 0x4D, 0x51, 0x56, 0x5B, 0x62, 0x63, 0x68, 0x6A, 0x6B, 0x6D, 0x78];
const ACCESS = [   // id, icon (null: a label), name, screens
  ["open", null, "Open caves and the Armos' stairs", [0x04, 0x0A, 0x0B, 0x0C, 0x0E, 0x0F, 0x1A, 0x1C, 0x1F, 0x21, 0x22,
    0x25, 0x34, 0x37, 0x3D, 0x44, 0x4A, 0x4E, 0x5E, 0x64, 0x66, 0x6F, 0x70, 0x74, 0x75]],
  ["bomb", "bombs", "Bomb walls", B_],
  ["candle1", "candle1", "Bushes to burn (blue candle)", CANDLE_],
  ["candle2", "candle2", "Bushes to burn (red candle)", CANDLE_],
  ["bracelet", "bracelet", "Rocks to push (power bracelet)", [0x11, 0x1B]],
  ["recorder", "recorder", "The recorder's secrets", [0x3C, 0x42, 0x58]],
  ["raft", "raft", "Docks (raft)", [0x2F, 0x45]],
  ["ladder", "ladder", "Across the water (ladder; and a bomb)", [0x19]],
];
let accShown = null;                        // the one lit now (renderMap keeps it lit)
function showAccess(a) {
  accShown = a;
  $("map").classList.toggle("acc-on", !!a);
  $("map").querySelectorAll(".cell").forEach((c) => c.classList.toggle("acc-hit", !!a && a[3].includes(+c.dataset.s)));
  $("access").querySelectorAll("button").forEach((b) => b.classList.toggle("cur", !!a && b.dataset.id === a[0]));
}
function renderAccess() {
  const box = $("access"); box.replaceChildren();
  const show = showAccess;
  let held = null;                          // (a tap holds it on until another tap)
  for (const a of ACCESS) {
    const b = el("button", { type: "button", className: "acc", title: `${a[2]}: ${a[3].length}` });
    b.dataset.id = a[0];
    b.append(a[1] ? icon(a[1]) : el("span", { className: "acclabel", textContent: "OPEN" }));
    b.onmouseenter = () => show(a);
    b.onmouseleave = () => show(held);
    b.onclick = () => { held = held === a ? null : a; show(held); };
    box.append(b);
  }
}
renderAccess();
function openPicker(s, cell) {
  const p = $("picker"); picking = s; p.replaceChildren();
  p.append(el("div", { className: "ptitle", textContent: `${"ABCDEFGH"[s >> 4]}${(s & 15) + 1}: what's here?` }));
  const grid = el("div", { className: "pgrid" });
  for (const [v, label, cls, text] of MARKS) {
    // (owner 2026-11-27) a level, shrine or triforce cave already on another square: blacked out until it's taken off there
    const taken = (cls === "lvl" || cls === "shr" || cls === "tri") && Object.entries(S.ow).some(([k, x]) => +k !== s && x === v);
    const b = el("button", { type: "button", className: "pick " + cls + (S.ow[s] === v ? " sel" : "") + (taken ? " taken" : ""),
      title: taken ? `${text}: already on the map` : text, disabled: taken },
      // (owner 2026-11-27) a level or shrine: just its big box, the number or letter (no "Level" text)
      cls === "lvl" || cls === "shr" ? [markTag(cls, label)] : [markTag(cls, label), el("small", { textContent: text })]);
    b.onclick = () => {
      S.ow[s] = v; save(); closePicker(); renderMap();
      if (/^[LS]/.test(v)) {                       // a level or shrine: its map below
        S.cur = v.slice(1); save();
        if (brush === "O" && isShrine(S.cur)) brush = "room";
        renderBrushes(); renderDun();
      }
    };
    grid.append(b);
  }
  const done = el("button", { type: "button", className: "wide", textContent: S.owDone[s] ? "Unmark done" : "Mark done ✓" });
  done.onclick = () => { S.owDone[s] = !S.owDone[s]; save(); closePicker(); renderMap(); };
  const clear = el("button", { type: "button", className: "wide quiet", textContent: "Clear" });
  clear.onclick = () => { delete S.ow[s]; delete S.owDone[s]; delete S.owX[s]; delete S.owBuy[s]; revoke("shop:" + s); save(); closePicker(); renderAll(); };
  p.append(grid, el("div", { className: "prow" }, [done, clear]));
  p.hidden = false;
  // place it under the tile, inside the panel
  const r = cell.getBoundingClientRect(), host = p.parentElement.getBoundingClientRect();
  const w = Math.min(320, host.width - 16);
  p.style.width = w + "px";
  p.style.left = Math.max(8, Math.min(r.left - host.left, host.width - w - 8)) + "px";
  p.style.top = (r.bottom - host.top + 4) + "px";
}
// a shop's square, clicked: its wares; the one bought: an X on the map and into the inventory
function openShop(s, cell) {
  const p = $("picker"); picking = s; p.replaceChildren();
  p.append(el("div", { className: "ptitle", textContent: `${"ABCDEFGH"[s >> 4]}${(s & 15) + 1}: shop, what did you buy?` }));
  const grid = el("div", { className: "omgrid" });
  for (const [img, name, gives] of SHOP_WARES) {
    const b = el("button", { type: "button", className: "omi" + (S.owBuy[s] === img ? " sel" : ""), title: name }, [icon(img)]);
    const buy = (e) => {
      if (e) e.preventDefault();
      S.owBuy[s] = img; S.owX[s] = 1; if (gives) grant("shop:" + s, gives); else revoke("shop:" + s);
      save(); closePicker(); renderAll();
    };
    b.onclick = buy; b.oncontextmenu = buy;
    grid.append(b);
  }
  const change = el("button", { type: "button", className: "wide", textContent: "Change mark" });
  change.onclick = (e) => { e.stopPropagation(); openPicker(s, cell); };
  const undo = el("button", { type: "button", className: "wide quiet", textContent: "Not bought" });
  undo.onclick = () => { delete S.owBuy[s]; delete S.owX[s]; revoke("shop:" + s); save(); closePicker(); renderAll(); };
  p.append(grid, el("div", { className: "prow" }, [change, undo]));
  p.hidden = false;
  const r = cell.getBoundingClientRect(), host = p.parentElement.getBoundingClientRect();
  const w = Math.min(300, host.width - 16);
  p.style.width = w + "px";
  p.style.left = Math.max(8, Math.min(r.left - host.left, host.width - w - 8)) + "px";
  p.style.top = (r.bottom - host.top + 4) + "px";
}
function closePicker() { $("picker").hidden = true; picking = null; }
document.addEventListener("click", (e) => { if (picking !== null && !$("picker").contains(e.target)) closePicker(); });
document.addEventListener("keydown", (e) => { if (e.key === "Escape") closePicker(); });

// ---------------------------------------------------------------- dungeons
let brush = "room";
const BAR = ["room", "E", "erase"];   // the brushes above the map (the others: old saves' marks only)
const dun = (k) => (S.dun[k] = S.dun[k] || { name: "", done: false, cells: {}, doors: {}, g8: true });
function renderDTabs() {
  const t = $("dtabs"); t.replaceChildren();
  for (const k of DUNGEONS) {
    const d = S.dun[k];
    const b = el("button", { type: "button", className: "dtab" + (k === S.cur ? " cur" : "") + (d && d.done ? " done" : "") + (sideDone(k) ? " all" : ""),
      textContent: k, title: (/\d/.test(k) ? `Level ${k}` : `Shrine ${k}`) + (d && d.name ? `: ${d.name}` : "") });
    b.onclick = () => { S.cur = k; save(); if (brush === "O" && isShrine(k)) brush = "room"; renderBrushes(); renderDun(); };
    t.append(b);
  }
}
// old men: none in the shrines, one per level 1-8 (drawing another moves it); level 9 is free
const isShrine = (k) => /[A-D]/.test(k);
function renderBrushes() {
  const b = $("brushes"); b.replaceChildren();
  for (const [id, label, title] of BRUSHES) {
    if (!BAR.includes(id)) continue;
    const off = id === "O" && isShrine(S.cur);
    const btn = el("button", { type: "button", className: "brush" + (id === brush ? " cur" : ""), disabled: off,
      title: off ? "Shrines have no old man" : id === "O" && S.cur !== "9" ? "Old man (one per level)" : title });
    btn.append(id === "room" ? el("i", { className: "sw" }) : id === "E" ? entArrow("bar") : el("span", { textContent: label }),
      el("small", { textContent: id === "room" ? "Room" : id === "erase" ? "Remove" : title.split(" ")[0] }));
    btn.onclick = () => { brush = id; renderBrushes(); };
    b.append(btn);
  }
}
// the room grid: 8 x 8 rooms, a door slot between each two neighbours. A door: click green, right-click a wall (a
// thin red line; the same again: none), the mouse wheel through green, yellow, dark blue, red, purple. A room: right-click / click as the
// brush says; the wheel (down) opens its item list (map, compass, key, bomb, triforce, potion, I).
const DOORS = ["green", "yellow", "navy", "red", "purple"];
const WALL_V = 9;                      // (owner 2026-11-27) right-click: a wall, a thin red line along the side
const RITEMS = [["map", "map.png", "Map"], ["compass", "compass.png", "Compass"], ["key", "key.png", "Key"],
  ["bomb", "bombs.png", "Bomb"], ["tri", "triforce.png", "Triforce"], ["potion", "potion1.png", "Potion"], ["rupee5", "rupee.png", "5 rupees"], ["I", null, "I"]];
const RENEMIES = [["dig", "en_digdogger.png", "Digdogger"], ["gohma", "en_gohma.png", "Blue Gohma"], ["gleeok", "en_gleeok.png", "Gleeok"],
  ["wiz", "en_wizzrobe.png", "Blue Wizzrobes"], ["nut", "en_darknut.png", "Blue Darknuts"], ["dod", "en_dodongo.png", "Dodongos"]];
// a room's kind (right-click with the Room brush): a plain room, three moats, the old man, item stairs, numbers 1-8
const RKINDS = [["blank", "Blank room"], ["vmoat", "Vertical moat"], ["hmoat", "Horizontal moat"], ["hmoat2", "Double horizontal moat"],
  ["chevy", "Chevy moat"], ["circle", "Square moat"], ["hchute", "Horizontal chute"], ["vchute", "Vertical chute"],
  ["O", "Old man"], ["stair", "Item stairs"], ...[1, 2, 3, 4, 5, 6, 7, 8].map((n) => ["n" + n, String(n)]), ["q", "?"], ["x", "Remove room"]];
const ART = {
  // (owner 2026-11-27) the moats as the rooms have them: the vertical one east of the middle, the horizontal one
  // north of it; the Chevy room all water but the land: its chevy shape in the middle and a spot by each door
  vmoat: '<rect x="60" y="0" width="14" height="100"/>',
  hmoat: '<rect x="0" y="24" width="100" height="14"/>',
  hmoat2: '<rect x="0" y="22" width="100" height="13"/><rect x="0" y="65" width="100" height="13"/>',
  chevy: '<path fill-rule="evenodd" d="M0 0 H100 V100 H0 Z M14 38 H32 V26 H68 V38 H86 V62 H68 V74 H32 V62 H14 Z'
    + ' M40 0 H60 V12 H40 Z M40 88 H60 V100 H40 Z M0 40 H10 V60 H0 Z M90 40 H100 V60 H90 Z"/>',
  circle: '<path fill-rule="evenodd" d="M14 14 H86 V86 H14 Z M27 27 V73 H73 V27 Z"/>',      // (the square moat: id kept)
  hchute: '<rect class="blk" x="10" y="28" width="80" height="10"/><rect class="blk" x="10" y="62" width="80" height="10"/>',
  vchute: '<rect class="blk" x="34" y="8" width="8" height="84"/><rect class="blk" x="58" y="8" width="8" height="84"/>',
  stair: '<path class="st" d="M20 80 H40 V62 H58 V44 H76 V26 H86 V80 Z"/>',
};
function roomArt(kind) {
  if (kind === "O") return el("img", { src: "img/cardD.png", className: "rk px", alt: "Old man", draggable: false });
  if (kind === "x") return el("b", { className: "rk rx", textContent: "✕" });
  if (/^n\d$/.test(kind)) return el("b", { className: "rk rn c" + kind.slice(1), textContent: kind.slice(1) });
  if (kind === "q") return el("b", { className: "rk rn rq", textContent: "?" });            // (owner 2026-11-27) not sure yet
  if (ART[kind]) {
    const w = document.createElement("span"); w.className = "rk art " + kind;
    w.innerHTML = `<svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">${ART[kind]}</svg>`
      + (kind === "stair" ? '<b class="si">I</b>' : "");                 // (item stairs: a capital I by them)
    return w;
  }
  return null;
}
let rpicking = null;
// the entrance: an arrow from the south, over the room's south door
function entArrow(cls) {
  const w = document.createElement("span"); w.className = "ent " + cls;
  w.innerHTML = '<svg viewBox="0 0 10 16" aria-hidden="true"><path d="M5 0 L10 6 H6.5 V16 H3.5 V6 H0 Z"/></svg>';
  return w;
}
function wheelDir(e) { return e.deltaY > 0 ? 1 : e.deltaY < 0 ? -1 : 0; }
// (touch screens have no wheel: a long press does the wheel-down step; the click after it is dropped)
function longPress(node, fn) {
  let held = null, longed = false;
  node.addEventListener("touchstart", () => { longed = false; held = setTimeout(() => { longed = true; fn(); }, 450); }, { passive: true });
  ["touchend", "touchmove", "touchcancel"].forEach((t) => node.addEventListener(t, () => clearTimeout(held)));
  node.addEventListener("click", (e) => { if (longed) { longed = false; e.stopImmediatePropagation(); e.preventDefault(); } }, true);
}
function renderDun() {
  renderDTabs(); renderSide();
  const d = dun(S.cur);
  d.doors = d.doors || {};
  $("ddone").checked = d.done;
  renderQuest(); renderNicknames();
  // LEVEL-X / SHRINE-X, one letter over each column (as the game's map screen: lines your map up with it)
  const lab = (isShrine(S.cur) ? "SHRINE-" : "LEVEL-") + S.cur;
  $("dlabel").setAttribute("aria-label", lab);
  $("dlabel").replaceChildren(...[...lab.padEnd(8, " ")].slice(0, 8).map((ch, c) => {
    const s = el("span", { textContent: ch.trim() }); s.style.gridColumn = String(c * 2 + 1); s.ariaHidden = "true"; return s;
  }));
  const g = $("dgrid"); g.replaceChildren();
  const redraw = () => { save(); renderDun(); renderOM(); };
  for (let row = 0; row < 8; row++) for (let col = 0; col < 8; col++) {
    const i = row * 8 + col;
    const c = d.cells[i] || {};
    const cell = el("button", { type: "button", className: "room" + (c.r ? " r" + c.r : ""), title: "ABCDEFGH"[row] + (col + 1) });
    cell.style.gridRow = String(row * 2 + 1); cell.style.gridColumn = String(col * 2 + 1);
    const it = RITEMS.find((x) => x[0] === c.it);
    if (it) cell.append(it[1] ? el("img", { src: "img/" + it[1], className: "rit px", alt: it[2], draggable: false })
      : el("b", { className: "rit ri", textContent: "I" }));
    const en = RENEMIES.find((x) => x[0] === c.en);
    if (en) cell.append(el("img", { src: "img/" + en[1], className: "ren px", alt: en[2], title: en[2], draggable: false }));
    const kind = c.m === "O" ? "O" : c.k;
    const art = kind && roomArt(kind); if (art) cell.prepend(art);
    if (c.m === "E") cell.append(entArrow("in"));
    else if (c.m && c.m !== "O") cell.append(el("span", { className: "mk", textContent: (BRUSHES.find((x) => x[0] === c.m) || [, "?"])[1] }));
    // (owner, 2026-11-26: left and right swapped) right-click: what the brush draws (the Room brush: its kind)
    cell.oncontextmenu = (e) => {
      e.preventDefault();
      if (brush === "erase") { delete d.cells[i]; redraw(); return; }
      if (!Object.keys(d.cells).length) {                 // an empty map: the first room is the entrance
        d.cells[i] = { r: 1, m: "E" }; redraw(); return;
      }
      if ((d.cells[i] || {}).m === "O" && (brush === "O" || brush === "room") && /^[1-8]$/.test(S.cur)) {
        e.stopPropagation(); openOMRoom(+S.cur, cell); return;                // his room again: what did you take?
      }
      if (brush === "room") { e.stopPropagation(); openKinds(i, cell, e); return; }
      const cur = d.cells[i] || {};
      if (brush === "O" && isShrine(S.cur)) return;
      cur.m = cur.m === brush ? undefined : brush; if (cur.m && !cur.r) cur.r = 1;
      if ((cur.m === "O" && S.cur !== "9") || cur.m === "E")   // one old man per level 1-8, one entrance: drawing another moves it
        for (const [j, c] of Object.entries(d.cells)) if (+j !== i && c.m === cur.m) { delete c.m; if (!c.r && !c.it && !c.en && !c.k) delete d.cells[j]; }
      if (!cur.r && !cur.m && !cur.it && !cur.en && !cur.k) delete d.cells[i]; else d.cells[i] = cur;
      redraw();
    };
    // click: a plain room; again, cleared; again, not cleared
    cell.onclick = (e) => {
      if (!Object.keys(d.cells).length) { d.cells[i] = { r: 1, m: "E" }; redraw(); return; }
      const cur = d.cells[i] || {};
      cur.r = cur.r === 1 ? 2 : 1; d.cells[i] = cur; redraw();
    };
    cell.addEventListener("wheel", (e) => {
      e.preventDefault();
      const w = wheelDir(e);
      if (w > 0) openRoomItems(i, cell); else if (w < 0) openRoomItems(i, cell, true);
    }, { passive: false });
    longPress(cell, () => openRoomItems(i, cell));
    g.append(cell);
  }
  // doors: "h" between a room and the one east of it, "v" between a room and the one south of it
  for (let row = 0; row < 8; row++) for (let col = 0; col < 8; col++) {
    for (const k of ["h", "v"]) {
      if ((k === "h" && col === 7) || (k === "v" && row === 7)) continue;
      const key = `${k}${row * 8 + col}`, v = d.doors[key] || 0;
      const dc = v === WALL_V ? "wall" : DOORS[v - 1];
      const door = el("button", { type: "button", className: `door ${k}` + (v ? " " + dc : ""),
        title: v ? `Door: ${dc === "navy" ? "dark blue" : dc === "wall" ? "wall (red line)" : dc}` : "Door" });
      door.style.gridRow = String(k === "h" ? row * 2 + 1 : row * 2 + 2);
      door.style.gridColumn = String(k === "h" ? col * 2 + 2 : col * 2 + 1);
      door.append(el("i"));
      const set = (n) => { if (n) d.doors[key] = n; else delete d.doors[key]; save(); renderDun(); };
      door.onclick = () => set(v === 1 ? 0 : 1);                           // click: green (again: none)
      door.oncontextmenu = (e) => { e.preventDefault(); set(v === WALL_V ? 0 : WALL_V); };   // right-click: a wall (again: none)
      door.addEventListener("wheel", (e) => {
        e.preventDefault();
        const w = wheelDir(e); if (!w) return;
        set(v ? ((v - 1 + w + DOORS.length) % DOORS.length) + 1 : (w > 0 ? 1 : DOORS.length));
      }, { passive: false });
      longPress(door, () => set(v ? (v % DOORS.length) + 1 : 1));
      g.append(door);
    }
  }
  drawShape();
}
function openRoomItems(i, cell, enemies = false) {
  const p = $("rpick"), d = dun(S.cur); rpicking = i; p.replaceChildren();
  const list = enemies ? RENEMIES : RITEMS, field = enemies ? "en" : "it";
  p.append(el("div", { className: "ptitle", textContent: `${"ABCDEFGH"[i >> 3]}${(i & 7) + 1}: ${enemies ? "enemy" : "item"}` }));
  const grid = el("div", { className: "rgrid" });
  const keep = (c) => { if (!c.r && !c.m && !c.it && !c.en) delete d.cells[i]; else d.cells[i] = c; };
  for (const [id, img, name] of list) {
    const cur = (d.cells[i] || {})[field] === id;
    const b = el("button", { type: "button", className: "rpi" + (cur ? " sel" : "") + (enemies ? " en" : ""), title: name },
      [img ? el("img", { src: "img/" + img, className: "px", alt: name, draggable: false }) : el("b", { textContent: "I" })]);
    b.onclick = () => {
      const c = d.cells[i] || {};
      if (c[field] === id) delete c[field]; else { c[field] = id; if (!c.r) c.r = 1; }
      keep(c); save(); closeRoomItems(); renderDun();
    };
    grid.append(b);
  }
  const clear = el("button", { type: "button", className: "wide quiet", textContent: enemies ? "No enemy" : "No item" });
  clear.onclick = () => { const c = d.cells[i]; if (c) { delete c[field]; keep(c); } save(); closeRoomItems(); renderDun(); };
  const other = el("button", { type: "button", className: "wide", textContent: enemies ? "Items" : "Enemies" });
  other.onclick = (e) => { e.stopPropagation(); openRoomItems(i, cell, !enemies); };
  p.append(grid, el("div", { className: "prow" }, [other, clear]));
  p.hidden = false;
  const r = cell.getBoundingClientRect(), host = p.parentElement.getBoundingClientRect();
  const w = Math.min(260, host.width - 16);
  p.style.width = w + "px";
  p.style.left = Math.max(8, Math.min(r.left - host.left, host.width - w - 8)) + "px";
  p.style.top = (r.bottom - host.top + 4) + "px";
}
function openKinds(i, cell, ev) {
  const p = $("rpick"), d = dun(S.cur); rpicking = i; p.replaceChildren();
  const c0 = d.cells[i] || {};
  p.append(el("div", { className: "ptitle", textContent: `${"ABCDEFGH"[i >> 3]}${(i & 7) + 1}: room` }));
  const grid = el("div", { className: "rgrid kinds" });
  for (const [id, name] of RKINDS) {
    if (id === "O" && isShrine(S.cur)) continue;
    const cur = id === "x" ? false : id === "O" ? c0.m === "O" : (c0.k || "blank") === id && c0.r;
    // a number: two rooms a level at most (a pair of stairs)
    const used = /^n/.test(id) ? Object.entries(d.cells).filter(([j, o]) => +j !== i && o.k === id).length : 0;
    const full = used >= 2;
    const b = el("button", { type: "button", className: "rpi kind" + (cur ? " sel" : ""), disabled: full,
      title: full ? `${name}: already in two rooms` : name });
    const pv = el("span", { className: "kpv" }); const a = roomArt(id); if (a) pv.append(a);
    b.append(pv); if (!/^n/.test(id) && id !== "q") b.append(el("small", { textContent: name }));
    b.onclick = () => {
      if (id === "x") { delete d.cells[i]; save(); closeRoomItems(); renderDun(); renderOM(); return; }
      const c = d.cells[i] || {};
      if (!c.r) c.r = 1;
      if (id === "O") {
        c.m = "O";
        if (S.cur !== "9") for (const [j, o] of Object.entries(d.cells)) if (+j !== i && o.m === "O") { delete o.m; if (!o.r && !o.it && !o.en && !o.k) delete d.cells[j]; }
      } else {
        if (c.m === "O") delete c.m;
        if (id === "blank") delete c.k; else c.k = id;
      }
      d.cells[i] = c; save(); closeRoomItems(); renderDun(); renderOM();
    };
    grid.append(b);
  }
  p.append(grid);
  p.hidden = false;
  const r = cell.getBoundingClientRect(), host = p.parentElement.getBoundingClientRect();
  const w = Math.min(300, host.width - 16);
  p.style.width = w + "px";
  p.style.left = Math.max(8, Math.min(r.left - host.left, host.width - w - 8)) + "px";
  // (owner 2026-11-27) its bottom at the cursor (the cell's middle without one), kept on the page
  const y = ev && ev.clientY ? ev.clientY : (r.top + r.bottom) / 2;
  p.style.top = Math.max(8 - host.top, y - host.top - p.offsetHeight) + "px";
}
function openOMRoom(n, cell) {
  const p = $("rpick"); rpicking = -1; p.replaceChildren();
  const o = (S.om[n] = S.om[n] || {});
  p.append(el("div", { className: "ptitle", textContent: `Level ${n} old man: what did you take?` }));
  const grid = el("div", { className: "omgrid" });
  for (const [img, name] of OM_ITEMS) {
    const b = el("button", { type: "button", className: "omi" + (o.item === img ? " sel" : ""), title: name }, [icon(img)]);
    b.onclick = () => { o.item = img; o.found = true; grant("om:" + n, img); save(); closeRoomItems(); renderAll(); };
    grid.append(b);
  }
  if (S.ug) grid.append(ugButton(cell, `Level ${n} old man`, 0, o.item,
    (img, lit) => { o.item = img; o.found = true; grant("om:" + n, img, lit); save(); }));
  const none = el("button", { type: "button", className: "wide quiet", textContent: "Nothing taken" });
  none.onclick = () => { o.item = null; o.found = true; revoke("om:" + n); save(); closeRoomItems(); renderAll(); };
  const row = [none];
  if (cell.parentElement && cell.parentElement.id === "dgrid") {
    const kind = el("button", { type: "button", className: "wide", textContent: "Room type" });
    const ci = [...cell.parentElement.children].indexOf(cell);
    kind.onclick = (e) => { e.stopPropagation(); openKinds(ci, cell); };
    row.unshift(kind);
  }
  p.append(grid, el("div", { className: "prow" }, row));
  p.hidden = false;
  const r = cell.getBoundingClientRect(), host = p.parentElement.getBoundingClientRect();
  const w = Math.min(300, host.width - 16);
  p.style.width = w + "px";
  p.style.left = Math.max(8, Math.min(r.left - host.left, host.width - w - 8)) + "px";
  p.style.top = (r.bottom - host.top + 4) + "px";
}
function closeRoomItems() { $("rpick").hidden = true; rpicking = null; }
document.addEventListener("click", (e) => { if (rpicking !== null && !$("rpick").contains(e.target)) closeRoomItems(); });
document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeRoomItems(); });
$("dname").addEventListener("change", (e) => { dun(S.cur).name = e.target.value; save(); renderDTabs(); drawShape(); });
// the chosen nickname's outline: a faint line around its rooms on this map (SHAPES: shapes.js)
function drawShape() {
  const g = $("dgrid"); if (!g) return;
  g.querySelector(".shape")?.remove();
  const key = shapeKey(mapQuest(S.cur), dun(S.cur).name || "");
  if (!key) return;
  const set = new Set(SHAPES[key]), rooms = g.querySelectorAll(".room");
  if (rooms.length < 64) return;
  const gap = (rooms[1].offsetLeft - rooms[0].offsetLeft - rooms[0].offsetWidth) / 2;
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("class", "shape"); svg.setAttribute("aria-hidden", "true");
  let d = "";
  for (const i of set) {
    const r = rooms[i], row = i >> 3, col = i & 7, W = g.clientWidth - 1, H = g.clientHeight - 1;
    const x0 = Math.max(1, r.offsetLeft - gap), y0 = Math.max(1, r.offsetTop - gap),
      x1 = Math.min(W, r.offsetLeft + r.offsetWidth + gap), y1 = Math.min(H, r.offsetTop + r.offsetHeight + gap);
    if (row === 0 || !set.has(i - 8)) d += `M${x0} ${y0}H${x1}`;
    if (row === 7 || !set.has(i + 8)) d += `M${x0} ${y1}H${x1}`;
    if (col === 0 || !set.has(i - 1)) d += `M${x0} ${y0}V${y1}`;
    if (col === 7 || !set.has(i + 1)) d += `M${x1} ${y0}V${y1}`;
  }
  const p = document.createElementNS("http://www.w3.org/2000/svg", "path"); p.setAttribute("d", d);
  svg.append(p); g.append(svg);
}
if (window.ResizeObserver) new ResizeObserver(() => drawShape()).observe($("dgrid"));
$("ddone").addEventListener("change", (e) => { dun(S.cur).done = e.target.checked; save(); renderDTabs(); });
$("dclear").addEventListener("click", () => { dun(S.cur).cells = {}; dun(S.cur).doors = {}; save(); renderDun(); renderOM(); });
// each level's own set (LoL, 1Q-4Q: the row above its nickname box): which nicknames the box offers, its side
// column's layout (floor item, item stairs) and the outlines. A level not set yet takes the last set picked.
const QUESTS = [["lol", "LoL"], ["1q", "1Q"], ["2q", "2Q"], ["3q", "3Q"], ["4q", "4Q"], ["custom", "Custom"]];
// Custom (Chaos or Mixed): any dungeon of any set, the quests' as "2Q 4 - The D"
const CUSTOM_NAMES = () => [...QNAMES.lol, ...["1q", "2q", "3q", "4q"].flatMap((q) => QNAMES[q].map((n, i) => `${q.toUpperCase()} ${i + 1} - ${n}`))];
// a nickname as the dropdown shows it -> its SHAPES key (undefined: no outline)
function shapeKey(q, name) {
  let m;
  if (q === "custom") {
    if ((m = /^([1-4])Q (\d) - (.+)$/.exec(name))) return `${m[1]}q:${m[3]}`;
    return SHAPES["lol:" + name] ? "lol:" + name : undefined;
  }
  const k = `${q}:${name.replace(/^\d\s*-\s*/, "")}`;
  return SHAPES[k] ? k : undefined;
}
const QNAMES = {
  lol: NICKNAMES.slice(0, NICKNAMES.indexOf("The Eagle")),
  "1q": ["The Eagle", "The Moon", "The Manji", "The Snake", "The Lizard", "The Dragon", "The Demon", "The Lion", "The Skull"],
  "2q": ["The E", "The A", "The L", "The D", "The Z", "The Cap", "The Flail", "The Whip", "The Pig"],
  "3q": ["The Sword", "The Kite", "The Islands", "The Candle", "The Crane", "The Dancer", "The Lock Picks", "The Vire", "The Serpent"],
  "4q": ["The Bow and Arrow", "The Rabbit", "The Broken Boomerang", "The Whirlwind", "The Hammer", "The Scorpion", "The Armos",
    "The Crown", "The Swiss Cheese"],
};
// levels 1-8: [item stairs, floor item] (level 9: two item stairs in every set)
const LAYOUT = {
  lol: { 1: [1, 1], 2: [0, 1], 3: [1, 0], 4: [1, 0], 5: [1, 0], 6: [1, 0], 7: [1, 0], 8: [2, 0] },
  "2q": { 1: [0, 1], 2: [1, 0], 3: [0, 1], 4: [2, 0], 5: [1, 0], 6: [1, 0], 7: [1, 0], 8: [2, 0] },
  "3q": { 1: [1, 1], 2: [1, 0], 3: [1, 0], 4: [1, 1], 5: [1, 0], 6: [1, 1], 7: [0, 1], 8: [1, 1] },
  "4q": { 1: [0, 1], 2: [0, 1], 3: [0, 1], 4: [1, 0], 5: [0, 1], 6: [1, 1], 7: [0, 1], 8: [1, 1] },
};
LAYOUT["1q"] = LAYOUT.lol;
const mapQuest = (k) => {
  const q = (S.mq || {})[k] || S.qlast || "lol";
  return /[A-D]/.test(k) && q !== "custom" ? "lol" : q;               // (shrines: LoL's, or Custom)
};
const layoutOf = (lv) => {
  const q = mapQuest(String(lv));
  if (q !== "custom") return LAYOUT[q][lv];
  const m = /^([1-4])Q (\d) - /.exec(dun(String(lv)).name || "");      // (Custom: a quest level on its own number: its layout)
  return LAYOUT[m && +m[2] === lv ? m[1] + "q" : "lol"][lv];
};
function renderQuest() {
  const box = $("dquest"); box.replaceChildren();
  const k = S.cur, cur = mapQuest(k);
  for (const [q, name] of QUESTS) {
    if (isShrine(k) && q !== "lol" && q !== "custom") continue;      // (shrines: LoL's, or Custom)
    const b = el("button", { type: "button", className: "qbtn" + (cur === q ? " cur" : ""), textContent: name,
      title: `Level ${k}: ${name}`, ariaPressed: String(cur === q) });
    b.onclick = () => { S.mq = S.mq || {}; S.mq[k] = q; S.qlast = q; save(); renderAll(); };
    box.append(b);
  }
  // the pencil (a quest): every level 1-9 that quest, each named its own level's nickname (its outline on its map);
  // again: those names off
  const ug = el("button", { type: "button", className: "qbtn ugt" + (S.ug ? " cur" : ""), textContent: "UG",
    title: "Upgrade mix: an UG choice in the item spots' pickers (old men, item stairs, floor items, prizes)", ariaPressed: String(!!S.ug) });
  ug.onclick = () => { S.ug = !S.ug; save(); renderAll(); };
  box.append(ug);
  if (isShrine(k)) return;
  const on = !["lol", "custom"].includes(cur) && S.autoq === cur;
  const pen = el("button", { type: "button", className: "qbtn pen" + (on ? " cur" : ""), disabled: cur === "lol" || cur === "custom",
    title: cur === "lol" || cur === "custom" ? "Pick a quest (1Q-4Q) to fill in its levels" : on ? `Clear the ${cur.toUpperCase()} outlines`
      : `Put all nine ${cur.toUpperCase()} outlines on their maps`, ariaPressed: String(on), ariaLabel: "Fill in the quest's levels" });
  pen.innerHTML = '<svg viewBox="0 0 24 24" width="15" height="15" aria-hidden="true"><path d="M4 20l1-5L16 4l4 4L9 19z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/><path d="M14 6l4 4" stroke="currentColor" stroke-width="2"/></svg>';
  pen.onclick = () => {
    S.mq = S.mq || {};
    for (let lv = 1; lv <= 9; lv++) {
      const d = dun(String(lv)), auto = `${lv} - ${QNAMES[cur][lv - 1]}`;
      if (on) { if (d.name === auto) d.name = ""; }
      else { S.mq[lv] = cur; d.name = auto; }
    }
    S.autoq = on ? null : cur; S.qlast = cur; save(); renderAll();
  };
  box.append(pen);
}
function renderNicknames() {
  // the dungeons this map can be: its set's (LoL: the designs that can be this level / a shrine), then only those
  // whose outline holds every room marked here
  const k = S.cur, q = mapQuest(k), d = dun(k), cls = /^\d$/.test(k) ? k : "S";
  const names = q === "custom" ? CUSTOM_NAMES()                       // (Chaos / Mixed: any dungeon anywhere)
    : q === "lol" ? QNAMES.lol.filter((n) => (SHAPE_CLASSES[n] || "").includes(cls))
    : QNAMES[q].map((n, i) => `${i + 1} - ${n}`);                        // (a quest: "level - name", in order)
  const rooms = Object.entries(d.cells).filter(([, c]) => c.r || c.m || c.k || c.it || c.en).map(([i]) => +i);
  // (the entrance: a room with none of the dungeon's rooms south of it, the way in being from the south)
  const ent = Object.entries(d.cells).find(([, c]) => c.m === "E");
  const fits = (n) => {
    const sh = SHAPES[shapeKey(q, n)];
    const e = ent && +ent[0];                     // (level 9: the old man's room and one more north of it too)
    return !sh || (rooms.every((r) => sh.includes(r)) && (!ent || (!sh.includes(e + 8) &&
      (k !== "9" || (sh.includes(e - 8) && sh.includes(e - 16))))));
  };
  const ok = names.filter(fits);
  const head = !rooms.length ? "Nickname" : ok.length ? `Nickname (${ok.length} of ${names.length} fit your rooms)`
    : "No dungeon fits your rooms";
  const opts = [el("option", { value: "", textContent: head }), ...ok.map((n) => el("option", { value: n, textContent: n }))];
  if (d.name && !ok.includes(d.name)) opts.push(el("option", { value: d.name, textContent: d.name + " (doesn't fit)" }));
  $("dname").replaceChildren(...opts);
  $("dname").value = d.name || "";
}

// ---------------------------------------------------------------- timer, notes, new run
function fmt(ms) {
  const t = Math.floor(ms / 1000);
  return `${Math.floor(t / 3600)}:${String(Math.floor(t / 60) % 60).padStart(2, "0")}:${String(t % 60).padStart(2, "0")}`;
}
const elapsed = () => S.timer.acc + (S.timer.start ? Date.now() - S.timer.start : 0);
function tick() { $("clock").textContent = fmt(elapsed()); $("t-go").textContent = S.timer.start ? "Pause" : (S.timer.acc ? "Resume" : "Start"); }
$("t-go").onclick = () => {
  if (S.timer.start) { S.timer.acc += Date.now() - S.timer.start; S.timer.start = null; } else S.timer.start = Date.now();
  save(); tick();
};
$("t-reset").onclick = () => { S.timer = { acc: 0, start: null }; save(); tick(); };
setInterval(tick, 500);
$("notes").value = S.notes;
$("notes").addEventListener("input", (e) => { S.notes = e.target.value; save(); });
$("reset-all").onclick = () => { $("confirm").hidden = false; };
$("c-no").onclick = () => { $("confirm").hidden = true; };
$("c-yes").onclick = () => { S = fresh(); save(); $("confirm").hidden = true; $("notes").value = ""; renderAll(); };

// (saves from before 0.355: the 16 x 8 grid -> 8 x 8; the half that was drawn on)
for (const d of Object.values(S.dun)) {
  if (d.g8) continue;
  const keys = Object.keys(d.cells || {}).map(Number);
  const off = keys.length && keys.every((i) => (i & 15) >= 8) ? 8 : 0;
  const cells = {};
  for (const i of keys) { const col = (i & 15) - off; if (col >= 0 && col < 8) cells[(i >> 4) * 8 + col] = d.cells[i]; }
  d.cells = cells; d.doors = d.doors || {}; d.g8 = true;
}
// (saves from before 0.306: no old man in the shrines, one per level 1-8)
for (const [k, d] of Object.entries(S.dun)) {
  let seen = false;
  for (const [i, c] of Object.entries(d.cells || {})) {
    if (c.m !== "O") continue;
    if (/[A-D]/.test(k) || (k !== "9" && seen)) { delete c.m; if (!c.r) delete d.cells[i]; } else seen = true;
  }
}


// ---------------------------------------------------------------- the dungeon map's side column
// levels 1-8: the triforce piece, the old man, the blue potion; level 1-2's floor item, the item stairs (none in level 2,
// two in level 8); level 9: its two item stairs, Ganon, Zelda. What's picked goes into the panels above too.
const BOXOPTS = [["cardS", "Shop card"], ["cardD", "Dungeon card"], ["cardX", "Shrine card"], ["xp1", "XP bag"],
  ["xp2", "Big XP bag"], ["potion2", "Red potion"]];
const L9OPTS = [["arrow2", "Silver arrows"], ["ring2", "Red ring"], ["sword3", "Magical sword"], ["boom2", "Magical boomerang"],
  ["candle2", "Red candle"], ["book2", "Blue book"], ["shield", "Magical shield"], ["potion2", "Red potion"],
  ["xp1", "XP bag"], ["xp2", "Big XP bag"]];
const PRIZEOPTS = [...ITEMS.flatMap(([, steps, names]) => steps.map((st, i) => [st, names[i]])),
  ["cardS", "Shop card"], ["cardD", "Dungeon card"], ["cardX", "Shrine card"], ["xp1", "XP bag"], ["xp2", "Big XP bag"]];
// a level / shrine whose side column is all marked: green in the tabs and the Triforce and Shrines panel
function sideDone(k) {
  const sd = (S.side || {})[k]; if (!sd) return false;
  if (/[A-D]/.test(k)) return !!sd.prize;
  const lv = +k, st = sd.st || [], bx = sd.box || [];
  if (lv === 9) return !!(st[0] && st[1] && sd.ganon && sd.zelda);
  const o = S.om[lv] || {};
  const [nst, flr] = layoutOf(lv);
  return S.tri.includes(lv) && !!sd.pot && !!(o.item || o.found) && (!flr || !!bx[0]) &&
    st.slice(0, nst).filter(Boolean).length === nst;
}
// (Upgrade mix) UG: the tier's upgrades Link may be offered now (tier -1: any); left-click shows it in the box,
// right-click also marks it bought
function ugButton(btn, title, tier, cur, pick) {
  const b = el("button", { type: "button", className: "omi ug" + (UPI(cur) ? " sel" : ""), title: "An upgrade", textContent: "UG" });
  b.onclick = (e) => { e.stopPropagation(); upPick(btn, title, tier, cur, pick); };
  return b;
}
function upPick(btn, title, tier, cur, pick) {
  const p = $("rpick"); rpicking = -2; p.replaceChildren();
  p.append(el("div", { className: "ptitle", textContent: `${title}: which upgrade? (right-click: bought)` }));
  const grid = el("div", { className: "omgrid" });
  UPGRADES.forEach((name, i) => {
    if (tier >= 0 && tierOf(i) !== tier) return;
    const ok = !UP_NEEDS[i] || UP_NEEDS[i](), v = `up:${i}`;
    if ((!ok || (S.ups[i] || 0) === 2) && cur !== v) return;
    const b = el("button", { type: "button", className: "omi" + (cur === v ? " sel" : ""), title: name }, [icon(v)]);
    b.onclick = () => { pick(v, false); closeRoomItems(); renderAll(); };
    b.oncontextmenu = (e) => { e.preventDefault(); pick(v, true); closeRoomItems(); renderAll(); };
    grid.append(b);
  });
  if (!grid.children.length) grid.append(el("div", { className: "hint", textContent: "None offered now" }));
  p.append(grid);
  p.hidden = false;
  const r = btn.getBoundingClientRect(), host = p.parentElement.getBoundingClientRect();
  const w = Math.min(300, host.width - 16);
  p.style.width = w + "px";
  p.style.left = Math.max(8, Math.min(r.left - host.left - w + r.width, host.width - w - 8)) + "px";
  p.style.top = (r.bottom - host.top + 4) + "px";
}
function sidePick(btn, title, opts, cur, pick, clear, tier = null) {
  const p = $("rpick"); rpicking = -2; p.replaceChildren();
  p.append(el("div", { className: "ptitle", textContent: title }));
  const grid = el("div", { className: "omgrid" });
  for (const [img, name] of opts) {
    const b = el("button", { type: "button", className: "omi" + (cur === img ? " sel" : ""), title: name }, [icon(img)]);
    b.onclick = () => { pick(img); closeRoomItems(); };
    grid.append(b);
  }
  if (S.ug && tier !== null) grid.append(ugButton(btn, title, tier, cur, pick));
  const none = el("button", { type: "button", className: "wide quiet", textContent: "Clear" });
  none.onclick = () => { clear(); closeRoomItems(); };
  p.append(grid, el("div", { className: "prow" }, [none]));
  p.hidden = false;
  const r = btn.getBoundingClientRect(), host = p.parentElement.getBoundingClientRect();
  const w = Math.min(300, host.width - 16);
  p.style.width = w + "px";
  p.style.left = Math.max(8, Math.min(r.left - host.left - w + r.width, host.width - w - 8)) + "px";
  p.style.top = (r.bottom - host.top + 4) + "px";
}
function stairArt() {
  const a = roomArt("stair"); a.classList.add("sstair"); return a;
}
function renderSide() {
  const box = $("dside"); if (!box) return;
  box.replaceChildren();
  const k = S.cur, lv = /^\d$/.test(k) ? +k : 0;
  box.hidden = false;
  S.side = S.side || {};
  const sd = (S.side[k] = S.side[k] || { box: [], st: [] });
  if (!lv) {                                   // a shrine: its prize (taken: lit in the shrines row above)
    const v = sd.prize;
    box.append(el("div", { className: "slabel", textContent: "Prize" }));
    const b = el("button", { type: "button", className: "sbox blank" + (v ? " on" : ""),
      title: "Shrine prize" + (v ? ": " + optName(PRIZEOPTS, v) : "") }, v ? [icon(v)] : []);
    b.onclick = (e) => {
      e.stopPropagation();
      sidePick(b, `Shrine ${k} prize`, PRIZEOPTS, v, (img, lit) => {
        sd.prize = img; grant(`side:${k}:prize`, img, lit); if (!S.shrines.includes(k)) S.shrines = [...S.shrines, k]; save();
      }, () => { sd.prize = null; revoke(`side:${k}:prize`); S.shrines = S.shrines.filter((x) => x !== k); save(); }, 2);
    };
    box.append(b);
    return;
  }
  const sbtn = (cls, title, kids, click) => {
    const b = el("button", { type: "button", className: "sbox " + cls, title }, kids);
    b.onclick = (e) => { e.stopPropagation(); click(b); };
    box.append(b); return b;
  };
  if (lv <= 8) {
    const on = S.tri.includes(lv);
    sbtn("tri" + (on ? " on" : ""), `Triforce piece ${lv}`, [icon("triforce"), el("span", { className: "sn", textContent: lv })], () => {
      S.tri = on ? S.tri.filter((x) => x !== lv) : [...S.tri, lv]; save();
    });
    const o = S.om[lv] || {};
    sbtn("om" + (o.item ? " on" : ""), `Level ${lv} old man` + (o.item ? ": took " + optName(OM_ITEMS, o.item) : ""),
      [icon(o.item || "cardD")], (b) => openOMRoom(lv, b));
    sbtn("pot" + (sd.pot ? " on" : ""), "Blue potion", [icon("potion1")], () => {
      sd.pot = !sd.pot; if (sd.pot) grant(`side:${k}:pot`, "potion1"); else revoke(`side:${k}:pot`); save();
    });
    const slot = (arr, i, opts, title, stairs) => {
      const v = sd[arr][i];
      const kids = stairs ? [stairArt()] : [];
      if (v) kids.push(icon(v, stairs ? "over" : ""));
      sbtn((stairs ? "st" : "blank") + (v ? " on" : ""), title + (v ? ": " + optName(opts, v) : ""), kids, (b) =>
        sidePick(b, title, opts, v, (img, lit) => { sd[arr][i] = img; grant(`side:${k}:${arr}:${i}`, img, lit); save(); },
          () => { sd[arr][i] = null; revoke(`side:${k}:${arr}:${i}`); save(); }, 1));
    };
    const [nst, flr] = layoutOf(lv);                                     // (the map's set: LAYOUT)
    if (flr) slot("box", 0, BOXOPTS, "Floor item");
    for (let i = 0; i < nst; i++) slot("st", i, BOXOPTS, "Item stairs", true);
  } else {
    const slot = (i) => {
      const v = sd.st[i];
      sbtn("st" + (v ? " on" : ""), "Item stairs" + (v ? ": " + optName(L9OPTS, v) : ""), [stairArt(), ...(v ? [icon(v, "over")] : [])], (b) =>
        sidePick(b, "Level 9 item stairs", L9OPTS, v, (img, lit) => { sd.st[i] = img; grant(`side:9:st:${i}`, img, lit); save(); },
          () => { sd.st[i] = null; revoke(`side:9:st:${i}`); save(); }, -1));
    };
    slot(0); slot(1);
    sbtn("boss" + (sd.ganon ? " on" : ""), "Ganon", [icon("en_ganon")], () => { sd.ganon = !sd.ganon; save(); });
    sbtn("boss" + (sd.zelda ? " on" : ""), "Zelda", [icon("en_zelda")], () => { sd.zelda = !sd.zelda; save(); });
  }
}

function renderCounters() {
  counter("hearts", "heart", "Hearts", () => S.hearts, (v) => { S.hearts = v; }, 1, 16);
  counter("bombups", "bombs", "Bomb upgrades", () => S.bombups, (v) => { S.bombups = v; }, 0, 3);
}
function renderAll() {
  renderItems(); renderCounters();
  renderTri(); renderUps(); renderMap(); renderBrushes(); renderDun(); renderSide(); tick();
}
// (owner 2026-11-27) every tracker window open in this browser shows the same run: another window's save arrives here
addEventListener("storage", (e) => {
  if (e.key !== KEY) return;
  try { S = Object.assign(fresh(), e.newValue ? JSON.parse(e.newValue) : {}); } catch (err) { return; }
  if (document.activeElement !== $("notes")) $("notes").value = S.notes;
  renderAll();
});
// the Stream layout (button or ?stream): one 640px column (the upgrades a bar beside the overworld), zoomed to fit the window;
// Wide (button or ?stream=wide, owner 2026-11-27): the dungeon map beside it instead, for a whole monitor
const STREAM_KEY = "lol-tracker-stream";            // (sessionStorage: each window its own layout, kept over a reload)
const WIDE_KEY = "lol-tracker-stream-wide";
function fitStream() {
  if (!document.body.classList.contains("stream")) { document.body.style.zoom = ""; return; }
  document.body.style.zoom = 1;
  const w = document.querySelector("main").offsetWidth;        // (tracker.css: 640, or 1240 wide)
  const measure = () => document.querySelector("main").getBoundingClientRect().bottom + scrollY + 4;   // (not the page: it fills the window)
  let h = measure();
  const c = document.body.classList;
  if (c.contains("onemap")) {             // One map: fitted to the taller of the two, so the switch never rescales
    const ow = c.contains("view-ow");
    c.toggle("view-ow", !ow); c.toggle("view-dun", ow);
    h = Math.max(h, measure());
    c.toggle("view-ow", ow); c.toggle("view-dun", !ow);
  }
  document.body.style.zoom = Math.min(innerWidth / w, innerHeight / h);
}
function setStream(on) {
  document.body.classList.toggle("stream", on);
  try { sessionStorage.setItem(STREAM_KEY, on ? "1" : ""); } catch (e) { /* storage off */ }
  $("stream").classList.toggle("cur", on);
  fitStream();
}
function setWide(on) {
  document.body.classList.toggle("wide", on);
  try { sessionStorage.setItem(WIDE_KEY, on ? "1" : ""); } catch (e) { /* storage off */ }
  $("stream-wide").classList.toggle("cur", on);
  if (typeof applyOneMap === "function") applyOneMap();
  fitStream();
}
// One map (button or ?onemap, owner 2026-11-27; test page): the overworld and the dungeons share one space, a big
// switch above it (each window its own; not with Wide, which has room for both)
const ONEMAP_KEY = "lol-tracker-onemap", VIEW_KEY = "lol-tracker-mapview";
let oneMap = false, mapView = "ow";
function applyOneMap() {
  const on = oneMap && !document.body.classList.contains("wide");
  document.body.classList.toggle("onemap", on);
  document.body.classList.toggle("view-ow", on && mapView === "ow");
  document.body.classList.toggle("view-dun", on && mapView === "dun");
  $("onemap").classList.toggle("cur", oneMap);
  document.querySelectorAll("#maptoggle button").forEach((b) => b.classList.toggle("cur", b.dataset.v === mapView));
  try { sessionStorage.setItem(ONEMAP_KEY, oneMap ? "1" : ""); sessionStorage.setItem(VIEW_KEY, mapView); } catch (e) { /* storage off */ }
  fitStream();
}
$("onemap").onclick = () => { oneMap = !oneMap; applyOneMap(); };
document.querySelectorAll("#maptoggle button").forEach((b) => { b.onclick = () => { mapView = b.dataset.v; applyOneMap(); }; });
$("stream").onclick = () => setStream(!document.body.classList.contains("stream"));
$("stream-wide").onclick = () => setWide(!document.body.classList.contains("wide"));
addEventListener("resize", fitStream);
if (window.ResizeObserver) new ResizeObserver(() => requestAnimationFrame(fitStream)).observe(document.querySelector("main"));
let streamOn = /[?&]stream\b/.test(location.search);
let wideOn = /[?&]stream=wide\b/.test(location.search);
try {
  streamOn = streamOn || sessionStorage.getItem(STREAM_KEY) === "1";
  wideOn = wideOn || sessionStorage.getItem(WIDE_KEY) === "1";
  localStorage.removeItem(STREAM_KEY); localStorage.removeItem(WIDE_KEY);       // (the old shared setting)
} catch (e) { /* storage off */ }
oneMap = /[?&]onemap\b/.test(location.search);
try {
  oneMap = oneMap || sessionStorage.getItem(ONEMAP_KEY) === "1";
  mapView = sessionStorage.getItem(VIEW_KEY) === "dun" ? "dun" : "ow";
} catch (e) { /* storage off */ }
setWide(wideOn);
setStream(streamOn);
applyOneMap();
renderAll();
if (VER) document.querySelector(".brand span").textContent = `TRACKER · BETA ${VER}`;
