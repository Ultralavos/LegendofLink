"""Legend of Link: the end screen, after the credits, and the file's clock.

The clock: four bytes of save RAM (CLOCK: frames, seconds, minutes, hours; file 2's name, which nothing writes since
lol_af keeps the file unregistered) count every frame from the file's start (lol_saveblock's new-file clear zeroes
them) to the end: the frame's sound call in the NMI (bank 7 $E561, JSR $9825 with bank 0 in) goes through TICK first,
which counts in the game's modes 2-$12 (not the title, the menu, registering, elimination or the ending), up to
99:59:59. Kept at once (not undone by a reset), so it is the time from start to finish.

The end screen: the credits' last wait (bank 2 $ABA5, the Start press: JSR $EBA3 before the file is wiped) runs SHOW
first (bank 0, far-called). With NMI and the picture off it draws a page into nametable $2000 (the font's tiles, $00-
$2F of the background patterns at $1000; pictures copied into tiles $70-$E8, a colon and the boxes' lines in $E9-$EF:
the level's own patterns, which the next level load brings back; the common ones and the menu's stay),
shows it, and waits (the sound driver kept running): Start flips the page, Select ends.

  page 1: Levels 1-9 and shrines A-D, each with its design's nickname (lol_genload's records: the design) and the
          item its old man gave (a level) or its reward (a shrine), kept by lol_bombup's rec in the odds' saved bytes
  page 2: the time, the badges, the upgrades bought, the inventory: the items above the box, the sword, the box

Pictures are the game's own: an item's 8x16 sprite halves read back from the pattern tables (the vanilla items'
tile from ItemIdToSlot / Anim_ItemFrameTiles, the new items' halves from lol_bombup's WLW / WRW, the potion's from
PTILE), or an upgrade's from lol_pictures' data; an 8-wide item is centred in its 16x16 cell, the raft and ladder
mirrored as the game draws them."""
from lol_af import Asm, BANK, place, patch

CLOCK = 0x600A                          # save RAM: frames, seconds, minutes, hours
SOUND = 0x9825                          # bank 0: the sound driver (every NMI)
NMI_SOUND = 0xE561                      # bank 7: JSR SOUND
CREDITS_START = 0xABA5                  # bank 2: JSR $EBA3 once Start is pressed at the credits' end
STUB = 0xBB20                           # bank 2 free (the end of $B932-$BB3F)
BUF0, BUF1, ATTR = 0x0200, 0x0220, 0x0240   # the OAM buffer (the sprites are off on this screen)
NEXT_T, PAGE, PAD, PR, PC, PPAL, HLL, HLH, HRL, HRH, PMODE, TMP, TMP2, CNT, IDX = range(0x0280, 0x028F)
T_FIRST, T_LAST = 0x70, 0xE9            # picture tiles (the level's own patterns: the common ones, $00-$6F and
T_COLON, T_TL, T_H, T_TR, T_V, T_BL, T_BR = range(0xE9, 0xF0)   # the menu's $F2-$FF, are left as they are)
BG_PALETTES = [0x0F, 0x30, 0x12, 0x00,  # text (white), the boxes (blue)
               0x0F, 0x02, 0x22, 0x30,  # the game's blue items (sprite palette 1)
               0x0F, 0x16, 0x27, 0x30,  # red (2)
               0x0F, 0x29, 0x27, 0x17]  # Link's (0)
SPR_TO_BG = (3, 1, 2, 1)
CENTER, MIRROR, PAIR = 0, 1, 2
WRAM_DELTA = 0x3870


def custom_tiles():
    colon = [0x00, 0x18, 0x18, 0x00, 0x00, 0x18, 0x18, 0x00]
    rows = {T_COLON: (colon, None)}
    blank = [0] * 8
    line = [0, 0, 0, 0xFF, 0xFF, 0, 0, 0]
    vert = [0x18] * 8
    rows[T_H] = (None, line)
    rows[T_V] = (None, vert)
    rows[T_TL] = (None, [0, 0, 0, 0x1F, 0x1F, 0x18, 0x18, 0x18])
    rows[T_TR] = (None, [0, 0, 0, 0xF8, 0xF8, 0x18, 0x18, 0x18])
    rows[T_BL] = (None, [0x18, 0x18, 0x18, 0x1F, 0x1F, 0, 0, 0])
    rows[T_BR] = (None, [0x18, 0x18, 0x18, 0xF8, 0xF8, 0, 0, 0])
    out = bytearray()
    for t in range(T_COLON, T_BR + 1):
        p0, p1 = rows[t]
        out += bytes(p0 or blank) + bytes(p1 or blank)
    return bytes(out)


def item_table(rom):
    """Per item code 0-$2A: (kind, tile or FLAG, BG palette)."""
    import lol_bombup as B
    w = lambda a, n: rom[BANK(1) + a + WRAM_DELTA - 0x8000:BANK(1) + a + WRAM_DELTA - 0x8000 + n]
    slot_of, pal_of, f_idx, frames = w(0x72A4, 0x24), w(0x72EC, 0x24), w(0x78B7, 0x30), w(0x78DC, 0x40)
    level = {1: 1, 2: 2, 3: 3, 6: 1, 7: 2, 8: 1, 9: 2, 0x1F: 1, 0x20: 2, 0x12: 1, 0x13: 2}
    out = []
    for c in range(0x24):
        s = slot_of[c]
        p = pal_of[s]
        y = s
        if s in (0, 4, 2, 7, 0x0B):
            p = (p + level.get(c, 1)) & 0xFF
            if s == 0 and p == 2:
                y = 0x20                                # the magical sword's picture
        p &= 3
        t = frames[f_idx[y]]
        kind = MIRROR if 0x6C <= t < 0x7C else CENTER
        out.append((kind, t, SPR_TO_BG[p]))
    pal = lambda code: out[code][2]
    out.append((CENTER, B.TILE, pal(B.CONV[0])))        # $24 the bomb upgrade
    out.append((CENTER, out[0x11][1], 1))               # $25 the blue book
    for c in range(0x26, 0x2B):                         # badges, XP potions: their halves by FLAG
        out.append((PAIR, c - 0x23, pal(B.CONV[c - 0x24])))
    return out


def display_name(nm):
    import re
    import lol_quests
    m = re.match(r"^(\d)Q L(\d)$", nm)
    if m:
        s = lol_quests.nickname(m.group(1) + "q", int(m.group(2)))
    elif re.match(r"^(Shape|Green|Blue|Magenta|Yellow|Cyan|Red) \d+$", nm):
        s = nm
    else:
        s = "The " + nm
    return s.upper()[:24]


def enc(s):
    from lol_ending import FONT
    return bytes(T_COLON if c == ":" else FONT[c] for c in s) + b"\xff"


def build_show(org, rom, names, items, L):
    """The end screen (bank 0). L: lol_pictures' LOAD labels."""
    import lol_bombup as B
    import lol_genload as GL
    import lol_uptable as T
    from lol_odds import STORE
    N = T.N_UP
    a = Asm(org)
    # --- entry
    a.label("show").b(0x08, 0x8A, 0x48, 0x98, 0x48)
    a.abs(0x20, "off")
    a.b(0xA2, 0x1F).label("pal_c").abs(0xBD, "bgpal").abs(0x9D, ATTR).b(0xCA).br(0x10, "pal_c")
    a.b(0xA9, 0x3F, 0xA2, 0x00).abs(0x20, "addr")
    a.b(0xA2, 0x00).label("pal_w").abs(0xBD, ATTR).abs(0x8D, 0x2007).b(0xE8, 0xE0, 0x20).br(0xD0, "pal_w")
    # the custom tiles
    a.b(0xA9, 0x10 + (T_COLON >> 4), 0xA2, (T_COLON << 4) & 0xFF).abs(0x20, "addr")
    a.b(0xA2, 0x00).label("ct_w").abs(0xBD, "ctiles").abs(0x8D, 0x2007).b(0xE8, 0xE0, len(custom_tiles()))
    a.br(0xD0, "ct_w")
    a.b(0xA9, 0x00).abs(0x8D, PAGE).b(0xA9, 0xFF).abs(0x8D, PAD)
    a.label("redraw").abs(0x20, "off").abs(0x20, "cls")
    a.abs(0xAD, PAGE).br(0xD0, "rd2").abs(0x20, "page1").abs(0x4C, "rd_on")
    a.label("rd2").abs(0x20, "page2")
    a.label("rd_on").abs(0x20, "attrs")
    a.abs(0x20, "vwait").b(0xA9, 0x00).abs(0x8D, 0x2005).abs(0x8D, 0x2005)
    a.b(0xA9, 0x10).abs(0x8D, 0x2000).b(0xA9, 0x0A).abs(0x8D, 0x2001)
    # the wait: a frame each, the sound driver, the pad (Start flips, Select ends)
    a.label("wait").abs(0x20, "vwait").abs(0x20, SOUND)
    a.b(0xA9, 0x01).abs(0x8D, 0x4016).b(0xA9, 0x00).abs(0x8D, 0x4016)
    a.b(0xA2, 0x08).label("pad_l").abs(0xAD, 0x4016).b(0x4A).abs(0x2E, TMP).b(0xCA).br(0xD0, "pad_l")
    a.abs(0xAD, PAD).b(0x49, 0xFF).abs(0x2D, TMP).abs(0x8D, TMP2)                   # the new presses
    a.abs(0xAD, TMP).abs(0x8D, PAD)
    a.abs(0xAD, TMP2).b(0x29, 0x20).br(0xD0, "end")
    a.abs(0xAD, TMP2).b(0x29, 0x10).br(0xF0, "wait")
    a.abs(0xAD, PAGE).b(0x49, 0x01).abs(0x8D, PAGE).abs(0x4C, "redraw")
    a.label("end").abs(0x20, "off")
    a.b(0x68, 0xA8, 0x68, 0xAA, 0x28, 0x60)
    # off: the picture and NMI off (vblank first: no half-drawn frame)
    a.label("off").abs(0x20, "vwait").b(0xA9, 0x00).abs(0x8D, 0x2001)
    a.b(0xA5, 0xFF, 0x29, 0x7B).abs(0x8D, 0x2000).b(0x60)                           # (+1 per write, NMI off)
    a.label("vwait").abs(0xAD, 0x2002)
    a.label("vw_l").abs(0xAD, 0x2002).br(0x10, "vw_l").b(0x60)
    # addr: A = high, X = low
    a.label("addr").b(0x48).abs(0xAD, 0x2002).b(0x68).abs(0x8D, 0x2006).abs(0x8E, 0x2006).b(0x60)
    # ntaddr: PR / PC -> the nametable address
    a.label("ntaddr").abs(0xAD, PR).b(0x4A, 0x4A, 0x4A, 0x09, 0x20).b(0x48)
    a.abs(0xAD, PR).b(0x0A, 0x0A, 0x0A, 0x0A, 0x0A).abs(0x0D, PC).b(0xAA, 0x68).abs(0x4C, "addr")
    # cls: the nametable blank, the attribute shadow 0, the first picture tile
    a.label("cls").b(0xA9, 0x20, 0xA2, 0x00).abs(0x20, "addr")
    a.b(0xA9, 0x24, 0xA0, 0x04, 0xA2, 0xC0)
    a.label("cl_l").abs(0x8D, 0x2007).b(0xCA).br(0xD0, "cl_l").b(0x88).br(0xD0, "cl_l")
    a.b(0xA9, 0x00, 0xA2, 0x3F).label("cl_a").abs(0x9D, ATTR).b(0xCA).br(0x10, "cl_a")
    a.b(0xA9, T_FIRST).abs(0x8D, NEXT_T).b(0x60)
    a.label("attrs").b(0xA9, 0x23, 0xA2, 0xC0).abs(0x20, "addr")
    a.b(0xA2, 0x00).label("at_l").abs(0xBD, ATTR).abs(0x8D, 0x2007).b(0xE8, 0xE0, 0x40).br(0xD0, "at_l").b(0x60)
    # text: PR / PC, ($00) the string ($FF ends)
    a.label("text").abs(0x20, "ntaddr").b(0xA0, 0x00)
    a.label("tx_l").b(0xB1, 0x00, 0xC9, 0xFF).br(0xF0, "tx_e").abs(0x8D, 0x2007).b(0xC8).br(0xD0, "tx_l")
    a.label("tx_e").b(0x60)
    # stext: A = the index of a fixed string (tables slo / shi), at PR / PC
    a.label("stext").b(0xAA).abs(0xBD, "slo").b(0x85, 0x00).abs(0xBD, "shi").b(0x85, 0x01).abs(0x4C, "text")
    # tile1: A = a tile at PR / PC
    a.label("tile1").b(0x48).abs(0x20, "ntaddr").b(0x68).abs(0x8D, 0x2007).b(0x60)
    # num2: A = 0-99 at PR / PC (Y = 0: no leading zero). Y kept
    a.label("num2").b(0xA2, 0x00)
    a.label("n2_l").b(0xC9, 0x0A).br(0x90, "n2_d").b(0xE9, 0x0A, 0xE8).br(0xD0, "n2_l")
    a.label("n2_d").abs(0x8D, TMP).abs(0x8E, TMP2).abs(0x20, "ntaddr").abs(0xAD, TMP2).br(0xD0, "n2_t")
    a.b(0xC0, 0x00).br(0xF0, "n2_o")
    a.label("n2_t").abs(0x8D, 0x2007)
    a.label("n2_o").abs(0xAD, TMP).abs(0x8D, 0x2007).b(0x60)
    # --- pictures
    # half: HxL / HxH (X = 0 left, 2 right) into BUF0 / BUF1 (Y = 0 / $20): high 0: a sprite tile from the pattern
    # tables, else 32 bytes of ROM (bank 0)
    a.label("half").abs(0xBD, HLH).br(0xD0, "h_rom")
    a.abs(0xBD, HLL).b(0x29, 0x01, 0x0A, 0x0A, 0x0A, 0x0A).abs(0x8D, TMP)                # table: $10
    a.abs(0xBD, HLL).b(0x4A, 0x4A, 0x4A, 0x4A).abs(0x0D, TMP).b(0x48)
    a.abs(0xBD, HLL).b(0x29, 0xFE, 0x0A, 0x0A, 0x0A, 0x0A, 0xAA, 0x68).abs(0x20, "addr")
    a.abs(0xAD, 0x2007).b(0xA2, 0x20)                                                  # (the read's delay)
    a.label("h_pl").abs(0xAD, 0x2007).abs(0x99, BUF0).b(0xC8, 0xCA).br(0xD0, "h_pl").b(0x60)
    a.label("h_rom").b(0x85, 0x03).abs(0xBD, HLL).b(0x85, 0x02, 0x98, 0x48, 0x18, 0x69, 0x20, 0x85, 0x04)
    a.b(0x68, 0xAA, 0xA0, 0x00)
    a.label("h_rl").b(0xB1, 0x02).abs(0x9D, BUF0).b(0xE8, 0xC8, 0xE4, 0x04).br(0xD0, "h_rl").b(0x60)
    # pic: PMODE, HLL/HLH (HRL/HRH for PAIR), PPAL at PR / PC: four tiles, the nametable, the attribute shadow
    a.label("pic").abs(0xAD, NEXT_T).b(0xC9, T_LAST - 3).br(0x90, "p_ok").b(0x60)
    a.label("p_ok").b(0xA2, 0x00, 0xA0, 0x00).abs(0x20, "half")
    a.abs(0xAD, PMODE).b(0xC9, PAIR).br(0xD0, "p_np").b(0xA2, 0x02, 0xA0, 0x20).abs(0x20, "half").abs(0x4C, "p_w")
    a.label("p_np").b(0xC9, MIRROR).br(0xD0, "p_cen")
    a.b(0xA2, 0x1F).label("p_mi").abs(0xBD, BUF0).b(0xA0, 0x08)
    a.label("p_mb").b(0x0A).abs(0x6E, TMP).b(0x88).br(0xD0, "p_mb").abs(0xAD, TMP).abs(0x9D, BUF1)
    a.b(0xCA).br(0x10, "p_mi").abs(0x4C, "p_w")
    a.label("p_cen").b(0xA2, 0x1F).label("p_cl").abs(0xBD, BUF0).b(0x0A, 0x0A, 0x0A, 0x0A).abs(0x9D, BUF1)
    a.abs(0xBD, BUF0).b(0x4A, 0x4A, 0x4A, 0x4A).abs(0x9D, BUF0).b(0xCA).br(0x10, "p_cl")
    # write: tiles NEXT_T.. (BUF0 the left column's two, BUF1 the right's)
    a.label("p_w").abs(0xAD, NEXT_T).b(0x4A, 0x4A, 0x4A, 0x4A, 0x09, 0x10).b(0x48)
    a.abs(0xAD, NEXT_T).b(0x0A, 0x0A, 0x0A, 0x0A, 0xAA, 0x68).abs(0x20, "addr")
    a.b(0xA2, 0x00).label("p_wl").abs(0xBD, BUF0).abs(0x8D, 0x2007).b(0xE8, 0xE0, 0x40).br(0xD0, "p_wl")
    a.abs(0x20, "ntaddr").abs(0xAD, NEXT_T).abs(0x8D, 0x2007).b(0x18, 0x69, 0x02).abs(0x8D, 0x2007)
    a.abs(0xEE, PR).abs(0x20, "ntaddr").abs(0xAD, NEXT_T).b(0x18, 0x69, 0x01).abs(0x8D, 0x2007)
    a.b(0x18, 0x69, 0x02).abs(0x8D, 0x2007).abs(0xCE, PR)
    a.abs(0xAD, NEXT_T).b(0x18, 0x69, 0x04).abs(0x8D, NEXT_T)
    # the attribute: byte (PR / 4) * 8 + PC / 4, bits 2 * ((PR & 2) + (PC & 2) / 2)
    a.abs(0xAD, PR).b(0x29, 0xFC, 0x0A).abs(0x8D, TMP).abs(0xAD, PC).b(0x4A, 0x4A, 0x18).abs(0x6D, TMP)
    a.abs(0x8D, IDX)
    a.abs(0xAD, PR).b(0x29, 0x02, 0x0A).abs(0x8D, TMP).abs(0xAD, PC).b(0x29, 0x02).abs(0x0D, TMP).b(0xA8)  # 0,2,4,6
    a.abs(0xAD, PPAL).abs(0x8D, TMP).b(0xA9, 0x03).abs(0x8D, TMP2)
    a.b(0xC0, 0x00).label("p_sh").br(0xF0, "p_sd").abs(0x0E, TMP).abs(0x0E, TMP2).b(0x88).br(0xD0, "p_sh")
    a.label("p_sd").abs(0xAE, IDX).abs(0xAD, TMP2).b(0x49, 0xFF).abs(0x3D, ATTR).abs(0x0D, TMP).abs(0x9D, ATTR)
    a.b(0x60)
    # ipic: A = an item code at PR / PC
    a.label("ipic").b(0xAA).abs(0xBD, "ipal").abs(0x8D, PPAL).abs(0xBD, "ikind").abs(0x8D, PMODE)
    a.b(0xA9, 0x00).abs(0x8D, HLH).abs(0x8D, HRH)
    a.abs(0xBD, "itile").abs(0x8D, HLL).abs(0xAD, PMODE).b(0xC9, PAIR).br(0xD0, "ip_go")
    a.abs(0xBC, "itile").abs(0xB9, B.WLW).abs(0x8D, HLL).abs(0xB9, B.WRW).abs(0x8D, HRL)
    a.label("ip_go").abs(0x4C, "pic")
    # upic: X = an upgrade at PR / PC
    a.label("upic").abs(0xBD, L["hlo"]).abs(0x8D, HLL).abs(0xBD, L["hhi"]).abs(0x8D, HLH)
    a.b(0x8A, 0x48, 0x18, 0x69, N, 0xAA).abs(0xBD, L["hlo"]).abs(0x8D, HRL).abs(0xBD, L["hhi"]).abs(0x8D, HRH)
    a.b(0x68, 0xAA).abs(0xBC, L["upal"]).abs(0xB9, "ipal").abs(0x8D, PPAL).b(0xA9, PAIR).abs(0x8D, PMODE)
    a.abs(0x4C, "pic")
    # uown: X = an upgrade; Z clear if owned (X kept)
    a.label("uown").abs(0xBD, L["ualo"]).b(0x85, 0x02).abs(0xBD, L["uahi"]).b(0x85, 0x03)
    a.b(0xA0, 0x00, 0xB1, 0x02).abs(0x3D, L["ubits"]).b(0x60)
    # box: the corners at (PR, PC) and (TMP rows, CNT columns) apart
    a.label("box").abs(0xAD, PR).abs(0x8D, IDX)
    a.b(0xA9, T_TL).abs(0x20, "tile1")
    a.abs(0xAC, CNT).label("bx_t").b(0xA9, T_H).abs(0x8D, 0x2007).b(0x88).br(0xD0, "bx_t")
    a.b(0xA9, T_TR).abs(0x8D, 0x2007)
    a.abs(0xAC, TMP).label("bx_v").abs(0xEE, PR).b(0xA9, T_V).abs(0x20, "tile1")
    a.abs(0xAD, PC).b(0x48, 0x18).abs(0x6D, CNT).b(0x69, 0x01).abs(0x8D, PC).b(0xA9, T_V).abs(0x20, "tile1")
    a.b(0x68).abs(0x8D, PC).b(0x88).br(0xD0, "bx_v")
    a.abs(0xEE, PR).b(0xA9, T_BL).abs(0x20, "tile1")
    a.abs(0xAC, CNT).label("bx_b").b(0xA9, T_H).abs(0x8D, 0x2007).b(0x88).br(0xD0, "bx_b")
    a.b(0xA9, T_BR).abs(0x8D, 0x2007).abs(0xAD, IDX).abs(0x8D, PR).b(0x60)
    # at: A = PR, X = PC
    a.label("at").abs(0x8D, PR).abs(0x8E, PC).b(0x60)

    # --- page 1: Levels 1-9, shrines A-D: the label, the nickname, the item
    a.label("page1").b(0xA9, 0x00).abs(0x8D, CNT)
    a.label("p1_l").abs(0xAD, CNT).b(0x0A, 0x18, 0x69, 0x02).b(0xA2, 0x02).abs(0x20, "at")
    a.abs(0xAD, CNT).b(0x18, 0x69, S_LABEL).abs(0x20, "stext")
    a.abs(0xEE, PR).b(0xA9, 0x04).abs(0x8D, PC)
    a.abs(0xAE, CNT).abs(0xBD, "recofs").b(0xAA).abs(0xBD, GL.REC).br(0xF0, "p1_nn")
    a.b(0xAA, 0xCA).abs(0xBD, "nlo").b(0x85, 0x00).abs(0xBD, "nhi").b(0x85, 0x01).abs(0x20, "text").abs(0x4C, "p1_it")
    a.label("p1_nn").b(0xA9, S_UNSEEN).abs(0x20, "stext")
    a.label("p1_it").abs(0xCE, PR).b(0xA9, 28).abs(0x8D, PC)
    a.abs(0xAE, CNT).abs(0xBC, "stoidx").abs(0xB9, STORE).br(0x10, "p1_nx").b(0x29, 0x7F).abs(0x20, "ipic")
    a.label("p1_nx").abs(0xEE, CNT).abs(0xAD, CNT).b(0xC9, 13).br(0xF0, "p1_e").abs(0x4C, "p1_l")
    a.label("p1_e").b(0xA9, 28, 0xA2, 0x05).abs(0x20, "at").b(0xA9, S_KEYS).abs(0x4C, "stext")

    # --- page 2
    a.label("page2").b(0xA9, 2, 0xA2, 2).abs(0x20, "at").b(0xA9, S_TIME).abs(0x20, "stext")
    a.b(0xA9, 2, 0xA2, 7).abs(0x20, "at")                                           # H (one or two digits)
    a.abs(0xAD, CLOCK + 3).b(0xC9, 10).br(0xB0, "t_h2").abs(0xEE, PC)
    a.label("t_h2").b(0xA0, 0x00).abs(0x20, "num2")
    a.b(0xA9, 9).abs(0x8D, PC).b(0xA9, T_COLON).abs(0x20, "tile1")
    a.b(0xA9, 10).abs(0x8D, PC).abs(0xAD, CLOCK + 2).b(0xA0, 0x01).abs(0x20, "num2")
    a.b(0xA9, 12).abs(0x8D, PC).b(0xA9, T_COLON).abs(0x20, "tile1")
    a.b(0xA9, 13).abs(0x8D, PC).abs(0xAD, CLOCK + 1).b(0xA0, 0x01).abs(0x20, "num2")
    # the badges: S, D, X (2 bits each of $0673)
    a.b(0xA9, 5, 0xA2, 2).abs(0x20, "at").b(0xA9, S_BADGES).abs(0x20, "stext")
    a.b(0xA9, 0x00).abs(0x8D, CNT)
    a.label("bd_l").abs(0xAD, 0x0673).abs(0xAE, CNT).br(0xF0, "bd_s")
    a.label("bd_sh").b(0x4A, 0x4A, 0xCA).br(0xD0, "bd_sh")
    a.label("bd_s").b(0x29, 0x03).br(0xF0, "bd_nx").b(0x48)
    a.abs(0xAD, CNT).b(0x0A, 0x0A, 0x0A, 0x18, 0x69, 0x04).b(0xAA, 0xA9, 0x06).abs(0x20, "at")
    a.abs(0xAD, CNT).b(0x18, 0x69, 0x26).abs(0x20, "ipic")
    a.abs(0xEE, PR).abs(0xEE, PC).abs(0xEE, PC).b(0xA9, FONT_X).abs(0x20, "tile1")
    a.b(0x68).abs(0x8D, 0x2007)
    a.label("bd_nx").abs(0xEE, CNT).abs(0xAD, CNT).b(0xC9, 0x03).br(0xD0, "bd_l")
    # the upgrades bought
    a.b(0xA9, 9, 0xA2, 2).abs(0x20, "at").b(0xA9, S_UPGRADES).abs(0x20, "stext")
    a.b(0xA9, 0x00).abs(0x8D, CNT)
    a.b(0xA9, 10, 0xA2, 4).abs(0x20, "at")
    a.b(0xA2, 0x00).label("up_l").abs(0x20, "uown").br(0xF0, "up_nx")
    a.b(0x8A, 0x48).abs(0x20, "upic").b(0x68, 0xAA)
    a.abs(0xAD, PC).b(0x18, 0x69, 0x04).abs(0x8D, PC).b(0xC9, 32).br(0x90, "up_nx")
    a.b(0xA9, 0x04).abs(0x8D, PC).abs(0xEE, PR).abs(0xEE, PR)
    a.label("up_nx").b(0xE8, 0xE0, N).br(0xD0, "up_l")
    # the inventory: the items above the box, the sword's box, the box
    a.b(0xA9, 14, 0xA2, 2).abs(0x20, "at").b(0xA9, S_INVENTORY).abs(0x20, "stext")
    a.b(0xA9, 0x00).abs(0x8D, CNT)
    a.label("iv_l").abs(0xAE, CNT).abs(0xBD, "iv_row").abs(0x8D, PR).abs(0xBD, "iv_col").abs(0x8D, PC)
    a.abs(0xBD, "iv_kind").br(0x30, "iv_sp")
    a.abs(0xBC, "iv_addr").abs(0xB9, 0x0600).br(0xF0, "iv_nx")                       # (all in page $06)
    a.b(0x18).abs(0x7D, "iv_base").abs(0x20, "ipic").abs(0x4C, "iv_nx")             # code = base + the byte
    a.label("iv_sp").abs(0x20, "special")
    a.label("iv_nx").abs(0xEE, CNT).abs(0xAD, CNT).b(0xC9, len(INV)).br(0xF0, "iv_bx").abs(0x4C, "iv_l")
    a.label("iv_bx").b(0xA9, 19, 0xA2, 5).abs(0x20, "at").b(0xA9, 2).abs(0x8D, TMP).abs(0x8D, CNT)
    a.abs(0x20, "box")
    a.b(0xA9, 19, 0xA2, 13).abs(0x20, "at").b(0xA9, 4).abs(0x8D, TMP).b(0xA9, 14).abs(0x8D, CNT)
    a.abs(0x20, "box")
    a.b(0xA9, 27, 0xA2, 5).abs(0x20, "at").b(0xA9, S_KEYS).abs(0x4C, "stext")
    # special (A = the kind): $80 the bow and arrows, $81 the potion or the letter, $82 the boomerangs, $83 the
    # bombs, $84 the book
    a.label("special").b(0xC9, 0x80).br(0xD0, "sp_1")
    a.abs(0xAD, 0x0659).br(0xF0, "sp_bow")                                            # arrows: $08 / $09
    a.b(0x18, 0x69, 0x07, 0xAA).abs(0xBD, "ipal").abs(0x8D, PPAL).abs(0xBD, "itile").abs(0x8D, HLL)
    a.abs(0xAD, 0x065A).br(0xF0, "sp_one")
    a.b(0xA2, 0x0A).abs(0xBD, "itile").abs(0x8D, HRL).b(0xA9, PAIR).abs(0x8D, PMODE)  # the bow beside them
    a.label("sp_h0").b(0xA9, 0x00).abs(0x8D, HLH).abs(0x8D, HRH).abs(0x4C, "pic")
    a.label("sp_one").b(0xA9, CENTER).abs(0x8D, PMODE).br(0xF0, "sp_h0")
    a.label("sp_bow").abs(0xAD, 0x065A).br(0xF0, "sp_r").b(0xA9, 0x0A).abs(0x4C, "ipic")
    a.label("sp_1").b(0xC9, 0x81).br(0xD0, "sp_2")
    a.abs(0xAC, 0x065E).br(0xF0, "sp_let").b(0xC0, 0x05).br(0x90, "sp_pt").b(0xA0, 0x04)
    a.label("sp_pt").b(0x88).abs(0xB9, B.PTILE).abs(0x8D, HLL).abs(0xB9, B.PPAL).b(0x29, 0x03, 0xAA)
    a.abs(0xBD, "sprbg").abs(0x8D, PPAL).b(0xA9, CENTER).abs(0x8D, PMODE).br(0xF0, "sp_h0")
    a.label("sp_let").abs(0xAD, 0x0666).br(0xF0, "sp_r").b(0xA9, 0x15).abs(0x4C, "ipic")
    a.label("sp_2").b(0xC9, 0x82).br(0xD0, "sp_3")
    a.abs(0xAD, 0x0675).br(0xF0, "sp_wb").b(0xA9, 0x1E).abs(0x4C, "ipic")
    a.label("sp_wb").abs(0xAD, 0x0674).br(0xF0, "sp_r").b(0xA9, 0x1D).abs(0x4C, "ipic")
    a.label("sp_3").b(0xC9, 0x83).br(0xD0, "sp_4")
    a.abs(0xAD, 0x0658).br(0xF0, "sp_r").b(0xA9, 0x00).abs(0x4C, "ipic")
    a.label("sp_4").abs(0xAD, 0x0661).br(0xF0, "sp_r").b(0xC9, 0x02).br(0xF0, "sp_bb")
    a.b(0xA9, 0x11).abs(0x4C, "ipic")
    a.label("sp_bb").b(0xA9, 0x25).abs(0x4C, "ipic")
    a.label("sp_r").b(0x60)

    # --- tables
    a.label("bgpal").b(*BG_PALETTES, *BG_PALETTES[4:8], *BG_PALETTES[8:12], *BG_PALETTES[12:16], *BG_PALETTES[4:8])
    a.label("ctiles").b(*custom_tiles())
    a.label("sprbg").b(*SPR_TO_BG)
    a.label("ikind").b(*[k for k, t, p in items])
    a.label("itile").b(*[t for k, t, p in items])
    a.label("ipal").b(*[p for k, t, p in items])
    a.label("recofs").b(*[5 * s for s in range(13)])
    a.label("stoidx").b(*range(9), 11, 12, 13, 14)
    a.label("iv_row").b(*[r for r, c, ad, kind, base in INV])
    a.label("iv_col").b(*[c for r, c, ad, kind, base in INV])
    a.label("iv_addr").b(*[ad & 0xFF for r, c, ad, kind, base in INV])
    a.label("iv_kind").b(*[kind for r, c, ad, kind, base in INV])
    a.label("iv_base").b(*[base for r, c, ad, kind, base in INV])
    for k, nm in enumerate(names):
        a.label(f"nm{k}").b(*enc(nm))
    a.label("nlo").b(*([0] * len(names)))
    a.label("nhi").b(*([0] * len(names)))
    for k, s in enumerate(STRINGS):
        a.label(f"s{k}").b(*enc(s))
    a.label("slo").b(*([0] * len(STRINGS)))
    a.label("shi").b(*([0] * len(STRINGS)))
    return a


STRINGS = [f"LEVEL-{n}" for n in range(1, 10)] + [f"SHRINE-{c}" for c in "ABCD"] + [
    "???", "START-FLIP  SELECT-END", "TIME", "OLD MEN CARDS", "UPGRADES", "INVENTORY"]
S_LABEL, S_UNSEEN, S_KEYS, S_TIME, S_BADGES, S_UPGRADES, S_INVENTORY = 0, 13, 14, 15, 16, 17, 18
FONT_X = 0x21                           # "X"
# the inventory: (row, column, address, kind, base): kind 0 the item base + the byte (1-3 / 1-2), $80-$82 special
INV = [(16, 6, 0x0660, 0, 0x0B),         # raft ($0C)
       (16, 10, 0x0661, 0x84, 0),        # book: $11, the blue $25
       (16, 14, 0x0662, 0, 0x11),        # ring: $12 / $13
       (16, 18, 0x0663, 0, 0x0C),        # ladder ($0D)
       (16, 22, 0x0664, 0, 0x0A),        # magical key ($0B)
       (16, 26, 0x0665, 0, 0x13),        # bracelet ($14)
       (20, 6, 0x0657, 0, 0x00),         # sword 1-3
       (20, 14, 0x0675, 0x82, 0),        # boomerang (either)
       (20, 18, 0x0658, 0x83, 0),        # bombs
       (20, 22, 0x065A, 0x80, 0),        # bow / arrows (the bow's byte or the arrows')
       (20, 26, 0x065B, 0, 0x05),        # candle $06 / $07
       (22, 14, 0x065C, 0, 0x04),        # recorder ($05)
       (22, 18, 0x065D, 0, 0x03),        # food ($04)
       (22, 22, 0x065E, 0x81, 0),        # potion / letter
       (22, 26, 0x065F, 0, 0x0F)]        # wand ($10)


def build_tick(org):
    """TICK (bank 0): the clock, then the sound driver."""
    a = Asm(org)
    a.label("tick").b(0xA5, 0x12, 0xC9, 0x02).br(0x90, "go").b(0xC9, 0x13).br(0xB0, "go")
    a.b(0xC9, 0x0E).br(0xF0, "go").b(0xC9, 0x0F).br(0xF0, "go")
    a.abs(0xAD, CLOCK + 3).b(0xC9, 99).br(0x90, "run")
    a.abs(0xAD, CLOCK + 2).b(0xC9, 59).br(0x90, "run").abs(0xAD, CLOCK + 1).b(0xC9, 59).br(0xB0, "go")
    a.label("run").b(0xA2, 0x00)
    a.label("lp").abs(0xFE, CLOCK).abs(0xBD, CLOCK).abs(0xDD, "lim").br(0x90, "go")
    a.b(0xA9, 0x00).abs(0x9D, CLOCK).b(0xE8, 0xE0, 0x03).br(0xD0, "lp").abs(0xEE, CLOCK + 3)
    a.label("go").abs(0x4C, SOUND)
    a.label("lim").b(60, 60, 60)
    return a


def apply(rom: bytearray, notes: list) -> None:
    import lol_entrances
    if not lol_entrances.GEN:
        return
    import lol_v3core as V
    import lol_pictures as P
    import lol_genload as GL
    items = item_table(rom)
    ds, _ = GL.designs()
    names = [display_name(d[2]) for d in ds]
    L = P.LOAD

    def build(org):
        a = build_show(org, rom, names, items, L)
        code = bytearray(a.bytes())
        lab = a.labels
        for tl, th, key, n in (("nlo", "nhi", "nm", len(names)), ("slo", "shi", "s", len(STRINGS))):
            for k in range(n):
                t = lab[f"{key}{k}"]
                code[lab[tl] - org + k], code[lab[th] - org + k] = t & 0xFF, t >> 8
        a.code = code
        a.fix = []
        return a
    show = V.put0(rom, build)
    tick = V.put0(rom, build_tick)
    # the NMI's sound call (bank 7; lol_genload's finish copies it to bank 15)
    patch(rom, 7, NMI_SOUND, bytes([0x20, SOUND & 0xFF, SOUND >> 8]),
          bytes([0x20, tick.labels["tick"] & 0xFF, tick.labels["tick"] >> 8]))
    # the credits' Start: the end screen first
    st = Asm(STUB)
    st.b(*V.far(0, show.labels["show"])).abs(0x4C, 0xEBA3)
    place(rom, 2, STUB, st.bytes())
    patch(rom, 2, CREDITS_START, bytes([0x20, 0xA3, 0xEB]), bytes([0x20, STUB & 0xFF, STUB >> 8]))
    notes.append(f"end screen: {len(show.bytes())} bytes in bank 0 at ${show.labels['show']:04X}; clock at "
                 f"${CLOCK:04X} (tick ${tick.labels['tick']:04X})")
