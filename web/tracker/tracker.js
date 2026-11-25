"use strict";
// Legend of Link tracker: items, triforce and shrines, cards, upgrades, the overworld's 71 entrances and a room grid
// per level and shrine. Everything is kept in localStorage (one key), so a refresh keeps the run.

const KEY = "lol-tracker-v1";
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
  "Zombie Link", "Brain Potion", "X-ray Glasses"];   // (lol_uptable's order: the icons up_00..up_36)
const PRICE = [50, 100, 125, 50, 100, 150, 50, 100, 150, 50, 100, 150, 50, 125, 150, 25, 50, 50, 50, 50, 50, 50, 75,
  100, 100, 100, 125, 150, 150, 200, 50, 200, 100, 25, 75, 50, 200];
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
const BRUSHES = [   // id, label, title
  ["room", "", "Room: click again to mark it cleared, again to erase"],
  ["E", "E", "Entrance"], ["S", "S", "Stairs"], ["O", "O", "Old man"], ["B", "B", "Boss"],
  ["T", "▲", "Triforce or prize"], ["I", "★", "Item"], ["K", "K", "Locked door"], ["X", "✸", "Bomb wall"],
  ["?", "?", "Something to check"],
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
const fresh = () => ({ items: {}, hearts: 3, om: {}, bombups: 0, tri: [], shrines: [], cards: { S: 0, D: 0, X: 0 }, ups: {},
  ow: {}, owDone: {}, dun: {}, cur: "1", notes: "", timer: { acc: 0, start: null } });
let S = fresh();
try { const raw = localStorage.getItem(KEY); if (raw) S = Object.assign(fresh(), JSON.parse(raw)); } catch (e) { /* new run */ }
function save() { try { localStorage.setItem(KEY, JSON.stringify(S)); } catch (e) { /* storage unavailable: still works */ } }

// a click advances, a right-click or a long press goes back
function stepper(node, fn) {
  let held = null, longed = false;
  node.addEventListener("click", (e) => { if (longed) { longed = false; return; } fn(+1, e); });
  node.addEventListener("contextmenu", (e) => { e.preventDefault(); fn(-1, e); });
  node.addEventListener("touchstart", () => { longed = false; held = setTimeout(() => { longed = true; fn(-1); }, 450); }, { passive: true });
  ["touchend", "touchmove", "touchcancel"].forEach((t) => node.addEventListener(t, () => clearTimeout(held)));
}
const icon = (name, cls = "") => el("img", { src: `img/${name}.png`, className: `px ${cls}`, alt: "", draggable: false });

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
    const b = el("button", { type: "button", className: "tpiece" + (on ? " on" : ""), title: `Triforce piece ${n}` });
    b.append(icon("triforce"), el("span", { textContent: n }));
    b.onclick = () => { S.tri = on ? S.tri.filter((x) => x !== n) : [...S.tri, n]; save(); renderTri(); };
    t.append(b);
  }
  const s = $("shrines"); s.replaceChildren();
  for (const c of ["A", "B", "C", "D"]) {
    const on = S.shrines.includes(c);
    const b = el("button", { type: "button", className: "shrine" + (on ? " on" : ""), textContent: c, title: `Shrine ${c} prize taken` });
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
const omDrawn = (n) => Object.values((S.dun[String(n)] || {}).cells || {}).some((c) => c.m === "O");
let omOpen = null;
function renderOM() {
  S.om = S.om || {};
  const box = $("oldmen"); box.replaceChildren();
  for (let n = 1; n <= 8; n++) {
    const o = S.om[n] || {};
    const auto = omDrawn(n), lit = auto || o.found || o.item;
    const name = o.item ? OM_ITEMS.find((x) => x[0] === o.item)[1] : null;
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
    b.onclick = () => { o.item = img; o.found = true; save(); closeOM(); renderOM(); };
    g.append(b);
  }
  const found = el("button", { type: "button", className: "wide", textContent: o.found && !o.item ? "Not found" : "Found, nothing taken" });
  found.onclick = () => { o.found = !(o.found && !o.item); o.item = null; save(); closeOM(); renderOM(); };
  const clear = el("button", { type: "button", className: "wide quiet", textContent: "Clear" });
  clear.onclick = () => { delete S.om[n]; save(); closeOM(); renderOM(); };
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
function renderUps() {
  const box = $("upgrades"); box.replaceChildren();
  UPGRADES.forEach((name, i) => {
    const v = S.ups[i] || 0;
    const b = el("button", { type: "button", className: "up " + ["", "seen", "own"][v], title: `${name} (${PRICE[i]})` });
    b.append(el("img", { src: `../manual/img/up_${String(i).padStart(2, "0")}.png`, className: "px", alt: name, draggable: false }));
    b.onmouseenter = () => { $("up-name").textContent = `${name} · ${PRICE[i]} rupees`; };
    stepper(b, (d) => { S.ups[i] = (v + d + 3) % 3; save(); renderUps(); $("up-name").textContent = `${name} · ${["not seen", "seen", "bought"][S.ups[i]]}`; });
    box.append(b);
  });
}

// ---------------------------------------------------------------- overworld
const MARK = Object.fromEntries(MARKS.map((m) => [m[0], m]));
let picking = null;
function renderMap() {
  const map = $("map");
  map.querySelectorAll(".cell").forEach((c) => c.remove());
  const all = [...ENTRANCES, ...Object.keys(FIXED).map(Number)];
  for (const s of all) {
    const row = s >> 4, col = s & 15;
    const cell = el("button", { type: "button", className: "cell", title: "ABCDEFGH"[row] + (col + 1) });
    cell.style.left = `${col * 6.25}%`; cell.style.top = `${row * 12.5}%`;
    if (FIXED[s]) { cell.classList.add("fixed"); cell.append(el("span", { className: "tag " + FIXED[s][1], textContent: FIXED[s][0] })); cell.disabled = true; }
    else {
      const m = MARK[S.ow[s]];
      if (m) cell.append(el("span", { className: "tag " + m[2], textContent: m[1] }));
      else cell.classList.add("open");
      if (S.owDone[s]) cell.append(el("span", { className: "check", textContent: "✓" }));
      cell.onclick = (e) => { e.stopPropagation(); openPicker(s, cell); };
    }
    map.append(cell);
  }
  $("spots").textContent = ENTRANCES.filter((s) => !S.ow[s]).length;
}
function openPicker(s, cell) {
  const p = $("picker"); picking = s; p.replaceChildren();
  p.append(el("div", { className: "ptitle", textContent: `${"ABCDEFGH"[s >> 4]}${(s & 15) + 1}: what's here?` }));
  const grid = el("div", { className: "pgrid" });
  for (const [v, label, cls, text] of MARKS) {
    const b = el("button", { type: "button", className: "pick " + cls + (S.ow[s] === v ? " sel" : ""), title: text },
      [el("span", { className: "tag " + cls, textContent: label }), el("small", { textContent: text })]);
    b.onclick = () => { S.ow[s] = v; save(); closePicker(); renderMap(); };
    grid.append(b);
  }
  const done = el("button", { type: "button", className: "wide", textContent: S.owDone[s] ? "Unmark done" : "Mark done ✓" });
  done.onclick = () => { S.owDone[s] = !S.owDone[s]; save(); closePicker(); renderMap(); };
  const clear = el("button", { type: "button", className: "wide quiet", textContent: "Clear" });
  clear.onclick = () => { delete S.ow[s]; delete S.owDone[s]; save(); closePicker(); renderMap(); };
  p.append(grid, el("div", { className: "prow" }, [done, clear]));
  p.hidden = false;
  // place it under the tile, inside the panel
  const r = cell.getBoundingClientRect(), host = p.parentElement.getBoundingClientRect();
  const w = Math.min(320, host.width - 16);
  p.style.width = w + "px";
  p.style.left = Math.max(8, Math.min(r.left - host.left, host.width - w - 8)) + "px";
  p.style.top = (r.bottom - host.top + 4) + "px";
}
function closePicker() { $("picker").hidden = true; picking = null; }
document.addEventListener("click", (e) => { if (picking !== null && !$("picker").contains(e.target)) closePicker(); });
document.addEventListener("keydown", (e) => { if (e.key === "Escape") closePicker(); });

// ---------------------------------------------------------------- dungeons
let brush = "room";
const dun = (k) => (S.dun[k] = S.dun[k] || { name: "", done: false, cells: {} });
function renderDTabs() {
  const t = $("dtabs"); t.replaceChildren();
  for (const k of DUNGEONS) {
    const d = S.dun[k];
    const b = el("button", { type: "button", className: "dtab" + (k === S.cur ? " cur" : "") + (d && d.done ? " done" : ""),
      textContent: k, title: (/\d/.test(k) ? `Level ${k}` : `Shrine ${k}`) + (d && d.name ? `: ${d.name}` : "") });
    b.onclick = () => { S.cur = k; save(); renderDun(); };
    t.append(b);
  }
}
function renderBrushes() {
  const b = $("brushes"); b.replaceChildren();
  for (const [id, label, title] of BRUSHES) {
    const btn = el("button", { type: "button", className: "brush" + (id === brush ? " cur" : ""), title });
    btn.append(id === "room" ? el("i", { className: "sw" }) : el("span", { textContent: label }),
      el("small", { textContent: id === "room" ? "Room" : title.split(" ")[0] }));
    btn.onclick = () => { brush = id; renderBrushes(); };
    b.append(btn);
  }
}
function renderDun() {
  renderDTabs();
  const d = dun(S.cur);
  $("dname").value = d.name; $("ddone").checked = d.done;
  const g = $("dgrid"); g.replaceChildren();
  for (let i = 0; i < 128; i++) {
    const c = d.cells[i] || {};
    const cell = el("button", { type: "button", className: "room" + (c.r ? " r" + c.r : "") });
    if (c.m) cell.append(el("span", { textContent: BRUSHES.find((x) => x[0] === c.m)[1] }));
    cell.onclick = () => {
      const cur = d.cells[i] || {};
      if (brush === "room") cur.r = ((cur.r || 0) + 1) % 3;
      else { cur.m = cur.m === brush ? undefined : brush; if (cur.m && !cur.r) cur.r = 1; }
      if (!cur.r && !cur.m) delete d.cells[i]; else d.cells[i] = cur;
      save(); renderDun(); renderOM();
    };
    cell.oncontextmenu = (e) => { e.preventDefault(); delete d.cells[i]; save(); renderDun(); renderOM(); };
    g.append(cell);
  }
}
$("dname").addEventListener("input", (e) => { dun(S.cur).name = e.target.value; save(); renderDTabs(); });
$("ddone").addEventListener("change", (e) => { dun(S.cur).done = e.target.checked; save(); renderDTabs(); });
$("dclear").addEventListener("click", () => { dun(S.cur).cells = {}; save(); renderDun(); renderOM(); });
$("nicknames").append(...NICKNAMES.map((n) => el("option", { value: n })));

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

function renderAll() {
  renderItems();
  counter("hearts", "heart", "Hearts", () => S.hearts, (v) => { S.hearts = v; }, 1, 16);
  counter("bombups", "bombs", "Bomb upgrades", () => S.bombups, (v) => { S.bombups = v; }, 0, 3);
  renderTri(); renderUps(); renderMap(); renderBrushes(); renderDun(); tick();
}
renderAll();
