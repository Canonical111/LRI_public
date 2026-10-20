"""Audit all published coefficients against exact or independently implemented checks."""
from pathlib import Path
import sys,json
from fractions import Fraction as F
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'code'))
from circle_jets import Engine
from analytic_checks import c2,vacuum2,window4

def error(a,b):
    a=np.asarray(a,float);b=np.asarray(b,float)
    return float(np.max(abs(a-b))),float(np.max(abs(a-b)/np.maximum(1,abs(b))))

def main():
    records=[];res=ROOT/'results';maxc2=maxvac=maxwin=0.
    for f in sorted((res/'coefficients').glob('*_d8.json')):
        a=json.loads(f.read_text());L=a['cutoff'];maxc2=max(maxc2,abs(a['C'][2]-float(c2(L))))
        grids=range(0,L+1,2) if a['scheme']!='raw' else [L]
        maxvac=max(maxvac,max(abs(row[2]-float(vacuum2(ell))) for row,ell in zip(a['vacuum_coefficients'],grids)))
        if a['scheme']=='consistent':
            raw=res/f'coefficients/raw_L{L}_d8.json'
            if raw.exists():
                b=json.loads(raw.read_text());maxwin=max(maxwin,abs(a['C'][4]-b['C'][4]-float(window4(L))))
                assert error(a['C'][:4],b['C'][:4])[0]<1e-11
        if a['scheme']=='literal':
            b=json.loads((res/f'coefficients/consistent_L{L}_d8.json').read_text())
            assert error(a['C'][:6],b['C'][:6])[0]<1e-10
        exact=res/f'exact/{a["scheme"]}_L{L}_d8.json'
        if exact.exists():
            b=json.loads(exact.read_text());dif=error(a['C'],[float(F(z)) for z in b['rational_C']])
            records.append(dict(check='exact rational independent coordinates',L=L,scheme=a['scheme'],absolute=dif[0],scaled=dif[1]))
            assert dif[1]<5e-12,dif
    assert maxc2<1e-12 and maxvac<1e-11 and maxwin<1e-10,(maxc2,maxvac,maxwin)
    # All recomputations below are small: no huge reference campaign hidden in tests.
    base=Engine(4,8,'consistent').solve(False)
    for kwargs,label in [({'full_order':True},'ordinary full-order recursion'),({'reflection':False},'unreduced spatial reflection'),({'envelope':False},'unreduced auxiliary angular states'),({'pmax':23},'particle support enlarged 19 to 23'),({'batch':3},'independent vacuum batching')]:
        a=Engine(4,8,'consistent',**kwargs).solve(False);dif=error(a['C'],base['C'])
        records.append(dict(check=label,L=4,absolute=dif[0],scaled=dif[1]));assert dif[1]<5e-12,(label,dif)
    # The saved unreduced full-angle pilots extend to L18.
    for f in sorted((res/'envelope_replays').glob('*.json')):
        a=json.loads(f.read_text());b=json.loads((res/'coefficients'/f.name).read_text());dif=error(a['C'],b['C'])
        records.append(dict(check='saved full vs exact auxiliary envelope',L=a['cutoff'],absolute=dif[0],scaled=dif[1]));assert dif[1]<5e-12
    out=dict(records=records,max_C2_exact_error=maxc2,max_vacuum2_exact_error=maxvac,max_window4_exact_error=maxwin,max_scaled_comparison=max(r['scaled'] for r in records),scope='Implementation tolerances are not physical coefficient errors.')
    (res/'coefficient_validation.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
if __name__=='__main__':main()
