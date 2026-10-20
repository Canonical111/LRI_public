#!/usr/bin/env python3
from pathlib import Path
import json,hashlib
root=Path(__file__).resolve().parents[1]
m=json.loads((root/'MANIFEST_SHA256.json').read_text())
for relative,sha in m.items():
 p=root/relative
 if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=sha:raise SystemExit('Mismatch: '+relative)
print(f'{len(m)} manifest-listed files verified')
