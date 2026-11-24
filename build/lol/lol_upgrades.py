"""Legend of Link: H1's paid hint cave (hint shop 2, cave 12, person $76; only at H1) sells three upgrades, one per
visit (the shopkeeper's 'YOU CAN ONLY BUY ONE!!'); a bought one shows as an empty place. Bits of UPGRADES (saved):
  1  sword beams at any health (50 rupees; the wood sword's picture)
  2  boomstick: the wand's shot ends in a bomb blast, at a wall or a monster (100; the wand)
  4  regeneration: a quarter heart back every 600 frames Link takes no damage (200; a heart container)
The book no longer makes the wand's fire (its damage bonus stays).

Hooks (bank 7, into code here in the common area, the same in banks 0-6):
  MakeSwordShot's LDA ForceSwordShot ($0529) -> beams: [$0529] | bit 1
  HandleShotBlocked's LDA InvBook / BEQ Deactivate -> boom: with bit 2 a bomb (slot $10/$11, if free) in state $12
    at the shot, which blows next frame; then the shot goes
  BeginUpdateWorld's LDA InvClock -> regen (each frame of play), then LDA InvClock
Bank 1: InitCave's shop fill (JSR at $85F9) first writes the cave's wares for person $76; the cave take's JSR $BD2F
(the item) for person $76 sets the bit instead."""
HVE = 0x016F                            # lol_build: the containers enemies level up by (HeartValues; hard mode + 3)
from lol_af import Asm, place, patch, BANK

UPGRADES = 0x066B                       # saved inventory byte the game never uses
UGET, USET = None, None                 # (bank 1 helpers, set in apply)
COMMON = 0xBE00                         # free in banks 0-6
BANK1 = 0xBA03                          # bank 1 free
WS_CODE, WS_TABLE = 0xBF08, 0x8CB0         # bank 1 free: the white sword cave's code (after TABLES1) / list ($8CAE-$8CFF)
TABLES1 = 0xBE20                        # bank 1 free ($BE1E-$BF4F): the upgrade caves' tables, quote and take
UP2 = 0x0673                            # the badges' byte: its bits 6-7 are two more upgrades
LIKELIKE_BOMBS, RUPEE_SPEED, GANON_BOOMERANG = (UPGRADES, 0x80), (UP2, 0x40), (UP2, 0x80)
# (person, cave, [(item, price, (byte, bit))]): H1's hint shop 2, the waterfall's (B11) hint shop 1 and B2's
# (the letter cave's, moved there; its letter is gone)
SHOPS = [(0x76, 12, [(0x2B, 50, (UPGRADES, 0x01)), (0x2C, 100, (UPGRADES, 0x02)), (0x2D, 200, (UPGRADES, 0x04))]),
         (0x75, 11, [(0x2E, 50, (UPGRADES, 0x10)), (0x2F, 100, (UPGRADES, 0x08)), (0x30, 150, (UPGRADES, 0x20))]),
         (0x72, 8, [(0x31, 50, LIKELIKE_BOMBS), (0x32, 100, RUPEE_SPEED), (0x33, 150, GANON_BOOMERANG)])]
# three more (test 7), their bits in the file's odds byte 19 (SRAM, cleared for a new file; the shops save at once)
UP3 = 0x606A + 19
CRUSHER, JAMMER, BOMBSMITH = (UP3, 0x01), (UP3, 0x02), (UP3, 0x04)
POUCH, BAT_POTION, PIERCING = (UP3, 0x08), (UP3, 0x10), (UP3, 0x20)   # (PIERCING: bow mastery)
import lol_uptable as T
ROLL1 = None                                # bank 1 free: the roll (set in apply)
SWORD_UP, BUBBLE_RING, FAIRY = 0x08, 0x10, 0x20
N_UP = T.N_UP                               # (the upgrades: lol_uptable's rows)
assert all((T.ROWS[k][T.SAVE][0] >> 8) == (0x06 if k < 9 else 0x60) for k in range(N_UP))   # (uget's CPX #9 rule)
# the white sword cave's list, in priority: (item, inventory byte, offered while that byte is below this)
WS_LIST = [(0x02, 0x0657, 2),   # white sword (Link has no better sword)
           (0x0A, 0x065A, 1),   # bow
           (0x08, 0x0659, 1),   # wood arrows (no arrows)
           (0x10, 0x065F, 1),   # wand
           (0x0D, 0x0663, 1),   # ladder
           (0x05, 0x065C, 1),   # recorder
           (0x14, 0x0665, 1),   # power bracelet
           (0x0C, 0x0660, 1),   # raft
           (0x11, 0x0661, 1),   # red book
           (0x1D, 0x0674, 1),   # boomerang (and no magical one)
           (0x24, 0x067C, 20),  # bomb upgrade (capacity under 20)
           (0x20, 0x065E, 2),   # red potion (no red potion)
           (0x1C, 0x0676, 1),   # magical shield
           (0x04, 0x065D, 1)]   # bait
FAIRY_OWNED = 0x40                      # set with the first bottle: a fairy fountain then fills it again
POND = 0x8DA7                           # bank 4 UpdatePondFairy: INC ObjState+1 / LDA #$40 / STA ObjState / STA $63
POND_CODE = 0x9B04                      # bank 4 free (vanilla padding $9B01-$9B1F, before InitDarknut)
FAIRY_TILE = None                       # the status bar's fairy: a background tile the item pictures left blank
                                        # (not $60: the scroll split's sprite 0 needs it blank)
FAIRY_PPU = 0x20D5                      # left of the hearts' bottom row
FAIRY_ICON = ("...33...",              # (that status bar column's colors: 1 white, 2 gray, 3 blue)
              "11.33.11",
              "11133111",
              ".111111.",
              "..1331..",
              "...33...",
              "..3..3..",
              "........")
DIED = 0x7BA9                           # bank 1 $B419, run from WRAM: Link died (LDA HeartValues / AND #$F0)
BUBBLE_HIT = 0x845F                     # bank 4 UpdateBubble: LDA $06 / BEQ exit / LDA ObjType,X
LEVEL_CHAR_PPU = 0x2048                 # "LEVEL-X" (bank 6's LevelNumberTransferBuf at PPU $2042): X
HAS_MAP = 0xB5EF                        # bank 5: Z set without the current level's map
QUESTION = 0x2E                         # the '?' tile
LABEL5 = 0xADB0                         # bank 5 free: the status bar level label
FLAGS = (0x00, 0x00, 0xC0)              # as shop A's (pay; show the items and prices)
QUOTE = 12                              # hint shop 2's second hint (unused now)
QUOTE_TEXT = ["BUY A NEW UPGRADE!"]
SHOP_QUOTE_SELECTOR = 0xC0 | 2 * QUOTE   # shop flags + the quote
CAVE_WARES, CAVE_PRICES = 0x6A7E, 0x6ABA
TL, TH, PH, PP = 0x0175, 0x0176, 0x0177, 0x0178   # regen timer, the hearts last frame (stack page, unused)
REGEN_FRAMES = 600
QUARTER = 0x40
WRAM = 0x3870                           # bank 1 $A500-$B76F runs from WRAM (cpu - $3870)
DEACT_LINK_SHOT = 0xF411                # LDX #$0E / JMP ResetObjState


def apply(rom: bytearray, notes: list) -> None:
    global FAIRY_TILE
    import lol_bombup
    FAIRY_TILE = lol_bombup.FREE_PAIRS[0]
    assert FAIRY_TILE != 0x60
    import lol_v3core as V, lol_books
    # --- bodies in bank 0, far-called ---
    def b_regen(org):                                  # (the stub has checked the upgrade)
        a = Asm(org)
        a.label("regen").abs(0xAD, 0x066F).b(0x29, 0x0F).abs(0xCD, PH).br(0x90, "rg_hurt").br(0xD0, "rg_tick")
        a.abs(0xAD, 0x0670).abs(0xCD, PP).br(0x90, "rg_hurt")
        a.label("rg_tick").abs(0xEE, TL).br(0xD0, "rg_cmp").abs(0xEE, TH)
        a.label("rg_cmp").abs(0xAD, TH).b(0xC9, REGEN_FRAMES >> 8).br(0x90, "rg_keep")
        a.abs(0xAD, TL).b(0xC9, REGEN_FRAMES & 0xFF).br(0x90, "rg_keep")
        a.b(0xA9, 0x00).abs(0x8D, TL).abs(0x8D, TH)
        a.abs(0xAD, 0x0670).b(0x18, 0x69, QUARTER).br(0x90, "rg_set")              # partial + a quarter
        a.b(0x48).abs(0xAD, 0x066F).b(0x29, 0x0F, 0x85, 0x00)                     # (the next heart:)
        a.abs(0xAD, 0x066F).b(0x4A, 0x4A, 0x4A, 0x4A, 0xC5, 0x00).br(0xF0, "rg_full")
        a.abs(0xEE, 0x066F).b(0x68).abs(0x4C, "rg_set")                           # one more full heart
        a.label("rg_full").b(0x68, 0xA9, 0xFF)                                     # (the last heart: full)
        a.label("rg_set").abs(0x8D, 0x0670).abs(0x4C, "rg_keep")
        a.label("rg_hurt").b(0xA9, 0x00).abs(0x8D, TL).abs(0x8D, TH)
        a.label("rg_keep").abs(0xAD, 0x066F).b(0x29, 0x0F).abs(0x8D, PH).abs(0xAD, 0x0670).abs(0x8D, PP)
        return a.b(0x60)
    def b_boom(org):                                   # X = $0E, the magic shot; the stub has checked the upgrade
        a = Asm(org)
        a.label("boom").b(0xA0, 0x10).abs(0xB9, 0x00AC).br(0xF0, "bm_put")
        a.b(0xC8).abs(0xB9, 0x00AC).br(0xD0, "bm_out")
        a.label("bm_put").b(0xA9, 0x12).abs(0x99, 0x00AC).b(0xA9, 0x00).abs(0x99, 0x0028)
        a.b(0xB5, 0x70).abs(0x99, 0x0070).b(0xB5, 0x84).abs(0x99, 0x0084)
        # every monster's invincibility timer cleared, so the blast (4) lands right after the shot's hit (2)
        a.label("bm_out").b(0xA9, 0x00, 0xA0, 0x0B).label("bv").abs(0x99, 0x04F0).b(0x88).br(0xD0, "bv")
        return a.b(0x60)
    def b_sword(org):                                  # sword +1, then the books' bonus
        a = Asm(org)
        a.label("sword").b(0xA5, 0x09, 0xC9, 0x01).br(0xD0, "sw_go").abs(0xAD, UPGRADES).b(0x29, SWORD_UP).br(0xF0, "sw_go")
        a.b(0xA5, 0xAC + 0x0D, 0xC9, 0x30).br(0xB0, "sw_go")
        a.b(0xA5, 0x07, 0x18, 0x69, 0x10).br(0x90, "sw_st").b(0xA9, 0xFF)
        a.label("sw_st").b(0x85, 0x07)
        return a.label("sw_go").abs(0x4C, lol_books.BONUS0)
    def b_died(org):                                   # the fairy's used up; back with up to 8 hearts
        a = Asm(org)
        a.label("died").abs(0xAD, UPGRADES).b(0x29, 0xFF ^ FAIRY).abs(0x8D, UPGRADES)
        a.abs(0xAD, 0x066F).b(0x29, 0xF0, 0x85, 0x0F, 0x4A, 0x4A, 0x4A, 0x4A, 0xC9, 0x07).br(0x90, "fa_n").b(0xA9, 0x07)
        a.label("fa_n").b(0x05, 0x0F).abs(0x8D, 0x066F).b(0xA9, 0xFF).abs(0x8D, 0x0670)
        return a.b(0xA9, 0x08).abs(0x8D, 0x0602).b(0x60)                            # a tune
    RF = T.bit("refilling bag")
    from lol_newups import RT_LO, RT_HI, RLAST, REFILL_FRAMES
    def b_refill(org):                                 # a bomb every 90 s while the bag isn't full; a bomb used
        a = Asm(org)                                   # (fewer than last frame) restarts the count
        a.label("refill").abs(0xAD, 0x0658).abs(0xCD, RLAST).abs(0x8D, RLAST).br(0x90, "rs")
        a.abs(0xAD, 0x0658).abs(0xCD, 0x067C).br(0xB0, "rs")
        a.abs(0xEE, RT_LO).br(0xD0, "c").abs(0xEE, RT_HI)
        a.label("c").abs(0xAD, RT_HI).b(0xC9, REFILL_FRAMES >> 8).br(0x90, "r").br(0xD0, "add")
        a.abs(0xAD, RT_LO).b(0xC9, REFILL_FRAMES & 0xFF).br(0x90, "r")
        a.label("add").abs(0xEE, 0x0658).abs(0xAD, 0x0658).abs(0x8D, RLAST)
        a.label("rs").b(0xA9, 0x00).abs(0x8D, RT_LO).abs(0x8D, RT_HI)
        return a.label("r").b(0x60)
    B0 = {n: V.put0(rom, f).labels[n] for n, f in (("regen", b_regen), ("boom", b_boom), ("sword", b_sword),
                                                    ("died", b_died), ("refill", b_refill))}
    def b_frame(org):                                  # every frame of play: regen, the refilling bag
        a = Asm(org)
        a.label("frame").abs(0xAD, UPGRADES).b(0x29, 0x04).br(0xF0, "f1").abs(0x20, B0["regen"])
        a.label("f1").abs(0xAD, RF[0]).b(0x29, RF[1]).br(0xF0, "f2").abs(0x20, B0["refill"])
        return a.label("f2").b(0x60)
    B0["frame"] = V.put0(rom, b_frame).labels["frame"]
    # --- bank 7 stubs ---
    s_regen = V.put7(rom, lambda o: Asm(o).abs(0xAD, UPGRADES).b(0x29, 0x04).br(0xD0, "go").abs(0xAD, RF[0])
                     .b(0x29, RF[1]).br(0xF0, "o").label("go").b(*V.far(0, B0["frame"]))
                     .label("o").abs(0xAD, 0x066C).b(0x60)).cpu                     # (then the replaced LDA InvClock)
    s_boom = V.put7(rom, lambda o: Asm(o).abs(0xAD, UPGRADES).b(0x29, 0x02).br(0xF0, "d").b(*V.far(0, B0["boom"]))
                    .label("d").abs(0x4C, DEACT_LINK_SHOT)).cpu                      # (the shot ends)
    # --- the common area (banks 0-6): what WRAM code calls, and the beams' check ---
    a = Asm(COMMON)
    a.label("beam").abs(0xAD, UPGRADES).b(0x29, 0x01).abs(0x0D, 0x0529).b(0x60)
    # Link died: with the fairy, the body above, and out past the damage routine
    a.label("died").abs(0xAD, UPGRADES).b(0x29, FAIRY).br(0xD0, "fa_use").abs(0xAD, 0x066F).b(0x60)
    a.label("fa_use").b(*V.far(0, B0["died"])).b(0x68, 0x68, 0x60)
    code = a.bytes()
    for bank in range(7):
        place(rom, bank, COMMON, code)
    # the books' bonus stub far-calls the sword +1 first
    for bank in range(7):
        at = BANK(bank) + lol_books.BSTUB + 5 - 0x8000
        assert rom[at:at + 2] == bytes([lol_books.BONUS0 & 0xFF, lol_books.BONUS0 >> 8])
        rom[at:at + 2] = bytes([B0["sword"] & 0xFF, B0["sword"] >> 8])
    # bubbles (bank 4 only, after the common code): with the ring, no touch (Z set); else LDA $06 / BEQ and the type
    b4 = Asm(COMMON + len(code))
    b4.label("bubble").abs(0xAD, UPGRADES).b(0x29, BUBBLE_RING).br(0xD0, "bu_no")
    b4.b(0xA5, 0x06).br(0xF0, "bu_r").abs(0xBD, 0x034F).b(0x60)
    b4.label("bu_no").b(0xA9, 0x00)
    b4.label("bu_r").b(0x60)
    place(rom, 4, b4.cpu, b4.bytes())
    # the status bar (bank 5 only): the fairy left of the hearts while Link has it (after the XP record, every
    # other frame), then the level's label
    h5 = Asm(COMMON + len(code))
    h5.label("hud").b(0xA9, FAIRY_PPU >> 8).abs(0x8D, 0x0309).b(0xA9, FAIRY_PPU & 0xFF).abs(0x8D, 0x030A)
    h5.b(0xA9, 0x01).abs(0x8D, 0x030B).abs(0xAD, UPGRADES).b(0x29, FAIRY).br(0xF0, "hu_no")
    h5.b(0xA9, FAIRY_TILE).br(0xD0, "hu_st")
    h5.label("hu_no").b(0xA9, 0x24)
    h5.label("hu_st").abs(0x8D, 0x030C).b(0xA9, 0xFF).abs(0x8D, 0x030D)
    h5.abs(0x4C, LABEL5)                                                         # (c5's "hu", below)
    place(rom, 5, h5.cpu, h5.bytes())
    L = {**a.labels, **b4.labels, **h5.labels}
    patch(rom, 7, 0xF860, bytes([0xAD, 0x29, 0x05]), bytes([0x20, L["beam"] & 0xFF, L["beam"] >> 8]))
    patch(rom, 7, 0xF3D9, bytes.fromhex("ad6106f035"), bytes([0x4C, s_boom & 0xFF, s_boom >> 8]))
    patch(rom, 7, 0xEC7A, bytes([0xAD, 0x6C, 0x06]), bytes([0x20, s_regen & 0xFF, s_regen >> 8]))
    j = lambda n: bytes([0x20, L[n] & 0xFF, L[n] >> 8])
    patch(rom, 1, DIED + 0x3870, bytes([0xAD, 0x6F, 0x06]), j("died"))
    bb = BANK(4) + BUBBLE_HIT - 0x8000
    assert rom[bb:bb + 2] == bytes([0xA5, 0x06]) and rom[bb + 2] == 0xF0 and rom[bb + 4:bb + 7] == bytes([0xBD, 0x4F, 0x03])
    exit_ = BUBBLE_HIT + 4 + rom[bb + 3]                                         # BEQ's target
    new = j("bubble") + bytes([0xF0, (exit_ - (BUBBLE_HIT + 5)) & 0xFF, 0xEA, 0xEA])
    rom[bb:bb + 7] = new
    import os
    gen = bool(os.environ.get("LOL_GEN"))
    c5 = Asm(LABEL5)
    # in a level, the status bar's " LEVEL-X" (or "SHRINE-X" for the generated shrines A-D), every other frame
    c5.label("hu").b(0xA5, 0x10).br(0xF0, "hu_r").abs(0xAD, 0x6BB1).br(0xF0, "hu_r")
    c5.b(0xA0, 9)
    if gen:
        c5.b(0xC9, 0x0A).br(0x90, "hu_c").b(0xA0, 19)
    c5.label("hu_c").b(0xA2, 9)
    c5.label("hu_l").abs(0xB9, "hu_t").abs(0x9D, 0x030D).b(0x88, 0xCA).br(0x10, "hu_l")
    c5.abs(0xAD, 0x6BB1).abs(0x8D, 0x0317).b(0xA9, 0xFF).abs(0x8D, 0x0318)
    c5.label("hu_r").b(0x60)
    # the level's character (bank 5 $B02A, InitMode3_Sub7): its number or letter
    c5.label("lvq").abs(0xAD, 0x6BB1).b(0x60)
    c5.label("hu_t").b(0x20, 0x41, 0x08, 0x24, 0x15, 0x0E, 0x1F, 0x0E, 0x15, 0x62)       # " LEVEL-"
    c5.b(0x20, 0x41, 0x08, 0x1C, 0x11, 0x1B, 0x12, 0x17, 0x0E, 0x62)                    # "SHRINE-"
    code5 = c5.bytes()
    assert c5.labels["hu"] == LABEL5
    at = BANK(5) + LABEL5 - 0x8000
    assert all(x == 0xFF for x in rom[at:at + len(code5)])
    rom[at:at + len(code5)] = code5
    lv = c5.labels["lvq"]
    patch(rom, 5, 0xB02A, bytes([0xAD, 0xB1, 0x6B]), bytes([0x20, lv & 0xFF, lv >> 8]))
    # B2's upgrades
    def free_at(bank, lo, hi, size):
        base = BANK(bank) - 0x8000
        run = 0
        for cpu in range(lo, hi):
            run = run + 1 if rom[base + cpu] == 0xFF else 0
            if run == size + 4:
                return cpu - size - 1
        raise AssertionError(f"no {size} free bytes in bank {bank}")
    # like-like bombs (bank 4 SetUpDroppedItem's LDA Item_ObjMonsterType,X): with the upgrade a like-like ($17)
    # drops as a blue octorok ($09) does: the drop group with bombs
    def build4(cpu):
      g4 = Asm(cpu)
      g4.abs(0xBD, 0x0412).b(0xC9, 0x17).br(0xD0, "oc_c").abs(0xAD, LIKELIKE_BOMBS[0]).b(0x29, LIKELIKE_BOMBS[1])
      g4.br(0xF0, "ll_n").b(0xA9, 0x09, 0x60)
      g4.label("ll_n").b(0xA9, 0x17)
      g4.label("ll_r").b(0x60)
      # red octoroks at 10+ containers (HVE, lol_enemies2's bomb octoroks): the bomb-dropping class (the third
      # list, whose table holds the bombs; looked up as a blue octorok, $09, as the like-like's upgrade does)
      g4.label("oc_c").b(0xC9, 0x07).br(0xF0, "oc_x").b(0xC9, 0x08).br(0xD0, "ll_r")
      g4.label("oc_x").abs(0xAD, HVE).b(0xC9, 0x90).br(0x90, "oc_n").b(0xA9, 0x09, 0x60)
      g4.label("oc_n").abs(0xBD, 0x0412).b(0x60)
      # Ganon (bank 4 Ganon_CheckCollisions' JSR CheckMonsterSwordCollision): with the upgrade the boomerang (slot
      # $0F) near his middle ([02] / [03]) hits him for the sword's damage: it turns back, and the hit goes to
      # HandleMonsterWeaponCollision (WRAM $7C16) as the sword's would (CheckMonsterWeaponCollision's own boomerang
      # case would only stun, for no damage)
      g4.label("ganon").abs(0x20, 0x7D29)
      # lol_modes' swordless: the wand's stab (slot $12, states $3x; not an arrow) near his middle hits him as the
      # sword would
      g4.abs(0xAD, 0x7FF7).br(0xF0, "gn_b").b(0xA5, 0xAC + 0x12, 0x29, 0xF0, 0xC9, 0x30).br(0xD0, "gn_b")
      g4.b(0xA5, 0x70 + 0x12, 0x18, 0x69, 0x04, 0x38, 0xE5, 0x02).br(0xB0, "gw_x").b(0x49, 0xFF, 0x69, 0x01)
      g4.label("gw_x").b(0xC9, 0x10).br(0xB0, "gn_b")
      g4.b(0xA5, 0x84 + 0x12, 0x18, 0x69, 0x08, 0x38, 0xE5, 0x03).br(0xB0, "gw_y").b(0x49, 0xFF, 0x69, 0x01)
      g4.label("gw_y").b(0xC9, 0x10).br(0xB0, "gn_b")
      g4.b(0xA9, 0x0D, 0x85, 0x00, 0xA8, 0xA9, 0x01, 0x85, 0x09, 0xA9, 0x20, 0x85, 0x07)
      g4.abs(0x20, 0x7C16).abs(0x4C, 0x7DAA)
      g4.label("gn_b")
      g4.abs(0xAD, GANON_BOOMERANG[0]).b(0x29, GANON_BOOMERANG[1]).br(0xF0, "gn_r")
      g4.b(0xA5, 0xAC + 0x0F).br(0xF0, "gn_r")
      g4.b(0xA5, 0x70 + 0x0F, 0x18, 0x69, 0x04, 0x38, 0xE5, 0x02).br(0xB0, "gn_x").b(0x49, 0xFF, 0x69, 0x01)
      g4.label("gn_x").b(0xC9, 0x10).br(0xB0, "gn_r")
      g4.b(0xA5, 0x84 + 0x0F, 0x18, 0x69, 0x08, 0x38, 0xE5, 0x03).br(0xB0, "gn_y").b(0x49, 0xFF, 0x69, 0x01)
      g4.label("gn_y").b(0xC9, 0x10).br(0xB0, "gn_r")
      g4.b(0xA9, 0x50, 0x85, 0xAC + 0x0F)                                       # the boomerang comes back
      g4.b(0xA9, 0x0D, 0x85, 0x00, 0xA8, 0xA9, 0x01, 0x85, 0x09)                 # as the sword (slot $0D, type 1)
      g4.b(0xA9, 0x10).abs(0xAC, 0x0657).b(0xC0, 0x02).br(0x90, "gn_hit").b(0xA9, 0x20, 0xC0, 0x03).br(0x90, "gn_hit")
      g4.b(0xA9, 0x40)
      g4.label("gn_hit").b(0x85, 0x07).abs(0x20, 0x7C16).abs(0x4C, 0x7DAA)        # then ParryOrShove (his hit timer)
      g4.label("gn_r").b(0x60)
      return g4
    at4 = free_at(4, 0xB560, 0xBBA0, len(build4(0).bytes()))
    g4 = build4(at4)
    code4 = g4.bytes()
    place(rom, 4, at4, code4)
    patch(rom, 4, 0xB06E, bytes([0xBD, 0x12, 0x04]), bytes([0x20, at4 & 0xFF, at4 >> 8]))
    gn = g4.labels["ganon"]
    patch(rom, 4, 0xAF0E, bytes([0x20, 0x29, 0x7D]), bytes([0x20, gn & 0xFF, gn >> 8]))
    # like-likes with the upgrade: 7 hit points (vanilla 9) and blue. Bank 7 InitObject's STA ObjHP,X ($FD67)
    # calls a helper that, for a like-like ([00] = $17), stores $70 and sets the object's "ignore the sprite
    # attribute table" bit; UpdateLikeLike's two draws ($9CED / $9D44) then draw with palette 1 ($04 / $05)
    # Bank 7 InitObject's STA ObjHP,X ($FD67, bank 4 in) becomes JSR to STA / JMP init4 (bank 4): a like-like
    # ([00] = $17) with its upgrade gets $70 HP; a gibdo ($30) once Link has 8 containers gets $90 HP and the blue
    # darknut's q-speed $28. Both get the object's "ignore the sprite attribute table" bit, and their draws then
    # set the palette ($04 / $05): like-like 1 (blue), gibdo 2 (red)
    AT7, INIT4, INIT4B, PAL4, WM4 = 0xFFCD, 0xBB7C, 0xBCA4, 0xA896, 0xBD90          # (free: $FFCC-$FFEA, $BB7A-$BB9F,
    g7 = Asm(AT7)                                                         #  $9B01-$9B1F, $A895-$A8BF)
    g7.abs(0x9D, 0x0485).abs(0x4C, INIT4)
    c7 = g7.bytes()
    place(rom, 7, AT7 - 0x4000, c7)                    # (place maps bank 7 from $8000)
    patch(rom, 7, 0xFD67, bytes([0x9D, 0x85, 0x04]), bytes([0x20, AT7 & 0xFF, AT7 >> 8]))
    assert LIKELIKE_BOMBS[1] == 0x80
    ga = Asm(INIT4)
    ga.b(0xA5, 0x00, 0xC9, 0x17).br(0xD0, "i_g")
    ga.abs(0xAD, LIKELIKE_BOMBS[0]).br(0x10, "i_r")                          # (bit 7: BPL)
    ga.b(0xA9, 0x70)
    ga.label("i_set").abs(0x9D, 0x0485).abs(0xBD, 0x04BF).b(0x09, 0x08).abs(0x9D, 0x04BF)
    ga.label("i_r").b(0x60)
    ga.label("i_g").abs(0x4C, INIT4B)
    ca = ga.bytes(); assert INIT4 + len(ca) <= 0xBB9F
    place(rom, 4, INIT4, ca)
    # (bank 4's $BCA4-$BCFF: free in every bank, past the common item code; used here by bank 4 alone)
    gb = Asm(INIT4B)
    gb.b(0xC9, 0x30).br(0xD0, "j_v").abs(0xAD, HVE).b(0xC9, 0x70).br(0x90, "j_r")
    gb.b(0xA9, 0x28).abs(0x9D, 0x03BC).b(0xA9, 0x90).abs(0x4C, ga.labels["i_set"])
    # a vire ($12) once Link has 12 containers: 6 HP, red
    gb.label("j_v").b(0xC9, 0x12).br(0xD0, "j_w").abs(0xAD, HVE).b(0xC9, 0xB0).br(0x90, "j_r")
    gb.b(0xA9, 0x60).abs(0x4C, ga.labels["i_set"])
    gb.label("j_r").b(0x60)
    gb.label("j_w").abs(0x4C, WM4)
    # ... and splits (UpdateVire's LDA #$1C / STA $00 at $9D75, JSR Shoot at $9D79) into two blue wizzrobes ($23,
    # state 0) instead of red keese
    gb.label("v_type").b(0xA9, 0x1C).abs(0xAC, HVE).b(0xC0, 0xB0).br(0x90, "v_st").b(0xA9, 0x23)
    gb.label("v_st").b(0x85, 0x00, 0x60)
    gb.label("v_shoot").abs(0x20, 0xB195).b(0xA5, 0x00, 0xC9, 0x23).br(0xD0, "v_r")
    gb.b(0xA9, 0x00).abs(0x99, 0x00AC)
    gb.label("v_r").b(0x60)
    for k in (3, 4):
        gb.label(f"e{k}").abs(0x20, PAL4).abs(0x4C, (0x77DF, 0x77DB)[k - 3])   # gibdo, vire draws
    cb = gb.bytes(); assert INIT4B + len(cb) <= 0xBCFF, hex(INIT4B + len(cb))
    global GB_LABELS
    GB_LABELS = gb.labels
    place(rom, 4, INIT4B, cb)
    # Red wallmasters ($27) once Link has 12 containers: 5 HP, red, q-speed $28 (vanilla $18), a heart of damage
    # (vanilla half), and the trip back to the entrance also takes a heart container. (bank 4 $BD90-$BDFF: free
    # in every bank, past the common pre-load code; used here by bank 4 alone)
    gw = Asm(WM4)
    gw.b(0xC9, 0x27).br(0xD0, "w_r").abs(0xAD, HVE).b(0xC9, 0xB0).br(0x90, "w_r")
    gw.b(0xA9, 0x50).abs(0x9D, 0x0485)
    gw.label("w_r").b(0x60)
    gw.label("w_spd").abs(0xAD, HVE).b(0xC9, 0xB0, 0xA9, 0x18).br(0x90, "w_s").b(0xA9, 0x28)
    gw.label("w_s").abs(0x9D, 0x03BC).b(0x60)
    gw.label("w_pal").b(0x29, 0xF0, 0x48).abs(0xAD, HVE).b(0xC9, 0xB0, 0x68, 0x09, 0x01).br(0x90, "w_p").b(0x49, 0x03)
    gw.label("w_p").b(0x60)
    gw.label("w_steal").abs(0x20, 0x828A).abs(0xAD, HVE).b(0xC9, 0xB0).br(0x90, "w_x")
    gw.b(0x38, 0xE9, 0x10).abs(0x8D, 0x066F)                                  # containers - 1
    gw.b(0x4A, 0x4A, 0x4A, 0x4A, 0x85, 0x00).abs(0xAD, 0x066F).b(0x29, 0x0F, 0xC5, 0x00).br(0x90, "w_x")
    gw.abs(0xAD, 0x066F).b(0x29, 0xF0, 0x05, 0x00).abs(0x8D, 0x066F)          # full hearts no more than that
    gw.label("w_x").b(0x60)
    cw = gw.bytes(); assert WM4 + len(cw) <= 0xBE00, hex(WM4 + len(cw))
    place(rom, 4, WM4, cw)
    patch(rom, 4, 0x9161 + 4, bytes.fromhex("a9189dbc03"), bytes([0x20, gw.labels["w_spd"] & 0xFF, gw.labels["w_spd"] >> 8]))
    patch(rom, 4, 0x924D, bytes.fromhex("29f00901"), bytes([0x20, gw.labels["w_pal"] & 0xFF, gw.labels["w_pal"] >> 8]))
    patch(rom, 4, 0x91C1, bytes.fromhex("208a82"), bytes([0x20, gw.labels["w_steal"] & 0xFF, gw.labels["w_steal"] >> 8]))
    # the damage (bank 1 HarmLink's LDA ObjTypeToDamagePoints,Y, run from WRAM $7B42): bank 7 $FFD4
    DMG7 = 0xFFD4
    gd = Asm(DMG7)
    gd.abs(0xB9, 0x7A4A).b(0xC0, 0x27).br(0xD0, "d_r").b(0x48).abs(0xAD, HVE).b(0xC9, 0xB0, 0x68).br(0x90, "d_r")
    gd.b(0xA9, 0x01)
    gd.label("d_r").b(0x60)
    cd = gd.bytes(); assert DMG7 + len(cd) <= 0xFFEA, hex(DMG7 + len(cd))
    place(rom, 7, DMG7 - 0x4000, cd)
    patch(rom, 1, 0xB3B2, bytes.fromhex("b94a7a"), bytes([0x20, DMG7 & 0xFF, DMG7 >> 8]))
    patch(rom, 4, 0x9D75, bytes.fromhex("a91c8500"), bytes([0x20, gb.labels["v_type"] & 0xFF, gb.labels["v_type"] >> 8, 0xEA]))
    patch(rom, 4, 0x9D79, bytes.fromhex("2095b1"), bytes([0x20, gb.labels["v_shoot"] & 0xFF, gb.labels["v_shoot"] >> 8]))
    # ... and a like-like holding Link eats a bomb (bank 4 UpdateLikeLike's LDA #0 / STA InvMagicShield / LDA #$C0 /
    # STA ObjCaptureTimer,X at $9D34, which runs each frame from capture time $60): the first at $60, then one each
    # 300 frames (the timer runs $61-$F6 twice, [0193] the half), and the magic shield stays
    def buildcap(cpu):
        gc = Asm(cpu)
        gc.abs(0xAD, LIKELIKE_BOMBS[0]).br(0x30, "c_up")
        gc.b(0xA9, 0x00).abs(0x8D, 0x0676).b(0xA9, 0xC0).abs(0x9D, 0x042C).b(0x60)
        gc.label("c_up").abs(0xBD, 0x042C).b(0xC9, 0x60).br(0xD0, "c_2")
        gc.b(0xA9, 0x00).abs(0x8D, 0x0193).br(0xF0, "c_eat")
        gc.label("c_2").b(0xC9, 0xF7).br(0x90, "c_r")
        gc.b(0xA9, 0x61).abs(0x9D, 0x042C)
        gc.abs(0xAD, 0x0193).b(0x49, 0x01).abs(0x8D, 0x0193).br(0xD0, "c_r")
        gc.label("c_eat").abs(0xAD, 0x0658).br(0xF0, "c_r").abs(0xCE, 0x0658)
        gc.label("c_r").b(0x60)
        return gc
    atc = free_at(4, 0xAFB0, 0xB000, len(buildcap(0).bytes()))          # (vanilla free space)
    place(rom, 4, atc, buildcap(atc).bytes())
    patch(rom, 4, 0x9D34, bytes.fromhex("a9008d7606a9c09d2c04"), bytes([0x20, atc & 0xFF, atc >> 8]) + b"\xea" * 7)
    gp = Asm(PAL4)                                     # like-like ($17) palette 1, the others 2
    gp.label("pal").b(0x48).abs(0xBD, 0x04BF).b(0x29, 0x08).br(0xF0, "pal_n")
    gp.abs(0xBD, 0x034F).b(0xC9, 0x17).br(0xF0, "pal_1").b(0xA9, 0x02).br(0xD0, "pal_s")   # (the CMP's flags,
    gp.label("pal_1").b(0xA9, 0x01)                                                          #  not the LDA's)
    gp.label("pal_s").b(0x85, 0x04, 0x85, 0x05)
    gp.label("pal_n").b(0x68, 0x60)
    for k in (0, 1):
        gp.label(f"e{k}").abs(0x20, "pal").abs(0x4C, (0x77DB, 0x8297)[k])
    cp = gp.bytes(); assert PAL4 + len(cp) <= 0xA8BF, hex(PAL4 + len(cp))
    place(rom, 4, PAL4, cp)
    DRAWS = ((0x9CED, 0x20, 0x77DB, gp.labels["e0"]), (0x9D44, 0x20, 0x8297, gp.labels["e1"]),   # like-like x2
             (0x9B48, 0x4C, 0x77DF, gb.labels["e3"]), (0x9DE0, 0x4C, 0x77DB, gb.labels["e4"]))   # gibdo, vire
    for site, op, target, e in DRAWS:
        patch(rom, 4, site, bytes([op, target & 0xFF, target >> 8]), bytes([op, e & 0xFF, e >> 8]))
    # rupee speed (bank 5 InitLinkSpeed's LDA #$60 / STA $00): with the upgrade $60 + rupees / 2, as ZORA's
    # "rupees affect speed"
    def build5(cpu):
        g5 = Asm(cpu)
        g5.abs(0xAD, RUPEE_SPEED[0]).b(0x29, RUPEE_SPEED[1]).br(0xF0, "rs_n")      # (X and Y kept)
        g5.abs(0xAD, 0x066D).b(0x4A, 0x18, 0x69, 0x60, 0x85, 0x00, 0x60)
        g5.label("rs_n").b(0xA9, 0x60, 0x85, 0x00, 0x60)
        return g5
    at5 = free_at(5, 0xAF00, 0xB000, len(build5(0).bytes()))
    place(rom, 5, at5, build5(at5).bytes())
    patch(rom, 5, 0xB366, bytes([0xA9, 0x60, 0x85, 0x00]), bytes([0x20, at5 & 0xFF, at5 >> 8, 0xEA]))

    # a fairy fountain fills the bottle again (once Link has had one)
    f4 = Asm(POND_CODE)
    f4.abs(0xAD, UPGRADES).b(0x29, FAIRY_OWNED).br(0xF0, "pn").abs(0xAD, UPGRADES).b(0x09, FAIRY).abs(0x8D, UPGRADES)
    f4.label("pn").b(0xA9, 0x40, 0x85, 0xAC, 0x60)
    place(rom, 4, POND_CODE, f4.bytes())
    patch(rom, 4, POND, bytes.fromhex("e6ada94085ac"), bytes([0xE6, 0xAD, 0x20, POND_CODE & 0xFF, POND_CODE >> 8, 0xEA]))
    import lol_build                      # bank 5: the XP status bar code's RTS
    HUD_END = lol_build.HUD_CPU + len(lol_build.build_hud(lol_build.HUD_CPU)) - 1
    hb = BANK(5) + HUD_END - 0x8000
    assert rom[hb:hb + 4] == bytes([0x60, 0xFF, 0xFF, 0xFF]), rom[hb:hb + 4].hex()
    rom[hb:hb + 3] = bytes([0x4C, L["hud"] & 0xFF, L["hud"] >> 8])
    from lol_bombup import tile_bytes, BG_CHR
    ft = BG_CHR + FAIRY_TILE * 16
    assert FAIRY_TILE < 0x60 and not any(rom[ft:ft + 16])   # (past $6F is CommonMiscPatterns: the HUD and cursor tiles)
    rom[ft:ft + 16] = tile_bytes(FAIRY_ICON)

    apply_caves_later.append(True)                                           # (lol_build: apply_caves, after lol_pictures)
    # Critter crusher: HarmLink's start (bank 1 $B3AA, run from WRAM: JSR $7E26, X the monster touching Link) for a
    # gel ($14 / $15) or a keese ($1B-$1D) with the upgrade: no harm, and the monster takes a sword hit of $FF damage
    # (HandleMonsterWeaponCollision, WRAM $7C16), then out of the collision check (its caller's return)
    CR_W, CR_C = 0xB751, 0xBFE4                 # bank 1's free bytes that run from WRAM ($7EE1); banks 0-6's free
    cw_ = Asm(CR_W - WRAM)
    cw_.abs(0xAD, CRUSHER[0]).b(0x4A).br(0x90, "cr_n")
    assert CRUSHER[1] == 0x01
    cw_.abs(0xBD, 0x034F).b(0xC9, 0x14).br(0xF0, "cr_k").b(0xC9, 0x15).br(0xF0, "cr_k")
    cw_.b(0xC9, 0x1B).br(0x90, "cr_n").b(0xC9, 0x1E).br(0x90, "cr_k")
    cw_.label("cr_n").abs(0x4C, 0x7E26)
    cw_.label("cr_k").abs(0x4C, CR_C)
    cwb = cw_.bytes(); assert len(cwb) <= 0xB770 - CR_W, len(cwb)
    place(rom, 1, CR_W, cwb)
    patch(rom, 1, 0xB3AA, bytes([0x20, 0x26, 0x7E]), bytes([0x20, (CR_W - WRAM) & 0xFF, (CR_W - WRAM) >> 8]))
    cc = Asm(CR_C)
    cc.b(0xA9, 0xFF, 0x85, 0x07, 0xA9, 0x01, 0x85, 0x09, 0xA0, 0x0D).abs(0x20, 0x7C16).b(0x68, 0x68, 0x60)
    for bank in range(7):
        place(rom, bank, CR_C, cc.bytes())
    # Statue jammer: bank 4's statue shot (UpdateStatues' LDA #$55 / JSR $82AF at $86D2) is skipped with the upgrade
    SJ = 0xBB4C                                 # bank 4 free ($BB4C-$BB79)
    sj = Asm(SJ)
    sj.abs(0xAD, JAMMER[0]).b(0x29, JAMMER[1]).br(0xD0, "sj_r").b(0xA9, 0x55).abs(0x4C, 0x82AF)
    sj.label("sj_r").b(0x60)
    place(rom, 4, SJ, sj.bytes())
    patch(rom, 4, 0x86D2, bytes.fromhex("a95520af82"), bytes([0x20, SJ & 0xFF, SJ >> 8, 0xEA, 0xEA]))
    # Bombsmith: the bomb blast's door check (bank 7 $F99F: JSR $A3F6, bank 5 in, the door's type; 4 a bomb wall)
    # calls this instead: a locked door (5 / 6) counts as a bomb wall with the upgrade (the blast opens it, no key)
    BS = 0xBD46                                 # bank 5 free (26 bytes)
    bs = Asm(BS)
    bs.abs(0x20, 0xA3F6).b(0xC9, 0x05).br(0x90, "bs_r").b(0xC9, 0x07).br(0xB0, "bs_r").b(0xA8)
    bs.abs(0xAD, BOMBSMITH[0]).b(0x29, BOMBSMITH[1]).br(0xF0, "bs_o").b(0xA9, 0x04, 0x60)
    bs.label("bs_o").b(0x98)
    bs.label("bs_r").b(0x60)
    bsb = bs.bytes(); assert len(bsb) <= 26
    place(rom, 5, BS, bsb)
    patch(rom, 7, 0xF99F, bytes([0x20, 0xF6, 0xA3]), bytes([0x20, BS & 0xFF, BS >> 8]))
    notes.append(f"upgrade shops H1 (beams 50, boomstick 100, regen 200), B11 (bubble ring 50, sword +1 100, "
                 f"fairy 150) and B2 (like-like bombs 50, rupee speed 100, Ganon boomerang 150) ({len(code)} common bytes at ${COMMON:04X})")


apply_caves_later = []


def apply_caves(rom: bytearray, notes: list) -> None:
    """The upgrade caves (bank 0's engine, bank 1's hooks) and the white sword cave: after lol_pictures (its LOAD)."""
    import lol_books
    # bank 1: the cave
    f = BANK(1) + 0x85F9 - 0x8000
    assert rom[f] == 0x20
    fill = rom[f + 1] | rom[f + 2] << 8
    # The three upgrade caves (H1, B11, B2) each sell one item of each tier. The first time Link enters one it
    # takes the next rank (0, 1, 2; saved, rank + 1 in 2 bits per cave, in this file's odds byte 18); the picks
    # come from the file's seed (odds byte 17) by a fixed LCG, so they never change: rank 0 rolls each tier by
    # TIER_ODDS (out of 64), rank 1 rolls again until it differs from rank 0's, rank 2 gets the one left.
    CI, RANK, TT, TB, XS, P0, P1, IDX, TMP = 0x0194, 0x0195, 0x0196, 0x0197, 0x0198, 0x0199, 0x019A, 0x019B, 0x019C
    ESX, EK, EB = 0x608D, 0x608E, 0x608F        # elig's scratch (save RAM's spare bytes)
    from lol_odds import STORE, PER_FILE, SEED_AT
    RANKS_AT = 18
    import lol_v3core as V3, lol_pictures as PIC
    from lol_bombup import WLW, WRW
    # --- the engine (bank 0, far-called): the cave's wares (upw) and the take (uptake) ---
    POUCH_I, BAT_I, MAP_I = T.index("potion pouch"), T.index("bat potion"), T.index("map master")
    assert BAT_I == POUCH_I + 1
    from lol_af import AF_MAP
    weights = [w for tier in T.TIERS for w in T.weights256(tier)]
    KINDS = {"ge": 0, "lt": 1, "notowned": 2, "rank0": 3, "anynz": 4, "ge_or_swordless": 5}
    clauses, cptr = [], []
    for k in range(N_UP):
        cptr.append(len(clauses))
        for c in T.ROWS[k][T.COND]:
            if c[0] in ("ge", "lt", "ge_or_swordless"):
                assert c[1] >> 8 == 0x06
                clauses += [KINDS[c[0]], c[1] & 0xFF, c[2]]
            elif c[0] == "notowned":
                clauses += [2, 0, T.index(c[1])]
            elif c[0] == "rank0":
                clauses += [3, 0, 0]
            else:
                assert c[1] >> 8 == 0x06 and c[2] >> 8 == 0x06
                clauses += [4, c[1] & 0xFF, c[2] & 0xFF]
        clauses.append(0xFF)
    assert len(clauses) < 256

    def b_engine(org):
        b = Asm(org)
        # upw: an upgrade cave's wares ($0350 the person); C set: not an upgrade cave
        b.label("upw").abs(0xAD, 0x0350).b(0xA2, 0x00)
        b.label("w_find").abs(0xDD, "persons").br(0xF0, "w_got").b(0xE8, 0xE0, 0x03).br(0xD0, "w_find")
        b.b(0x38, 0x60)
        b.label("w_got").abs(0x8E, CI)
        b.abs(0xAD, STORE + SEED_AT).br(0xD0, "w_sd").b(0xA5, 0x15, 0x45, 0x18, 0x09, 0x01)
        b.abs(0x8D, STORE + SEED_AT)
        b.label("w_sd").abs(0x8D, P1)                                             # (P1: the seed)
        # this cave's rank (0-2: the order Link first entered the three; saved, rank + 1 in 2 bits per cave)
        b.abs(0xAD, STORE + RANKS_AT).abs(0xAE, CI).br(0xF0, "w_f0")
        b.label("w_fs").b(0x4A, 0x4A, 0xCA).br(0xD0, "w_fs")
        b.label("w_f0").b(0x29, 0x03).br(0xD0, "w_have")
        b.abs(0xAD, STORE + RANKS_AT).abs(0x8D, TMP).b(0xA2, 0x01)               # new: 1 + the caves ranked
        for _ in range(3):
            b.abs(0xAD, TMP).b(0x29, 0x03).br(0xF0, f"w_c{_}").b(0xE8)
            b.label(f"w_c{_}").abs(0x4E, TMP).abs(0x4E, TMP)
        b.abs(0x8E, IDX).b(0x8A).abs(0x8D, TMP).abs(0xAE, CI).br(0xF0, "w_p0")   # IDX: rank + 1
        b.label("w_ps").abs(0x0E, TMP).abs(0x0E, TMP).b(0xCA).br(0xD0, "w_ps")
        b.label("w_p0").abs(0xAD, STORE + RANKS_AT).abs(0x0D, TMP).abs(0x8D, STORE + RANKS_AT)
        b.abs(0xAD, IDX)
        b.label("w_have").b(0x38, 0xE9, 0x01).abs(0x8D, RANK)
        b.b(0xA9, 0x00).abs(0x8D, TT)
        b.label("w_tier").abs(0xAE, TT).abs(0xBD, "tstart").abs(0x8D, TB)
        b.abs(0xAD, P1).abs(0x5D, "tconst").abs(0x8D, XS)                       # the LCG: seed ^ the tier's constant
        b.abs(0x20, "roll").abs(0x8D, IDX)                                        # rank 0's pick
        b.abs(0xAD, RANK).br(0xF0, "w_use")
        b.abs(0xAD, IDX).abs(0x8D, TMP)
        b.label("w_r1").abs(0x20, "roll").abs(0xCD, TMP).br(0xF0, "w_r1").abs(0x8D, IDX)   # rank 1's
        b.abs(0xAD, RANK).b(0xC9, 0x01).br(0xF0, "w_use")
        b.label("w_r2").abs(0x20, "roll").abs(0xCD, TMP).br(0xF0, "w_r2").abs(0xCD, IDX).br(0xF0, "w_r2")
        b.abs(0x8D, IDX)                                                          # rank 2's: not the others
        b.label("w_use").abs(0xAD, IDX).b(0x18).abs(0x6D, TB).b(0xAA).abs(0xBD, "tier_items").abs(0x8D, IDX)
        b.abs(0xAC, CI).abs(0xB9, "cofs").b(0x18).abs(0x6D, TT).abs(0x8D, TMP)    # this ware's place
        b.abs(0xAE, IDX).abs(0x20, "uget").br(0xD0, "w_owned")
        b.abs(0xAE, TT).abs(0xAD, IDX).abs(0x9D, T.WIX)                          # ware slot TT: this upgrade
        b.abs(0xBD, "flags").b(0x09, T.WARE_CODES[0]).b(0x18).abs(0x6D, TT)      # its slot's item code
        b.abs(0xAC, TMP).abs(0x99, CAVE_WARES)
        b.abs(0xAE, IDX).abs(0xBD, "uprices").abs(0x99, CAVE_PRICES).abs(0x4C, "w_nx")
        b.label("w_owned").abs(0xAE, TT).b(0xA9, 0xFF).abs(0x9D, T.WIX)
        b.abs(0xBD, "flags").b(0x09, 0x3F).abs(0xAC, TMP).abs(0x99, CAVE_WARES)
        b.b(0xA9, 0x00).abs(0x99, CAVE_PRICES)
        b.label("w_nx").abs(0xEE, TT).abs(0xAD, TT).b(0xC9, 0x03).br(0xF0, "w_done").abs(0x4C, "w_tier")
        b.label("w_done").b(0xA2, 0x01).abs(0x20, PIC.LOAD["load"])                # the wares' (and owned) pictures
        b.b(0x18, 0x60)
        # roll: the LCG (x * 5 + $3B), a full byte walked through this tier's weights (out of 256); A = the pick
        # (within the tier). A pick whose conditions Link doesn't meet rolls again.
        b.label("roll").abs(0xAD, XS).b(0x0A, 0x0A, 0x18).abs(0x6D, XS).b(0x18, 0x69, 0x3B).abs(0x8D, XS)
        b.abs(0xAE, TB)
        b.label("r_lp").b(0x38).abs(0xFD, "todds").br(0x90, "r_got").b(0xE8).br(0xD0, "r_lp")
        b.label("r_got").abs(0xBC, "tier_items").abs(0x20, "elig").br(0xB0, "roll")
        b.b(0x8A, 0x38).abs(0xED, TB).b(0x60)
        # elig: Y = the upgrade; C clear if every condition of its holds (X kept)
        b.label("elig").abs(0x8E, ESX).abs(0xBE, "cptr")
        b.label("e_lp").abs(0xBD, "cl").b(0xC9, 0xFF).br(0xF0, "e_ok")
        b.abs(0x8D, EK).abs(0xBC, "cl1").abs(0xBD, "cl2").abs(0x8D, EB)
        b.abs(0xAD, EK).br(0xF0, "k_ge").b(0xC9, 0x01).br(0xF0, "k_lt").b(0xC9, 0x02).br(0xF0, "k_no")
        b.b(0xC9, 0x03).br(0xF0, "k_r0").b(0xC9, 0x05).br(0xF0, "k_gs")
        b.abs(0xB9, 0x0600).abs(0xAC, EB).abs(0x19, 0x0600).br(0xF0, "e_no").br(0xD0, "e_nx")   # anynz
        b.label("k_gs").abs(0xAD, 0x7FF7).br(0xD0, "e_nx")                         # (lol_modes' swordless)
        b.label("k_ge").abs(0xB9, 0x0600).abs(0xCD, EB).br(0x90, "e_no").br(0xB0, "e_nx")
        b.label("k_lt").abs(0xB9, 0x0600).abs(0xCD, EB).br(0xB0, "e_no").br(0x90, "e_nx")
        b.label("k_no").b(0x8A, 0x48).abs(0xAE, EB).abs(0x20, "uget").abs(0x8D, EK).b(0x68, 0xAA)
        b.abs(0xAD, EK).br(0xD0, "e_no").br(0xF0, "e_nx")
        b.label("k_r0").abs(0xAD, RANK).br(0xD0, "e_no")
        b.label("e_nx").b(0xE8, 0xE8, 0xE8).abs(0x4C, "e_lp")
        b.label("e_ok").abs(0xAE, ESX).b(0x18, 0x60)
        b.label("e_no").abs(0xAE, ESX).b(0x38, 0x60)
        # uget / uset: X = the upgrade; A = its owned bit (Z clear: owned). Y used, X kept. (Bits of 0-8: $06xx;
        # 9 on: $60xx)
        b.label("uget").abs(0xBC, "ualo").b(0xE0, 9).br(0xB0, "ug_h").abs(0xB9, 0x0600).abs(0x3D, "ubits").b(0x60)
        b.label("ug_h").abs(0xB9, 0x6000).abs(0x3D, "ubits").b(0x60)
        b.label("uset").abs(0xBC, "ualo").b(0xE0, 9).br(0xB0, "us_h")
        b.abs(0xB9, 0x0600).abs(0x1D, "utbits").abs(0x99, 0x0600).b(0x60)
        b.label("us_h").abs(0xB9, 0x6000).abs(0x1D, "utbits").abs(0x99, 0x6000).b(0x60)
        # uptake: X = the ware slot. Its upgrade (WIX) gets its bit, and moves to the next owned slot (the pictures
        # stay where they are: the slot's tables and palette are copied); the map master's maps; the item tune
        b.label("uptake").abs(0x8E, TMP).abs(0xBD, T.WIX).b(0xAA)
        b.abs(0x20, "uset").b(0x8A, 0x48)
        b.abs(0xAC, T.OWN_N).b(0xC0, 0x03).br(0xB0, "t_pp").abs(0xAE, TMP)
        b.abs(0xBD, WLW + 11).abs(0x99, WLW + 8).abs(0xBD, WRW + 11).abs(0x99, WRW + 8)
        b.abs(0xBD, T.SCONV + 3).abs(0x99, T.SCONV).abs(0xEE, T.OWN_N)
        b.label("t_pp").b(0x68, 0xAA)
        b.b(0xE0, MAP_I).br(0xD0, "t_nm")                                         # map master: every map
        b.b(0xA9, 0xFF).abs(0x8D, 0x0668).abs(0x8D, AF_MAP).b(0xA9, 0x01).abs(0x8D, 0x066A)
        b.label("t_nm").b(0xE0, POUCH_I).br(0x90, "t_np").b(0xE0, BAT_I + 1).br(0xB0, "t_np")
        b.b(0xA2, 0x01).abs(0x20, PIC.LOAD["load"])                               # the potion's pictures anew
        b.label("t_np").b(0xA9, 0x08).abs(0x8D, 0x0602).b(0x60)                   # the item tune
        # tables
        b.label("persons").b(*[p for p, c, w in SHOPS])
        b.label("cofs").b(*[3 * c for p, c, w in SHOPS])
        b.label("tconst").b(0x00, 0x5D, 0xA7)
        b.label("todds").b(*weights)
        b.label("tier_items").b(*[k for tier in T.TIERS for k in tier])
        b.label("tstart").b(*[sum(len(x) for x in T.TIERS[:i]) for i in range(3)])
        b.label("ualo").b(*[T.ROWS[k][T.SAVE][0] & 0xFF for k in range(N_UP)])
        b.label("ubits").b(*[T.ROWS[k][T.SAVE][1] for k in range(N_UP)])
        b.label("utbits").b(*[T.ROWS[k][T.SAVE][1] | (FAIRY if T.ROWS[k][T.SAVE] == (UPGRADES, FAIRY_OWNED) else 0)
                              for k in range(N_UP)])                              # (the bottle: with its fairy)
        b.label("uprices").b(*[T.ROWS[k][T.PRICE] for k in range(N_UP)])
        b.label("flags").b(*FLAGS)
        b.label("cptr").b(*cptr)
        b.label("cl").b(*clauses)
        b.labels["cl1"] = b.labels["cl"] + 1
        b.labels["cl2"] = b.labels["cl"] + 2
        return b
    E = V3.put0(rom, b_engine).labels
    # --- bank 1: the cave's hook (InitCave's JSR at $85F9) and the take's (the caves' JSR TakeItem at $891E) ---
    from lol_newups import free_in
    import sys
    import lolpaths
    for pth in (lolpaths.ZORA, lolpaths.Q3B):
        if pth not in sys.path:
            sys.path.insert(0, pth)
    from zora.rom.serialize.text import _encode_quote
    import build_mock as base

    import lol_modes
    lol_modes.install(rom, notes)
    ws_at = [WS_CODE]
    def b_hooks(org):
        b = Asm(org)
        b.label("wares").b(*V3.far(0, lol_modes.CAVE)).b(*V3.far(0, E["upw"])).br(0xB0, "w_ws")
        b.abs(0xAD, 0x0350).abs(0x4C, fill)
        b.label("w_ws").abs(0x4C, ws_at[0])                                   # (not an upgrade cave)
        b.label("take").b(0x48).abs(0xAD, 0x0350).b(0xA0, 0x00)
        b.label("t_find").abs(0xD9, "persons1").br(0xF0, "t_got").b(0xC8, 0xC0, 0x03).br(0xD0, "t_find")
        b.b(0x68).abs(0x4C, lol_books.TAKE)
        b.label("t_got").b(0x68).b(*V3.far(0, E["uptake"])).b(0x60)           # (X: the ware slot)
        b.label("persons1").b(*[p for p, c, w in SHOPS])
        b.label("text").b(*_encode_quote(base.centered(QUOTE_TEXT)))
        return b
    b = b_hooks(0x8000)
    n1 = len(b.bytes())
    at1 = free_in(rom, 1, n1, 0xB000)
    b = b_hooks(at1)
    code1 = b.bytes()
    place(rom, 1, at1, code1)
    L1 = b.labels
    rom[f + 1:f + 3] = bytes([L1["wares"] & 0xFF, L1["wares"] >> 8])
    t = b                                                                     # (the take and text labels)
    # The white sword cave (person $6C) offers, each time Link walks in, the first item of WS_LIST he doesn't have
    # (a key when he has them all), in its middle place; taking it still empties the cave for good.
    def ws_build(org):
      w = Asm(org)
      w.b(0xC9, 0x6C).br(0xF0, "ws").abs(0x4C, fill)
      w.label("ws").b(0xA2, 0x00)
      w.label("ws_lp").abs(0xBC, WS_TABLE + 1).abs(0xB9, 0x0600).abs(0xDD, WS_TABLE + 2).br(0xB0, "ws_nx")
      w.abs(0xBD, WS_TABLE).b(0xC9, 0x02).br(0xD0, "ws_b").abs(0xAD, 0x7FF7).br(0xF0, "ws_put")   # swordless:
      w.abs(0xAD, 0x067C).b(0xC9, 32).br(0xB0, "ws_nx").b(0xA9, 0x24).br(0xD0, "ws_st")            # a bomb upgrade
      w.label("ws_b").b(0xC9, 0x1D).br(0xD0, "ws_put").abs(0xAC, 0x0675).br(0xF0, "ws_put")   # no boomerang of any kind
      w.label("ws_nx").b(0xE8, 0xE8, 0xE8, 0xE0, 3 * len(WS_LIST)).br(0xD0, "ws_lp")
      w.b(0xA9, 0x19).br(0xD0, "ws_st")                                       # everything: a key
      w.label("ws_put").abs(0xBD, WS_TABLE)
      w.label("ws_st").abs(0x8D, 0x019C).abs(0xAD, CAVE_WARES + 7).b(0x29, 0xC0).abs(0x0D, 0x019C).abs(0x8D, CAVE_WARES + 7)
      w.abs(0xAD, 0x0350).abs(0x4C, fill)
      return w
    nws = len(ws_build(0x8000).bytes())
    ws_at[0] = free_in(rom, 1, nws, 0xB000)
    cw = ws_build(ws_at[0]).bytes()
    place(rom, 1, ws_at[0], cw)
    place_again = b_hooks(at1).bytes()                                        # (its jump to the new place)
    rom[BANK(1) + at1 - 0x8000:BANK(1) + at1 - 0x8000 + len(place_again)] = place_again
    tbl = bytes(x for item, addr, most in WS_LIST for x in (item, addr & 0xFF, most))
    assert WS_TABLE + len(tbl) <= 0x8D00
    place(rom, 1, WS_TABLE, tbl)
    patch(rom, 1, 0x891E, bytes([0x20, lol_books.TAKE & 0xFF, lol_books.TAKE >> 8]), bytes([0x20, t.labels["take"] & 0xFF, t.labels["take"] >> 8]))
    for person, cave, wares in SHOPS:
        rom[0x45B2 + cave] = SHOP_QUOTE_SELECTOR
    q = t.labels["text"]
    rom[0x4010 + 2 * QUOTE:0x4010 + 2 * QUOTE + 2] = bytes([q & 0xFF, q >> 8])
