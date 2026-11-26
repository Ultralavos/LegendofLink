// Legend of Link randomizer: the build, run in the browser (Pyodide in a web worker).
// In:  {type: "build", rom: ArrayBuffer (a clean PRG1 ROM), original: ArrayBuffer (the player's ROM), seed, start}
// Out: {type: "status", text} while loading; {type: "ready"}; {type: "result", rom, ips, log, icons} or {type: "error", text}
"use strict";

const PYODIDE = "0.28.3";
let pyodide = null;

const GLUE = `
import os, sys, io, contextlib, traceback
sys.path.insert(0, "/lol/build/lol")
os.environ["ZORA_PATH"] = "/lol/zora"

FRESH = ("lol_", "lolpaths", "new_grids", "build_q3", "build_mock", "release")

def _b(x):                                       # a JS Uint8Array (JsProxy) or bytes -> bytes
    return x.to_bytes() if hasattr(x, "to_bytes") else bytes(x)

def run_build(rom_bytes, original_bytes, seed, start, dset, set_seed, mix=False, fixed=False, tunic=None, noflash=False, race=False, upmix=False):
    os.environ["LOL_GEN"] = "1"
    os.environ["LOL_FIXED"] = "1" if fixed else "0"
    os.environ["LOL_MIX"] = "1" if mix else "0"
    os.environ["LOL_START"] = start
    os.environ["LOL_NOFLASH"] = "1" if noflash else "0"
    os.environ["LOL_RACE"] = "1" if race else "0"
    os.environ["LOL_UPMIX"] = "1" if upmix else "0"
    if tunic:
        os.environ["LOL_TUNIC"] = str(tunic)
    else:
        os.environ.pop("LOL_TUNIC", None)
    os.environ["LOL_SET"] = dset
    os.environ["LOL_SET_SEED"] = str(set_seed)
    if seed is None:
        os.environ.pop("LOL_SEED", None)
    else:
        os.environ["LOL_SEED"] = str(seed)
    for m in list(sys.modules):                  # every build starts from fresh module state
        if m.startswith(FRESH):
            del sys.modules[m]
    with open("/tmp/in.nes", "wb") as f:
        f.write(_b(rom_bytes))
    sys.argv = ["lol_build.py", "/tmp/in.nes", "/tmp/out.ips", "/tmp/out.nes"]
    log = io.StringIO()
    with contextlib.redirect_stdout(log):
        import lol_build
        lol_build.main()
    out = open("/tmp/out.nes", "rb").read()
    ips = lol_build.make_ips(_b(original_bytes), out)
    import json, lol_seedcode
    return out, ips, log.getvalue(), json.dumps(lol_seedcode.ICONS)
`;

async function init() {
  postMessage({ type: "status", text: "Loading Python (first time takes a little while)..." });
  importScripts(`https://cdn.jsdelivr.net/pyodide/v${PYODIDE}/full/pyodide.js`);
  pyodide = await loadPyodide();
  postMessage({ type: "status", text: "Loading the Legend of Link build..." });
  const zip = await (await fetch("lol-build.zip", { cache: "no-cache" })).arrayBuffer();
  pyodide.unpackArchive(zip, "zip", { extractDir: "/lol" });
  pyodide.runPython(GLUE);
  postMessage({ type: "ready" });
}

const ready = init().catch((e) => postMessage({ type: "error", text: String(e) }));

onmessage = async (ev) => {
  await ready;
  const msg = ev.data;
  if (msg.type !== "build") return;
  try {
    postMessage({ type: "status", text: "Building your game..." });
    const run = pyodide.globals.get("run_build");
    const res = run(new Uint8Array(msg.rom), new Uint8Array(msg.original), msg.seed, msg.start, msg.dset,
                    msg.setSeed, !!msg.mix, !!msg.fixed, msg.tunic || null, !!msg.noflash, !!msg.race, !!msg.upmix);
    const [rom, ips, log, icons] = res.toJs();
    res.destroy();
    const romBytes = new Uint8Array(rom);           // (Python bytes arrive as Uint8Array)
    const ipsBytes = new Uint8Array(ips);
    postMessage({ type: "result", rom: romBytes, ips: ipsBytes, log, icons: JSON.parse(icons) },
                [romBytes.buffer, ipsBytes.buffer]);
  } catch (e) {
    postMessage({ type: "error", text: String(e) });
  }
};
