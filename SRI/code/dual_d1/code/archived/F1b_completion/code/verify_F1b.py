#!/usr/bin/env python3
"""Rebuild the full F1b vacuum correction from exact archived lower moments.

This is an independent subtraction/normalization reassembly, not a reintegration
of the original lower kernels. All computations before numerical evaluation are
exact. No rational projection is used when building the full result.
"""
from pathlib import Path
from fractions import Fraction
import argparse, hashlib, itertools, json, sys, time
import sympy as s
from archived_read_expression import load
ROOT=Path(__file__).resolve().parents[1]
ell=s.Symbol('ell')
DERIV={(0,0):'base',(1,0):'v',(0,1):'d',(1,1):'vd'}
POWERS={'Q2':(0,1),'Q4':(0,1),'Z2':(-1,0),'Z4':(-1,0)}

def write_expr(path,ex):
    path.write_text(s.sstr(s.expand(ex),order='none'))

def build():
    manifest=json.loads((ROOT/'inputs/previous_normalization_shift.json').read_text())
    raw={}; hashes=[]
    for rec in manifest['raw_inputs']:
        p=ROOT/'inputs/series'/rec['name']
        sha=hashlib.sha256(p.read_bytes()).hexdigest()
        assert sha==rec['sha256'],p
        raw[p.name]=load(p)
        hashes.append({'file':str(p.relative_to(ROOT)),'sha256':sha})
    def coeff(moment,der,power,k):
        return s.expand(raw[f'{moment}_{der}_p{power}.expr']).coeff(ell,k)
    def atom(moment,der):
        return {(p,k):coeff(moment,der,p,k) for p in POWERS[moment] for k in (0,1)}
    def conv_atoms(atoms):
        # Retain every epsilon power; nonnegative log degree permits an exact
        # truncation to degrees 0 and 1 throughout multiplication.
        poly={(0,0):s.Integer(1)}
        for moment,der in atoms:
            other=atom(moment,der); new={}
            for (p,k),a in poly.items():
                for (q,l),b in other.items():
                    if k+l<=1 and a!=0 and b!=0:
                        key=(p+q,k+l);new[key]=new.get(key,0)+a*b
            poly={key:s.expand(value) for key,value in new.items()}
        return s.expand(poly.get((0,1),s.Integer(0)))
    # Independent, explicitly differentiated Leibniz formula: 4 + 5 + 4 terms.
    terms=[
      ('Q4Z2_1',-1,[('Q4','vd'),('Z2','base')]),
      ('Q4Z2_2',-1,[('Q4','v'),('Z2','d')]),
      ('Q4Z2_3',-1,[('Q4','d'),('Z2','v')]),
      ('Q4Z2_4',-1,[('Q4','base'),('Z2','vd')]),
      ('Q2Z2sq_1',1,[('Q2','vd'),('Z2','base'),('Z2','base')]),
      ('Q2Z2sq_2',2,[('Q2','v'),('Z2','base'),('Z2','d')]),
      ('Q2Z2sq_3',2,[('Q2','d'),('Z2','base'),('Z2','v')]),
      ('Q2Z2sq_4',2,[('Q2','base'),('Z2','v'),('Z2','d')]),
      ('Q2Z2sq_5',2,[('Q2','base'),('Z2','base'),('Z2','vd')]),
      ('Q2Z4_1',-1,[('Q2','vd'),('Z4','base')]),
      ('Q2Z4_2',-1,[('Q2','v'),('Z4','d')]),
      ('Q2Z4_3',-1,[('Q2','d'),('Z4','v')]),
      ('Q2Z4_4',-1,[('Q2','base'),('Z4','vd')]),
    ]
    expressions={name:s.expand(factor*conv_atoms(atoms)) for name,factor,atoms in terms}
    groups={label:s.expand(sum(ex for name,ex in expressions.items() if name.startswith(label+'_')))
            for label in ('Q4Z2','Q2Z2sq','Q2Z4')}
    total=s.expand(sum(groups.values()))
    # Jet-ring method: independent derivative bookkeeping. dv,dd are both at
    # most one, so the Taylor coefficients have no additional factorials.
    def jet(moment):
        return {(a,b,p,k):coeff(moment,der,p,k)
                for (a,b),der in DERIV.items() for p in POWERS[moment] for k in (0,1)}
    def multiply(A,B):
        out={}
        for x,a in A.items():
            if a==0: continue
            for y,b in B.items():
                if b==0:continue
                z=tuple(i+j for i,j in zip(x,y))
                if z[0]>1 or z[1]>1 or z[3]>1:continue
                out[z]=out.get(z,0)+a*b
        return {k:s.expand(v) for k,v in out.items()}
    J={name:jet(name) for name in POWERS}
    key=(1,1,0,1)
    jet_total=s.expand(-multiply(J['Q4'],J['Z2']).get(key,0)
              +multiply(multiply(J['Q2'],J['Z2']),J['Z2']).get(key,0)
              -multiply(J['Q2'],J['Z4']).get(key,0))
    assert s.expand(jet_total-total)==0,'Leibniz vs independent jet-ring assembly'
    previous=load(ROOT/'inputs/previous_normalization_shift.expr')
    assert s.expand(total-previous)==0,'Difference from saved exact normalization correction'
    def rational(ex):
        ex=ex.xreplace({x:s.S.Zero for x in ex.free_symbols if str(x).startswith('R_')})
        ex=ex.xreplace({x:s.S.Zero for x in ex.atoms(s.Function) if x.func in (s.log,s.polylog,s.zeta)})
        return s.expand(ex).subs(s.pi,0)
    assert rational(total)==-s.Rational(8719,2)
    # Derive all 16 required two-kink cutoff polynomials directly from the
    # elementary radial integral, rather than treating those files as axioms.
    e,r,v=s.symbols('epsilon r v',positive=True)
    # At delta=0 the endpoint pair has W2=r^(-2v).
    weights={'base':s.Integer(1),'v':-2*s.log(r),
             'd':-s.log(r)**2,'vd':2*s.log(r)**3-s.log(r)**2}
    small_checks=[]
    for moment,degree in [('Z2',0),('Q2',1)]:
        for der,weight in weights.items():
            integ=s.integrate((1-r)*r**(degree-2)*weight,(r,e,1))
            integ=s.expand(integ).subs(s.log(e),ell)
            for p in POWERS[moment]:
                got=s.expand(integ).coeff(e,p)
                expect=raw[f'{moment}_{der}_p{p}.expr']
                assert s.expand(got-expect)==0,(moment,der,p,got,expect)
                small_checks.append(f'{moment}_{der}_p{p}')
    for name,ex in {**expressions,**groups,'Dnorm':total}.items():
        write_expr(ROOT/'data'/f'{name}.expr',ex)
    report={'status':'F1b_exact_reassembly_passed','input_files_checked':len(hashes),
       'independent_derivative_methods':['explicit 13-term Leibniz formula','bigraded jet-ring multiplication'],
       'independent_methods_equal':True,'previous_expression_exactly_reproduced':True,
       'two_kink_coefficients_rederived':small_checks,'rational_projection':str(rational(total)),
       'term_rational_projections':{n:str(rational(ex)) for n,ex in expressions.items()},
       'group_rational_projections':{n:str(rational(ex)) for n,ex in groups.items()},
       'input_hashes':hashes,
       'exact_expression':'data/Dnorm.expr',
       'new_raw_four_kink_integration':False,'F1c_not_evaluated':True,
       'P6_full_exact_value_not_claimed':True}
    (ROOT/'verification/exact_reassembly.json').write_text(json.dumps(report,indent=2))
    print('Exact reassembly PASS; group rational parts',report['group_rational_projections'],flush=True)
    print('13 term rational parts',report['term_rational_projections'],flush=True)
    print('Distinct periods:',len([x for x in total.free_symbols if str(x).startswith('R_')]),flush=True)
    return {**expressions,**groups,'Dnorm':total}

if __name__=='__main__':
    build()
