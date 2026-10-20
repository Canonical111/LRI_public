"""Lower-moment singular jet of the squared-charge response.
Only negative cutoff powers are used. The vacuum-normalized connected
current has no power divergence in this matched prescription; hence these
coefficients follow from Q4 Z2 - Q2 Z2^2 + Q2 Z4. No finite six-kink
coefficient or C8 ansatz enters.
"""
from pathlib import Path
from fractions import Fraction as Q
from itertools import product
import json,time
import sympy as s
import derive_divergence_controls as dc
import boundary_log_controls as bl
ROOT=Path(__file__).resolve().parent.parent
L=dc.L;dc.DER[(2,0)]='vv'
old=json.loads((ROOT/'lower_divergence_prediction.json').read_text())
table=old['lower_rational_polynomials'].copy()

def lookup(n,k,iv,p):
    key=f'{k}{n}_{dc.DER[iv,0]}_p{p}'
    if key in table:return s.sympify(table[key],locals={'ell':L})
    ex=dc.raw(n,k,iv,0,p);table[key]=str(ex);return ex

def main():
    st=time.time();terms=[(1,[(4,'Q'),(2,'Z')]),(-1,[(2,'Q'),(2,'Z'),(2,'Z')]),(1,[(2,'Q'),(4,'Z')])];M={}
    for p in (-2,-1):
        out=0
        for sign,factors in terms:
            for i in range(len(factors)):
                for j in range(len(factors)):
                    for powers in product(*(dc.POWERS[f] for f in factors)):
                        if sum(powers)!=p:continue
                        term=s.Integer(sign)
                        for k,((n,kind),power) in enumerate(zip(factors,powers)):term*=lookup(n,kind,int(i==k)+int(j==k),power)
                        out+=term
        M[p]=s.expand(out)
    controls=json.loads((ROOT/'boundary_control_logjets.json').read_text());B={}
    for tag in ('base','v','d'):
        B[tag]={p:s.S.Zero for p in (-2,-1)}
        for face in (1,2,3):
            row=next(x for x in controls if x['source']==f'B6_{tag}_f{face}_stage3.jsonl')
            for (p,m),v in zip(row['demands'],row['values']):B[tag][p]+=(2 if face<3 else 1)*s.Rational(v)*L**m
    result=[]
    for p in (-2,-1):
        Bphys=s.expand(-p*M[p]-s.diff(M[p],L))
        Bdim=s.expand(Bphys+12*L*B['v'][p]-36*L**2*B['base'][p])
        corr=s.expand(L*(B['v'][p]+Bdim-6*B['d'][p])+L**2*(-3*B['base'][p]-9*B['v'][p])+18*L**3*B['base'][p])
        co=[Q(str(corr.coeff(L,j))) for j in range(bl.MAXLOG+1)];invcorr=bl.inverse_euler(co,p)
        expected=s.sympify(next(x['polynomial'] for x in old['prediction'] if x['power']==p),locals={'ell':L})
        target=[Q(str(expected.coeff(L,j)))-invcorr[j] for j in (0,1)]
        result.append({'power':p,'Q6_vv_singular_polynomial':str(M[p]),'Bvv_physical':str(Bphys),'Bvv_dimensionless':str(Bdim),'scale_correction_to_mixed_B':str(corr),'scale_correction_to_mixed_volume':list(map(str,invcorr)),'expected_dimensionless_mixed_moments':list(map(str,target))})
    report={'method':'exact lower-moment singular factorization, independent of the new mixed six-kink integral','projection':'weight zero','derivative':'v^2','entries':result,'lower_inputs':table,'seconds':time.time()-st,'C8_conjecture_used':False}
    (ROOT/'vv_singular_control.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='lower_inputs'},indent=2))
if __name__=='__main__':main()
