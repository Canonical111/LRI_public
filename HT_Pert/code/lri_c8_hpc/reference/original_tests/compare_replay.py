#!/usr/bin/env python3
import argparse,json
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('directory',type=Path);a=p.parse_args()
files=list(a.directory.glob('*_d8.json'))
if not files:raise ValueError('No degree-eight outputs found')
err=0.
for f in files:
    r=json.loads(f.read_text());base=ROOT/'results'/r['scheme']/f.name
    b=json.loads(base.read_text())
    for key in ('C','r','g'):
        np.testing.assert_allclose(r[key],b[key],rtol=5e-11,atol=1e-7)
        err=max(err,float(np.max(abs(np.array(r[key])-b[key]))))
print(f'{len(files)} point replays pass; max absolute coefficient difference {err:.6g}')
