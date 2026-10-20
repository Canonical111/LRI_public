#!/usr/bin/env python3
"""Regenerate inputs/ from reference/ into a temporary directory and require byte identity with the shipped tree."""
from __future__ import annotations
import filecmp,json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from prepare_inputs import prepare,verify

def files(d:Path)->set[str]:return {str(p.relative_to(d))for p in d.rglob('*')if p.is_file()and p.name!='.DS_Store'}

def run():
    shipped=ROOT/'inputs';verify(shipped)
    with tempfile.TemporaryDirectory(prefix='c6_inputs_')as td:
        dest=Path(td)/'inputs';dest.mkdir();prepare(dest)
        a,b=files(shipped),files(dest)
        if a!=b:raise AssertionError(f'file sets differ: only shipped {sorted(a-b)[:5]}, only regenerated {sorted(b-a)[:5]}')
        bad=[f for f in sorted(a)if not filecmp.cmp(shipped/f,dest/f,shallow=False)]
        if bad:raise AssertionError(f'{len(bad)} regenerated files differ, e.g. {bad[:5]}')
        m=json.loads((dest/'manifest.json').read_text())
    return {'status':'passed','test':'inputs_regeneration','files':len(a),'sources_recorded':len(m['sources']),'graph_counts':m['graph_counts']}
if __name__=='__main__':print(json.dumps(run(),indent=2))
