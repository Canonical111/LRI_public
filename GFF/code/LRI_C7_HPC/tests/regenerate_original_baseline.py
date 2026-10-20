#!/usr/bin/env python3
"""Regenerate tests/fixtures/assemble_original_0227dc5.json from the tools at commit 0227dc5 (needs git history).
The pipeline suite compares `assemble.py --original` against this fixture without Git."""
import subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as td:
    subprocess.run(f'git -C "{ROOT}" archive 0227dc5 | tar -x -C "{td}"',shell=True,check=True)
    out=Path(td)/'orig.json';subprocess.run([sys.executable,str(Path(td)/'tools/assemble.py'),'--original','--output',str(out)],check=True)
    dest=ROOT/'tests/fixtures/assemble_original_0227dc5.json'
    if dest.exists() and dest.read_bytes()!=out.read_bytes():sys.exit('regenerated baseline differs from the committed fixture')
    dest.write_bytes(out.read_bytes());print('baseline fixture:',dest)
