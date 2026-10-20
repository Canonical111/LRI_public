#!/usr/bin/env python3
"""Rewrite MANIFEST.sha256 over every git-tracked file (except itself). Run before committing a release."""
from pathlib import Path
import hashlib,subprocess
ROOT=Path(__file__).resolve().parents[1]
names=sorted(n for n in subprocess.run(['git','-C',str(ROOT),'ls-files','-z'],check=True,capture_output=True).stdout.decode().split('\0') if n and n!='MANIFEST.sha256')
missing=[n for n in names if not (ROOT/n).is_file()]
if missing:raise SystemExit('tracked but missing: '+' '.join(missing))
(ROOT/'MANIFEST.sha256').write_text(''.join(f'{hashlib.sha256((ROOT/n).read_bytes()).hexdigest()}  {n}\n' for n in names))
print(f'{len(names)} files')
