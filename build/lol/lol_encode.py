"""Legend of Link: Race Rom (the page's toggle, LOL_RACE=1; owner, 2026-11-25): the level data encoded, so ROM viewers and map tools (the Z1R visualizer)
can't read a seed's overworld, dungeons, caves and shops from the patched ROM. Gameplay is the same.

Encoded: bank 6 $8400-$9CD7 (the five level blocks - overworld, the dungeons' two first-quest and two second-quest
blocks - and the ten level infos), every byte XORed with a 64-byte key at ((hi << 3) ^ lo) & $3F of its address.
The key is a hash of the plain data (the same seed: the same patch). The game only ever reads those bytes through
CopyBlock (bank 6 $80D7, as it loads a level into WRAM), whose LDA ($00),Y / STA ($02),Y becomes JSR dec: a source
in that range is decoded on the way. Not cheat-proof: the decoder is in the ROM (and this file).

Last step of lol_build (after the seed code, which is of the plain ROM and marked as a Race Rom's: its own code).
Off by default (spoiler-log seeds stay plain)."""
import hashlib
import os
from lol_af import Asm, BANK, patch

LO, HI = 0x8400, 0x9CD8                 # bank 6: the encoded range [LO, HI)
COPY = 0x80D7                           # CopyBlock
KEY_AT = 45                             # (dec's code length: the key follows)
DOMAIN = b"Legend of Link level key\x00"


def _idx(cpu):
    return ((cpu >> 8 << 3) ^ cpu) & 0x3F


def _key(data):
    return hashlib.sha256(DOMAIN + data).digest() + hashlib.sha256(DOMAIN + b"2" + data).digest()


def xor(rom, key):
    base = BANK(6) - 0x8000
    for cpu in range(LO, HI):
        rom[base + cpu] ^= key[_idx(cpu)]


def apply(rom: bytearray, notes: list) -> None:
    if os.environ.get("LOL_RACE") != "1":
        return
    from lol_newups import free_in
    base = BANK(6) - 0x8000
    key = _key(bytes(rom[base + LO:base + HI]))

    def dec(o):
        a = Asm(o)
        a.label("dec").b(0xA5, 0x01, 0xC9, LO >> 8).br(0x90, "pl").b(0xC9, HI >> 8).br(0x90, "en").br(0xD0, "pl")
        a.b(0xA5, 0x00, 0xC9, HI & 0xFF).br(0xB0, "pl")
        a.label("en").b(0x8A, 0x48, 0xA5, 0x01, 0x0A, 0x0A, 0x0A, 0x45, 0x00, 0x29, 0x3F, 0xAA)
        a.b(0xB1, 0x00).abs(0x5D, "key").b(0x91, 0x02, 0x68, 0xAA, 0x60)
        a.label("pl").b(0xB1, 0x00, 0x91, 0x02, 0x60)
        a.label("key").b(*key)
        return a
    n = len(dec(0xA000).bytes())
    at = free_in(rom, 6, n, 0xA000, 0xBE00)
    d = dec(at)
    assert d.labels["key"] - at == KEY_AT
    assert not (LO <= at < HI)
    rom[base + at:base + at + n] = d.bytes()
    patch(rom, 6, COPY, bytes.fromhex("a000b1009102"), bytes([0xA0, 0x00, 0x20, at & 0xFF, at >> 8, 0xEA]))
    xor(rom, key)
    notes.append(f"level data: encoded (bank 6 ${LO:04X}-${HI - 1:04X}; decoder ${at:04X}, {n} bytes)")


def decode(rom: bytes) -> bytes:
    """A finished ROM's level data, plain again (tests; a no-op on a plain ROM)."""
    rom = bytearray(rom)
    base = BANK(6) - 0x8000
    if rom[base + COPY + 2] != 0x20:
        return bytes(rom)
    at = rom[base + COPY + 3] | rom[base + COPY + 4] << 8
    k = base + at + KEY_AT              # (dec's code, then the key)
    xor(rom, bytes(rom[k:k + 64]))
    return bytes(rom)
