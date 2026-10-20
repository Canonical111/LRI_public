#!/usr/bin/env python3
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
m=json.loads((ROOT/'MANIFEST_SHA256.json').read_text())
for rel,sha in m.items():
    p=ROOT/rel
    if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=sha:
        raise RuntimeError('Integrity check failed: '+rel)
print(f'All {len(m)} packaged files match SHA-256 manifest.')
