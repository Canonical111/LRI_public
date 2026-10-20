#!/usr/bin/env python3
from pathlib import Path
import hashlib
ROOT=Path(__file__).resolve().parents[1]
n=0
for line in (ROOT/'MANIFEST.sha256').read_text().splitlines():
    digest,name=line.split('  ',1);p=ROOT/name
    assert p.is_file(),f'Missing {name}'
    assert hashlib.sha256(p.read_bytes()).hexdigest()==digest,f'Changed {name}'
    n+=1
print(f'Verified {n} files.')
