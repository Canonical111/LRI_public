#!/usr/bin/env python3
"""Write or verify SHA256SUMS_HPC.json: a flat {path: sha256} map of every package file except itself.

Files are the git-tracked files when a .git directory is present, otherwise every file except build outputs and
caches (bin/c6_integrate, __pycache__, *.pyc, .venv/, runs/, .DS_Store). Paths are sorted in C (byte) order.
verify exits non-zero when a listed file is missing or changed; unlisted files are reported (an error with --strict).
"""
from __future__ import annotations
import argparse,json,subprocess,sys
from pathlib import Path
from common import ROOT,digest,publish
NAME='SHA256SUMS_HPC.json'
SKIP_DIRS={'.git','__pycache__','.venv','runs'}

def package_files()->list[str]:
    if (ROOT/'.git').exists():
        out=subprocess.run(['git','-C',str(ROOT),'ls-files','-z'],capture_output=True,check=True).stdout.decode().split('\0')
        names=[f for f in out if f and f!=NAME and (ROOT/f).is_file()]
    else:
        names=[str(p.relative_to(ROOT))for p in ROOT.rglob('*')if p.is_file()and not SKIP_DIRS.intersection(p.relative_to(ROOT).parts)
               and p.name not in (NAME,'.DS_Store')and p.suffix!='.pyc'and str(p.relative_to(ROOT))!='bin/c6_integrate']
    return sorted(names,key=lambda s:s.encode())

def write():
    sums={f:digest(ROOT/f)for f in package_files()};target=ROOT/NAME
    text=json.dumps(sums,indent=2)+'\n'
    if target.exists():target.unlink()
    publish(target,text);print(f'{NAME}: {len(sums)} files')

def verify(strict:bool)->int:
    listed=json.loads((ROOT/NAME).read_text());present=set(package_files())
    missing=[f for f in listed if not (ROOT/f).is_file()];changed=[f for f in listed if (ROOT/f).is_file()and digest(ROOT/f)!=listed[f]]
    extra=sorted(present-set(listed))
    for label,items in (('missing',missing),('changed',changed),('unlisted',extra)):
        for f in items[:50]:print(f'{label}: {f}')
        if len(items)>50:print(f'{label}: ... {len(items)-50} more')
    print(f'{len(listed)} listed, {len(missing)} missing, {len(changed)} changed, {len(extra)} unlisted')
    return 1 if missing or changed or (strict and extra) else 0

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['write','verify']);p.add_argument('--strict',action='store_true');a=p.parse_args()
    if a.command=='write':write()
    else:sys.exit(verify(a.strict))
