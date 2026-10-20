#!/usr/bin/env python3
"""Check the shipped note (Resummation/note): MANIFEST.json sha256 of every listed file (when present), every figure
the TeX includes exists, and the files listed in MANIFEST.json (added at export).
Usage: python3 note/tools/check_note.py   (from Resummation/) or python3 tools/check_note.py (from note/)."""
import hashlib, json, re, sys
from pathlib import Path

NOTE = Path(__file__).resolve().parent.parent
bad = []
tex = (NOTE/'lri_resummation.tex').read_text()
figs = [f for f in re.findall(r'(?:\\widefig|\\includegraphics)(?:\[[^\]]*\])?\{([^}]+)\}', tex) if not f.startswith('#')]
for f in figs:
    if not (NOTE/'figures'/f).exists() and not (NOTE/f).exists():
        bad.append('missing figure ' + f)
man = NOTE/'MANIFEST.json'
n = 0
if man.exists():
    m = json.loads(man.read_text())
    files = m.get('files', m)
    items = files.items() if isinstance(files, dict) else [(e['path'], e['sha256']) for e in files]
    for rel, h in items:
        h = h['sha256'] if isinstance(h, dict) else h
        p = NOTE/rel
        n += 1
        if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest() != h:
            bad.append('sha256 ' + rel)
print('note: %d figures checked, %d manifest entries checked, %d problems' % (len(figs), n, len(bad)))
for b in bad:
    print('  ', b)
sys.exit(1 if bad else 0)
