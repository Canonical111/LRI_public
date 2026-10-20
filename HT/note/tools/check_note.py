#!/usr/bin/env python3
"""Check the HT note: (1) numbers_d1.tex and sections/repro_d1.tex are up to date with data/quoted_numbers_d1.json;
(2) data/quoted_numbers_d1.json equals ../results/HT_1d/quoted_numbers.json and the d = 1 table fragments equal
../results/HT_1d/note_tables/* when run inside the public tree (HT/note); (3) every file listed in MANIFEST.json has its
sha256 (--checksums). Exit 1 on any failure."""
import hashlib, json, subprocess, sys
from pathlib import Path
H = Path(__file__).resolve().parents[1]; bad = []
for cmd in (['tools/gen_numbers_d1.py', '--check'],):
    if subprocess.run([sys.executable, *cmd], cwd=H).returncode: bad.append(' '.join(cmd))
import importlib.util
old = (H / 'sections/repro_d1.tex').read_text()
if subprocess.run([sys.executable, 'tools/gen_repro_d1.py'], cwd=H, capture_output=True).returncode: bad.append('tools/gen_repro_d1.py failed')
if (H / 'sections/repro_d1.tex').read_text() != old: bad.append('sections/repro_d1.tex was stale (regenerated)')
R = H.parent / 'results/HT_1d'
if R.exists():
    if (R / 'quoted_numbers.json').read_bytes() != (H / 'data/quoted_numbers_d1.json').read_bytes(): bad.append('quoted_numbers differ from results/HT_1d')
    for f in ('tab_d1_ident.tex', 'tab_d1_omegaeff.tex'):
        if (R / 'note_tables' / f).read_bytes() != (H / 'sections' / f).read_bytes(): bad.append(f + ' differs from results/HT_1d/note_tables')
    print('compared with', R)
if '--checksums' in sys.argv and (H / 'MANIFEST.json').exists():
    for name, sha in json.loads((H / 'MANIFEST.json').read_text())['files'].items():
        p = H / name
        if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest() != sha: bad.append('checksum ' + name)
print('FAIL: ' + '; '.join(bad) if bad else 'note checks passed'); sys.exit(1 if bad else 0)
