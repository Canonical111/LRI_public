#!/usr/bin/env python3
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
manifest=json.loads((ROOT/'MANIFEST_SHA256.json').read_text())
for name,expected in manifest.items():
 p=Path(name)
 if p.is_absolute() or '..' in p.parts:raise ValueError('Unsafe manifest path')
 if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=expected:raise SystemExit('Integrity failure: '+name)
print(f'{len(manifest)} file checksums verified.')
