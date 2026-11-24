"""Legend of Link: the overworld's item screen shows the bought upgrades left of the triforce (two columns, in the
order beams, boomstick, regen, bubble ring, sword +1, fairy) and the badges right of it (S, D, X: the icon and
"x1".."x3"; only those Link has, packed).

Bank 5's UpdateMenuActive (JSR DrawSubmenuItems at $80D4) becomes JSR here: DrawSubmenuItems, then in the
overworld the icons as sprites (each through AnimateItemObject past its position fetch, bank 7 $E71C, so the new
items' pictures and palettes apply), and on even frames the counts as background tiles in the item screen's
nametable (the status bar's XP code uses the tile buffer on odd frames)."""
from lol_af import Asm, place, patch

CODE = 0xB9B4                           # bank 5 free (PRG1 $B9B3-$BB9F)
HOOK = 0x80D4                           # JSR DrawSubmenuItems
DRAW_SUBMENU = 0xB6A7
ITEM_AT = 0xE71C                        # bank 7: AnimateItemObject's PLA (item id), with [00] X / [01] Y set
UPGRADES, BADGES = 0x066B, 0x0673
import lol_uptable as T
BADGE_ITEMS = (0x26, 0x27, 0x28)
CNT, IDX, NUM = 0x0179, 0x017A, 0x017B  # (stack page, unused)
COUNTS = 0x017C                          # 3 bytes: each badge row's count
ROWS = (21, 24, 27)                     # the item screen's nametable rows of the three icon rows
NT = 0x2800                             # the item screen's nametable
SCROLL = 62                             # nametable y - screen y while the item screen is open
UP_X = (0x10, 0x28)
BADGE_X, TEXT_COL = 0xC0, 26


def sprite_y(row):
    return row * 8 - SCROLL - 1


def apply(rom: bytearray, notes: list) -> None:
    global CODE
    n = len(_build(rom, CODE).bytes())
    from lol_newups import free_in
    CODE = free_in(rom, 5, n, 0xB9B4, 0xBBA0)
    a = _build(rom, CODE)
    code = a.bytes()
    assert CODE + len(code) <= 0xBBA0
    place(rom, 5, CODE, code)
    s = a.labels["sub"]
    patch(rom, 5, HOOK, bytes([0x20, DRAW_SUBMENU & 0xFF, DRAW_SUBMENU >> 8]), bytes([0x20, s & 0xFF, s >> 8]))
    notes.append(f"item screen: upgrades and badges ({len(code)} bytes in bank 5 at ${CODE:04X})")


def _build(rom, org):
    a = Asm(org)
    a.label("draw").b(0x48).abs(0x4C, ITEM_AT)                                   # PHA / JMP (item in A)
    a.label("sub").abs(0x20, DRAW_SUBMENU).b(0xA5, 0x10).br(0xF0, "ow").b(0x60)
    # the owned upgrades: the owned slots' codes ($2B..), as many as lol_pictures filled (OWN_N)
    a.label("ow").b(0xA2, 0x00)
    a.label("u_lp").abs(0xEC, T.OWN_N).br(0xB0, "u_end")
    a.abs(0xBD, "ux").b(0x85, 0x00).abs(0xBD, "uy").b(0x85, 0x01).abs(0x8E, IDX)
    a.b(0x8A, 0x18, 0x69, T.OWNED_CODES[0]).abs(0x20, "draw").abs(0xAE, IDX).b(0xE8).br(0xD0, "u_lp")
    a.label("u_end")
    # badges
    a.b(0xA9, 0x00).abs(0x8D, CNT).abs(0x8D, COUNTS).abs(0x8D, COUNTS + 1).abs(0x8D, COUNTS + 2).b(0xA2, 0x00)
    a.label("b_lp").abs(0xAD, BADGES).b(0xE0, 0x00).br(0xF0, "b_sh0").b(0x4A, 0x4A, 0xE0, 0x01).br(0xF0, "b_sh0")
    a.b(0x4A, 0x4A)
    a.label("b_sh0").b(0x29, 0x03).br(0xF0, "b_nx")
    a.abs(0xAC, CNT).abs(0x99, COUNTS).abs(0x8E, IDX)
    a.b(0xA9, BADGE_X, 0x85, 0x00).abs(0xB9, "by").b(0x85, 0x01)
    a.abs(0xBD, "bitems").abs(0x20, "draw").abs(0xEE, CNT).abs(0xAE, IDX)
    a.label("b_nx").b(0xE8, 0xE0, 0x03).br(0xD0, "b_lp")
    # the counts (even frames): three records "x1" / blanks, then the end
    a.b(0xA5, 0x15, 0x4A).br(0x90, "t_go").b(0x60)
    a.label("t_go").b(0xA2, 0x00, 0xA0, 0x00)
    a.label("t_lp").abs(0xBD, "thi").abs(0x99, 0x0302).abs(0xBD, "tlo").abs(0x99, 0x0303)
    a.b(0xA9, 0x02).abs(0x99, 0x0304)
    a.abs(0xBD, COUNTS).br(0xF0, "t_blank").abs(0x99, 0x0306).b(0xA9, 0x21)    # "x" and the digit
    a.abs(0x99, 0x0305).br(0xD0, "t_nx")
    a.label("t_blank").b(0xA9, 0x24).abs(0x99, 0x0305).abs(0x99, 0x0306)
    a.label("t_nx").b(0x98, 0x18, 0x69, 0x05, 0xA8, 0xE8, 0xE0, 0x03).br(0xD0, "t_lp")
    a.b(0xA9, 0xFF).abs(0x99, 0x0302).b(0x60)
    a.label("bitems").b(*BADGE_ITEMS)
    a.label("ux").b(*[UP_X[0] + 0x0C] * 3)                          # (at most three: one a row, beside the badges)
    a.label("uy").b(*[sprite_y(ROWS[k]) for k in range(3)])
    a.label("by").b(*[sprite_y(r) for r in ROWS])
    addrs = [NT + (r + 1) * 32 + TEXT_COL for r in ROWS]
    a.label("thi").b(*[x >> 8 for x in addrs])
    a.label("tlo").b(*[x & 0xFF for x in addrs])
    return a
