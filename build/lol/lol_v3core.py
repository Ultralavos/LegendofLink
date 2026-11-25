"""Legend of Link v3.0: room in the fixed bank, one far call, and code that lives in one bank.

Stage 2 (apply_early, run before every other module):
1. The object jump tables leave bank 7. UpdateObject ($FBB1) and InitObject ($FD7F) end in JSR TableJump followed by
   their tables (106 and 95 entries). Both run with bank 4 in (UpdateObject switches to it first; InitObject is only
   reached from there), so the JSR and its table move to bank 4 ($B5D0) and bank 7 keeps a JMP: 402 bytes freed.
2. FAR, in the freed space: JSR FAR / .byte bank, back / .word routine calls the routine in that bank, then switches
   to `back` ($FF: no switch back - a caller in bank 7 or WRAM that switches itself; $FE: back to the bank that was
   in, read from its ID byte at $BFF9). A, X and Y go in as they were; A and the flags come back from the routine;
   X and Y as the routine leaves them; $00/$01 are kept. Nested far calls work (`back` rides on the stack).
   (Tracking the current bank in SwitchBank was tried and dropped: every switch got slower.)
3. ID: every switchable bank 0-6 has its number at $BFF9 (free in all of them), so `back` $FE needs no tracking.

Stage 3: code that was copied into banks 0-6 (so it ran whatever bank was in) moves to one bank. Its body goes in
bank 0 (alloc0) and a far call reaches it: from bank 7 through a short stub there (alloc7), from code that runs in
any bank (WRAM) through a stub left in the common area. Code only ever reached from one bank stays in that bank.

apply (late): the odds trampoline (lol_odds TRAMP, bank 7) becomes a far call to the engine, now in bank 3."""
from lol_af import Asm, BANK

SWITCH = 0xFFAC
TABLE_JUMP = 0xE5E2
U_AT, U_N = 0xFBB1, 0x6A                   # UpdateObject's JSR TableJump and its table
I_AT, I_N = 0xFD7F, 0x5F                   # InitObject's
F_A, F_X, F_Y, F_B, F_V, F_P, F_R = 0x01A8, 0x01A9, 0x01AA, 0x01AB, 0x01AC, 0x01AE, 0x01AF   # (stack page)
TABLES4 = 0xB5D0                           # bank 4 (free)
FAR = U_AT + 3                             # bank 7 $FBB4
HERE = 0xFE                                # FAR's `back`: the bank that was in
BANK_ID = 0xBFF9                           # in banks 0-6
_free7 = []                                # bank 7's free runs [first, end) after apply_early
_free0 = [[0x8000, 0x8D60], [0xA000, 0xBB80],   # bank 0 (verified free runs; $BBA0- is the common area)
           [0xBC10, 0xBC80], [0xBD30, 0xBD8C]]   # (2026-11-25: free in every finished ROM, used by no other bank's
                                                 #  copies at these addresses in bank 0)
used0 = 0
used7 = 0


def b7(cpu):
    return BANK(7) + cpu - 0xC000


def far(bank, routine, back=HERE):
    """JSR FAR / .byte bank, back / .word routine (7 bytes)."""
    return bytes([0x20, FAR & 0xFF, FAR >> 8, bank, back, routine & 0xFF, routine >> 8])


def _alloc(free, n):
    for r in free:
        if r[1] - r[0] >= n:
            at = r[0]
            r[0] += n
            return at
    raise AssertionError(f"no {n} free bytes")


def alloc0(n):
    global used0
    used0 += n
    return _alloc(_free0, n)


def alloc7(n):
    global used7
    used7 += n
    return _alloc(_free7, n)


def put0(rom, build):
    """build(org) -> Asm; placed in bank 0. Returns the Asm."""
    n = len(build(0x8000).bytes())
    at = alloc0(n)
    a = build(at)
    off = BANK(0) + at - 0x8000
    assert all(x == 0xFF for x in rom[off:off + n]), hex(at)
    rom[off:off + n] = a.bytes()
    return a


def put7(rom, build):
    n = len(build(0xC000).bytes())
    at = alloc7(n)
    a = build(at)
    assert all(x == 0xFF for x in rom[b7(at):b7(at) + n]), hex(at)
    rom[b7(at):b7(at) + n] = a.bytes()
    return a


def apply_early(rom: bytearray, notes: list) -> None:
    # 1. the tables to bank 4
    moved = []
    for at, n in ((U_AT, U_N), (I_AT, I_N)):
        assert rom[b7(at):b7(at) + 3] == bytes([0x20, TABLE_JUMP & 0xFF, TABLE_JUMP >> 8])
        moved.append(bytes(rom[b7(at):b7(at) + 3 + 2 * n]))
    size = sum(len(m) for m in moved)
    base4 = BANK(4) - 0x8000
    assert all(x == 0xFF for x in rom[base4 + TABLES4:base4 + TABLES4 + size + 2])
    at4 = TABLES4
    for (at, n), m in zip(((U_AT, U_N), (I_AT, I_N)), moved):
        rom[base4 + at4:base4 + at4 + len(m)] = m
        rom[b7(at):b7(at) + 3] = bytes([0x4C, at4 & 0xFF, at4 >> 8])
        rom[b7(at) + 3:b7(at) + 3 + 2 * n] = b"\xFF" * (2 * n)
        at4 += len(m)
    # 2. FAR in the freed space (UpdateObject's old table)
    a = Asm(FAR)
    a.label("far").abs(0x8D, F_A).abs(0x8E, F_X).abs(0x8C, F_Y)
    a.b(0xA5, 0x00, 0x48, 0xA5, 0x01, 0x48, 0xBA)
    a.abs(0xBD, 0x0103).b(0x85, 0x00).abs(0xBD, 0x0104).b(0x85, 0x01)
    a.b(0xA0, 0x01, 0xB1, 0x00).abs(0x8D, F_B).b(0xC8, 0xB1, 0x00).abs(0x8D, F_R)
    a.b(0xC9, HERE).br(0xD0, "f_k").abs(0xAD, BANK_ID).abs(0x8D, F_R)          # $FE: the bank that's in
    a.label("f_k").b(0xC8, 0xB1, 0x00).abs(0x8D, F_V).b(0xC8, 0xB1, 0x00).abs(0x8D, F_V + 1)
    a.abs(0xBD, 0x0103).b(0x18, 0x69, 0x04).abs(0x9D, 0x0103).br(0x90, "f_nc").abs(0xFE, 0x0104)
    a.label("f_nc").b(0x68, 0x85, 0x01, 0x68, 0x85, 0x00)
    a.abs(0xAD, F_R).b(0x48).abs(0xAD, F_B).abs(0x20, SWITCH)
    a.abs(0xAD, F_A).abs(0xAE, F_X).abs(0xAC, F_Y).abs(0x20, "fj")
    a.b(0x08).abs(0x8D, F_A).b(0x68).abs(0x8D, F_P).b(0x68).b(0x30, 0x03).abs(0x20, SWITCH)   # (BMI: $FF stays)
    a.abs(0xAD, F_P).b(0x48).abs(0xAD, F_A).b(0x28, 0x60)
    a.label("fj").abs(0x6C, F_V)
    code = a.bytes()
    assert len(code) <= 2 * U_N, len(code)
    rom[b7(FAR):b7(FAR) + len(code)] = code
    assert a.labels["far"] == FAR
    _free7[:] = [[FAR + len(code), U_AT + 3 + 2 * U_N], [I_AT + 3, I_AT + 3 + 2 * I_N]]
    # 3. the bank IDs
    for bank in range(7):
        at = BANK(bank) + BANK_ID - 0x8000
        assert rom[at] == 0xFF, bank
        rom[at] = bank
    notes.append(f"v3 core: object tables in bank 4 at ${TABLES4:04X} ({size} bytes); FAR at ${FAR:04X} "
                 f"({len(code)} bytes); bank IDs at ${BANK_ID:04X}")


def apply(rom: bytearray, notes: list) -> None:
    global used7
    # the odds trampoline: a far call to the engine (its caller's RET as before)
    import lol_odds as O
    t = bytes([0xA9, O.ENGINE_BANK, 0x20, 0xAC, 0xFF, 0x20, O.ENGINE & 0xFF, O.ENGINE >> 8, 0xAD, O.RET & 0xFF,
               O.RET >> 8, 0x4C, 0xAC, 0xFF])
    assert rom[b7(O.TRAMP):b7(O.TRAMP) + len(t)] == t
    nt = far(O.ENGINE_BANK, O.ENGINE, 0xFF) + bytes([0xAD, O.RET & 0xFF, O.RET >> 8, 0x4C, 0xAC, 0xFF])
    rom[b7(O.TRAMP):b7(O.TRAMP) + len(t)] = nt + b"\xFF" * (len(t) - len(nt))
    left7 = sum(e - s for s, e in _free7) + len(t) - len(nt)
    left0 = sum(e - s for s, e in _free0)
    notes.append(f"v3: bank 0 holds {used0} bytes of moved code ({left0} left in its first run), bank 7 {used7} of "
                 f"stubs ({left7} left)")
