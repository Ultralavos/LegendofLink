"""Legend of Link: odds tables for the old man choices, the A-F rewards and the shops.

Each list has a table (odds/<list>.csv): a row per heart level 1-16, a column per item, the numbers out of 128 (a row
may add up to less: the rest is "roll again"). Link's level is his containers plus that list's badges (S shops, D old
men, X rewards), at most 16.

Owner 2026-11-24: lines instead of rolls. The build turns each list's row for each level into a line: the items with
odds above 0, shuffled by their odds (lines()). A pick takes the first item of the level's line that Link can get
(owned, or its first tier missing: the lists' two conditions; the heart snubber's swords, Zombie Link's rings) and
isn't picked yet - or, for a second tier Link can't have yet, its first tier (LOWER: owner 2026-11-25); when the
line runs out, the vanilla fallback (the old man's hint, A-F's red potion, an empty place).

  old men   two picks; the level is saved the first time Link enters the room, so the offer stays
  A-F       one pick; saved the same way
  shops     three picks, never saved: they change when the containers or S badges change
The rolls are a hash of a per-file seed, the place (room / screen) and the level, so a saved offer comes out the same
each visit. Saved bytes: the unused third file's item area (bank 2 never touches it), 20 per file: 0-10 the old men
(Levels 1-9, 2Q 4 = E, 2Q 6 = F), 11-16 A-F, 17 the seed; lol_af clears them for a new file. Once the old man's
item or the reward is taken, lol_bombup's rec keeps that item there with bit 7 set (the end screen reads it); the
engine leaves such a byte alone.

The engine is in bank 3 (ENGINE; bank 4 until v3), reached through a bank-7 trampoline (TRAMP) that returns to the caller's bank."""
import csv, os

HERE = os.path.dirname(os.path.abspath(__file__))
ODDS_DIR = os.path.join(HERE, "odds")
ENGINE_BANK = 3                         # v3: bank 3 (was bank 4, the full monster bank)
ENGINE = 0xACA0                         # bank 3 free (after lol_genload's pattern getters)
import lol_fixed as _F, lol_entrances as _E
LATE = _F.FIXED and _E.GEN               # (1.0) the engine and its bigger tables: data bank 9, placed late
if LATE:
    ENGINE_BANK, ENGINE = 12, 0xB100               # (the top of data bank 12: lol_genload's variants stop below it)
_PENDING = []
TRAMP = 0xDFF0                          # bank 7 free (18 bytes)
LST, CTX, STO, NUM, OUT, RET = 0x0180, 0x0181, 0x0182, 0x0183, 0x0184, 0x0187   # (stack page, unused)
KEY, ACC, TRY, PK, CUM, RR, CAND, SEED, TT, UU, NOK = (0x0188, 0x0189, 0x018A, 0x018B, 0x018C, 0x018D, 0x018E,
                                                       0x018F, 0x0190, 0x0191, 0x0192)
EV, EV2 = TT, UU                        # (the heart snubber's even spread: mix's scratch, free outside a mix)
STORE = 0x606A                          # the third file's item area: 20 bytes per file
PER_FILE = 20
SEED_AT = 17
TRIES = 24
NAMES = ("old_men", "rewards", "shops")
# (owner 2026-11-25) a second tier picked while Link lacks the first gives the first: magical sword -> white sword,
# red candle -> blue candle, red ring -> blue ring, silver arrows -> wood arrows, blue book -> red book
LOWER = {0x03: 0x02, 0x07: 0x06, 0x13: 0x12, 0x09: 0x08, 0x25: 0x11}
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
    """The table for a list: odds/<name>.csv (written from the defaults the first time). (lol_upmix) a last entry
    named "upgrade" isn't in the file: each row takes a point from every item with odds for it."""
    if items and items[-1][0] == "upgrade":
        rows = load(name, items[:-1])
        return [[w - 1 if w > 0 else 0 for w in r] + [sum(1 for w in r if w > 0)] for r in rows]
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


BOOK_K = 0x01B0                         # (stack page, free) the pick the bookworm's red book takes ($FF: none)


def wrappers(a, list_id, items, p, ret_bank, store, n_pick, book=False):
    """In the caller's code: {p}count (CNT = how many picks) and {p}nth (K -> A = item, Y = its entry in the reversed
    tables, or A = $3F), with {p}t_item (reversed, as lol_choice's picker). store: code that leaves the save index in
    A ($FF: none), with the hash context in CTX (A also)."""
    from lol_choice import CNT, K
    n = len(items)
    a.label(p + "count")
    store(a)                                                                    # A = store index, CTX set
    a.abs(0x8D, STO).b(0xA9, list_id).abs(0x8D, LST).b(0xA9, n_pick).abs(0x8D, NUM)
    a.b(0xA9, ret_bank).abs(0x8D, RET).abs(0x20, TRAMP)
    a.abs(0xAD, NOK).b(0x85, CNT)
    if book:                            # (owner 2026-11-25) the bookworm's red book: lol_choice's BOOK_RT
        import lol_choice as C
        a.b(0xA0, n_pick).abs(0x20, C.BOOK_RT["bkc"])
    a.b(0x60)
    a.label(p + "nth")
    if book:
        a.abs(0x20, C.BOOK_RT["bkn"]).br(0x90, p + "n_nb").b(0xA0, n, 0x60)   # (Y = n: the extra entry)
        a.label(p + "n_nb")
    a.b(0xA4, K).abs(0xB9, OUT).b(0xC9, 0xFF).br(0xD0, p + "n_ok").b(0xA9, 0x3F, 0x60)
    a.label(p + "n_ok").b(0x49, 0xFF, 0x18, 0x69, n, 0xA8)                       # Y = n - 1 - i
    if items[-1][0] == "upgrade":       # (lol_upmix: the upgrade entry: this place's upgrade, or an empty place)
        import lol_upmix as UM, lol_v3core as V
        a.abs(0xB9, p + "t_item").b(0xC9, items[-1][1]).br(0xD0, p + "n_nu").b(*V.far(14, UM.V_URES)).b(0x60)
        a.label(p + "n_nu")
    import lol_v10                      # (1.0: the wood sword is a sword too)
    a.abs(0xB9, p + "t_item").b(0xC9, 0x04).br(0xB0, p + "n_r").b(0xC9, 0x01 if lol_v10.ON else 0x02).br(0x90, p + "n_r")
    a.abs(0xAD, 0x7FF7).br(0xF0, p + "n_sw").b(0xA9, 0x24, 0x60)                  # swordless: a bomb upgrade
    a.label(p + "n_sw").abs(0xB9, p + "t_item")
    a.label(p + "n_r").b(0x60)
    a.label(p + "t_item").b(*[c[1] for c in reversed(items)])


def lines(li, rows):
    """(owner 2026-11-24) The build's lines for a list: per level 1-16 its entries with odds above 0, in an order
    shuffled by the odds (likelier ones tend to come first). The game offers the first ones Link may get."""
    import random
    seed = int(os.environ.get("LOL_SET_SEED") or os.environ.get("LOL_SEED") or 0)
    rng = random.Random(seed * 1000003 + 0x0DD5 + 7 * li)
    out = []
    for row in rows:
        ent = [i for i, w in enumerate(row) if w > 0]
        out.append(sorted(ent, key=lambda i: -rng.random() ** (1 / row[i])))
    return out


def lol_fixed_v10():
    import lol_v10
    return lol_v10.ON


def apply(rom: bytearray, notes: list) -> None:
    from lol_af import Asm, place, BANK
    assert len(LISTS) == 3 and all(LISTS), LISTS
    import lol_v10 as V10
    v10 = V10.ON
    if v10:                             # (1.0, seeded) the build's lists: lol_v10; four shop kinds' own
        up = any(c[0] == "upgrade" for c in LISTS[0][1])
        idx = [{c[0]: i for i, c in enumerate(items)} for _, items in LISTS]
        sets = [V10.old_men_lines([c[0] for c in LISTS[0][1]], up), V10.shrine_lines(up)]
        sets += [V10.shop_lines(k, [c[0] for c in LISTS[2][1]]) for k in range(4)]
        set_list = [0, 1, 2, 2, 2, 2]
        line_sets = [[[idx[set_list[k]][n] for n in line] for line in lines_] for k, lines_ in enumerate(sets)]
    else:
        tables = [load(name, items) for name, items in LISTS]
        set_list = [0, 1, 2]
        line_sets = [lines(li, rows) for li, rows in enumerate(tables)]
    base, g = [], 0
    allitems = []
    for li, (name, items) in enumerate(LISTS):
        if li == 2 and lol_fixed_v10() and items == LISTS[0][1][:len(items)]:
            base.append(base[0])        # (1.0) the shops' items are the old men's: one set of tables
            continue
        base.append(g); g += len(items)
        allitems += items
    t = bytes([0xA9, ENGINE_BANK, 0x20, 0xAC, 0xFF, 0x20, ENGINE & 0xFF, ENGINE >> 8, 0xAD, RET & 0xFF, RET >> 8,
               0x4C, 0xAC, 0xFF])
    at = BANK(7) + TRAMP - 0xC000
    assert all(x == 0xFF for x in rom[at:at + len(t)])
    rom[at:at + len(t)] = t

    V10_FIX = []
    a = Asm(ENGINE)
    a.b(0xA5, 0x0E, 0x48, 0xA5, 0x0F, 0x48)                                     # keep $0E/$0F
    a.abs(0xAE, LST)
    # the level: containers + this list's badges, 1-16
    a.abs(0xAD, 0x0673).abs(0xBC, "bshift").br(0xF0, "k_b")
    a.label("k_sh").b(0x4A, 0x88).br(0xD0, "k_sh")
    a.label("k_b").b(0x29, 0x03).abs(0x8D, KEY)
    a.abs(0xAD, 0x066F).b(0x4A, 0x4A, 0x4A, 0x4A, 0x38).abs(0x6D, KEY)          # containers - 1 + 1 + badges
    if not v10:
        a.b(0xE0, 0x02).br(0xD0, "k_n4").abs(0xAC, 0x0350).b(0xC0, 0x7A).br(0xD0, "k_n4").b(0x18, 0x69, 0x01)  # shop 4: +1
    a.label("k_n4").b(0xC9, 0x11).br(0x90, "k_ok").b(0xA9, 0x10)
    a.label("k_ok").abs(0x8D, KEY)
    # this file's saved bytes: ($0E) = STORE + slot * 20
    a.b(0xA9, STORE & 0xFF, 0xA4, 0x16).br(0xF0, "p_lo").b(0x18, 0x69, PER_FILE)
    a.label("p_lo").b(0x85, 0x0E, 0xA9, STORE >> 8, 0x85, 0x0F)
    a.b(0xA0, SEED_AT, 0xB1, 0x0E).br(0xD0, "s_ok").b(0xA5, 0x15, 0x45, 0x18, 0x09, 0x01, 0x91, 0x0E)
    a.label("s_ok").abs(0x8D, SEED)
    a.abs(0xAC, STO).b(0xC0, 0xFF).br(0xF0, "w_ptr")
    a.b(0xB1, 0x0E).br(0xF0, "st_new").br(0x30, "w_ptr")                        # bit 7: given (lol_bombup rec)
    a.b(0xC9, 0x11).br(0xB0, "st_new").abs(0x8D, KEY).br(0x90, "w_ptr")
    a.label("st_new").abs(0xAD, KEY).b(0x91, 0x0E)
    # ($0E) = this list's row: weights + (level - 1) * n
    if v10:                             # (1.0) a shop: its kind's lines (CTX = the cave type, $77-$7A: shops A-D)
        a.label("w_ptr").b(0x8A)
        a.b(0xE0, 0x02).br(0xD0, "wp_n").abs(0xAD, CTX).b(0x38, 0xE9, 0x77).br(0xB0, "wp_k").b(0xA9, 0x00)
        a.label("wp_k").b(0xC9, 0x04).br(0x90, "wp_ok").b(0xA9, 0x00)
        a.label("wp_ok").b(0x18, 0x69, 0x02)
        a.label("wp_n")
        a.b(0xA8).abs(0xB9, "wlo").b(0x85, 0x0E).abs(0xB9, "whi").b(0x85, 0x0F)
    else:
        a.label("w_ptr").abs(0xBD, "wlo").b(0x85, 0x0E).abs(0xBD, "whi").b(0x85, 0x0F)
    if v10:                             # (1.0) the set's 16 line addresses (lo, then hi): lines end with $FF
        a.abs(0xAC, KEY).b(0x88, 0xB1, 0x0E, 0x48, 0x98, 0x18, 0x69, 0x10, 0xA8, 0xB1, 0x0E, 0x85, 0x0F, 0x68, 0x85, 0x0E)
    else:
        a.abs(0xAC, KEY)
        a.label("w_row").b(0x88).br(0xF0, "w_done").b(0xA5, 0x0E, 0x18).abs(0x7D, "nn").b(0x85, 0x0E)
        a.br(0x90, "w_row").b(0xE6, 0x0F).br(0xB0, "w_row")
    a.label("w_done")
    a.b(0xA9, 0xFF).abs(0x8D, OUT).abs(0x8D, OUT + 1).abs(0x8D, OUT + 2)
    a.b(0xA9, 0x00).abs(0x8D, NOK).abs(0x8D, PK)
    # (owner 2026-11-24) each pick: the first entry of this level's line (the build's order) that Link may get and
    # isn't picked yet; the line runs out: fewer picks
    a.label("pk_lp").abs(0xAD, PK).abs(0xCD, NUM).br(0xB0, "done")
    a.b(0xA9, 0x00).abs(0x8D, RR)
    a.label("wl").abs(0xAD, RR).abs(0xDD, "nn").br(0xB0, "done").b(0xA8, 0xB1, 0x0E, 0xC9, 0xFF).br(0xF0, "done")
    a.b(0xA8).abs(0x20, "ok").br(0xB0, "pk_take")
    # (owner 2026-11-25) a second tier Link can't have yet (no first tier): the first tier in its place
    a.label("dn").b(0x98, 0x18).abs(0x7D, "bases").b(0xA8).abs(0xB9, "down").b(0xC9, 0xFF).br(0xF0, "wl_nx")
    a.b(0xA8).abs(0x20, "ok").br(0xB0, "pk_take")
    if v10:                             # (1.0) down the line: magical sword -> white -> wood
        a.abs(0x4C, "dn")
    a.label("wl_nx").abs(0xEE, RR).abs(0x4C, "wl")
    a.label("pk_take").b(0x98).abs(0xAC, PK).abs(0x99, OUT).abs(0xEE, PK).abs(0xEE, NOK)
    a.abs(0x4C, "pk_lp")
    a.label("done").b(0x68, 0x85, 0x0F, 0x68, 0x85, 0x0E, 0x60)
    # snsw: Y = an entry (X the list): carry set if it's a sword and Link has the heart snubber (Y, X kept)
    import lol_uptable as UT
    sb = UT.bit("heart snubber")
    # (and the same for a ring with Zombie Link)
    zb = UT.bit("zombie link")
    a.label("snsw").abs(0x8C, EV2).b(0x98, 0x18).abs(0x7D, "bases").b(0xA8)
    a.abs(0xAD, sb[0]).b(0x29, sb[1]).br(0xF0, "sn_z").abs(0xB9, "isword").br(0xD0, "sn_yes")
    a.label("sn_z").abs(0xAD, zb[0]).b(0x29, zb[1]).br(0xF0, "sn_no").abs(0xB9, "isring").br(0xD0, "sn_yes")
    a.label("sn_no").abs(0xAC, EV2).b(0x18, 0x60)
    a.label("sn_yes").abs(0xAC, EV2).b(0x38, 0x60)
    # ok: Y = entry (of this list): carry set if Link may get it and it isn't picked yet (X = list kept)
    a.label("ok").b(0x98).abs(0x8D, CAND)
    a.abs(0x20, "snsw").br(0x90, "ok_sn").abs(0x4C, "ok_no")                      # (heart snubber: no swords)
    a.label("ok_sn")
    for k in range(3):
        a.abs(0xAD, OUT + k).abs(0xCD, CAND).br(0xD0, f"okp{k}").abs(0x4C, "ok_no").label(f"okp{k}")
    a.abs(0xAD, CAND).b(0x18).abs(0x7D, "bases").b(0xA8)                          # Y = the global entry
    ups = [g for g, c in enumerate(allitems) if c[0] == "upgrade"]
    if ups:                             # (lol_upmix: an upgrade entry: its own check)
        import lol_upmix as UM, lol_v3core as V
        for k, g in enumerate(ups):
            kind = 0 if g < len(LISTS[0][1]) else 1             # (old men's, a prize's)
            a.b(0xC0, g).br(0xD0, f"ok_u{k}").b(0x8A, 0x48, 0xA9, kind)
            a.b(*V.far(14, UM.V_UCHECK, ENGINE_BANK)).b(0x68, 0xAA).abs(0xAC, CAND).b(0x60)
            a.label(f"ok_u{k}")
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
    a.label("bshift").b(*BADGE_SHIFT)
    a.label("nn").b(*[len(items) for _, items in LISTS])
    a.label("bases").b(*base)
    a.label("wlo").b(*[0] * len(line_sets))
    a.label("whi").b(*[0] * len(line_sets))
    a.label("isword").b(*[1 if c[1] in ((0x01, 0x02, 0x03) if v10 else (0x02, 0x03)) else 0 for c in allitems])
    a.label("isring").b(*[1 if c[1] in (0x12, 0x13) else 0 for c in allitems])
    # down: per entry, the same list's entry of its first tier (sword, candle, ring, arrows, book), else $FF
    down = []
    for li, (_, items) in enumerate(LISTS):
        if li == 2 and base[2] == base[0] and li != 0:
            continue
        codes = [c[1] for c in items]
        for c in items:
            low = (V10.LOWER if v10 else LOWER).get(c[1])
            down.append(codes.index(low) if low in codes else 0xFF)
    a.label("down").b(*down)
    for k in (0, 1):
        a.label(f"ca{k}").b(*[c[3 + k][0] & 0xFF for c in allitems])
        a.label(f"clo{k}").b(*[c[3 + k][1] for c in allitems])
        a.label(f"chi{k}").b(*[c[3 + k][2] for c in allitems])
    if v10:                             # compact: each distinct line once, then the set's address table
        seen = {}
        for k, line_set in enumerate(line_sets):
            for h, line in enumerate(line_set):
                key = (set_list[k], tuple(line))
                if key not in seen:
                    seen[key] = f"ln{len(seen)}"
                    a.label(seen[key]).b(*line, 0xFF)
        for k, line_set in enumerate(line_sets):
            names = [seen[(set_list[k], tuple(line))] for line in line_set]
            a.label(f"w{k}")
            a.b(*[0] * 32)
            V10_FIX.append((k, names))
    else:
        for k, line_set in enumerate(line_sets):
            a.label(f"w{k}")
            n = len(LISTS[set_list[k]][1])
            for line in line_set:
                a.b(*(line + [0xFF] * (n - len(line))))
    code = bytearray(a.bytes())
    lo_at, hi_at = a.labels["wlo"] - ENGINE, a.labels["whi"] - ENGINE
    for k in range(len(line_sets)):
        w = a.labels[f"w{k}"]
        code[lo_at + k], code[hi_at + k] = w & 0xFF, w >> 8
    for k, names in V10_FIX:            # (1.0) the address tables
        at = a.labels[f"w{k}"] - ENGINE
        for h, nm in enumerate(names):
            code[at + h], code[at + 16 + h] = a.labels[nm] & 0xFF, a.labels[nm] >> 8
    if LATE:
        assert ENGINE + len(code) <= 0xBB60, hex(ENGINE + len(code))
        _PENDING.append(bytes(code))
    else:
        assert ENGINE + len(code) <= 0xBBA0, hex(ENGINE + len(code))
        place(rom, ENGINE_BANK, ENGINE, bytes(code))
    notes.append(f"odds tables: engine + tables {len(code)} bytes in bank {ENGINE_BANK} at ${ENGINE:04X} ("
                 + ", ".join(f"{LISTS[i][0]} {len(LISTS[i][1])} items" for i in range(3)) + ")")


def late(rom: bytearray) -> None:
    """(1.0) the engine into bank 9, once lol_genload has grown the ROM."""
    from lol_af import place
    for code in _PENDING:
        place(rom, ENGINE_BANK, ENGINE, code)
    _PENDING.clear()
