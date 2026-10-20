#!/usr/bin/env python3
"""Build the order-eight affine map C = K + sum_{L=5..8} J_L v_L from verified exact low-loop campaigns.

K: the fixed point of the deterministic exact all-tree quadratures of loops 2,3,4 at the chosen degrees (loop 1 is
b1=3, c1=1 exactly). J_L: complex-step derivative at that point (exact, since C2..C8 are affine in loops >= 5).
Reports: the degree convergence of K, C2..C4 against their exact values, the top-loop channel rule (C8 depends on
loop 8 only through 3c-b, which justifies the exclusion in campaign.plan_counts), and, if an exact loop-5 campaign is
given, the deterministic C5 sequence against the exact C5 and the loop-5 contributions to C6..C8 per degree.
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from c8lib import NW,NV,TOP,REFS,coefficients,jacobian
from campaign import verify_campaign,dump
from assemble8 import exact_complete

def exact_vectors(camp:Path)->dict:
    r=verify_campaign(camp);m=r['manifest']
    if m['mode']!='exact' or m['replicates']!=1:raise ValueError(f'{camp}: not an exact campaign')
    exact_complete(camp,m) # every active graph, all ordered trees, authenticated inputs
    out={}
    for N in m['degrees']:
        d=json.loads((camp/'merged'/f'N{N}.json').read_text());b=np.array(d['batches'],dtype=float)
        if b.shape!=(1,NV):raise ValueError(f'{camp} N{N}: bad shape')
        out[N]=b[0]
    return {'L':m['L'],'vectors':out,'manifest_sha256':r['manifest_sha256'],'input_sha256':m['input_sha256']}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--exact',type=Path,nargs='+',required=True,help='verified exact campaigns for loops 2,3,4 (and optionally 5)')
    p.add_argument('--degree',nargs='+',required=True,help='degree used for K, as L=N pairs, e.g. 2=24 3=24 4=20',metavar='L=N')
    p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    use={int(x.split('=')[0]):int(x.split('=')[1]) for x in map(str,a.degree)}
    camps={};src={}
    for c in a.exact:
        e=exact_vectors(c.resolve())
        if e['L'] in camps:raise ValueError(f'two exact campaigns for loop {e["L"]}')
        camps[e['L']]=e;src[e['L']]={'campaign':str(c.resolve()),'manifest_sha256':e['manifest_sha256'],'degrees':sorted(e['vectors'])}
    if set(camps)-{2,3,4,5} or not {2,3,4}<=set(camps):raise ValueError('need exact campaigns for loops 2,3,4 (optionally 5)')
    if set(use)!={2,3,4}:raise ValueError('give the K degree for loops 2,3,4')
    lower={L:camps[L]['vectors'][use[L]] for L in (2,3,4)};K=coefficients(lower)
    conv={}
    for L in (2,3,4):
        degs=sorted(camps[L]['vectors']);conv[L]=[]
        for N in degs:
            alt=dict(lower);alt[L]=camps[L]['vectors'][N];conv[L].append({'degree':N,'K_minus_chosen':(coefficients(alt)-K).tolist()})
    J={L:jacobian(lower,L) for L in range(5,TOP+1)}
    checks=[{'n':n,'K':float(K[n]),'reference':REFS[n],'difference':float(K[n]-REFS[n])} for n in (2,3,4)]
    j8=J[TOP][TOP];nz=[k for k in range(NV) if abs(j8[k])>1e-14*max(abs(j8))]
    rule={'nonzero_slots':nz,'ratio_B_over_A':float(j8[NW+NW-1]/j8[NW-1]) if j8[NW-1] else None}
    if nz!=[NW-1,2*NW-1] or abs(rule['ratio_B_over_A']+3)>1e-9:raise ArithmeticError(f'top-loop channel rule fails: {rule}')
    rule['statement']='C8 depends on loop 8 only through 3*c8(0)-b8(0): classes with 3*wb=wa contribute exactly zero'
    out={'schema':'c8-affine-1','slots':NW,'K':K.tolist(),'lower':{str(L):v.tolist() for L,v in lower.items()},'K_degrees':{str(k):v for k,v in use.items()},
         'loops':{str(L):{'J':J[L].tolist()} for L in J},'sources':{str(k):v for k,v in src.items()},'K_degree_convergence':{str(k):v for k,v in conv.items()},
         'lower_order_checks':checks,'top_loop_channel_rule':rule}
    if 5 in camps:
        seq=[]
        for N in sorted(camps[5]['vectors']):
            v=camps[5]['vectors'][N];c=K+J[5]@v
            seq.append({'degree':N,'C5':float(c[5]),'C5_minus_exact':float(c[5]-REFS[5]),'loop5_contribution':(J[5]@v).tolist()})
        out['loop5_exact_sequence']=seq
    dump(a.out,out)
    print(json.dumps({'K':out['K'],'checks':checks,'rule':rule,'loop5':out.get('loop5_exact_sequence')},indent=1))
if __name__=='__main__':main()
