# Walks into every dungeon a new game deals (emulator: run from a ZORA checkout, which has tests/emulator.py):
#   LOL_SET=shapes LOL_SEED=1 python3 PATH/tests/gen_walk.py built.nes 3
"""v2.02 test 4: roll every entrance (random order), then enter each dungeon and check the decoded rooms."""
import sys, random
from collections import Counter
from PIL import Image
from tests.emulator import Emulator, ROOM_ID, GAME_MODE, CUR_LEVEL, Button
import os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'build', 'lol'))
import lolpaths
if os.environ.get('LOL_SOURCE'):           # the clean ROM (1Q / 2Q sets read their footprints from it)
    lolpaths.SOURCE_ROM = open(os.environ['LOL_SOURCE'], 'rb').read()
import lol_genload as GL
rom = open(sys.argv[1], 'rb').read()
seed = int(sys.argv[2]) if len(sys.argv) > 2 else 3
OW = 0x18410
nm = lambda s: "ABCDEFGH"[s // 16] + str(s % 16 + 1)
ents = [s for s in range(128) if rom[OW + 0x80 + s] >> 2 and rom[OW + 0x280 + s] >> 6 != 2 and rom[OW + 0x80 + s] >> 2 != 0x14 and nm(s) != 'H8']
ds, out = GL.build_variants()
g = Emulator(rom); g.new_game(); g.run(30)
g[0x66F] = 0x99; g[0x671] = 0xFF
g[ROOM_ID], g[CUR_LEVEL], g[0x5A] = 0x1F, 0, 1
g[GAME_MODE], g[0x13], g[0x11] = 0x0A, 0, 0
g.run_until(lambda: g.mode == 5 and g[0x11] == 1, limit=900); g.run(10); g.run(14, Button.DOWN)
base = g.save()
sram = [g[0x7F00 + i] for i in range(0x100)]
order = ents[:]; random.Random(seed).shuffle(order)
dorder = []
for k, s in enumerate(order):
    g.load(base)
    for i in range(0xFF): g[0x7F00 + i] = sram[i]
    g.run(1 + k % 5)
    g[ROOM_ID] = s
    g.run_until(lambda: g[GAME_MODE] != 5, buttons=Button.UP, limit=200)
    g.run(3)
    sram = [g[0x7F00 + i] for i in range(0x100)]
    d = sram[ents.index(s)]
    if 1 <= d <= 0x0D:
        dorder.append(d)
print('dungeon order', [hex(d) for d in dorder])
recs = [[sram[0xAD + i * 5 + j] for j in range(5)] for i in range(13)]
used = [r[0] - 1 for r in recs]
print('designs', [ds[u][2] for u in used], 'distinct', len(set(used)) == 13)
print('bosses', [hex(r[2]) for r in recs])
shots = []
tot = Counter()
for k, s in enumerate(ents):
    d = sram[ents.index(s)]
    if not (1 <= d <= 0x0D):
        continue
    g.load(base)
    for i in range(0xFF): g[0x7F00 + i] = sram[i]
    g.run(1 + k % 3)
    g[ROOM_ID] = s
    g[0x68FE + s] = (d << 2) | (g[0x68FE + s] & 3)
    g.run_until(lambda: g[GAME_MODE] != 5, buttons=Button.UP, limit=200)
    try:
        g.run_until(lambda: g[GAME_MODE] == 5 and g[0x11] == 1, limit=1500)
    except AssertionError:
        print(nm(s), 'dest', hex(d), 'STUCK mode', hex(g[GAME_MODE]), hex(g[0x11]), hex(g[0x13]), 'lvl', g[CUR_LEVEL])
        Image.fromarray(g.last_frame).save(f'stuck_{d:x}.png')
        continue
    g.run(60)
    cg = g[0x168]
    if cg >= len(ds):
        print(nm(s), 'dest', hex(d), 'BAD design index', cg, 'mode', hex(g[GAME_MODE]), 'lvl', g[CUR_LEVEL], 'room', hex(g[ROOM_ID]))
        continue
    cells = ds[cg][3]
    A = [[g[GL.ATTR[t] + c] for t in range(6)] for c in range(128)]
    mon = lambda c: (A[c][2] & 0x3F) | (0x40 if A[c][3] & 0x80 else 0)
    bossrooms = [c for c in cells if 0x31 <= mon(c) < 0x4A and mon(c) not in (0x3A, 0x3B, 0x49)]
    items = [(c, A[c][4] & 0x1F, A[c][5] & 7) for c in cells if A[c][4] & 0x1F != 3]
    drop = sum(1 for _, it, t in items if t == 7)
    roars = [nm(c) for c in cells if A[c][4] & 0x60]
    push_bad = [nm(c) for c in cells if A[c][3] & 0x40 and A[c][5] & 7 not in (4, 5)]
    shut = lambda c: any(((A[c][i] >> 5) & 7) == 7 or ((A[c][i] >> 2) & 7) == 7 for i in (0, 1))
    push_noshut = [nm(c) for c in cells if A[c][5] & 7 == 4 and not shut(c)]
    mons = Counter(mon(c) for c in cells if mon(c) and c not in bossrooms)
    flags = g[0x6BAF] | g[0x6BB0] << 8
    lbl = ''.join(chr(x) for x in [])
    ic = Counter(A[c][4] & 0x1F for c in cells)
    marks = [c for c in cells if (A[c][4] & 0x1C) == 0x10]
    print(f"   items: tri {ic[0x1B]} map {ic[0x17]} compass {ic[0x16]} potion {ic[0x1F]} key {ic[0x19]} bombs {ic[0x00]} "
          f"rupees {ic[0x0F]} leftover marks {len(marks)} tri room {nm(g[0x6B7E+0x30])} floor {hex(g[0x16C] if False else 0)}")
    print(f"{nm(s):4} dest {d:2x} {ds[cg][2]:11} bossrooms {len(bossrooms)} {[hex(mon(c)) for c in bossrooms]} "
          f"items {len(items)} dropped {drop} roar {roars} push-no-stairs {push_bad} push-no-shutter {push_noshut} "
          f"flags {flags:04X} top monster {mons.most_common(2)}")
    if d >= 0x0A:
        pr = g[0x6B7E + 0x30]
        print(f"   SHRINE prize room {nm(pr)} item {g[GL.ATTR[4]+pr]:02x} layout {g[GL.ATTR[3]+pr]:02x} trig {g[GL.ATTR[5]+pr]:02x} "
              f"flag {g[flags+pr]:02x} INSIDE {g[0x678]} level {g[CUR_LEVEL]} quest {g[0x62D]}")
    tot['items'] += len(items); tot['drop'] += drop
    shots.append(g.last_frame[:64].copy())
print(tot)
w = 256
sheet = Image.new('RGB', (w * 4, 64 * ((len(shots) + 3) // 4)))
for i, f in enumerate(shots): sheet.paste(Image.fromarray(f), ((i % 4) * w, (i // 4) * 64))
sheet = sheet.resize((sheet.width * 2, sheet.height * 2), Image.NEAREST)
sheet.save('t4_bars.png')
