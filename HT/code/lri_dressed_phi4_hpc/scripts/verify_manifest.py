#!/usr/bin/env python3
"""Verify all distributed files; generated extra outputs are allowed."""
import hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
count=0
for line in (ROOT/'MANIFEST.sha256').read_text().splitlines():
    wanted,name=line.split('  ',1)
    p=(ROOT/name).resolve()
    if not p.is_relative_to(ROOT.resolve()):raise SystemExit('Unsafe manifest path')
    if not p.is_file():raise SystemExit('Missing file: '+name)
    got=hashlib.sha256(p.read_bytes()).hexdigest()
    if got!=wanted:raise SystemExit('Checksum mismatch: '+name)
    count+=1
print(f'Verified {count} distributed files.')
