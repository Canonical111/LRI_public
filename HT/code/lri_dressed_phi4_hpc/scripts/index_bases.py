#!/usr/bin/env python3
"""Freeze an exact per-delta index of accepted basis artifacts. Never overwrites."""
import argparse
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from lri_dressed.io import atomic_json,claim,digest
from lri_dressed.local_basis import load_basis

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--files',nargs='+',required=True)
    p.add_argument('--output',required=True)
    a=p.parse_args();entries=[];seen=set()
    for name in a.files:
        path=Path(name).resolve();rec=load_basis(path)
        delta=rec['config']['delta']
        if delta in seen:raise ValueError(f'Duplicate delta {delta}; select one explicit basis per delta')
        seen.add(delta);entries.append({'delta':delta,'path':str(path),'sha256':rec['sha256']})
    out=Path(a.output).resolve()
    row={'schema':'lri-dressed-basis-index-v1','entries':sorted(entries,key=lambda r:r['delta'],reverse=True)}
    row['sha256']=digest(row)
    with claim(out.with_name(out.name+'.lock')):
        if out.exists():raise FileExistsError('Index exists: use a new versioned path')
        atomic_json(out,row)
    print(f'Frozen {len(entries)} basis artifacts in {out}')

if __name__=='__main__':main()
