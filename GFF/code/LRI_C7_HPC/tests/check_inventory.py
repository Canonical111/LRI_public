#!/usr/bin/env python3
"""Validate all retained graph rows against the optimized sparse representation."""
import json,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1];report=[]
for L in range(2,8):
    f=(root/f'reference/inputs/L{L}_coord.txt').open();ll,ng=map(int,f.readline().split());assert ll==L
    ntot=0;ne=L*(L+1)//2;emax=0
    for gi in range(ng):
        a=f.readline().split();assert int(a[0])==gi;nt=int(a[-1])
        for _ in range(nt):
            a=list(map(int,f.readline().split()));assert len(a)==ne+1;key=a[0];assert key<2**(2*ne)
            ms=[(key>>(2*i))&3 for i in range(ne)]
            assert sum(ms)==2*L
            assert all(m or co==0 for m,co in zip(ms,a[1:]))
            emax=max(emax,max(abs(v) for v in a[1:]));ntot+=1
    assert not f.read().strip();report.append(dict(L=L,graphs=ng,forest_terms=ntot,max_abs_numerator_coefficient=emax))
Path(sys.argv[1]).write_text(json.dumps({'passed':True,'all_graphs_checked':sum(r['graphs'] for r in report),'all_forest_terms_checked':sum(r['forest_terms'] for r in report),'loops':report},indent=2)+'\n')
