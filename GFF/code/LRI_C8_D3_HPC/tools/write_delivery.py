#!/usr/bin/env python3
"""Regenerate DELIVERY_MANIFEST.json and SHA256SUMS (schema lri-c8-d3-hpc-delivery-1): kept for the C7(3) command name;
it runs `tools/verify_delivery.py --write` (C62d's form, ported in Stage 3a): every git-tracked payload file as it is on
disk, after `git add -A`; a tracked symlink is refused (R16); build outputs and caches stay excluded."""
from __future__ import annotations
import argparse,json,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import verify_delivery

if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);a=a.parse_args()
    try:r=verify_delivery.write(a.root)
    except (OSError,ValueError,subprocess.CalledProcessError)as e:r={'status':'failed','errors':[str(e)]}
    print(json.dumps(r,indent=2));sys.exit(0 if r['status']=='written'else 1)
