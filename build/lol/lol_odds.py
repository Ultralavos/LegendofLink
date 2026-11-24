"""Legend of Link: odds tables for the old man choices, the A-F rewards and the shops.

Each list has a table (odds/<list>.csv): a row per heart level 1-16, a column per item, the numbers out of 128 (a row
may add up to less: the rest is "roll again"). Link's level is his containers plus that list's badges (S shops, D old
men, X rewards), at most 16.

A pick rolls 0-127 and walks the row; an item Link can't get (owned, or its first tier missing: the lists' two
conditions) or already picked this time is rolled again, up to 24 times, then the first item of the row he can get
(with odds above 0) is taken; with none, the vanilla fallback (the old man's hint, A-F's red potion, an empty place).

  old men   two picks; the level is saved the first time Link enters the room, so the offer stays
  A-F       one pick; saved the same way
  shops     three picks, never saved: they change when the containers or S badges change
The rolls are a hash of a per-file seed, the place (room / screen) and the level, so a saved offer comes out the same
each visit. Saved bytes: the unused third file's item area (bank 2 never touches it), 20 per file: 0-10 the old men
(Levels 1-9, 2Q 4 = E, 2Q 6 = F), 11-16 A-F, 17 the seed; lol_af clears them for a new file.

The engine is in bank 3 (ENGINE; bank 4 until v3), reached through a bank-7 trampoline (TRAMP) that returns to the caller's bank."""
import csv, os

HERE = os.path.dirname(os.path.abspath(__file__))
ODDS_DIR = os.path.join(HERE, "odds")
ENGINE_BANK = 3                         # v3: bank 3 (was bank 4, the full monster bank)
ENGINE = 0xACA0                         # bank 3 free (after lol_genload's pattern getters)
TRAMP = 0xDFF0                          # bank 7 free (18 bytes)
LST, CTX, STO, NUM, OUT, RET = 0x0180, 0x0181, 0x0182, 0x0183, 0x0184, 0x0187   # (stack page, unused)
KEY, ACC, TRY, PK, CUM, RR, CAND, SEED, TT, UU, NOK = (0x0188, 0x0189, 0x018A, 0x018B, 0x018C, 0x018D, 0x018E,
                                                       0x018F, 0x0190, 0x0191, 0x0192)
STORE = 0x606A                          # the third file's item area: 20 bytes per file
PER_FILE = 20
SEED_AT = 17
TRIES = 24
NAMES = ("old_men", "rewards", "shops")
BADGE_SHIFT = (2, 4, 0)                 # D, X, S


def default_rows(items, most_default=16):
    """Odds that lean the way the old priority lists did: at each level the items Link may have (by the lists'
    fewest containers / most containers), earlier ones likelier; out of 64."""
    rows = []
    for h in range(1, 17):
        ok = [i for i, c in enumerate(items) if c[2] <= h and h <= (c[5] if len(c) > 5 else most_default)]
        w = {i: len(items) - k for k, i in enumerate(ok)}
        tot = sum(w.values()) or 1
        raw = {i: 64 * v / tot for i, v in w.items()}
        out = {i: int(v) for i, v in raw.items()}
        rest = 64 - sum(out.values()) if ok else 0
        for i in sorted(raw, key=lambda i: -(raw[i] - int(raw[i])))[:rest]:
            out[i] += 1
        rows.append([out.get(i, 0) for i in range(len(items))])
    return rows


def load(name, items):
    """The table for a list: odds/<name>.csv (written from the defaults the first time)."""
    path = os.path.join(ODDS_DIR, name + ".csv")
    if not os.path.exists(path):
        os.makedirs(ODDS_DIR, exist_ok=True)
        with open(path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["hearts"] + [c[0] for c in items] + ["total"])
            for h, row in enumerate(default_rows(items), 1):
                w.writerow([h] + row + [sum(row)])
    with open(path) as f:
        rd = list(csv.reader(f))
    head = rd[0][1:]
    if head and head[-1] == "total":
        head = head[:-1]
    assert head == [c[0] for c in items], (name, "columns", head)
    rows = []
    for k, line in enumerate(rd[1:17], 1):
        vals = [int(x or 0) for x in line[1:1 + len(items)]]
        assert int(line[0]) == k and sum(vals) <= 128, (name, "row", k, sum(vals))
        rows.append(vals)
    assert len(rows) == 16, (name, len(rows))
    return rows


LISTS = []                              # (name, items) in list order, set by the callers (lol_choice)


def register(list_id, name, items):
    while len(LISTS) <= list_id:
        LISTS.append(None)
    LISTS[list_id] = (name, items)


def wrappers(a, list_id, items, p, ret_bank, store, n_pick):
    """In the caller's code: {p}count (CNT = how many picks) and {p}nth (K -> A = item, Y = its entry in the reversed
    tables, or A = $3F), with {p}t_item (reversed, as lol_choice's picker). store: code that leaves the save index in
    A ($FF: none), with the hash context in CTX (A also)."""
    from lol_choice import CNT, K
    n = len(items)
    a.label(p + "count")
    store(a)                                                                    # A = store index, CTX set
    a.abs(0x8D, STO).b(0xA9, list_id).abs(0x8D, LST).b(0xA9, n_pick).abs(0x8D, NUM)
    a.b(0xA9, ret_bank).abs(0x8D, RET).abs(0x20, TRAMP)
    a.abs(0xAD, NOK).b(0x85, CNT, 0x60)
    a.label(p + "nth").b(0xA4, K).abs(0xB9, OUT).b(0xC9, 0xFF).br(0xD0, p + "n_ok").b(0xA9, 0x3F, 0x60)
    a.label(p + "n_ok").b(0x49, 0xFF, 0x18, 0x69, n, 0xA8)                       # Y = n - 1 - i
    a.abs(0xB9, p + "t_item").b(0xC9, 0x04).br(0xB0, p + "n_r").b(0xC9, 0x02).br(0x90, p + "n_r")
    a.abs(0xAD, 0x7FF7).br(0xF0, p + "n_sw").b(0xA9, 0x24, 0x60)                  # swordless: a bomb upgrade
    a.label(p + "n_sw").abs(0xB9, p + "t_item")
    a.label(p + "n_r").b(0x60)
    a.label(p + "t_item").b(*[c[1] for c in reversed(items)])


def apply(rom: bytearray, notes: list) -> None:
    from lol_af import Asm, place, BANK
    assert len(LISTS) == 3 and all(LISTS), LISTS
    tables = [load(name, items) for name, items in LISTS]
    base, g = [], 0
    for name, items in LISTS:
        base.append(g); g += len(items)
    allitems = [c for _, items in LISTS for c in items]
    t = bytes([0xA9, ENGINE_BANK, 0x20, 0xAC, 0xFF, 0x20, ENGINE & 0xFF, ENGINE >> 8, 0xAD, RET & 0xFF, RET >> 8,
               0x4C, 0xAC, 0xFF])
    at = BANK(7) + TRAMP - 0xC000
    assert all(x == 0xFF for x in rom[at:at + len(t)])
    rom[at:at + len(t)] = t

    a = Asm(ENGINE)
    a.b(0xA5, 0x0E, 0x48, 0xA5, 0x0F, 0x48)                                     # keep $0E/$0F
    a.abs(0xAE, LST)
    # the level: containers + this list's badges, 1-16
    a.abs(0xAD, 0x0673).abs(0xBC, "bshift").br(0xF0, "k_b")
    a.label("k_sh").b(0x4A, 0x88).br(0xD0, "k_sh")
    a.label("k_b").b(0x29, 0x03).abs(0x8D, KEY)
    a.abs(0xAD, 0x066F).b(0x4A, 0x4A, 0x4A, 0x4A, 0x38).abs(0x6D, KEY)          # containers - 1 + 1 + badges
    a.b(0xE0, 0x02).br(0xD0, "k_n4").abs(0xAC, 0x0350).b(0xC0, 0x7A).br(0xD0, "k_n4").b(0x18, 0x69, 0x01)  # shop 4: +1
    a.label("k_n4").b(0xC9, 0x11).br(0x90, "k_ok").b(0xA9, 0x10)
    a.label("k_ok").abs(0x8D, KEY)
    # this file's saved bytes: ($0E) = STORE + slot * 20
    a.b(0xA9, STORE & 0xFF, 0xA4, 0x16).br(0xF0, "p_lo").b(0x18, 0x69, PER_FILE)
    a.label("p_lo").b(0x85, 0x0E, 0xA9, STORE >> 8, 0x85, 0x0F)
    a.b(0xA0, SEED_AT, 0xB1, 0x0E).br(0xD0, "s_ok").b(0xA5, 0x15, 0x45, 0x18, 0x09, 0x01, 0x91, 0x0E)
    a.label("s_ok").abs(0x8D, SEED)
    a.abs(0xAC, STO).b(0xC0, 0xFF).br(0xF0, "w_ptr")
    a.b(0xB1, 0x0E).br(0xF0, "st_new").b(0xC9, 0x11).br(0xB0, "st_new").abs(0x8D, KEY).br(0x90, "w_ptr")
    a.label("st_new").abs(0xAD, KEY).b(0x91, 0x0E)
    # ($0E) = this list's row: weights + (level - 1) * n
    a.label("w_ptr").abs(0xBD, "wlo").b(0x85, 0x0E).abs(0xBD, "whi").b(0x85, 0x0F)
    a.abs(0xAC, KEY)
    a.label("w_row").b(0x88).br(0xF0, "w_done").b(0xA5, 0x0E, 0x18).abs(0x7D, "nn").b(0x85, 0x0E)
    a.br(0x90, "w_row").b(0xE6, 0x0F).br(0xB0, "w_row")
    a.label("w_done")
    a.b(0xA9, 0xFF).abs(0x8D, OUT).abs(0x8D, OUT + 1).abs(0x8D, OUT + 2)
    a.b(0xA9, 0x00).abs(0x8D, NOK).abs(0x8D, ACC).abs(0x8D, PK)
    # each pick
    a.label("pk_lp").abs(0xAD, PK).abs(0xCD, NUM).br(0xB0, "done")
    a.b(0xA9, TRIES).abs(0x8D, TRY)
    a.label("tr_lp")
    a.abs(0xAD, ACC).b(0x18, 0x69, 37).abs(0x8D, ACC)
    a.abs(0xAD, SEED).abs(0x4D, CTX).b(0x18).abs(0x6D, KEY).abs(0x20, "mix")
    a.b(0x18).abs(0x6D, ACC).abs(0x20, "mix").abs(0x4D, CTX).abs(0x20, "mix").b(0x29, 0x3F).abs(0x8D, RR)
    a.b(0xA9, 0x00).abs(0x8D, CUM).b(0xA0, 0x00)
    a.label("wk_lp").abs(0xAD, CUM).b(0x18, 0x71, 0x0E).abs(0x8D, CUM)
    a.abs(0xAD, RR).abs(0xCD, CUM).br(0x90, "wk_hit")
    a.b(0xC8, 0x98).abs(0xDD, "nn").br(0x90, "wk_lp").br(0xB0, "tr_nx")         # past the row: roll again
    a.label("wk_hit").abs(0x20, "ok").br(0xB0, "pk_take")
    a.label("tr_nx").abs(0xCE, TRY).br(0xD0, "tr_lp")
    # no luck: the first one he can get with odds above 0
    a.b(0xA0, 0x00)
    a.label("fb_lp").b(0xB1, 0x0E).br(0xF0, "fb_nx").abs(0x20, "ok").br(0xB0, "pk_take")
    a.label("fb_nx").b(0xC8, 0x98).abs(0xDD, "nn").br(0x90, "fb_lp").br(0xB0, "done")
    a.label("pk_take").b(0x98).abs(0xAC, PK).abs(0x99, OUT).abs(0xEE, PK).abs(0xEE, NOK)
    a.abs(0x4C, "pk_lp")
    a.label("done").b(0x68, 0x85, 0x0F, 0x68, 0x85, 0x0E, 0x60)
    # ok: Y = entry (of this list): carry set if Link may get it and it isn't picked yet (X = list kept)
    a.label("ok").b(0x98).abs(0x8D, CAND)
    for k in range(3):
        a.abs(0xAD, OUT + k).abs(0xCD, CAND).br(0xD0, f"okp{k}").abs(0x4C, "ok_no").label(f"okp{k}")
    a.abs(0xAD, CAND).b(0x18).abs(0x7D, "bases").b(0xA8)                          # Y = the global entry
    a.b(0x8A, 0x48)
    # lol_modes' swordless: a sword is a bomb upgrade (the wrappers' nth swaps the item), offered below 32 bombs
    a.abs(0xB9, "isword").br(0xF0, "ok_ns").abs(0xAD, 0x7FF7).br(0xF0, "ok_ns")
    a.abs(0xAD, 0x067C).b(0xC9, 32).br(0xB0, "ok_no2").abs(0x4C, "ok_all")
    a.label("ok_ns")
    for k in (0, 1):
        a.abs(0xBE, f"ca{k}").abs(0xBD, 0x0600).abs(0xD9, f"clo{k}").br(0x90, "ok_no2")
        a.abs(0xB9, f"chi{k}").br(0xF0, f"ok_y{k}").b(0xC9, 0xFE).br(0xD0, f"ok_c{k}")
        a.abs(0xBD, 0x0600).abs(0xCD, 0x067C).br(0xB0, "ok_no2").br(0x90, f"ok_y{k}")    # $FE: below max bombs
        a.label(f"ok_c{k}")
        a.abs(0xBD, 0x0600).abs(0xD9, f"chi{k}").br(0xB0, "ok_no2")
        a.label(f"ok_y{k}")
    a.label("ok_all").b(0x68, 0xAA).abs(0xAC, CAND).b(0x38, 0x60)
    a.label("ok_no2").b(0x68, 0xAA)
    a.label("ok_no").abs(0xAC, CAND).b(0x18, 0x60)
    # mix: x * 13 + $5B, then x ^ (x >> 3)
    a.label("mix").abs(0x8D, TT).b(0x0A, 0x0A).abs(0x8D, UU).b(0x0A, 0x18).abs(0x6D, UU).b(0x18).abs(0x6D, TT)
    a.b(0x18, 0x69, 0x5B).abs(0x8D, TT).b(0x4A, 0x4A, 0x4A).abs(0x4D, TT).b(0x60)
    a.label("bshift").b(*BADGE_SHIFT)
    a.label("nn").b(*[len(items) for _, items in LISTS])
    a.label("bases").b(*base)
    a.label("wlo").b(0, 0, 0)
    a.label("whi").b(0, 0, 0)
    a.label("isword").b(*[1 if c[1] in (0x02, 0x03) else 0 for c in allitems])
    for k in (0, 1):
        a.label(f"ca{k}").b(*[c[3 + k][0] & 0xFF for c in allitems])
        a.label(f"clo{k}").b(*[c[3 + k][1] for c in allitems])
        a.label(f"chi{k}").b(*[c[3 + k][2] for c in allitems])
    wat = {}
    for li, rows in enumerate(tables):
        a.label(f"w{li}"); wat[li] = len(a.code)
        for row in rows:
            a.b(*row)
    code = bytearray(a.bytes())
    lo_at, hi_at = a.labels["wlo"] - ENGINE, a.labels["whi"] - ENGINE
    for li in range(3):
        w = a.labels[f"w{li}"]
        code[lo_at + li], code[hi_at + li] = w & 0xFF, w >> 8
    assert ENGINE + len(code) <= 0xBBA0, hex(ENGINE + len(code))
    place(rom, ENGINE_BANK, ENGINE, bytes(code))
    notes.append(f"odds tables: engine + tables {len(code)} bytes in bank {ENGINE_BANK} at ${ENGINE:04X} ("
                 + ", ".join(f"{LISTS[i][0]} {len(LISTS[i][1])} items" for i in range(3)) + ")")
