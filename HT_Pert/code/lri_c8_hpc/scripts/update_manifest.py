#!/usr/bin/env python3
"""Regenerate MANIFEST_SHA256.json from the files tracked by git (the manifest itself excluded)."""
from pathlib import Path
import hashlib,json,subprocess
root=Path(__file__).resolve().parents[1]
files=subprocess.run(['git','ls-files','-z'],cwd=root,check=True,capture_output=True).stdout.decode().split('\0')
files=sorted(f for f in files if f and f!='MANIFEST_SHA256.json')
m={f:hashlib.sha256((root/f).read_bytes()).hexdigest() for f in files}
(root/'MANIFEST_SHA256.json').write_text(json.dumps(m,indent=2,sort_keys=True)+'\n')
print(f'{len(m)} files listed')
