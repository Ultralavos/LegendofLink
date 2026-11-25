"use strict";
// The page: checks the player's ROM, turns a PRG0 into PRG1 (the build's base), and runs the build in a worker.

const KNOWN = {   // SHA-1 of the ROM without its 16-byte header
  "a12d74c73a0481599a5d832361d168f4737bbcf6": "PRG0",
  "be2f5dc8c5ba8ec1a344a71f9fb204750af24fe7": "PRG1",
};
// Custom sprites: a ROM whose only changes are in the sprite pattern blocks (Link and the items, the enemies, the
// bosses; offsets without the header, as lol_seedcode.SPRITE_BLOCKS) is taken too. With those blocks zeroed (after
// prg0-to-prg1.ips for a PRG0, which touches none of them) it must match clean PRG1's.
const SPRITE_BLOCKS = [[32895, 1792], [53595, 1824], [55419, 544], [55963, 544], [56507, 256], [56763, 544],
                       [57307, 1024], [58331, 1024], [59355, 1024]];
const MASKED_PRG1 = "de692f18ce78c23645553f7399258b69c05afc0a";
const VERSION = "0.313";   // (owner: Beta 0.313, bumped with every change set; lol_seedcode.VERSION shows it on the title)

const $ = (id) => document.getElementById(id);
const NES_PALETTE = [   // (ZORA's page's)
  "#545454", "#001e74", "#081090", "#300088", "#440064", "#5c0030", "#540400", "#3c1800",
  "#202a00", "#083a00", "#004000", "#003c00", "#00323c", "#000000", "#000000", "#000000",
  "#989698", "#084cc4", "#3032ec", "#5c1ee4", "#8814b0", "#a01464", "#982220", "#783c00",
  "#545a00", "#287200", "#087c00", "#007628", "#006678", "#000000", "#000000", "#000000",
  "#eceeec", "#4c9aec", "#787cec", "#b062ec", "#e454ec", "#ec58b4", "#ec6a64", "#d48820",
  "#a0aa00", "#74c400", "#4cd020", "#38cc6c", "#38b4cc", "#3c3c3c", "#000000", "#000000",
  "#eceeec", "#a8ccec", "#bcbcec", "#d4b2ec", "#ecaeec", "#ecaed4", "#ecb4b0", "#e4c490",
  "#ccd278", "#b4de78", "#a8e290", "#98e2b4", "#a0d6e4", "#a0a2a0", "#000000", "#000000",
];

// The seed code (the file-select screen's four icons), drawn from the built ROM's own tiles and palette.
function showCode(icons) {
  const box = $("code-items");
  box.replaceChildren();
  for (const [name, pixels] of icons || []) {
    const item = document.createElement("div"); item.className = "code-item";
    const c = document.createElement("canvas"); c.width = c.height = 16; c.setAttribute("aria-hidden", "true");
    const img = new ImageData(16, 16);
    pixels.flat().forEach((color, i) => {
      const rgb = NES_PALETTE[color & 0x3F];
      img.data.set([1, 3, 5].map((k) => parseInt(rgb.slice(k, k + 2), 16)).concat(255), i * 4);
    });
    c.getContext("2d").putImageData(img, 0, 0);
    const label = document.createElement("span"); label.textContent = name;
    item.append(c, label); box.append(item);
  }
  $("code").style.display = icons && icons.length ? "block" : "none";
}
let rom = null, original = null, version = null, ready = false;
const worker = new Worker("worker.js");

function status(text, bad = false) { $("status").textContent = text; $("status").className = bad ? "bad" : ""; }
function refresh() { $("build").disabled = !(ready && rom); }

async function sha1(bytes) {
  const d = await crypto.subtle.digest("SHA-1", bytes);
  return [...new Uint8Array(d)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

function applyIps(base, ips) {
  const out = new Uint8Array(base);   // (a copy; the patches here never grow the file)
  if (String.fromCharCode(...ips.slice(0, 5)) !== "PATCH") throw new Error("not an IPS patch");
  let i = 5;
  for (;;) {
    if (ips[i] === 0x45 && ips[i + 1] === 0x4F && ips[i + 2] === 0x46) return out;   // EOF
    const off = (ips[i] << 16) | (ips[i + 1] << 8) | ips[i + 2]; i += 3;
    let n = (ips[i] << 8) | ips[i + 1]; i += 2;
    if (n === 0) {                                // RLE
      n = (ips[i] << 8) | ips[i + 1]; out.fill(ips[i + 2], off, off + n); i += 3;
    } else { out.set(ips.subarray(i, i + n), off); i += n; }
  }
}

$("rom").addEventListener("change", async () => {
  const f = $("rom").files[0];
  rom = null; refresh();
  if (!f) return;
  const bytes = new Uint8Array(await f.arrayBuffer());
  const body = bytes[0] === 0x4E && bytes[1] === 0x45 && bytes[2] === 0x53 ? bytes.subarray(16) : bytes;
  const bad = (text) => { $("romstatus").textContent = text; $("romstatus").className = "hint bad"; };
  if (body.length !== bytes.length - 16 || body.length !== 131072) {
    bad("That isn't a Legend of Zelda (USA) PRG0 or PRG1 ROM with its header."); return;
  }
  const toPrg1 = async (b) => applyIps(b, new Uint8Array(await (await fetch("prg0-to-prg1.ips")).arrayBuffer()));
  let v = KNOWN[await sha1(body)], custom = false;
  if (v) rom = v === "PRG0" ? await toPrg1(bytes) : bytes;
  else {
    // custom sprites? (PRG1, or PRG0 made PRG1; with the sprite blocks zeroed it must be clean PRG1)
    for (const [cand, name] of [[bytes, "PRG1"], [await toPrg1(bytes), "PRG0"]]) {
      const m = cand.slice(16);
      for (const [o, n] of SPRITE_BLOCKS) m.fill(0, o, o + n);
      if (await sha1(m) === MASKED_PRG1) { v = name; rom = cand; custom = true; break; }
    }
    if (!v) {
      bad("That isn't a clean Legend of Zelda (USA) PRG0 or PRG1 ROM. Custom sprites are fine, but only the " +
          "sprites of Link, the items and the enemies may be changed (nothing else, not even colors).");
      return;
    }
  }
  original = bytes; version = v;
  $("romstatus").textContent = `Found The Legend of Zelda (USA) ${v}${custom ? " with custom sprites" : ""}.`;
  $("romstatus").className = "hint ok";
  refresh();
});

$("seed").addEventListener("input", () => {     // (numbers only: anything else is dropped as it's typed)
  const v = $("seed").value, d = v.replace(/\D/g, "");
  if (d !== v) $("seed").value = d;
});

$("roll").addEventListener("click", () => {
  $("seed").value = String(crypto.getRandomValues(new Uint32Array(1))[0]);
});

$("build").addEventListener("click", () => {
  const raw = $("seed").value.trim();
  let seed = null;
  if (raw) {
    if (!/^\d+$/.test(raw) || Number(raw) > 4294967295) { status("The seed is a whole number from 0 to 4294967295.", true); return; }
    seed = Number(raw);
  }
  if (seed === null && !$("unseeded").checked) {  // (the build decides the dungeons: one fixed game, so a seed)
    seed = crypto.getRandomValues(new Uint32Array(1))[0];
    $("seed").value = String(seed);
  }
  $("build").disabled = true; $("downloads").style.display = "none"; $("code").style.display = "none";
  // the dungeon set's own seed: the game's seed, or (no seed) a fresh one for this build
  const setSeed = seed !== null ? seed : crypto.getRandomValues(new Uint32Array(1))[0];
  worker.postMessage({ type: "build", rom: rom.slice().buffer, original: original.slice().buffer, seed,
                       start: $("start").value, dset: $("dset").value, setSeed,
                       mix: $("mix").checked, fixed: !$("unseeded").checked });
});

worker.onmessage = (ev) => {
  const m = ev.data;
  if (m.type === "status") status(m.text);
  else if (m.type === "ready") { ready = true; status("Ready."); refresh(); }
  else if (m.type === "error") { status("Something went wrong: " + m.text, true); refresh(); }
  else if (m.type === "result") {
    const seed = $("seed").value.trim() || "free";
    const name = `LegendOfLink-v${VERSION}-${$("dset").value}-${$("start").value}${$("mix").checked ? "-mix" : ""}${$("unseeded").checked ? "-unseeded" : ""}-${seed}`;
    const link = (id, data, ext) => {
      const a = $(id); a.href = URL.createObjectURL(new Blob([data], { type: "application/octet-stream" }));
      a.download = `${name}.${ext}`;
    };
    link("dl-rom", m.rom, "nes");
    link("dl-ips", m.ips, `${version}.ips`);
    $("downloads").style.display = "flex";
    showCode(m.icons);
    status("Done. Your game is ready.");
    refresh();
  }
};
