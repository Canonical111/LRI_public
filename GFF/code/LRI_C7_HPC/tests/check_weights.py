#!/usr/bin/env python3
"""Checks of regenerated meromorphic Chebyshev weights before a new degree is used (PLAN section 4).

(a) Two tools/regenerate_weights.py outputs at different working precisions agree to <=1e-90 relative
    (absolute below 1e-90) and round to the same long double (exact rational rounding; also numpy on x86).
(b) Exact monomial moments with mpmath at 110 digits from --a, the formula of
    reference/code/check_meromorphic_weights.py over every axis, edge count, monomial 0..N and power -1..6.
(c) Optional: a regenerated degree (default 6) rounds exactly to the shipped reference/inputs/cw_L*_N*.bin.
"""
from __future__ import annotations
import argparse, json, sys
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path
import mpmath as mp
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tests'))
from make_validation_inputs import decode80, native_x87, parse_weights, round64, ulps

def load(d:Path,L:int,N:int)->list[str]:
    l,n,s=parse_weights(d/f'cw_L{L}_N{N}.txt')
    if (l,n)!=(L,N):raise ValueError('file name mismatch')
    return s
def provenance(d:Path,L:int):
    f=d/f'weights_L{L}_provenance.json';return json.loads(f.read_text()) if f.exists() else None

def agreement(sa:list[str],sb:list[str],native:bool)->dict:
    if len(sa)!=len(sb):raise ValueError('different value counts')
    worst=Decimal(0);at=None;ld_bad=0
    with localcontext() as c:
        c.prec=200 # Decimal(str) is exact; 200 digits hold every difference of <=150-digit strings.
        for i,(x,y) in enumerate(zip(sa,sb)):
            X,Y=Decimal(x),Decimal(y);s=max(abs(X),abs(Y));e=abs(X-Y)/s if s>=Decimal('1e-90') else abs(X-Y)
            if e>worst:worst,at=e,i
            ld_bad+=round64(Fraction(x))!=round64(Fraction(y))
    r={'values':len(sa),'max_error':format(worst,'.6E'),'worst_index':at,'long_double_rounding_mismatches':int(ld_bad)}
    if native:
        import numpy as np
        r['numpy_longdouble_mismatches']=int(sum(np.longdouble(x)!=np.longdouble(y) for x,y in zip(sa,sb)))
    r['passed']=worst<=Decimal('1e-90') and not ld_bad and not r.get('numpy_longdouble_mismatches',0);return r

def moments(s:list[str],L:int,N:int)->dict:
    mp.mp.dps=110;w=[mp.mpf(x) for x in s];D=L-1;B=2*L+1;nn=N+1;t=[(1+mp.cos(mp.pi*i/N))/2 for i in range(nn)]
    worst=mp.mpf(0);at=None;n=0;skipped=[]
    for axis in range(D):
        for b2 in range(B):
            a=mp.mpf(L-2-axis)-mp.mpf(b2)/2;b=mp.mpf(b2)/2
            for k in range(nn):
                tk=[x**k for x in t] # mpmath 0**0 == 1: the t=0 node carries the constant monomial.
                for r in range(-1,7):
                    if b==0 and a+k+1==0: # 1/b undefined; unreachable because b2=0 gives a=L-2-axis>=0.
                        skipped.append(dict(axis=axis,edge_count=b2,monomial=k,power=r));continue
                    exact=((1/b if r==-1 else 0) if a+k+1==0 else (0 if r==-1 else (-b)**r/(a+k+1)**(r+1)))
                    base=((axis*B+b2)*8+(r+1))*nn;calc=mp.fsum(w[base+i]*tk[i] for i in range(nn))
                    err=abs(calc-exact)/max(1,abs(exact));n+=1
                    if err>worst:worst,at=err,dict(axis=axis,edge_count=b2,monomial=k,power=r)
    return {'checks':n,'max_normalized_error':mp.nstr(worst,6),'worst':at,'skipped':len(skipped),'skipped_combinations':skipped,
            'skip_rule':'b==0 and a+k+1==0 (1/b undefined); never occurs, since b2=0 implies a=L-2-axis>=0 so a+k+1>=1; the generator likewise sets order -1 to 0 when b==0',
            'passed':worst<=mp.mpf('1e-80') and n>0}

def shipped(s:list[str],L:int,N:int,native:bool)->dict:
    f=ROOT/f'reference/inputs/cw_L{L}_N{N}.bin';blob=f.read_bytes()
    if len(blob)!=16*len(s):raise ValueError(f'{f}: {len(blob)} bytes for {len(s)} values')
    worst=Fraction(0);bad=0
    for i,x in enumerate(s):
        u=ulps(decode80(blob[16*i:16*i+10]),round64(Fraction(x)));worst=max(worst,u);bad+=u!=0
    r={'bin':f.name,'values':len(s),'exact_rounding_mismatches':int(bad),'max_ulp_error':str(worst)}
    if native:
        import numpy as np
        r['numpy_mismatches']=int(np.count_nonzero(np.array([np.longdouble(x) for x in s],dtype=np.longdouble)!=np.fromfile(str(f),dtype=np.longdouble)))
    r['passed']=not bad and not r.get('numpy_mismatches',0);return r

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--a',type=Path,required=True,help='regenerate_weights.py output (moment checks use it)');p.add_argument('--b',type=Path,required=True,help='the same weights at another --dps')
    p.add_argument('--L',type=int,nargs='+',default=[5,6,7],choices=range(2,8));p.add_argument('--degree',type=int,default=7);p.add_argument('--shipped-check',type=Path,help='directory with regenerated cw_L*_N{shipped-degree}.txt');p.add_argument('--shipped-degree',type=int,default=6)
    p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.out.exists():raise FileExistsError(a.out)
    try:native,info=native_x87()
    except ImportError:native,info=False,'numpy unavailable'
    if not native:print('NOTE: no native x86 80-bit long double ('+info+'); numpy cross-checks skipped, exact rational rounding checks still run',flush=True)
    report={'schema':'c7-weight-checks-1','a':str(a.a.resolve()),'b':str(a.b.resolve()),'degree':a.degree,'L':a.L,'native_x87_checks':native,'platform':info,'agreement':{},'moments':{},'shipped':{}}
    for L in a.L:
        sa=load(a.a,L,a.degree);sb=load(a.b,L,a.degree);report['agreement'][L]=r=agreement(sa,sb,native);r['provenance_a']=provenance(a.a,L);r['provenance_b']=provenance(a.b,L)
        print('PASS' if r['passed'] else 'FAIL',f'(a) L{L} N{a.degree} dps agreement',r['max_error'],'LD mismatches',r['long_double_rounding_mismatches'],flush=True)
        report['moments'][L]=r=moments(sa,L,a.degree);print('PASS' if r['passed'] else 'FAIL',f'(b) L{L} N{a.degree} moments',r['checks'],'max',r['max_normalized_error'],'skipped',r['skipped'],flush=True)
        if a.shipped_check:
            report['shipped'][L]=r=shipped(load(a.shipped_check,L,a.shipped_degree),L,a.shipped_degree,native);print('PASS' if r['passed'] else 'FAIL',f'(c) L{L} N{a.shipped_degree} regenerated vs shipped .bin','mismatches',r['exact_rounding_mismatches'],flush=True)
    report['passed']=all(r['passed'] for k in ('agreement','moments','shipped') for r in report[k].values())
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(report,indent=2)+'\n');print(('ALL WEIGHT CHECKS PASSED: ' if report['passed'] else 'WEIGHT CHECKS FAILED: ')+str(a.out));sys.exit(0 if report['passed'] else 1)
if __name__=='__main__':main()
