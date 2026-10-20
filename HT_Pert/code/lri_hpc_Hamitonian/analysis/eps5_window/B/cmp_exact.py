import json, glob
from fractions import Fraction as F
import numpy as np
for f in sorted(glob.glob('exact5_c*.json')):
    e=json.load(open(f)); c=e['cut4']
    try: o=json.load(open(f'full5_c{c}.json'))
    except FileNotFoundError: continue
    worst=0; n=0
    for v,ev in e['variants'].items():
        fv=o['variants'][v]
        pairs=[('r',ev['r'],fv['r']),('g',ev['g'],fv['g']),('C',ev['C'],fv['C'])]+[(k,ev[k],fv[k]) for k in ('spacing_d1','spacing_d2','spacing_d3')]
        for name,a,b in pairs:
            for k in range(6):
                x=float(F(a[k])); y=b[k]; d=abs(x-y)/max(1,abs(x)); n+=1
                if d>worst: worst=d; wh=(v,name,k,x,y)
    print(f'cut4={c}: {n} numbers, max rel diff float vs exact = {worst:.2e} at {wh}')
