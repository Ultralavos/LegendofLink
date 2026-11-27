"""Legend of Link: the page's "Upgrade mix (needs testing)" (owner 2026-11-26; LOL_UPMIX=1, seeded builds only:
lol_fixed.UPMIX).

Stage 1 (this module and its pieces elsewhere):
  - the item deck (lol_fixed.deck / lol_genload's dfx) holds one upgrade card besides the cards and XP bags, at a
    place the seed picks (lol_fixed.upos); each heart container Link gains moves it one place nearer the next card
    (UFLAGS' low nibble: the moves). Drawn, it is the first tier 2 upgrade of the seed's line that Link may have
    and doesn't own (lol_upgrades' upick: marked taken, as a cave's ware is, with the gone cave's code), shown as
    the third ware slot's item ($30); none (or three owned already): an orange XP bag.
  - taking a ware slot's item ($2E-$30) outside an upgrade cave gives its upgrade as buying it does (lol_upgrades'
    t_af: the bit, the owned slot's picture, map master's maps...).
State (owner 2026-11-27: file 3's spare per-file bytes in save RAM - the game's per-slot arrays at $6512 / $6515 /
$6518, slot 3's, which the menu never checks (the third file is hidden); cleared for a new file by lol_entrances. Until
0.398 they were in shrine A-C's records' fifth bytes, which hold a shrine's cellar items):
  UPDECK  the upgrade card's upgrade + 1 ($FF none, 0 not drawn yet)
  UPL9    level 9's (stage 4)
  UFLAGS  low nibble: the moves; bit 7: an upgrade taken from a shrine (stage 3)
"""
from lol_af import Asm, BANK

REC = 0x7FAD
UPDECK, UPL9, UFLAGS = 0x6514, 0x6517, 0x651A
from lol_genload import DECK_PTR        # (the item deck's next card)
CONTAINER = 0x1A
RANK, P0, P1, TMP = 0x0195, 0x0199, 0x019A, 0x019C   # (lol_upgrades' engine scratch)
KIND, SLOT = 0x01A1, 0x01A2             # (stack page, unused)
HINT_QS = 0x7F48                        # lol_genload: per entrance its hint quote + 1; a dungeon's entrance (never a hint
                                        # cave) keeps its old man's / prize's upgrade here: 0 not picked, $C0 none,
                                        # $80 | the upgrade
STORE = 0x7F00                          # lol_entrances: each entrance's destination (levels 1-9, shrines $0A-$0D)
N_ENT = 71
# fixed entry points (the last data bank, below its trampolines): lol_choice's and lol_odds' code is built before
# this module's
VEC = 0xBB50
NOSHOOT_AT = 0xBB00                     # (every build) noshoot, below the vectors; the Upgrade mix's code below it
V_NOSHOOT = VEC + 3 * 7
V_URES, V_UCHECK, V_UL9, V_UCARD, V_UITEM, V_UCAVE, V_UTAKE = (VEC + 3 * k for k in range(7))
UCONV = 0x01A3                          # (stack page, unused) 1 while in an upgrade cave turned plain shop
PLAIN_CAVE = 13                         # the plain shop's wares and prices: shop cave 13's (the shield, bombs, arrows)
TIER_OF = (0, 2)                        # old men: tier 1; shrine prizes: tier 3
CODE_OM, CODE_SH = 0x2E, 0x2F           # their ware slots' items (0, 1); the deck's and level 9's: $30 (slot 2)
UCARD = UITEM = BANKX = UAT = _PENDING = None                    # bank 0 (set in apply): the deck's next card; the upgrade card's item


def apply(rom: bytearray, notes: list) -> None:
    import lol_fixed
    if not lol_fixed.UPMIX:
        return
    import lol_v3core as V
    import lol_bombup as B
    import lol_upgrades as U
    (tk_af, af0), (tk_hi, hi0) = B.TAKE_FARS
    E = U.ENGINE
    import lol_pictures as PIC
    import lol_uptable as UT
    dk = lol_fixed.deck()
    TX = U.TEXTS
    from lol_saveblock import HINT_BUF
    from lol_swords import CAVE_WARES as W_ROM
    PW = [rom[W_ROM + 3 * PLAIN_CAVE + k] for k in range(3)]
    PP = [rom[W_ROM + 0x3C + 3 * PLAIN_CAVE + k] for k in range(3)]

    def build(o, bk):
        a = Asm(o)
        f0 = lambda r: V.far(0, r, bk)              # (a far call into bank 0 from here)
        # ucard (lol_genload's dfx, far-called): A = the deck's next card (0-4 lol_genload's citems, 5 the upgrade
        # card), DECK_PTR on. The upgrade card's place: UPOS0 - the moves; before it the deck's own, after it one back
        a.label("ucard").b(0xA9, lol_fixed.upos()).b(0x38).abs(0xED, UFLAGS).b(0x29, 0x0F).abs(0x8D, 0x0173)
        a.abs(0xAE, DECK_PTR).b(0xE0, len(dk) + 1).br(0xB0, "c_o")
        a.abs(0xEE, DECK_PTR).abs(0xEC, 0x0173).br(0x90, "c_lo").br(0xF0, "c_up")
        a.b(0xCA)
        a.label("c_lo").abs(0xBD, "deck").b(0x60)
        a.label("c_up").b(0xA9, 0x05, 0x60)
        a.label("c_o").b(0xA9, 0x03, 0x60)                                        # (none left: +15)
        # uitem: A = the upgrade card's item: its upgrade (UPDECK: 0 not picked yet, $FF none: an orange XP bag,
        # else the upgrade + 1), picked once (upick: the first tier 2 one Link may have) and shown as the third ware
        # slot's item ($30: WIX + 2, its picture loaded)
        a.label("uitem").abs(0xAD, UT.OWN_N).b(0xC9, 0x03).br(0x90, "u_go").b(0xA9, 0x29, 0x60)   # (three: XP)
        a.label("u_go").abs(0xAD, UPDECK).br(0xD0, "u_h")
        a.b(0xA9, 0x01).abs(0x20, "upick").br(0xB0, "u_n").b(0xE8).abs(0x8E, UPDECK).br(0xD0, "u_h")
        a.label("u_n").b(0xA9, 0xFF).abs(0x8D, UPDECK)
        a.label("u_h").abs(0xAD, UPDECK).b(0xC9, 0xFF).br(0xD0, "u_g").b(0xA9, 0x29, 0x60)
        a.label("u_g").b(0xAA, 0xCA).abs(0x8E, UT.WIX + 2).b(0xA9, 0xFF).abs(0x8D, UT.WIX).abs(0x8D, UT.WIX + 1)
        a.b(0xA2, 0x01).b(*f0(PIC.LOAD["load"]))
        a.b(0xA9, UT.WARE_CODES[2], 0x60)
        # pre (TakeItem's first far call): a heart container moves the upgrade card one nearer (while it's not the
        # next card already, nor drawn)
        a.label("pre").b(0xC9, CONTAINER).br(0xD0, "p_x").b(0x48)
        a.b(0xA9, lol_fixed.upos()).b(0x38).abs(0xED, UFLAGS).b(0x29, 0x0F)      # its place now
        a.abs(0xCD, DECK_PTR).br(0x90, "p_n").br(0xF0, "p_n")                    # (at or before the next: stays)
        a.abs(0xEE, UFLAGS)
        a.label("p_n").b(0x68)
        a.label("p_x").b(*f0(af0)).b(0x60)
        # hix (TakeItem's $24+ far call): a ware slot's item outside a cave: its upgrade
        a.label("hix").b(0xC9, 0x2E).br(0x90, "h_x").b(0xC9, 0x31).br(0xB0, "h_x")
        a.b(0x38, 0xE9, 0x2E, 0xAA).b(0xC9, 0x01).br(0xD0, "h_t")
        a.abs(0xAD, UFLAGS).b(0x09, 0x80).abs(0x8D, UFLAGS)                    # (a shrine's: no more there)
        a.label("h_t").b(*f0(E["t_af"])).b(0x60)
        a.label("h_x").b(*f0(hi0)).b(0x60)
        # upick: A = a tier (0-2; 3: any): X = the first upgrade of its line not taken, that Link doesn't own and
        # may have now (no cave's rank: those that need one never), marked taken (the gone cave's code, lol_upgrades'
        # LINES); C set: none (or Link owns three)
        # (A bit 7: a dry run, nothing marked)
        a.label("upick").abs(0x8D, P0).abs(0xAD, UT.OWN_N).b(0xC9, 0x03).br(0xB0, "pk_no")
        a.b(0xA9, 0xFF).abs(0x8D, RANK)
        a.abs(0xAD, P0).b(0x29, 0x7F, 0xAA).b(0xE0, 0x03).br(0x90, "pk_t")
        a.b(0xA2, 0x00, 0xA9, sum(len(x) for x in UT.TIERS)).abs(0x8D, P1).abs(0x4C, "pk_lp")   # any: every line
        a.label("pk_t").abs(0xBD, "tend").abs(0x8D, P1).abs(0xBD, "tstart").b(0xAA)
        a.label("pk_lp").b(0x8A).abs(0xCD, P1).br(0xB0, "pk_no")
        a.b(*f0(E["getc"])).br(0xD0, "pk_nx")                               # (taken)
        a.abs(0xBC, "tier_items").b(*f0(E["elig"])).br(0xB0, "pk_nx")    # (not now)
        a.b(0x8A, 0x48).abs(0xBD, "tier_items").b(0xAA).b(*f0(E["uget"])).abs(0x8D, TMP).b(0x68, 0xAA)
        a.abs(0xAD, TMP).br(0xD0, "pk_nx")                                      # (owned)
        a.abs(0xAD, P0).br(0x30, "pk_dry")
        a.b(0xA9, lol_fixed.gone_cave() + 1).b(*f0(E["setc"]))
        a.label("pk_dry")
        a.abs(0xBD, "tier_items").b(0xAA, 0x18, 0x60)
        a.label("pk_nx").b(0xE8).abs(0x4C, "pk_lp")
        a.label("pk_no").b(0x38, 0x60)
        # place: CTX (lol_odds: old men 0-8 levels 1-9, prizes 11-16 the letters) -> Y = its dungeon's entrance (C
        # clear), C set: none
        from lol_odds import CTX
        a.label("place").abs(0xAD, CTX).b(0xC9, 0x09).br(0xB0, "pl_h").b(0x69, 0x01).br(0x90, "pl_d")
        a.label("pl_h").b(0xE9, 0x01)                                            # (C set: CTX - 1 = $0A + letter)
        a.label("pl_d").abs(0x8D, TMP).b(0xA2, N_ENT - 1)
        a.label("pl_l").abs(0xBD, STORE).abs(0xCD, TMP).br(0xF0, "pl_f").b(0xCA).br(0x10, "pl_l").b(0x38, 0x60)
        a.label("pl_f").b(0x8A, 0xA8, 0x18, 0x60)
        # ucheck (lol_odds' ok, an upgrade entry; A = 0 old men, 1 a prize): C set if it may be offered
        a.label("ucheck").abs(0x8D, KIND).abs(0xAD, UT.OWN_N).b(0xC9, 0x03).br(0xB0, "uc_no")   # (three: none)
        a.abs(0x20, "place").br(0xB0, "uc_no")
        a.abs(0xB9, HINT_QS).br(0xF0, "uc_f").b(0xC9, 0xC0).br(0xF0, "uc_no").b(0x29, 0x3F, 0xAA)
        a.b(*f0(E["uget"])).br(0xD0, "uc_no").b(0x38, 0x60)                     # (picked here, not taken yet)
        a.label("uc_f").abs(0xAD, KIND).br(0xF0, "uc_1").abs(0xAD, UFLAGS).br(0x30, "uc_no")
        a.label("uc_1").abs(0xAC, KIND).abs(0xB9, "tierof").b(0x09, 0x80).abs(0x20, "upick").br(0xB0, "uc_no")
        a.b(0x38, 0x60)
        a.label("uc_no").b(0x18, 0x60)
        # ures (lol_odds' wrappers' nth: A = $2E / $2F): this place's upgrade, picked once (its tier's first that
        # Link may have), shown in its ware slot ($2E / $2F, the picture loaded); none: an empty place ($3F)
        a.label("ures").b(0x38, 0xE9, CODE_OM).abs(0x8D, KIND).abs(0xAD, UT.OWN_N).b(0xC9, 0x03).br(0xB0, "ur_e")
        a.abs(0x20, "place").br(0xB0, "ur_e")
        a.abs(0x8C, SLOT).abs(0xB9, HINT_QS).br(0xD0, "ur_h")
        a.abs(0xAD, KIND).br(0xF0, "ur_1").abs(0xAD, UFLAGS).br(0x30, "ur_n")
        a.label("ur_1").abs(0xAC, KIND).abs(0xB9, "tierof").abs(0x20, "upick").br(0xB0, "ur_n")
        a.b(0x8A, 0x09, 0x80).abs(0xAC, SLOT).abs(0x99, HINT_QS).br(0xD0, "ur_h")
        a.label("ur_n").b(0xA9, 0xC0).abs(0xAC, SLOT).abs(0x99, HINT_QS)
        a.label("ur_e").b(0xA9, 0x3F, 0x60)
        a.label("ur_h").b(0xC9, 0xC0).br(0xF0, "ur_e").b(0x29, 0x3F, 0xAA).b(*f0(E["uget"])).br(0xD0, "ur_e")
        a.abs(0xAC, KIND).b(0x8A).abs(0x99, UT.WIX).abs(0x20, "uload")
        a.abs(0xAD, KIND).b(0x18, 0x69, CODE_OM, 0x60)
        a.label("uload").b(0xA2, 0x01).b(*f0(PIC.LOAD["load"])).b(0x60)
        # ul9 (lol_genload's dfx: level 9's red potion, $FD): an upgrade of any tier instead while Link owns fewer
        # than three when it first shows (UPL9 as UPDECK); else the red potion
        a.label("ul9").abs(0xAD, UT.OWN_N).b(0xC9, 0x03).br(0x90, "l9_go").b(0xA9, 0x20, 0x60)   # (three: potion)
        a.label("l9_go").abs(0xAD, UPL9).br(0xD0, "l9_h")
        a.b(0xA9, 0x03).abs(0x20, "upick").br(0xB0, "l9_n").b(0xE8).abs(0x8E, UPL9).br(0xD0, "l9_h")
        a.label("l9_n").b(0xA9, 0xFF).abs(0x8D, UPL9)
        a.label("l9_h").abs(0xAD, UPL9).b(0xC9, 0xFF).br(0xD0, "l9_g").b(0xA9, 0x20, 0x60)
        a.label("l9_g").b(0xAA, 0xCA).b(*f0(E["uget"])).br(0xF0, "l9_s").b(0xA9, 0x20, 0x60)   # (taken: the potion)
        a.label("l9_s").abs(0x8E, UT.WIX + 2).abs(0x20, "uload").b(0xA9, UT.WARE_CODES[2], 0x60)
        # ucave (bank 1's cave fill, in place of the engine's upw): an upgrade cave while Link owns three and hasn't
        # bought there: a plain shop (UCONV; shop cave 13's wares); else upw as before
        from lol_upgrades import SHOPS, CAVE_WARES, CAVE_PRICES
        a.label("ucave").b(0xA9, 0x00).abs(0x8D, UCONV).abs(0xAD, 0x0350).b(0xA2, 0x02)
        a.label("cv_f").abs(0xDD, "cpers").br(0xF0, "cv_g").b(0xCA).br(0x10, "cv_f")
        a.label("cv_n").b(*f0(E["upw"])).b(0x60)
        a.label("cv_u").b(0xA0, 0x00)                                            # its line: the upgrade cave's
        a.label("cv_t0").abs(0xB9, "text0").abs(0x99, HINT_BUF).b(0xC8, 0xC0, len(TX[0])).br(0xD0, "cv_t0")
        a.abs(0x4C, "cv_n")
        a.label("cv_g").abs(0xAD, UT.OWN_N).b(0xC9, 0x03).br(0x90, "cv_u")
        a.abs(0xAD, UT.LINES + 7).abs(0x3D, "cmask").br(0xD0, "cv_u")
        a.b(0xA0, 0x00)                                                          # a plain shop's line
        a.label("cv_t1").abs(0xB9, "text1").abs(0x99, HINT_BUF).b(0xC8, 0xC0, len(TX[1])).br(0xD0, "cv_t1")
        a.abs(0xEE, UCONV).abs(0xBC, "cofs")
        for k in range(3):
            a.abs(0xAD, "pw" + str(k)).abs(0x99, CAVE_WARES).abs(0xAD, "pp" + str(k)).abs(0x99, CAVE_PRICES).b(0xC8)
        a.b(0x18, 0x60)
        # utake (bank 1's cave take, a ware of an upgrade cave's person; A the item, X the slot): C set: a plain
        # shop's (take it as a shop's); else the upgrade (the engine's uptake)
        a.label("utake").abs(0xAC, UCONV).br(0xF0, "ut_u").b(0x38, 0x60)
        a.label("ut_u").b(*f0(E["uptake"])).b(0x18, 0x60)
        a.label("text0").b(*TX[0])
        a.label("text1").b(*TX[1])
        a.label("cpers").b(*[p for p, c, w in SHOPS])
        a.label("cofs").b(*[3 * c for p, c, w in SHOPS])
        a.label("cmask").b(0x10, 0x20, 0x40)
        for k in range(3):
            a.label("pw" + str(k)).b(PW[k])
            a.label("pp" + str(k)).b(PP[k])
        a.label("tierof").b(*TIER_OF)
        a.label("deck").b(*dk)
        # (bank 0's tables, copied: this code runs in its own bank)
        a.label("tier_items").b(*[k for tier in UT.TIERS for k in tier])
        a.label("tstart").b(*[sum(len(x) for x in UT.TIERS[:i]) for i in range(3)])
        a.label("tend").b(*[sum(len(x) for x in UT.TIERS[:i + 1]) for i in range(3)])
        return a
    # (the switchable banks are full: the last data bank's top, below its trampolines; lol_genload's variants stop
    # short of it, UAT)
    from lol_af import place
    n = len(build(0x8000, 0).bytes())
    bk = 14
    at = (NOSHOOT_AT - n) & ~0x0F
    global UAT
    UAT = at
    a = build(at, bk)
    L = a.labels
    vec = Asm(VEC)
    for name in ("ures", "ucheck", "ul9", "ucard", "uitem", "ucave", "utake"):
        vec.abs(0x4C, L[name])
    global _PENDING
    _PENDING = (bk, at, a.bytes(), vec.bytes())            # (placed by late(): the data banks exist once lol_genload is in)
    L = a.labels
    global UCARD, UITEM, BANKX
    UCARD, UITEM, BANKX = L["ucard"], L["uitem"], bk
    for cpu, routine, new in ((tk_af, af0, L["pre"]), (tk_hi, hi0, L["hix"])):
        for bank in range(7):
            o = BANK(bank) + cpu - 0x8000
            assert bytes(rom[o:o + 7]) == V.far(0, routine), (bank, hex(cpu))
            rom[o:o + 7] = V.far(bk, new)
    notes.append(f"upgrade mix: the upgrade card at deck place {lol_fixed.upos()} of {len(lol_fixed.deck()) + 1}; "
                 f"the gone cave {lol_fixed.gone_cave()}")


def noshoot(o):
    """(owner 2026-11-26, every build) noshoot (bank 4's statue shot, far-called): C set while the room holds the
    purple (Hydra) Gohma, the pink Digdogger or the old man Patra (lol_gohma, lol_digdogger, lol_patra): those
    bosses may stand in any room ZORA allows (lol_gen.boss_of), statue rooms too. Y kept."""
    import lol_gohma, lol_digdogger, lol_patra
    HVE = 0x016F
    sj = Asm(o)
    sj.label("ns").b(0x98, 0x48, 0xA0, 0x0B)
    sj.label("sj_l").abs(0xB9, 0x034F)
    sj.b(0xC9, 0x33).br(0xF0, "sj_g").b(0xC9, 0x34).br(0xF0, "sj_g")
    sj.b(0xC9, 0x38).br(0xF0, "sj_d").b(0xC9, 0x18).br(0xF0, "sj_d")
    sj.b(0xC9, 0x47).br(0xF0, "sj_p").b(0xC9, 0x48).br(0xF0, "sj_p")
    sj.label("sj_n").b(0x88).br(0xD0, "sj_l").b(0x68, 0xA8, 0x18, 0x60)
    sj.label("sj_g").abs(0xAD, HVE).b(0xC9, lol_gohma.AT).br(0xB0, "sj_x").br(0x90, "sj_n")
    sj.label("sj_p").abs(0xAD, HVE).b(0xC9, lol_patra.AT).br(0xB0, "sj_x").br(0x90, "sj_n")
    sj.label("sj_d").abs(0xAD, HVE).b(0xC9, lol_digdogger.AT).br(0x90, "sj_n")
    sj.abs(0xAD, lol_digdogger.DGK).br(0xD0, "sj_n")                           # (the blue one shoots on)
    sj.label("sj_x").b(0x68, 0xA8, 0x38, 0x60)
    return sj


def late(rom: bytearray) -> None:
    """lol_build, after lol_genload (the data banks made): noshoot and its vector (every build); the Upgrade mix's
    code and vectors, at the last data bank's top."""
    from lol_af import place
    ns = noshoot(NOSHOOT_AT).bytes()
    assert NOSHOOT_AT + len(ns) <= VEC
    place(rom, 14, NOSHOOT_AT, ns)
    place(rom, 14, V_NOSHOOT, Asm(V_NOSHOOT).abs(0x4C, NOSHOOT_AT).bytes())
    if _PENDING is None:
        return
    bk, at, code, vec = _PENDING
    place(rom, bk, at, code)
    place(rom, bk, VEC, vec)
