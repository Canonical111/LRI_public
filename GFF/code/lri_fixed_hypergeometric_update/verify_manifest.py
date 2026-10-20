#!/usr/bin/env python3
"""Check the bytes supplied with this revision; no third-party dependencies."""
from pathlib import Path
import hashlib,json,sys
root=Path(__file__).resolve().parent
path=root/'sha256_manifest.json'
if not path.exists():raise SystemExit('sha256_manifest.json is missing')
records=json.loads(path.read_text());bad=[]
for rec in records:
    p=root/rec['path']
    if not p.is_file()or p.stat().st_size!=rec['bytes']or hashlib.sha256(p.read_bytes()).hexdigest()!=rec['sha256']:
        bad.append(rec['path'])
if bad:
    print('Changed or missing files:\n'+'\n'.join(bad));sys.exit(1)
print('Verified',len(records),'delivered files.')
