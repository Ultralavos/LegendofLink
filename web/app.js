"use strict";
// The page: checks the player's ROM, turns a PRG0 into PRG1 (the build's base), and runs the build in a worker.

const KNOWN = {   // SHA-1 of the ROM without its 16-byte header
  "a12d74c73a0481599a5d832361d168f4737bbcf6": "PRG0",
  "be2f5dc8c5ba8ec1a344a71f9fb204750af24fe7": "PRG1",
};
const VERSION = "2.02";

const $ = (id) => document.getElementById(id);
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
  const v = KNOWN[await sha1(body)];
  if (!v || body.length !== bytes.length - 16) {
    $("romstatus").textContent = "That isn't a clean Legend of Zelda (USA) PRG0 or PRG1 ROM with its header.";
    $("romstatus").className = "hint bad";
    return;
  }
  original = bytes; version = v;
  if (v === "PRG0") {
    const patch = new Uint8Array(await (await fetch("prg0-to-prg1.ips")).arrayBuffer());
    rom = applyIps(bytes, patch);
  } else rom = bytes;
  $("romstatus").textContent = `Found The Legend of Zelda (USA) ${v}.`;
  $("romstatus").className = "hint ok";
  refresh();
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
  $("build").disabled = true; $("downloads").style.display = "none";
  worker.postMessage({ type: "build", rom: rom.slice().buffer, original: original.slice().buffer, seed,
                       start: $("start").value });
});

worker.onmessage = (ev) => {
  const m = ev.data;
  if (m.type === "status") status(m.text);
  else if (m.type === "ready") { ready = true; status("Ready."); refresh(); }
  else if (m.type === "error") { status("Something went wrong: " + m.text, true); refresh(); }
  else if (m.type === "result") {
    const seed = $("seed").value.trim() || "free";
    const name = `LegendOfLink-v${VERSION}-${$("start").value}-${seed}`;
    const link = (id, data, ext) => {
      const a = $(id); a.href = URL.createObjectURL(new Blob([data], { type: "application/octet-stream" }));
      a.download = `${name}.${ext}`;
    };
    link("dl-rom", m.rom, "nes");
    link("dl-ips", m.ips, `${version}.ips`);
    $("downloads").style.display = "flex";
    status("Done. Your game is ready.");
    refresh();
  }
};
