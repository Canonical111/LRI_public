#!/usr/bin/env python3
"""R7 (opt-in rates, A-FLAG-6) development: derive a per-(campaign, sector, L) rate spec for `tools/design.py rates`
from a measured campaign, here J-SWEEP-1 (Stage 3b, job 54641706), which STANDS IN for the pilot as the host decided
(PLAN-REVIEW-LOG.md, "Stage 4c plan", 2026-10-04). J-SWEEP-1 is NOT a design pilot: it is a test-only bootstrap sweep
of all 24,173 graphs at 2 x 512 points, run on the Stage-3 binary (5c5328af...).

  r7_spec.py PILOT --package PKG --spec-out SPEC.json --record-out RECORD.json [--step 0.1] [--band 0.10]
             [--min-graphs 100] [--boot 1000]

Per (sector, L), from the pilot's merged tables read by tools/design.py (load_pilot: the vendored order-8 Jacobian at
the pilot's loop means, so y = J8 . jet is the graph's C8 projection):
  sigma_g = sqrt(n_g Var_rep(y_g)), c_g = row seconds / (replicates x n_g) (seconds per point), and the Neyman
  work-variance W^2 = (sum_g sigma_g sqrt(c_g))^2 of each campaign (the variance x cost at the optimal allocation
  within the stratum); campaign a ran at the rate .8, campaign b at .9.
The rule (one step toward the better measured rate; a and b stay 0.1 apart, so they differ for every graph):
  r = W_b^2 / W_a^2 (.9 over .8);
  fewer than --min-graphs graphs, or 1 - band <= r <= 1 / (1 - band): keep a .8, b .9;
  r < 1 - band (.9 is better): a .9, b 1 (step up);
  r > 1 / (1 - band) (.8 is better): a .7, b .8 (step down).
A graph-bootstrap (--boot resamples of the stratum's graphs, jointly in a and b; seed 7082026) gives a 68% and a 95%
interval of r for the record. Pure analysis of merged tables (seconds); no integration.
"""
from __future__ import annotations
import argparse,json,math,sys
from decimal import Decimal as D
from pathlib import Path
import numpy as np

DEFAULT={'a':D('.8'),'b':D('.9')}
LABEL=('J-SWEEP-1 (Stage 3b, Expanse job 54641706; test-only bootstrap sweep, all 24,173 graphs, 2 x 512 points, '
       'Stage-3 binary 5c5328af) stands in for the pilot (host decision 2026-10-04). It is NOT a design pilot.')

def fmt(x:D)->str:
    s=format(x.normalize(),'f');return s[1:]if s.startswith('0.')else s

def stratum_table(P,s,L,boot,rng):
    out={}
    for c in ('a','b'):
        G=P.groups[(c,s,L)];y=np.einsum('rgj,j->rg',G.Y,P.J8[L]);n=np.array([G.points[g]for g in G.graphs],float)
        sig=np.sqrt(n*y.var(0,ddof=1));cost=np.array([G.seconds.get(g,0.)for g in G.graphs])/(G.reps*n)
        out[c]=dict(graphs=list(G.graphs),sigma=sig,cost=cost,reps=G.reps,points=sorted(set(n.astype(int).tolist())))
    assert out['a']['graphs']==out['b']['graphs'],(s,L)
    W={c:float((out[c]['sigma']*np.sqrt(out[c]['cost'])).sum())for c in out}
    V={c:float((out[c]['sigma']**2).sum())for c in out};C={c:float(out[c]['cost'].sum())for c in out}
    r=(W['b']/W['a'])**2 if W['a']>0 else math.inf
    ng=len(out['a']['graphs']);qs=None
    if boot and ng>1:
        wa=out['a']['sigma']*np.sqrt(out['a']['cost']);wb=out['b']['sigma']*np.sqrt(out['b']['cost']);rs=[]
        for _ in range(boot):
            i=rng.integers(ng,size=ng);a_=wa[i].sum()
            if a_>0:rs.append((wb[i].sum()/a_)**2)
        qs={k:float(np.quantile(rs,q))for k,q in (('p2.5',.025),('p16',.16),('p50',.5),('p84',.84),('p97.5',.975))}
    return dict(graphs=ng,replicates=out['a']['reps'],points=out['a']['points'],W={c:W[c]for c in W},W2={c:W[c]**2 for c in W},
                V=V,C_seconds_per_point_sum=C,ratio_W2_b_over_a=r,ratio_V_b_over_a=V['b']/V['a']if V['a']>0 else None,
                ratio_C_b_over_a=C['b']/C['a']if C['a']>0 else None,bootstrap_ratio_W2=qs)

def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('pilot',type=Path);p.add_argument('--package',type=Path,required=True);p.add_argument('--spec-out',type=Path,required=True)
    p.add_argument('--record-out',type=Path,required=True);p.add_argument('--step',default='0.1');p.add_argument('--band',type=float,default=.10)
    p.add_argument('--min-graphs',type=int,default=100);p.add_argument('--boot',type=int,default=1000);a=p.parse_args(argv)
    sys.path.insert(0,str(a.package.resolve()/'tools'));import design as Dz
    P=Dz.load_pilot(a.pilot);rng=np.random.default_rng(7082026);step=D(a.step)
    spec={'a':{'free':{},'power':{}},'b':{'free':{},'power':{}}};rows=[]
    for s in Dz.SECTORS:
        for L in Dz.LOOPS:
            t=stratum_table(P,s,L,a.boot,rng);r=t['ratio_W2_b_over_a']
            if t['graphs']<a.min_graphs:dec='keep (fewer than --min-graphs graphs)';shift=D(0)
            elif r<1-a.band:dec='step up (.9 better than .8)';shift=step
            elif r>1/(1-a.band):dec='step down (.8 better than .9)';shift=-step
            else:dec='keep (within the band)';shift=D(0)
            ra,rb=DEFAULT['a']+shift,DEFAULT['b']+shift
            assert D(0)<ra<=D(1)and D(0)<rb<=D(1)and ra!=rb
            spec['a'][s][str(L)]=fmt(ra);spec['b'][s][str(L)]=fmt(rb)
            rows.append(dict(sector=s,L=L,decision=dec,rate_a=fmt(ra),rate_b=fmt(rb),**t))
    tot=lambda c:sum(x['W'][c]for x in rows)
    rec=dict(schema='c8-d2-r7-spec-derivation-1',label=LABEL,pilot=P.meta,pilot_is_design_pilot=False,
             rule=dict(text=__doc__.split('The rule')[1].split('A graph-bootstrap')[0].strip(),step=str(step),band=a.band,min_graphs=a.min_graphs,
                       defaults={k:fmt(v)for k,v in DEFAULT.items()},bootstrap=dict(resamples=a.boot,seed=7082026)),
             strata=rows,neyman_total=dict(W_a=tot('a'),W_b=tot('b'),F_pilot=((tot('a')+tot('b'))/2)**2),spec=spec)
    a.spec_out.write_text(json.dumps(spec,indent=1,sort_keys=True)+'\n');a.record_out.write_text(json.dumps(rec,indent=1,default=str)+'\n')
    for x in rows:
        b=x['bootstrap_ratio_W2'];bi=f" [{b['p2.5']:.3f}, {b['p97.5']:.3f}]"if b else''
        print(f"{x['sector']:5s} L{x['L']} graphs {x['graphs']:5d}  W2 b/a {x['ratio_W2_b_over_a']:.3f}{bi}  V b/a {x['ratio_V_b_over_a']:.3f}  C b/a {x['ratio_C_b_over_a']:.3f}  "
              f"-> a {x['rate_a']}, b {x['rate_b']}  ({x['decision']})")
    return 0
if __name__=='__main__':sys.exit(main())
