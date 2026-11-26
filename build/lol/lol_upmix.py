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
State (each shrine record's fifth byte, which a shrine never uses: cleared for a new file, kept by the records' copy):
  UPDECK  the upgrade card's upgrade + 1 ($FF none, 0 not drawn yet)
  UPL9    level 9's (stage 4)
  UFLAGS  low nibble: the moves; bit 7: an upgrade taken from a shrine (stage 3)
"""
from lol_af import Asm, BANK

REC = 0x7FAD
UPDECK = REC + 9 * 5 + 4
UPL9 = REC + 10 * 5 + 4
UFLAGS = REC + 11 * 5 + 4
DECK_PTR = 0x7FFF
CONTAINER = 0x1A
RANK, P0, P1, TMP = 0x0195, 0x0199, 0x019A, 0x019C   # (lol_upgrades' engine scratch)
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
        a.label("uitem").abs(0xAD, UPDECK).br(0xD0, "u_h")
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
        a.b(0x38, 0xE9, 0x2E, 0xAA).b(*f0(E["t_af"])).b(0x60)
        a.label("h_x").b(*f0(hi0)).b(0x60)
        # upick: A = a tier (0-2; 3: any): X = the first upgrade of its line not taken, that Link doesn't own and
        # may have now (no cave's rank: those that need one never), marked taken (the gone cave's code, lol_upgrades'
        # LINES); C set: none (or Link owns three)
        a.label("upick").abs(0x8D, P0).abs(0xAD, UT.OWN_N).b(0xC9, 0x03).br(0xB0, "pk_no")
        a.b(0xA9, 0xFF).abs(0x8D, RANK)
        a.abs(0xAE, P0).b(0xE0, 0x03).br(0x90, "pk_t")
        a.b(0xA2, 0x00, 0xA9, sum(len(x) for x in UT.TIERS)).abs(0x8D, P1).abs(0x4C, "pk_lp")   # any: every line
        a.label("pk_t").abs(0xBD, "tend").abs(0x8D, P1).abs(0xBD, "tstart").b(0xAA)
        a.label("pk_lp").b(0x8A).abs(0xCD, P1).br(0xB0, "pk_no")
        a.b(*f0(E["getc"])).br(0xD0, "pk_nx")                               # (taken)
        a.abs(0xBC, "tier_items").b(*f0(E["elig"])).br(0xB0, "pk_nx")    # (not now)
        a.b(0x8A, 0x48).abs(0xBD, "tier_items").b(0xAA).b(*f0(E["uget"])).abs(0x8D, TMP).b(0x68, 0xAA)
        a.abs(0xAD, TMP).br(0xD0, "pk_nx")                                      # (owned)
        a.b(0xA9, lol_fixed.gone_cave() + 1).b(*f0(E["setc"]))
        a.abs(0xBD, "tier_items").b(0xAA, 0x18, 0x60)
        a.label("pk_nx").b(0xE8).abs(0x4C, "pk_lp")
        a.label("pk_no").b(0x38, 0x60)
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
    at = (0xBB60 - n) & ~0x0F
    global UAT
    UAT = at
    a = build(at, bk)
    global _PENDING
    _PENDING = (bk, at, a.bytes())            # (placed by late(): the data banks exist once lol_genload is in)
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


def late(rom: bytearray) -> None:
    """lol_build, after lol_genload (the data banks made): the code, at the last data bank's top."""
    if _PENDING is None:
        return
    from lol_af import place
    bk, at, code = _PENDING
    place(rom, bk, at, code)
