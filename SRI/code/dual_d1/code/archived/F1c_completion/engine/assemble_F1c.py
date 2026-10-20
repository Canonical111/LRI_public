#!/usr/bin/env python3
"""F1c full finite-response subtraction. Missing scalars are errors.
All raw derivatives are taken before v=1,delta=0; no Taylor factorials.
"""
from pathlib import Path
from functools import lru_cache
from math import comb
import json, hashlib
import sympy as s
from read_expression import load

ROOT=Path(__file__).resolve().parent
OUT=ROOT.parent/'data';OUT.mkdir(exist_ok=True)
ell=s.Symbol('ell')
DER={(0,0):'base',(1,0):'v',(0,1):'d',(1,1):'vd',(2,0):'vv',(2,1):'vvd'}
USED={}
def keep(path):
    if not path.is_file(): raise FileNotFoundError(path)
    USED[str(path.relative_to(ROOT))]=hashlib.sha256(path.read_bytes()).hexdigest()
    return load(path)

@lru_cache(None)
def raw(name,i,j,p,m=0):
    fn=ROOT/'series'/f'{name}_{DER[i,j]}_p{p}.expr'
    return s.expand(keep(fn)).coeff(ell,m)

def raw_product(A,B,i,j):
    # For these two-kink factors all relevant powers are in [-1,1].
    total=0
    for a in range(i+1):
      for b in range(j+1):
       for p in (-1,0,1):
        total+=comb(i,a)*comb(j,b)*sum(
            raw(A,a,b,p,m)*raw(B,i-a,j-b,-p,0-m)
            for m in (0,))  # finite constants have nonnegative log degrees
    return s.expand(total)

@lru_cache(None)
def K4(i,j):
    return s.expand(raw('Q4',i,j,0)-raw_product('Q2','Z2',i,j))
@lru_cache(None)
def EK4(i,j):
    return s.expand(raw('EQ4',i,j,0)-raw_product('EQ2','Z2',i,j)
                    -raw_product('Q2','EZ2',i,j))
def jetprod(A,B):
    return s.expand(A[1,1]*B[0,0]+A[1,0]*B[0,1]
                    +A[0,1]*B[1,0]+A[0,0]*B[1,1])
def beta(name):return keep(ROOT/(name+'_symbolic.expr'))
def rational(ex):
    mapping={x:s.S.Zero for x in ex.free_symbols
             if str(x).startswith(('R_','Z'))}
    mapping.update({x:s.S.Zero for x in ex.atoms(s.log,s.polylog,s.zeta)})
    return s.expand(ex.xreplace(mapping).subs(s.pi,0))

def main():
    jets=[(0,0),(1,0),(0,1),(1,1)]
    q={(i,j):raw('Q2',i,j,0) for i,j in
          jets+[(2,0),(2,1)]}
    e={(i,j):raw('EQ2',i,j,0) for i,j in jets}
    f5=dict(zip(jets,map(beta,['b_check','G_check','R','Psi'])))
    f3={(0,0):s.S.One,(1,0):beta('a_check'),(0,1):beta('p_check'),(1,1):beta('E_check')}
    h4=dict(zip(jets,(-beta(x)/4 for x in ['c_check','f_check','q_check','M'])))
    k4={z:K4(*z) for z in jets}
    l2={
     (0,0):-2*q[0,0]-4*q[1,0]+2*e[0,0],
     (1,0):-6*q[1,0]-4*q[2,0]+2*e[0,0]+2*e[1,0],
     (0,1):-2*q[0,1]-4*q[1,1]+2*e[0,1],
     (1,1):-6*q[1,1]-4*q[2,1]+2*e[0,1]+2*e[1,1],
    }
    parts={
      'ct_Q2_b5':-2*jetprod(q,f5),
      'ct_K4_b3':-4*jetprod(k4,f3),
      'ct_lambda2_h4':-jetprod(l2,h4),
    }
    # Save partial established pieces even before both new four-kink moments finish.
    for name,ex in parts.items():
        ex=s.expand(ex)
        (OUT/(name+'.expr')).write_text(s.sstr(ex,order='none'))
        print(name,'terms',len(s.Add.make_args(ex)),'rational',rational(ex),flush=True)
    parts['ct_lambda4']=s.expand(-6*K4(1,1)-4*K4(2,1)+2*EK4(0,1)+2*EK4(1,1))
    extra={'K4_vd_finite':K4(1,1),'K4_vvd_finite':K4(2,1),
           'EK4_d_finite':EK4(0,1),'EK4_vd_finite':EK4(1,1),
           'Q4_vvd_finite':raw('Q4',2,1,0),'EQ4_vd_finite':raw('EQ4',1,1,0)}
    parts['Dct']=s.expand(sum(parts.values()))
    norm=keep(ROOT/'Dnorm.expr')
    parts['total_shift']=s.expand(parts['Dct']+norm)
    parts['Nd_known_part']=s.expand(-4*parts['total_shift'])
    for name,ex in {**parts,**extra}.items():
        ex=s.expand(ex)
        (OUT/(name+'.expr')).write_text(s.sstr(ex,order='none'))
        print(name,'terms',len(s.Add.make_args(ex)),'rational',rational(ex),flush=True)
    assert rational(parts['Dct'])==-190100
    assert rational(parts['total_shift'])==-s.Rational(388919,2)
    assert rational(parts['Nd_known_part'])-4*s.Rational(399343,2)==-20848
    (OUT/'input_hashes.json').write_text(json.dumps(USED,indent=2))
    (OUT/'assembly.json').write_text(json.dumps({
        'definition':'Nd = -4*(P6+Dnorm+Dct)',
        'parts':{k:{'terms':len(s.Add.make_args(v)),'pi0':str(rational(v))} for k,v in parts.items()},
        'rational_check_Nd':'-20848','P6_full_value_not_assumed':True,
        'new_raw_four_kink_finite_parts':{k:str(rational(v)) for k,v in extra.items()}
    },indent=2))
    print('F1C_ASSEMBLY_COMPLETE',flush=True)
if __name__=='__main__':main()
