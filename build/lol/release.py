"""python3 release.py V : LegendOfLink-vV (e.g. 2.01)-PRG1.ips and -PRG0.ips from t.nes (each checked)."""
import sys; sys.path.insert(0, '.')
from lol_build import make_ips
O = '/tmp/claude-0/-home-claude/031e4a9a-d5c6-5d71-8dc5-d25126757d5f/scratchpad/out/'
A = '/mnt/user-data/attachments/031e4a9a-d5c6-5d71-8dc5-d25126757d5f/'
t = open('t.nes', 'rb').read()
for tag, src in (('PRG1', '011232c8-Legend_of_Zelda_The_U_PRG1.nes'), ('PRG0', '4a047cfe-Legend_of_Zelda_The_USA.nes')):
    base = open(A + src, 'rb').read()
    ips = make_ips(base, t); open(O + f'LegendOfLink-v{sys.argv[1]}-{tag}.ips', 'wb').write(ips)
    r = bytearray(base) + bytearray(len(t) - len(base)); i = 5
    while ips[i:i + 3] != b'EOF':
        o = int.from_bytes(ips[i:i + 3], 'big'); n = int.from_bytes(ips[i + 3:i + 5], 'big'); i += 5
        r[o:o + n] = ips[i:i + n]; i += n
    assert bytes(r) == t, tag
    print(tag, len(ips), 'ok')
