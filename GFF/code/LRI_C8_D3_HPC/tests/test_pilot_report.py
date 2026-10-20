#!/usr/bin/env python3
"""A-DES-3 (pilot_report.py oracles and hand values) and A-DES-4 (pilot_select.py) on the Mac. Seeded; about a minute.

A-DES-3
  * P8_hat = 1.0865 exp(0.0890 (Var(Q) - 1.8696)) at the Gaussian point and at run1's Var(Q) values of
    reference/c8d3_recon/out/tail_calib.log (b_free_L7 1.874 -> 1.087, a_power_L7 2.035 -> 1.103); split_q per disjoint
    block of 8; the sector switch to R = 16 above 1.13;
  * Hill on seeded iid Pareto a = 2, 3 (and 2.5) and Gaussian |t| at R = 8 per campaign, 4,096 and 32,768 nested points:
    the medians of the mean Hill index within Monte Carlo error of tail_calib.log [A2], and the package's own
    screen_graph and confirm_graph (round-4 rule: screened in either campaign at 4,096 points, two-campaign mean
    xi(32,768) > 0.44) at the [A2] rates S and C4 within binomial error;
  * an injected synthetic pilot: the screen flags exactly the injected heavy L8 graph, confirm confirms it, and the
    zero-channel graph (tail_sum 0, a top 16 of zeros) is "undefined" in screen and confirm, never a NaN compared; a
    graph with one undefined campaign is still flagged by the other campaign's defined heavy entry (E.6 items 2-3);
  * actions 1, 3 and 5 of `full` on an injected pilot with a heavy-tailed L7 graph: action 1 flags only the heavy L8
    graph and never the L7 one; action 3's variance and cost shares equal hand values with no 32,768-point rows, with
    an empty PC (a P1c graph's 32,768-point sigma from PA raises its share above 3%) and with a PC; action 5's strata
    (the 500-value flag rule) and its pooled L8 and L <= 7 values equal hand-computed Var(Q) statistics;
  * kappa(R) = c4(R)^-2 = 175 pi/512, 2760615 pi/8388608, 1.007967750 (R = 8, 16, 64) to 1e-12 (closed forms against
    math.lgamma); at k = 0 P_G kappa_G = (R-1)/(R-2) = 7/6, 15/14, 63/62 to 1e-12; at P_hat 1.13 1.24678 (R = 8) and
    1.10400 (R = 16), at 1.196 1.36510 and 1.14806 (to 1e-5);
  * the seeded Monte Carlo (20,000 graphs x 50 trials, Gaussian replicate means, lognormal sigma and c):
    (sum s sqrt c)^2/(sum sigma sqrt c)^2 within 3 SE of c4(R)^2 and realised/plug-in cost of n ~ s/sqrt(c) within 3 SE
    of (R-1)/(R-2), R = 8 and 16;
  * cost_table on a mixed synthetic pilot (L <= 7 at R = 8, L8 at R = 16, floor-bound graphs): sigma_g with ddof = 1;
    the plug-in busy core-hours, the floor fraction, F = sum w_G F_G and the realistic hours equal an independent
    water-filling recomputation; floor-bound graphs get x1; switching one group from R = 8 to 16 changes F by
    w_G rho (15/14 - 7/6); at alpha = 1/2 without a binding floor the busy hours equal (sum sigma sqrt c)^2/(4 SE^2);
  * item 12: an oracle design (s_PA = sigma) on Gaussian fakes gives 1 within its Monte Carlo error after the
    c4(R_PF)^2 correction and 1/c4(R_PF)^2 without it; per sector (PF free L8 at R = 8, power L8 at R = 16 after action
    4): each sector's raw value and c4(R_PF)^2 equal a hand computation on its own graph-campaigns, independently of the
    selection's key order; mixed R within a sector is refused; cost_table puts each sector's value into that sector's L8
    P_hat only;
  * zero channel: a non-finite tail_sum or top value makes tail_stats "undefined"; an overflowing replicate variance
    leaves confirm_graph's V ratio None; the pinned real rows of tests/fixtures/zero_channel_tails.json (the power-L3
    kernel G7 and the other zero-channel kernels of class_b.py (e), worker rows of Expanse job repair3b) through
    tail_stats, screen_graph and confirm_graph give finite values or "undefined", never a NaN or an infinity.
Stage 3a repair round 3
  * E.6 items 9-10: boot_band resamples graphs (both campaigns of a graph together): the reviewer's 40-graph case, spies
    on alpha_p1c and action5 (one unit per graph with both campaigns' entries), stratified resampling;
  * E.7: every cost-table row against an independent recomputation at any alpha: the central cost, the Gaussian-kappa
    column, F at both ends of the P8_hat band, the optimum at both ends of the alpha band, the relative rows at both ends
    of the |C8| band, the band as the envelope of all corners; SU per MP self-check mode (mp_check_overhead, or "pending
    P1"); a |C8| band reaching 0;
  * A-PIL-2: the re-projection (PF and PC busy hours, auto lane times, reservations, step peaks) equals hand values; a
    line between the R = 8 and R = 16 peaks leaves only the R = 16 branch outside (the GO/NO-GO itself on campaign
    directories is in tests/test_pipeline.py);
  * zero-channel host refinement: an L8 graph with s_G = 4 is reported as "zero-channel heavy tail, not confirmed" and
    never flagged, confirmed, selected (pilot_select.confirm), counted in the 3% hold, or used by action 5, alpha_p1c
    and item 12; the real G1601 rows, flagged without the rule, are reported with it.
A-DES-4  pilot_select at full scale (16,064 free and 4,336 power L8 graphs): deterministic from the seed; stage A 1/8 of
  each stratum (+-1) plus the heaviest 1% per sector (labelled heaviest_1pct unless drawn); P1c a subset of the
  stratified part, 1/32 of each stratum's stage-A draw (+-1), at points 32,768 nest [4096]; confirm: every PC graph at
  32,768 nest [4096], the 25% cap held and filled (proportional within strata), all flagged graphs taken under the cap,
  the action-2b extension inside what is left; the empty PC with its reason; an unregistered seed refused (64).
  Stage 6 group B: S3-001 the PC cap holds at every step (one stratum with PC costs 1 and 99 s and a 50 s budget, every
  seed; confirm's recorded and recomputed cost within the cap) and production.read_selection refuses a confirm selection
  over its recorded cap or without one; S3-002 the flagged graphs of both sectors share the cap jointly (ten equally
  costly flagged graphs per sector and room for ten: 5 + 5, not 10 + 0) and a 2b extension never displaces screened
  graphs of the other sector; S3-003 pilot_select.pc_costs prices PC in PF's MP mode (an off-mode model with overhead on
  = 2 doubles every cost) and refuses a model of another executable, CPU or mode; S3-010 the cost table's allocated
  units and wall hours are on the target site's lane node (symmetry amdq 64 allocated CPUs per node, Expanse 128; the
  site CPUs equal slurm/site.sh's C8_CPU_EXPECT), the target site and both CPUs are recorded, a projection from PF's CPU
  to another site's is refused without a target-site model and with one every cost is scaled by its ratio.
  Stage 6 fix round 2, group P: S3-R2-002 sector-symmetric strata with heterogeneous costs (identical free and power
  strata of PC costs 1 and 99 s, a 100 s cap, 3,000 seeds through confirm): the 99-s graph is selected equally often in
  both sectors (3/8 each; before, 1/2 in free and 1/4 in power, as free sorts first), the cap holds at every seed, and
  relabelling the strata so that power sorts first leaves both frequencies; S3-R2-004 on symmetry with C8_SBATCH_ARGS
  '-p defq' the target CPU is the partition's (Intel Gold 6148, budget.partition_cpu, 80 allocated CPUs per node): an
  EPYC 7543 PF is refused without target measurements and with an AMD model, and scaled with an Intel one; amdq keeps the
  site CPU; S3-R2-005 the MP self-check columns of a projected table use the TARGET model's overheads (PF off/on 0.5,
  target 0.9: off = 0.9 x on), an explicit ratio model on another CPU is refused, and without a projection PF's model
  gives them.
--run1 (A-DES-3's Expanse part, J-RUN1): run1's tail facts reproduced from the pinned archive (cd3:tail_calib:70-77,140),
  the archive identified by its sha256 first. (1) Block maxima: per graph, campaign and replicate the largest checkpoint
  row max_abs (|t| = |norm (3 w_B - w_A) v_0| over the row's points, so the maximum over the replicate's n_g points);
  xi_sd = sd(ln max, ddof 1) sqrt(6)/pi over the 64 replicates (graphs with 64 positive maxima): power L7 has 590
  graphs, 34 / 37 / 33 above 0.38 (a, b, both) and 33 / 28 / 27 above 0.42, i.e. run1's 27 of 590. (2) P8_hat of
  pilot_report.py (split_q per disjoint block of 8 replicates, p8_pooled) on the eight L6/L7 groups, the replicate values
  of graph_replicates.csv projected on the old slots of the C8 Jacobian (the vendored jacobians at run1's means, new
  top slots and loop 8 at 0, as tail_calib.py/partial.py): graph counts 395/395/107/107/2298/2298/590/590, Var(Q) and
  P8_hat equal tail_calib.log's to its 3 printed decimals, spanning 1.078-1.103.
--zero-channel FILE (A-DES-3's real-tail part on Expanse, job repair3b): the zero-channel check above on the rows that
  tests/class_b.py --zero-channel-tails FILE has just written.
Usage: python3 -B tests/test_pilot_report.py [--output FILE]
       python3 -B tests/test_pilot_report.py --run1 [--archive TGZ] [--sha256 HEX] [--output FILE]
       python3 -B tests/test_pilot_report.py --zero-channel FILE [--output FILE]"""
from __future__ import annotations
import argparse,json,math,os,sys,tempfile
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tests')]
import pilot_report as pr  # noqa: E402
import pilot_select as ps  # noqa: E402
from common import Refuse  # noqa: E402
RESULTS=[]
def ok(name,**info):RESULTS.append({'test':name,**info});print('PASS',name,flush=True)
N1,N2,R8=4096,32768,8

class FakeCamp:
    """Camp.at() over simulated tails: data[(key, g, n)] = (jets per replicate, (tail_sum, top 16) per replicate)."""
    def __init__(self):self.data={}
    def at(self,key,g,n):
        if (key,g,n)not in self.data:raise KeyError(f'no row {key} {g} {n}')
        return self.data[(key,g,n)]

def tails_of(X,n):
    """X: (R, N2) |t| of one graph-campaign -> per replicate (tail_sum, top 16 descending) over the first n points."""
    Y=X[:,:n];top=-np.sort(-np.partition(Y,n-16,axis=1)[:,n-16:],axis=1);return [(float(Y[r].sum()),[float(v)for v in top[r]],n)for r in range(len(Y))]

def _ppf(u):
    """The standard normal quantile (Acklam's rational approximation, refined by one Halley step): numpy-only."""
    a=[-3.969683028665376e+01,2.209460984245205e+02,-2.759285104469687e+02,1.383577518672690e+02,-3.066479806614716e+01,2.506628277459239e+00]
    b=[-5.447609879822406e+01,1.615858368580409e+02,-1.556989798598866e+02,6.680131188771972e+01,-1.328068155288572e+01]
    c=[-7.784894002430293e-03,-3.223964580411365e-01,-2.400758277161838e+00,-2.549732539343734e+00,4.374664141464968e+00,2.938163982698783e+00]
    d=[7.784695709041462e-03,3.224671290700398e-01,2.445134137142996e+00,3.754408661907416e+00]
    u=np.asarray(u,float);x=np.empty_like(u);lo=u<0.02425;hi=u>1-0.02425;mid=~(lo|hi)
    q=np.sqrt(-2*np.log(u[lo]));x[lo]=(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5])/((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    q=np.sqrt(-2*np.log(1-u[hi]));x[hi]=-(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5])/((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    q=u[mid]-0.5;r=q*q;x[mid]=(((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q/(((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)
    from math import erfc
    e=0.5*np.vectorize(erfc,otypes=[float])(-x/math.sqrt(2))-u;w=e*math.sqrt(2*math.pi)*np.exp(x*x/2);return x-w/(1+x*w/2)

# [A2] of reference/c8d3_recon/out/tail_calib.log (200 graphs x 2 campaigns): medians of the mean Hill index, S and C4
A2={'gauss':(0.092,0.067,0.000,0.000),'pareto_3':(0.330,0.331,0.170,0.000),'pareto_2.5':(0.399,0.399,0.925,0.065),'pareto_2':(0.499,0.504,1.000,0.975)}

def hill_and_rates():
    rng=np.random.default_rng(20261004);G=200;out={}
    for fam,(h1r,h2r,Sr,Cr)in A2.items():
        c=FakeCamp();h1=[];h2=[];S=[];C=[]
        for g in range(G):
            for t in 'ab':
                U=np.clip(rng.random((R8,N2)),1e-300,1.)
                X=np.abs(_ppf(U))if fam=='gauss'else U**(-1/float(fam.split('_')[1]))
                jets=[[0.,float(x.mean())/3]for x in X]
                for n in (N1,N2):c.data[((t,'power',8),g,n)]=(jets,tails_of(X,n))
            sc=pr.screen_graph(c,'power',g,N1);cf=pr.confirm_graph(c,'power',g)
            for t in 'ab':h1.append(sc['campaigns'][t]['xi'])
            h2.append(cf['xi_mean_32768']);S.append(sc['flag']);C.append(sc['flag']and cf['confirmed'])
        m1,m2=float(np.median(h1)),float(np.median(h2))
        sd1=float(np.std(h1,ddof=1));sd2=float(np.std(h2,ddof=1))*math.sqrt(2)   # h2 here is a two-campaign mean; [A2] reports campaign a's
        se1=1.2533*sd1/math.sqrt(len(h1))*math.sqrt(1+len(h1)/200);se2=1.2533*sd2/math.sqrt(G)*math.sqrt(2)
        assert abs(m1-h1r)<=3*se1+5e-4,(fam,'hill 4096',m1,h1r,se1)
        assert abs(m2-h2r)<=3*se2+5e-4,(fam,'hill 32768',m2,h2r,se2)
        for got,ref,name in ((float(np.mean(S)),Sr,'S'),(float(np.mean(C)),Cr,'C4')):
            p=max(min((got+ref)/2,1-1/G),1/G);assert abs(got-ref)<=3*math.sqrt(p*(1-p)*2/G)+1/G,(fam,name,got,ref)
        out[fam]={'hill_4096':m1,'ref_4096':h1r,'xi_mean_32768':m2,'ref_32768':h2r,'S':float(np.mean(S)),'S_ref':Sr,'C4':float(np.mean(C)),'C4_ref':Cr}
    ok('A-DES-3: Hill medians at 4,096 and 32,768 points and the round-4 rates S and C4 of the package\'s screen_graph/confirm_graph on seeded iid '
       'Gaussian and Pareto a = 3, 2.5, 2 (200 graphs x 2 campaigns x 8 replicates) agree with tail_calib.log [A2] within Monte Carlo error',families=out)

def p8_formula():
    assert abs(pr.p8_of_varq(1.8696)-1.0865)<1e-12
    for vq,want in ((1.874,1.087),(2.035,1.103),(1.882,1.088)):assert abs(pr.p8_of_varq(vq)-want)<6e-4,(vq,pr.p8_of_varq(vq),want)
    y=np.arange(16.);q=pr.split_q(y);a=np.var(y[0:4],ddof=1);b=np.var(y[4:8],ddof=1);assert len(q)==2 and abs(q[0]-math.log(a/b))<1e-15
    sw=1.8696+math.log(1.13/1.0865)/0.0890
    qs_lo=list(np.random.default_rng(1).normal(0,math.sqrt(sw-0.2),4000));qs_hi=list(np.random.default_rng(2).normal(0,math.sqrt(sw+0.2),4000))
    assert pr.p8_pooled(qs_lo)<pr.P8_R16<pr.p8_pooled(qs_hi)and pr.p8_pooled([1.])is None
    ok('A-DES-3: P8_hat = 1.0865 exp(0.0890 (Var(Q) - 1.8696)) (Gaussian point; run1 Var(Q) 1.874, 2.035, 1.882 -> 1.087, 1.103, 1.088 of tail_calib.log); '
       'split_q per disjoint block of 8; the R = 16 switch at Var(Q) = %.4f'%sw)

def injected_pilot():
    rng=np.random.default_rng(9);c=FakeCamp()
    for g in range(6):
        for t in 'ab':
            U=np.clip(rng.random((R8,N2)),1e-300,1.);X=U**(-1/1.5)if g==3 else np.abs(_ppf(U))
            if g==5:X=np.zeros_like(X)
            jets=[[0.,float(x.mean())]for x in X]
            for n in (N1,N2):c.data[((t,'free',8),g,n)]=(jets,tails_of(X,n))
    sc={g:pr.screen_graph(c,'free',g,N1)for g in range(6)};cf={g:pr.confirm_graph(c,'free',g)for g in range(6)}
    assert [g for g in range(6)if sc[g]['flag']]==[3]and [g for g in range(6)if cf[g]['confirmed']]==[3]
    assert sc[5]['undefined']and not sc[5]['flag']and cf[5]['undefined']and not cf[5]['confirmed']
    ts=pr.tail_stats([(0.,[0.]*16)]);assert ts=={'undefined':'a replicate with tail_sum 0'}
    ts=pr.tail_stats([(5.,[1.]*15+[0.])]);assert 'undefined'in ts and pr.hill([1.]*15+[0.])is None and pr.hill([2.]*16)==0.
    for x in sc.values():
        for v in x['campaigns'].values():assert all(not(isinstance(z,float)and math.isnan(z))for z in v.values())
    # one campaign undefined, the other defined and heavy: the defined entry is still compared (E.6 items 2-3), the undefined
    # one is listed, never compared (Stage 3a repair round 1)
    U=np.clip(rng.random((R8,N2)),1e-300,1.);Xa=U**(-1/1.5);Xb=np.abs(_ppf(np.clip(rng.random((R8,N2)),1e-300,1.)))
    for t,X in (('a',Xa),('b',Xb)):
        tl=tails_of(X,N1)
        if t=='b':tl[0]=(tl[0][0],tl[0][1][:15]+[0.],N1)   # replicate 0: its top 16 holds a zero
        c.data[((t,'free',8),7,N1)]=([[0.,float(x.mean())]for x in X],tl)
    m=pr.screen_graph(c,'free',7,N1)
    assert m['flag']is True and m['undefined']==['b: a replicate whose top 16 holds a zero or fewer than 16 values']and 'undefined'in m['campaigns']['b'],m
    assert m['campaigns']['a']['xi']>pr.XI_SCREEN and m['campaigns']['a']['share_max']>pr.SHARE_SCREEN
    c.data[(('b','free',8),8,N1)]=c.data[(('b','free',8),7,N1)];c.data[(('a','free',8),8,N1)]=([[0.,float(x.mean())]for x in Xb],tails_of(Xb,N1))
    m2=pr.screen_graph(c,'free',8,N1);assert m2['flag']is False and m2['undefined'],m2   # undefined b, light a: not flagged
    ok('A-DES-3: on an injected synthetic pilot (L8, 6 graphs) the screen flags exactly the Pareto a = 1.5 graph and confirm confirms only it; the '
       'zero-channel graph (tail_sum 0, a top 16 of zeros) is "undefined" in both and never flagged; no NaN reaches a threshold; a graph whose '
       'campaign b is undefined (a zero in a top 16) and campaign a heavy (xi %.2f, share %.3f) is flagged by a and lists b as undefined; with a '
       'light campaign a it is not flagged'%(m['campaigns']['a']['xi'],m['campaigns']['a']['share_max']))

def kappa_and_realism():
    want={8:175*math.pi/512,16:2760615*math.pi/8388608,64:1.007967750}
    for R,v in want.items():assert abs(pr.kappa(R)-v)<=(1e-12 if R<64 else 5e-10),(R,pr.kappa(R),v)
    for R in (8,16,64):
        r=pr.realism(1.0,R);assert r['k']==0. and abs(r['P_G']*r['kappa_G']-(R-1)/(R-2))<=1e-12,(R,r)
        assert abs(r['kappa_G']-pr.kappa(R))<=1e-12 and abs(r['F_G']-r['P_G']*r['kappa_G']*pr.RHO)<=1e-15
    hand={(1.13,8):1.24678,(1.13,16):1.10400,(1.196,8):1.36510,(1.196,16):1.14806}
    got={k:(lambda r:r['P_G']*r['kappa_G'])(pr.realism(*k))for k in hand}
    for k,v in hand.items():assert abs(got[k]-v)<=1e-5,(k,got[k],v)
    ok('A-DES-3: kappa(R) = c4(R)^-2 = 175 pi/512, 2760615 pi/8388608 to 1e-12 and 1.007967750 (R = 64); P_G kappa_G = (R-1)/(R-2) at k = 0 '
       '(R = 8, 16, 64) to 1e-12; at P_hat 1.13 and 1.196: 1.24678, 1.10400, 1.36510, 1.14806 to 1e-5',values={f'{k[0]}|R{k[1]}':v for k,v in got.items()})

def realism_mc():
    rng=np.random.default_rng(51);G,T=20000,50;rec={}
    for R in (8,16):
        r1=[];r2=[]
        for _ in range(T):
            sig=np.exp(rng.normal(0,1,G));c=np.exp(rng.normal(-9,1.2,G));Y=rng.normal(0,1,(G,R))*sig[:,None];s=Y.std(1,ddof=1);w=np.sqrt(c)
            r1.append(((s*w).sum()/(sig*w).sum())**2);r2.append((sig**2*w/s).sum()/(s*w).sum())
        for v,want,name in ((r1,pr.c4(R)**2,'c4^2'),(r2,(R-1)/(R-2),'(R-1)/(R-2)')):
            m=float(np.mean(v));se=float(np.std(v,ddof=1))/math.sqrt(T);assert abs(m-want)<=3*se,(R,name,m,want,se)
        rec[R]={'c4sq':[float(np.mean(r1)),pr.c4(R)**2],'realised_over_plugin':[float(np.mean(r2)),(R-1)/(R-2)]}
    ok('A-DES-3: Monte Carlo (20,000 graphs x 50 trials; Gaussian replicate means, lognormal sigma and c): (sum s sqrt c)^2/(sum sigma sqrt c)^2 '
       'within 3 SE of c4(R)^2 and realised/plug-in cost of n ~ s/sqrt(c) within 3 SE of (R-1)/(R-2), R = 8 and 16',values=rec)

class FakePF:
    """The fields of Camp that per_graph_sigma and cost_table read: g[(c, s, L)] with total, jets, reps, cost; m."""
    def __init__(self,spec:dict,rng):
        self.g={};self.m={'mp_check':'stride16'};self.sigma={};self.spec=spec
        for (t,s,L),(R,ng)in spec.items():
            G={'total':{},'jets':{},'reps':R,'cost':{}};k=2*(9-L)
            for g in range(ng):
                n=4096;sig=float(np.exp(rng.normal(math.log(100),1.)));cpp=float(np.exp(rng.normal(-8,.8)))
                a=math.sqrt((R-1)/R*sig**2/n)
                for r in range(R):G['jets'][(r,g)]=[0.]*(k-1)+[a if r%2==0 else -a]
                G['total'][g]=n;G['cost'][g]=(n,cpp*n);self.sigma[(t,s,L,g)]=(sig,cpp)
            self.g[(t,s,L)]=G

def independent_table(pop:dict,SE:float,R:int,Rg:dict)->dict:
    """alpha = 1/2: n_g = max(4096, mu sigma_g/sqrt(c_g)), Var = sum sigma^2/(4 R n) = SE^2 (own bisection); F = sum w_G F_G with F_G at k = 0."""
    keys=list(pop);sig=np.array([pop[k][0]for k in keys]);c=np.array([pop[k][1]for k in keys])
    def n_of(mu):return np.maximum(4096.,mu*sig/np.sqrt(c))
    lo,hi=1e-30,1e30
    for _ in range(3000):
        mu=math.sqrt(lo*hi)
        if (sig**2/(4*R*n_of(mu))).sum()>SE**2:lo=mu
        else:hi=mu
        if hi/lo<1+1e-15:break
    n=n_of(hi);bound=n<=4096*1.000001;cost=R*n*c/3600;busy=float(cost.sum());floor=float(cost[bound].sum())
    w={};tot=0.
    for k,nn,cc,b in zip(keys,n,c,bound):
        if not b:G=k[:3];w[G]=w.get(G,0.)+nn*cc;tot+=nn*cc
    F=sum(v/tot*(Rg[G]-1)/(Rg[G]-2)*pr.RHO for G,v in w.items())if tot else 0.
    return {'busy':busy,'floor':floor,'floor_fraction':float(bound.mean()),'F':F,'w':{G:v/tot for G,v in w.items()},'realistic':floor+F*(busy-floor)}

def cost_table_checks():
    rng=np.random.default_rng(77)
    spec={('a','free',6):(8,120),('b','free',6):(8,120),('a','power',7):(8,80),('b','power',7):(8,80),('a','free',8):(16,150),('b','free',8):(16,150),
          ('a','power',8):(16,60),('b','power',8):(16,60)}
    P=FakePF(spec,rng);J8={L:np.array([0.]*(2*(9-L)-1)+[1.])for L in range(3,9)}
    pop=pr.per_graph_sigma(P,J8)
    for k,(sig,cg,R,n)in pop.items():assert abs(sig-P.sigma[k][0])<=1e-9*sig and abs(cg-P.sigma[k][1])<=1e-12*cg,(k,sig,P.sigma[k])
    p8={(s,c):1.0 for s in ('free','power')for c in ('L8','L<=7')}
    t=pr.cost_table(P,J8,0.9,{'central':0.5},p8,None,100.)
    Rg={G:R for G,(R,_)in spec.items()};mixed=0
    for row in t['rows']:
        if row['kind']!='absolute':continue
        ind=independent_table(pop,row['SE'],row['R'],Rg)
        assert abs(row['plugin_busy_core_hours']-ind['busy'])<=1e-6*ind['busy'],(row['SE'],row['plugin_busy_core_hours'],ind['busy'])
        assert abs(row['floor_fraction']-ind['floor_fraction'])<=1e-9 and abs(row['F']-ind['F'])<=1e-6*max(ind['F'],1e-12),(row['SE'],row['F'],ind['F'])
        assert abs(row['realistic_busy_core_hours']-ind['realistic'])<=1e-6*ind['realistic'] and abs(row['allocated_su']-row['realistic_busy_core_hours']/0.9)<=1e-9*row['allocated_su']
        if 0<ind['floor_fraction']<1:mixed+=1
        if ind['floor_fraction']==1:assert row['realistic_busy_core_hours']==row['plugin_busy_core_hours']   # floor-bound graphs x1
    assert mixed>=2,'no row with a partly binding floor'
    # alpha = 1/2 without a binding floor: (sum sigma sqrt c)^2/(4 SE^2)
    SE=0.05;o=pr.optimum(pop,SE,0.5,64);closed=sum(v[0]*math.sqrt(v[1])for v in pop.values())**2/(4*SE**2)/3600
    assert o['floor_fraction']==0 and abs(o['busy_core_hours']-closed)<=1e-6*closed,(o['busy_core_hours'],closed)
    # switching one group from R = 8 to 16 changes F by w_G rho (15/14 - 7/6)
    row=next(r for r in t['rows']if r['kind']=='absolute'and 0<r['floor_fraction']<1 and r['R']==64);G=('a','free',6)
    spec2=dict(spec);spec2[G]=(16,120);P2=FakePF(spec2,np.random.default_rng(77))
    t2=pr.cost_table(P2,J8,0.9,{'central':0.5},p8,None,100.);row2=next(r for r in t2['rows']if r['kind']=='absolute'and r['SE']==row['SE']and r['R']==64)
    w=row['factors']['a_free_L6']['w'];hand=w*pr.RHO*(15/14-7/6)
    assert abs((row2['F']-row['F'])-hand)<=1e-9,(row2['F']-row['F'],hand)
    ok('A-DES-3: cost_table on a mixed synthetic pilot (L6/L7 at R = 8, L8 at R = 16): sigma_g with ddof = 1; plug-in busy hours, floor fraction, '
       'F = sum w_G F_G, realistic and allocated hours equal an independent water-filling (%d rows with a partly binding floor; floor-bound x1); '
       'alpha = 1/2 with no binding floor equals (sum sigma sqrt c)^2/(4 SE^2); one group R 8 -> 16 changes F by w_G rho (15/14 - 7/6) = %.6g'%(mixed,hand))

def heldout_oracle():
    rng=np.random.default_rng(12);vals={'raw':[],'corrected':[]};R=16
    for _ in range(40):
        G=5000;sig=np.exp(rng.normal(0,1,G));c=np.exp(rng.normal(-9,1,G));s_pf=(rng.normal(0,1,(G,R))*sig[:,None]).std(1,ddof=1)
        d=pr.design_penalty_heldout(sig,s_pf,c,R);vals['raw'].append(d['raw']);vals['corrected'].append(d['corrected'])
    m={k:float(np.mean(v))for k,v in vals.items()};se={k:float(np.std(v,ddof=1))/math.sqrt(len(v))for k,v in vals.items()}
    assert abs(m['corrected']-1)<=3*se['corrected']and abs(m['raw']-1/pr.c4(R)**2)<=3*se['raw'],(m,se,1/pr.c4(R)**2)
    ok('A-DES-3: item 12 on Gaussian fakes with an oracle design (s_PA = sigma, R_PF = 16): corrected value 1 and raw 1/c4(16)^2 within 3 SE',values=m)

# ---------------------------------------------------------------- actions 1, 3 and 5 on an injected pilot (hand values)
def camp_of(groups:dict,R=R8)->pr.Camp:
    """A pilot_report.Camp without files: groups[(c, s, L)] = {g: (total points, jets per replicate, (tail_sum, top 16) per
    replicate, busy seconds per point)}; R is the replicate count, or {(c, s, L): R}; Camp.at and the length rule work on
    it unchanged."""
    c=pr.Camp.__new__(pr.Camp);c.run=Path('/injected');c.g={}
    for key,graphs in groups.items():
        Rk=R[key]if isinstance(R,dict)else R
        G={'reps':Rk,'total':{},'jets':{},'tails':{},'prefix':{},'cost':{},'promo':[]}
        for g,(total,jets,tails,cpp) in graphs.items():
            G['total'][g]=total;G['cost'][g]=(total,cpp*total)
            for r in range(Rk):G['jets'][(r,g)]=list(jets[r]);G['tails'][(r,g)]=(total,tails[r][0],list(tails[r][1]),'0')
        c.g[key]=G
    return c

def pm(sig:float,n:int,R:int=R8)->list:
    """Replicate values with mean 0 and n Var_ddof1 = sig^2 exactly (alternating +-a)."""
    a=math.sqrt((R-1)/R*sig**2/n);return [a if r%2==0 else -a for r in range(R)]

def hand_p8(qs:list)->float:
    m=sum(qs)/len(qs);v=sum((q-m)**2 for q in qs)/(len(qs)-1);return 1.0865*math.exp(0.0890*(v-1.8696))

def hand_q(y:list)->float:
    def var(x):m=sum(x)/len(x);return sum((u-m)**2 for u in x)/(len(x)-1)
    return math.log(var(y[:4])/var(y[4:8]))

def hand_p90(v:list)->float:
    s=sorted(v);x=0.9*(len(s)-1);i=int(math.floor(x));return s[i]+(x-i)*(s[min(i+1,len(s)-1)]-s[i])

def actions_hand():
    """Actions 1, 3 and 5 of `full` on an injected pilot with a heavy-tailed L7 graph (Pareto a = 1.5): actions 1-5 act on
    L8 graphs only; action 3 against hand values with an empty PC, where a P1c graph's 32,768-point sigma (from PA)
    raises its share above 3%, and with a PC that holds a larger one; action 5 strata and pooled values against
    hand-computed Var(Q)."""
    rng=np.random.default_rng(31);J8={7:np.array([0.,0.,0.,1.]),8:np.array([0.,1.])};light=lambda:[(1.,[1.]*16)]*R8
    # action 1: L8 free graphs 0..5 (graph 3 heavy), L7 free graphs 0..3 and 17 (graph 17 heavy, Pareto 1.5)
    grp={}
    for t in 'ab':
        for L,ids in ((8,range(6)),(7,(0,1,2,3,17))):
            d={}
            for g in ids:
                U=np.clip(rng.random((R8,N1)),1e-300,1.);X=U**(-1/1.5)if (L,g)in((8,3),(7,17))else np.abs(_ppf(U))
                tl=[(x[0],x[1])for x in tails_of(X,N1)];w=2*(9-L);d[g]=(N1,[[0.]*(w-1)+[float(x.mean())]for x in X],tl,1e-4)
            grp[(t,'free',L)]=d
    P=camp_of(grp)
    l7=pr.tail_stats([(x[0],x[1],N1)for x in grp[('a','free',7)][17][2]])
    assert l7['xi']>pr.XI_SCREEN,l7   # the L7 graph is heavy-tailed: a screen at L7 would flag it
    scr=pr.action1_screen(P);assert [x['graph']for x in scr if x['flag']]==[3]and 17 not in {x['graph']for x in scr}and len(scr)==6,scr
    # action 3: 40 free and 10 power L8 graphs at sigma 1 (cost 1e-4 s/point), the L7 groups (graph 117 heavy, sigma 50)
    # never enter; P1c graph 1 (free) confirmed, its PA 32,768-point sigma 2; a PC graph would add its own
    grp3={}
    for t in 'ab':
        grp3[(t,'free',8)]={g:(N1,[[0.,v]for v in pm(1.,N1)],light(),1e-4)for g in range(40)}
        grp3[(t,'power',8)]={g:(N1,[[0.,v]for v in pm(1.,N1)],light(),2e-4)for g in range(10)}
        grp3[(t,'free',7)]={g:(N1,[[0.,0.,0.,v]for v in pm(50. if g==117 else 1.,N1)],light(),1e-4)for g in (0,117)}
    P3=camp_of(grp3);pop=pr.per_graph_sigma(P3,J8)
    A=camp_of({(t,'free',8):{1:(N2,[[0.,v]for v in pm(2.,N2)],light(),1e-4)}for t in 'ab'})
    conf=[{'sector':'free','graph':1,'confirmed':True},{'sector':'free','graph':117,'confirmed':True}]   # 117: an L7 graph, no L8 graph of that id
    def hand(sig1):
        sig=[sig1 if g==1 else 1. for t in 'ab'for g in range(40)];c=[1e-4]*80;w=[s*math.sqrt(x)for s,x in zip(sig,c)]
        conf_w=sum(w[i]for i,g in enumerate([g for t in 'ab'for g in range(40)])if g==1)
        n=[s/math.sqrt(x)for s,x in zip(sig,c)];n90=hand_p90(n);gs=[g for t in 'ab'for g in range(40)]
        cost=sum((n90 if g==1 else nn)*x for g,nn,x in zip(gs,n,c));shc=sum(n90*x for g,x in zip(gs,c)if g==1)
        return conf_w/sum(w),shc/cost
    h0=pr.action3_hold(P3,None,None,J8,conf,pop)                       # no 32,768-point rows anywhere: PF's 4,096-point sigma
    vs,cs=hand(1.);assert abs(h0['free']['variance_share']-vs)<=1e-12 and abs(h0['free']['cost_share']-cs)<=1e-12 and h0['free']['hold']is False,(h0,vs,cs)
    h1=pr.action3_hold(P3,A,None,J8,conf,pop)                          # empty PC: PA's P1c rows give sigma(32,768) = 2
    vs1,cs1=hand(2.);assert abs(h1['free']['variance_share']-vs1)<=1e-12 and abs(h1['free']['cost_share']-cs1)<=1e-12 and h1['free']['hold']is True,(h1,vs1,cs1)
    assert vs<pr.HOLD_SHARE<vs1 and h1['free']['sigma_from_32768']==['a:1','b:1']and h1['power']=={**h1['power'],'confirmed':0,'variance_share':0.,'hold':False}
    C=camp_of({(t,'free',8):{1:(N2,[[0.,v]for v in pm(3.,N2)],light(),1e-4)}for t in 'ab'})
    h2=pr.action3_hold(P3,A,C,J8,conf,pop);vs2,cs2=hand(3.);assert abs(h2['free']['variance_share']-vs2)<=1e-12 and abs(h2['free']['cost_share']-cs2)<=1e-12,(h2,vs2)
    # action 5: stratum ('free', 0, 0) with 250 graphs (500 graph-campaign Q values) of Student-t-like replicates (heavy
    # Q spread), stratum ('free', 0, 1) with 100 such graphs (200 Q: never flagged), power with 300 Gaussian graphs; L7
    # graphs (the L <= 7 class, the C8 Jacobian combination J8[7] . jets) enter no stratum
    grp5={};ids={('free',0,0):range(250),('free',0,1):range(250,350),('power',0,0):range(300)};Y={}
    for t in 'ab':
        for s in ('free','power'):
            d={}
            for g in (x for k,v in ids.items()if k[0]==s for x in v):
                y=rng.standard_t(2,R8)if s=='free'else rng.normal(0,1,R8);Y[(t,s,8,g)]=[float(v)for v in y];d[g]=(N1,[[0.,v/3]for v in Y[(t,s,8,g)]],light(),1e-4)
            grp5[(t,s,8)]=d
        d={}
        for g in range(30):
            y=rng.normal(0,1,R8);Y[(t,'free',7,g)]=[float(v)for v in y];d[g]=(N1,[[0.,0.,0.,v]for v in Y[(t,'free',7,g)]],light(),1e-4)
        grp5[(t,'free',7)]=d
    P5=camp_of(grp5);strata,pooled=pr.action5(P5,J8,{k:list(v)for k,v in ids.items()})
    for k,v in ids.items():
        qs=[hand_q(Y[(t,k[0],8,g)])for t in 'ab'for g in v];key=f'{k[0]}|T{ps.T_LABELS[0]}|M{k[2]}'
        e=strata[key];assert e['graph_campaign_Q']==len(qs)and abs(e['P8_hat']-hand_p8(qs))<=1e-12*hand_p8(qs),(key,e,hand_p8(qs))
        assert e['flag']==(len(qs)>=500 and hand_p8(qs)>1.196),(key,e)
    assert strata[f'free|T{ps.T_LABELS[0]}|M0']['flag']is True and strata[f'free|T{ps.T_LABELS[0]}|M1']['flag']is False
    assert len(strata)==3   # no L7 stratum
    for (s,cl),qs in ((('free','L8'),[hand_q(Y[(t,'free',8,g)])for t in 'ab'for g in range(350)]),(('power','L8'),[hand_q(Y[(t,'power',8,g)])for t in 'ab'for g in range(300)]),
                      (('free','L<=7'),[hand_q(Y[(t,'free',7,g)])for t in 'ab'for g in range(30)])):
        assert abs(pooled[f'{s}|{cl}']['P8_hat']-hand_p8(qs))<=1e-12*hand_p8(qs),(s,cl)
    ok('A-DES-3: actions 1, 3 and 5 on an injected pilot: action 1 flags only the heavy L8 graph and never sees the heavy L7 graph (xi %.2f at '
       'L7); action 3 equals the hand variance and cost shares with no 32,768-point rows (%.4f, no hold), with an empty PC where the P1c graph\'s '
       'PA sigma(32,768) = 2 > PF\'s 1 raises the share to %.4f > 3%% (hold), and with a PC sigma 3 (%.4f); the L7 groups and a confirmation id '
       'with no L8 graph change nothing; action 5\'s strata (P8_hat from Var(Q), the 500-value flag rule) and pooled L8 / L <= 7 values equal '
       'hand-computed Q statistics; L7 graphs enter no stratum'%(l7['xi'],vs,vs1,vs2),stratum_flag=strata)
    return h1

def heldout_per_sector():
    """E.6 item 12 per sector (Stage 3a repair round 2): after action 4 PF has free L8 at R = 8 and power L8 at R = 16
    (--group-replicates power:8=16). heldout_by_sector gives each sector the raw value over its own stage-A stratified
    graph-campaigns (a and b pooled) and the correction c4(R_PF)^2 of its own R, equal to a hand computation; the
    selection's key order changes nothing; a sector whose two campaigns' PF L8 groups differ in R is refused; and
    cost_table takes each sector's value into that sector's L8 P_hat only."""
    rng=np.random.default_rng(41);J8={8:np.array([0.,1.])};Rs={'free':8,'power':16};ids={'free':list(range(12)),'power':list(range(100,110))}
    light=lambda R:[(1.,[1.]*16)]*R;pf={};pa={};cpp={};sig={}
    for s,R in Rs.items():
        for g in ids[s]:sig[(s,g)]=float(np.exp(rng.normal(0,.7)));cpp[(s,g)]=float(np.exp(rng.normal(-8,.5)))
        for t in 'ab':
            pf[(t,s,8)]={g:(N1,[[0.,float(v)]for v in rng.normal(0,1,R)*sig[(s,g)]],light(R),cpp[(s,g)])for g in ids[s]}
            pa[(t,s,8)]={g:(N1,[[0.,float(v)]for v in rng.normal(0,1,R8)*sig[(s,g)]],light(R8),cpp[(s,g)])for g in ids[s]}
    P=camp_of(pf,{k:Rs[k[1]]for k in pf});A=camp_of(pa)
    sel={'power:8':[{'id':g,'label':'stratified'if g!=100 else'p1c'}for g in ids['power']],'free:8':[{'id':g,'label':'stratified'}for g in ids['free']]}
    A.sel={'groups':sel};ho=pr.heldout_by_sector(A,P,J8)
    def sd(v):m=sum(v)/len(v);return math.sqrt(sum((x-m)**2 for x in v)/(len(v)-1))
    for s,R in Rs.items():
        a,b,c=[],[],[]
        for g in (x['id']for x in sel[f'{s}:8']if x['label']=='stratified'):
            for t in 'ab':
                a.append(sd([pa[(t,s,8)][g][1][r][1]for r in range(R8)]));b.append(sd([pf[(t,s,8)][g][1][r][1]for r in range(R)]));c.append(cpp[(s,g)])
        w=[math.sqrt(x)for x in c];raw=sum(y*y/x*u for x,y,u in zip(a,b,w))*sum(x*u for x,u in zip(a,w))/sum(y*u for y,u in zip(b,w))**2
        c4sq=2/(R-1)*math.exp(2*(math.lgamma(R/2)-math.lgamma((R-1)/2)))
        e=ho[s];assert e['R_PF']==R and e['graphs']==len(a)and abs(e['raw']-raw)<=1e-12*raw and abs(e['c4_sq']-c4sq)<=1e-13 and abs(e['corrected']-raw*c4sq)<=1e-12*raw,(s,e,raw,c4sq)
    assert abs(ho['power']['c4_sq']-pr.c4(16)**2)<=1e-15 and abs(ho['free']['c4_sq']-pr.c4(8)**2)<=1e-15
    A.sel={'groups':dict(reversed(list(sel.items())))};assert pr.heldout_by_sector(A,P,J8)==ho   # the key order changes nothing
    P.g[('b','power',8)]['reps']=8
    try:pr.heldout_by_sector(A,P,J8);raise AssertionError('mixed R within a sector accepted')
    except ValueError as x:assert 'one R_PF per sector'in str(x)and '[8, 16]'in str(x),x
    # cost_table: each sector's held-out value enters only that sector's L8 P_hat
    spec={(t,s,L):(16 if L==8 else 8,40)for t in 'ab'for s in ('free','power')for L in (7,8)};Q=FakePF(spec,np.random.default_rng(5))
    J={L:np.array([0.]*(2*(9-L)-1)+[1.])for L in (7,8)};p8={(s,c):1.0 for s in ('free','power')for c in ('L8','L<=7')}
    t0=pr.cost_table(Q,J,0.9,{'central':0.5},p8,None,100.);t1=pr.cost_table(Q,J,0.9,{'central':0.5},p8,{'free':1.13},100.)
    row=lambda t:next(r for r in t['rows']if r['kind']=='absolute'and r['target']==0.5)
    f0,f1=row(t0)['factors'],row(t1)['factors'];want=pr.realism(1.13,16)
    for k in f1:
        if k.endswith('free_L8'):assert abs(f1[k]['P_G']-want['P_G'])<=1e-12 and abs(f1[k]['kappa_G']-want['kappa_G'])<=1e-12,(k,f1[k],want)
        else:assert f1[k]['P_G']==f0[k]['P_G']and f1[k]['kappa_G']==f0[k]['kappa_G'],k
    assert f1['a_free_L8']['P_G']>f0['a_free_L8']['P_G']
    ok('A-DES-3: item 12 per sector (PF free L8 R = 8, power L8 R = 16): each sector\'s raw value and c4(R_PF)^2 (%.6f, %.6f) equal a hand '
       'computation on its own stratified graph-campaigns; the selection key order changes nothing; mixed R within a sector is refused; '
       'cost_table puts a sector\'s held-out value into that sector\'s L8 P_hat only'%(ho['free']['c4_sq'],ho['power']['c4_sq']),
       heldout={s:{k:v for k,v in e.items()}for s,e in ho.items()})

# ---------------------------------------------------------------- A-DES-3, zero-channel graphs with real tail fields
def finite_tree(x,where='')->None:
    """Every float in a pilot_report output (dicts, lists, tuples) is finite: no NaN and no infinity reaches a reader."""
    if isinstance(x,float):
        if not math.isfinite(x):raise AssertionError(f'non-finite {x} at {where}')
    elif isinstance(x,dict):
        for k,v in x.items():finite_tree(v,f'{where}/{k}')
    elif isinstance(x,(list,tuple)):
        for i,v in enumerate(x):finite_tree(v,f'{where}[{i}]')

def zc_camp(k:dict,doc:dict)->tuple:
    """A pilot_report.Camp of one kernel entry of a c8-d3-zero-channel-tails-1 document, built from the worker's raw rows
    by the merge's rules (production._final_pass, C.3): per replicate the full stream (jets: the exact sum of the task
    values; tails: tools/tails.merge_tails) and the nest-point prefix row (jets: the running sum scaled by total/P;
    tails: the rows ending at or before P). The groups sit under the kernel's own key (campaign, sector, L), which
    full()'s item 2 reads at any L, and under (campaign, sector, 8), the only keys screen_graph and confirm_graph read
    (the thresholds act on L8 graphs; here the real rows of a lower-loop zero-channel kernel stand in for one)."""
    import decimal,tails
    from decimal import Decimal as Dd
    P=doc['nest'][0];N=doc['points'];R=doc['replicates'];g=k['graph'];c=pr.Camp.__new__(pr.Camp);c.run=Path('/zero-channel');c.g={}
    for t,cd in k['campaigns'].items():
        G={'reps':R,'total':{g:N},'jets':{},'tails':{},'prefix':{},'cost':{g:(N,0.)},'promo':[]}
        for r in range(R):
            rows=sorted((x for x in cd['rows']if x['rep']==r),key=lambda x:x['begin'])
            assert [(x['begin'],x['end'],x['total'])for x in rows]==[(0,P,N),(P,N,N)]and all(x['graph']==g for x in rows),(t,r,rows)
            with decimal.localcontext()as ctx:
                ctx.prec=50;run=[Dd(0)]*len(rows[0]['values']);pre=None
                for x in rows:
                    run=[a+Dd(v)for a,v in zip(run,x['values'])]
                    if x['end']==P:pre=[float(v*(Dd(N)/Dd(P)))for v in run]
                full=[float(v)for v in run]
            m=tails.merge_tails(rows)[(r,g)];m1=tails.merge_tails([x for x in rows if x['end']<=P])[(r,g)]
            assert m['points']==N and m1['points']==P
            G['jets'][(r,g)]=full;G['tails'][(r,g)]=(N,float(m['tail_sum']),[float(v)for v in m['tail_top']],m['tail_argmax'])
            G['prefix'][(r,g,P)]=(pre,float(m1['tail_sum']),[float(v)for v in m1['tail_top']],m1['tail_argmax'])
        c.g[(t,k['sector'],k['L'])]=G;c.g[(t,k['sector'],8)]=G
    return c,P,N

def zero_channel_check(doc:dict,label:str)->dict:
    """A-DES-3: a zero-channel graph's real tail fields (the worker's rows of a kernel with 3 w_B = w_A: max_abs 0 at every
    point, tail_top and tail_sum positive) through pilot_report: tail_stats at both lengths and both campaigns (full()'s
    item 2), screen_graph at 4,096 points, confirm_graph (alpha unknown and 0.5), and the replicate statistics of the
    paired lengths (split_q, sigma): every entry is finite or "undefined", never a NaN or an infinity compared with a
    threshold; screen flags and confirmations are booleans."""
    from decimal import Decimal as Dd
    if doc.get('schema')!='c8-d3-zero-channel-tails-1':raise AssertionError(f'{label}: not a c8-d3-zero-channel-tails-1 document')
    names=[f'{k["sector"]} L{k["L"]} G{k["graph"]}'for k in doc['kernels']]
    if 'power L3 G7'not in names:raise AssertionError(f'{label}: no power-L3 G7 rows (A-DES-3 names that kernel): {names}')
    out={}
    for k,name in zip(doc['kernels'],names):
        for cd in k['campaigns'].values():
            for x in cd['rows']:
                if not(Dd(x['max_abs'])==0 and Dd(x['tail_top'][0])>0 and Dd(x['tail_sum'])>0 and Dd(x['tail_sum']).is_finite()):
                    raise AssertionError(f'{label} {name}: row uid {x["uid"]} is not zero-channel (max_abs {x["max_abs"]}, tail_sum {x["tail_sum"]})')
        c,P,N=zc_camp(k,doc);s,L,g=k['sector'],k['L'],k['graph'];rec={'stats':{}}
        for t in sorted(k['campaigns']):
            for n in (P,N):
                jets,tl=pr.rows_at(c,(t,s,L),g,n);x=pr.tail_stats(tl);finite_tree(x,f'{name} {t} {n} tail_stats')
                if 'undefined'not in x:assert all(isinstance(x[f],float)for f in ('xi','share_max','share_logmean')),x
                y=pr.y_top(jets);q=pr.split_q(y);finite_tree(q,f'{name} {t} {n} split_q');sig=math.sqrt(n*float(np.var(y,ddof=1)))
                assert math.isfinite(sig),(name,t,n,sig)
                rec['stats'][f'{t}_{n}']={kk:v for kk,v in x.items()if kk!='shares'}|{'sigma_top_slot':sig,'Q_values':len(q)}
        sc=pr.screen_graph(c,s,g,P);finite_tree(sc,f'{name} screen');assert isinstance(sc['flag'],bool),sc
        for t,e in sc['campaigns'].items():assert 'undefined'in e or (math.isfinite(e['xi'])and math.isfinite(e['share_max'])),(name,t,e)
        cfs=[pr.confirm_graph(c,s,g),pr.confirm_graph(c,s,g,0.5)]
        for cf in cfs:
            finite_tree(cf,f'{name} confirm');assert isinstance(cf['confirmed'],bool),cf
            assert cf.get('undefined')or math.isfinite(cf['xi_mean_32768']),cf
        rec.update(screen={'flag':sc['flag'],'undefined':sc['undefined'],'campaigns':sc['campaigns']},
                   confirm={'confirmed':cfs[0]['confirmed'],'xi_mean_32768':cfs[0].get('xi_mean_32768'),'undefined':cfs[0].get('undefined'),
                            'supporting_alpha_half':cfs[1].get('supporting')})
        out[name]=rec
    defined=sum(1 for r in out.values()for v in r['stats'].values()if 'undefined'not in v);undefined=sum(1 for r in out.values()for v in r['stats'].values()if 'undefined'in v)
    ok(f'A-DES-3 zero-channel graphs with real tail fields ({label}; {", ".join(names)}; worker {doc["worker"]["sha256"][:12]}): every row has max_abs 0 '
       f'and positive tail fields; tail_stats at {P:,} and {N:,} points in both campaigns ({defined} finite, {undefined} "undefined"), '
       f'screen_graph, confirm_graph (alpha unknown and 1/2), split_q and sigma give finite values or "undefined", no NaN or infinity; '
       f'flags and confirmations are booleans',kernels=out,worker=doc['worker'],slurm_job=doc.get('slurm_job'))
    return out

ZC_FIXTURE=ROOT/'tests/fixtures/zero_channel_tails.json'
ZC_FIXTURE_SHA256='df30569db9e69d34f48c6e6f1147009975de717912e3c1fac31b269f914ec372'   # Expanse job 54672564 (repair3b on 592fb7f2aa4f)

def zero_channel_fixture()->dict:
    """The pinned real rows (tests/fixtures/zero_channel_tails.json) through zero_channel_check on the Mac."""
    import hashlib
    data=ZC_FIXTURE.read_bytes();h=hashlib.sha256(data).hexdigest()
    if h!=ZC_FIXTURE_SHA256:raise AssertionError(f'{ZC_FIXTURE}: sha256 {h} is not the pinned {ZC_FIXTURE_SHA256}')
    doc=json.loads(data);assert doc['slurm_job']=='54672564'and doc['worker']['sha256'].startswith('24adff54'),doc['worker']
    return zero_channel_check(doc,'tests/fixtures/zero_channel_tails.json, Expanse job 54672564')

def zero_channel_synthetic():
    """The guards behind the zero-channel rule on synthetic rows: a non-finite tail_sum or top value, or an overflowing
    replicate variance, gives "undefined" (tail_stats) or None (confirm_graph's supporting values); none is compared."""
    assert pr.tail_stats([(math.inf,[1.]*16,N1)])=={'undefined':'a replicate with a non-finite tail_sum'}
    assert pr.tail_stats([(math.nan,[1.]*16,N1)])=={'undefined':'a replicate with a non-finite tail_sum'}
    assert 'undefined'in pr.tail_stats([(5.,[math.nan]+[1.]*15,N1)])and 'undefined'in pr.tail_stats([(5.,[math.inf]+[1.]*15,N1)])
    c=FakeCamp();rng=np.random.default_rng(3)
    for t in 'ab':
        for n in (N1,N2):
            X=np.abs(_ppf(np.clip(rng.random((R8,n)),1e-300,1.)));c.data[((t,'free',8),0,n)]=([[0.,1e300*(-1)**r]for r in range(R8)],tails_of(X,n))
    with np.errstate(over='ignore'):cf=pr.confirm_graph(c,'free',0,0.5)
    finite_tree(cf,'overflow');assert all(v['V_ratio']is None for v in cf['supporting'].values()),cf
    assert pr.fin(math.nan)is None and pr.fin(math.inf)is None and pr.fin(1.5)==1.5 and pr.fin(True)is None
    ok('A-DES-3: a non-finite tail_sum or top-16 value makes tail_stats "undefined"; an overflowing replicate variance leaves confirm_graph\'s '
       'V ratio None; no NaN or infinity in its output')

# ---------------------------------------------------------------- Stage 3a repair round 3
def graph_bootstrap():
    """E.6 items 9-10: the bands resample GRAPHS, a graph's two campaigns together. (1) The reviewer's case (40 graphs whose
    two campaigns share the graph's variance ratio): the band over graph units is wider than the band over graph-campaign
    entries (1.48 x in the review; > 1.2 x required) and equals exactly the band over one-entry graph units (alpha_hat is
    a ratio of sums, so a unit's duplicated entry changes nothing). (2) Spies on boot_band inside alpha_p1c and action5:
    one unit per graph, holding the entries of campaigns a and b of THAT graph (hand values), the central alpha band
    stratified by sector. (3) A stratified resample keeps every stratum's size."""
    rng=np.random.default_rng(1);per=[]
    for g in range(40):f=float(rng.lognormal(0,.8));per.append((1.,f*8**(-(2*.53-1))))
    st=lambda vv:pr.alpha_hat([x[1]for u in vv for x in u],[x[0]for u in vv for x in u])
    b_g=pr.boot_band([[x,x]for x in per],st);b_1=pr.boot_band([[x]for x in per],st);b_gc=pr.boot_band([[x]for x in per for _ in 'ab'],st)
    ratio=(b_g[1]-b_g[0])/(b_gc[1]-b_gc[0]);assert np.allclose(b_g,b_1,rtol=1e-12,atol=0)and ratio>1.2,(b_g,b_1,b_gc,ratio)
    # (2) alpha_p1c: P1c graphs 0..5 (free) and 10..12 (power); campaign t of graph g has V1 = (g+1)(1 or 2), V2 = 0.9 V1
    c=FakeCamp();want={}
    for s,ids in (('free',range(6)),('power',range(10,13))):
        for g in ids:
            for t in 'ab':
                v1=(g+1)*(1 if t=='a'else 2);want[(s,g,t)]=v1
                for n,v in ((N1,v1),(N2,.9*v1)):c.data[((t,s,8),g,n)]=([[0.,y/3]for y in pm(math.sqrt(v),n)],[(1.,[1.]*16,n)]*R8)
    calls=[];orig=pr.boot_band
    def spy(units,stat,*a,**k):calls.append((units,k.get('strata')));return orig(units,stat,*a,**k)
    pr.boot_band=spy
    try:al=pr.alpha_p1c(c,[('free',g)for g in range(6)]+[('power',g)for g in range(10,13)])
    finally:pr.boot_band=orig
    per_sector=[u for u,stv in calls if stv is None];strat=[(u,stv)for u,stv in calls if stv is not None]
    assert [len(u)for u in per_sector]==[6,3]and len(strat)==1 and strat[0][1]==['free']*6+['power']*3,[len(u)for u,_ in calls]
    for units,(s,ids) in zip(per_sector,(('free',range(6)),('power',range(10,13)))):
        for u,g in zip(units,ids):
            assert len(u)==2 and all(abs(x[0]-want[(s,g,t)])<=1e-9*want[(s,g,t)]for x,t in zip(u,'ab')),(s,g,u)
    assert al['bootstrap_unit'].startswith('graph')and al['band68'][0]<=al['central']<=al['band68'][1]
    # (2') action5: the pooled band's units are graphs, each holding the Q values of both campaigns of that graph
    J8={8:np.array([0.,1.]),7:np.array([0.,0.,0.,1.])};grp={};Y={}
    for t in 'ab':
        grp[(t,'free',8)]={g:(N1,[[0.,v]for v in Y.setdefault((t,8,g),[float(x)for x in rng.normal(0,1,16)])],[(1.,[1.]*16)]*16,1e-4)for g in range(12)}
        grp[(t,'free',7)]={g:(N1,[[0.,0.,0.,v]for v in Y.setdefault((t,7,g),[float(x)for x in rng.normal(0,1,16)])],[(1.,[1.]*16)]*16,1e-4)for g in range(5)}
    P=camp_of(grp,16);calls.clear();pr.boot_band=spy
    try:strata,pooled=pr.action5(P,J8,{('free',0,0):list(range(12))})
    finally:pr.boot_band=orig
    for units,_ in calls:
        L=8 if len(units)==12 else 7;assert len(units)in(12,5)
        for u,g in zip(units,range(len(units))):
            hand=[q for t in 'ab'for q in pr.split_q([3*v for v in Y[(t,L,g)]]if L==8 else Y[(t,L,g)])]
            assert len(u)==4 and np.allclose(u,hand,rtol=1e-12,atol=0),(L,g)   # R = 16: two Q per campaign, both campaigns
    assert pooled['free|L8']['graphs']==12 and pooled['free|L<=7']['graphs']==5 and pooled['free|L8']['bootstrap_unit'].startswith('graph')
    # (3) a stratified resample keeps the stratum sizes
    seen=[]
    pr.boot_band([('x',i)for i in range(5)]+[('y',i)for i in range(3)],lambda vv:seen.append(sum(1 for s,_ in vv if s=='x'))or 0.,n=50,strata=['x']*5+['y']*3)
    assert set(seen)=={5}
    ok('E.6 items 9-10: bootstrap bands resample graphs (a graph\'s two campaigns together): on the reviewer\'s 40-graph case the graph band is '
       '%.2f x the graph-campaign band and equals the one-entry-per-graph band (to rounding); spies show alpha_p1c and action5 passing one unit per graph '
       'with both campaigns\' entries of that graph (hand values), the central alpha band stratified by sector; a stratified resample keeps the '
       'stratum sizes'%ratio,ratio=ratio)

def indep_opt(pop:dict,SE:float,a:float,R:int)->tuple:
    """The E.7 optimum by hand at any alpha: n_g = max(4096, (mu 2a k_g/(R c_g))^(1/(2a+1))), k_g = sigma^2 n_ref^(2a-1)/(4R),
    sum k_g n_g^(-2a) = SE^2 (own bisection on mu); returns (busy core-h, floor core-h, non-floor busy per group)."""
    keys=list(pop);sig=np.array([pop[k][0]for k in keys]);c=np.array([pop[k][1]for k in keys]);nref=np.array([pop[k][3]for k in keys],float)
    k=sig**2*nref**(2*a-1)/(4*R);lo,hi=-200.,200.
    def n_of(lm):return np.maximum(4096.,(math.exp(lm)*2*a*k/(R*c))**(1/(2*a+1)))
    for _ in range(300):
        mid=(lo+hi)/2
        if (k/n_of(mid)**(2*a)).sum()>SE**2:lo=mid
        else:hi=mid
    n=n_of(hi);bound=n<=4096*1.000001;busy=float((R*n*c).sum())/3600;floor=float((R*n*c)[bound].sum())/3600;w={}
    for kk,nn,cc,b in zip(keys,n,c,bound):
        if not b:w[kk[:3]]=w.get(kk[:3],0.)+nn*cc
    return busy,floor,w

def indep_real(pop,SE,a,R,P8:dict,Rg:dict)->tuple:
    """(realistic core-h, F, Gaussian-kappa F) by hand from indep_opt and pr.realism (oracle-tested above)."""
    busy,floor,w=indep_opt(pop,SE,a,R);tot=sum(w.values());F=Fg=0.
    for G,x in w.items():
        r=pr.realism(max(P8[(G[1],'L8'if G[2]==8 else'L<=7')],pr.penk(8,0.)),Rg[G]);F+=x/tot*r['F_G'];Fg+=x/tot*r['P_G']*pr.kappa(Rg[G])*pr.RHO
    return floor+F*(busy-floor),F,Fg

def cost_table_bands():
    """E.7's bands and columns against an independent recomputation (mixed synthetic pilot: L6/L7 at R = 8, L8 at R = 16,
    a partly binding floor): each row's realistic cost at the central alpha and P8_hat; F at both ends of the P8_hat band;
    the optimum at both ends of the alpha band; for relative targets the SE at both ends of the |C8| band; the row band =
    the envelope over all those corners (busy core-h, SU, wall hours); the Gaussian-kappa column; the allocated SU per
    MP self-check mode from a model's mp_check_overhead (model in 'on'; in 'stride16'; none: "pending P1"); a |C8| band
    that reaches 0 leaves the relative rows unbounded above."""
    spec={('a','free',6):(8,60),('b','free',6):(8,60),('a','power',7):(8,40),('b','power',7):(8,40),('a','free',8):(16,80),('b','free',8):(16,80),
          ('a','power',8):(16,30),('b','power',8):(16,30)}
    P=FakePF(spec,np.random.default_rng(78));P.m['mp_check']='on';J8={L:np.array([0.]*(2*(9-L)-1)+[1.])for L in range(3,9)};pop=pr.per_graph_sigma(P,J8)
    Rg={G:R for G,(R,_)in spec.items()};p8={('free','L8'):1.12,('power','L8'):1.15,('free','L<=7'):1.10,('power','L<=7'):1.09}
    pb={k:[v-.03,v+.04]for k,v in p8.items()};lo={k:v[0]for k,v in pb.items()};hi={k:v[1]for k,v in pb.items()};al={'central':.53,'band68':[.5,.56]};eta=.9
    ratios=pr.mp_ratios({'mp_check':'on','mp_check_overhead':{'off':.8,'stride16':.9}},'on','test model')
    t=pr.cost_table(P,J8,eta,al,p8,None,100.,pb,10.,ratios);checked=0;rel=0
    for row in t['rows']:
        SE,R=row['SE'],row['R'];real,F,Fg=indep_real(pop,SE,.53,R,p8,Rg)
        assert abs(row['realistic_busy_core_hours']-real)<=1e-6*real and abs(row['F']-F)<=1e-6*max(F,1e-12)and abs(row['F_kappa_gauss']-Fg)<=1e-6*max(Fg,1e-12),(SE,R,row['F'],F)
        assert abs(row['band_p8']['F'][0]-indep_real(pop,SE,.53,R,lo,Rg)[1])<=1e-6 and abs(row['band_p8']['F'][1]-indep_real(pop,SE,.53,R,hi,Rg)[1])<=1e-6
        for a,x in zip(al['band68'],row['band_alpha']['realistic_busy_core_hours']):h=indep_real(pop,SE,a,R,p8,Rg)[0];assert abs(x-h)<=1e-6*h,(SE,R,a,x,h)
        SEs=[SE]
        if row['kind']=='relative':
            rel+=1;assert row['band_c8']['SE']==[row['target']*110.,row['target']*90.]and not row['band_c8']['unbounded_above'];SEs+=row['band_c8']['SE']
            for x,s2 in zip(row['band_c8']['realistic_busy_core_hours'],row['band_c8']['SE']):h=indep_real(pop,s2,.53,R,p8,Rg)[0];assert abs(x-h)<=1e-6*h
        env=[indep_real(pop,s2,a,R,m,Rg)[0]for s2 in SEs for a in (.53,.5,.56)for m in (p8,lo,hi)]
        b=row['band'];assert abs(b['realistic_busy_core_hours'][0]-min(env))<=1e-6*min(env)and abs(b['realistic_busy_core_hours'][1]-max(env))<=1e-6*max(env),(SE,b,min(env),max(env))
        assert abs(b['allocated_su'][1]-max(env)/eta)<=1e-6*max(env)/eta and abs(b['wall_hours_22_nodes'][0]-min(env)/eta/(22*128))<=1e-6*min(env)
        assert b['corners']==len(env)and b['realistic_busy_core_hours'][0]<=row['realistic_busy_core_hours']<=b['realistic_busy_core_hours'][1]
        mp=row['allocated_su_by_mp_check'];assert mp['on']==row['allocated_su']and abs(mp['off']-.8*mp['on'])<=1e-12*mp['on']and abs(mp['stride16']-.9*mp['on'])<=1e-12*mp['on']
        checked+=1
    assert rel==6 and checked==len(t['rows'])
    r2=pr.mp_ratios({'mp_check':'stride16','mp_check_overhead':{'on':1.25,'off':.9}},'on','m2');assert abs(r2['off']-.9/1.25)<=1e-15 and abs(r2['stride16']-1/1.25)<=1e-15
    r3=pr.mp_ratios({'mp_check':'on'},'on','m3');assert all(v.startswith('pending P1')for v in r3.values())and set(r3)=={'off','stride16'}
    t3=pr.cost_table(P,J8,eta,{'central':.5},p8,None,5.,None,6.,r3)
    for row in t3['rows']:
        assert all(isinstance(v,str)for k,v in row['allocated_su_by_mp_check'].items()if k!='on')and 'band_p8'not in row and 'band_alpha'not in row
        if row['kind']=='relative':assert row['band']['unbounded_above']and row['band_c8']['C8_abs']==[11.]and row['band_c8']['unbounded_above']
    ok('E.7: on a mixed synthetic pilot every row of the cost table (%d, %d relative) equals an independent recomputation: the realistic cost and F '
       'at the central alpha and P8_hat, the Gaussian-kappa F, F at both ends of the P8_hat band, the optimum at both ends of the alpha band, the '
       'relative rows at both ends of the |C8| band, and the row band as the envelope of all corners (core-h, SU, wall hours); SU per MP '
       'self-check mode from mp_check_overhead (model in on: x0.8/x0.9; in stride16: off 0.72, stride16 0.8; none: "pending P1"); a |C8| band '
       'reaching 0 leaves the relative rows unbounded above'%(checked,rel))

def reproject_hand():
    """A-PIL-2's re-projection on a synthetic campaign (free L7 100 and L8 1,000 graphs, power L8 300; 0.01 s per L8 point,
    0.002 per L7 point; f_E 1.1, eta 1.2, 16 threads, 0.25 h indices): the PF and PC busy hours, the auto lane times
    (slurm_submit.auto_lane_time) and reservations, the step peaks (the runbook's shared jobs at F39 billing) equal hand
    values; a line between the R = 8 and R = 16 peaks leaves only the R = 16 branch outside; action 4's mixed R adds its
    own branch; without a line or committed SU the projection is not evaluated."""
    c=pr.Camp.__new__(pr.Camp);c.m={'threads':16,'index_sizing':{'index_hours':.25}}
    c.inv={'free':{'7':[{'id':i}for i in range(100)],'8':[{'id':i}for i in range(1000)]},'power':{'8':[{'id':i}for i in range(300)]}}
    spp={f'{t}:{s}:{L}:{r["id"]}':(.01 if L=='8'else .002)for s in c.inv for L,rows in c.inv[s].items()for r in rows for t in 'ab'}
    fe={'f_E':1.1,'mp_check_factor':1.};o=pr.StageAOptions(line_cap=None,spent=12.5)
    def T(est,n):
        k=max(1,math.ceil(est/(.25*3600*16*.9)));need=est/k/(16*.9)*1.5+300;W=est/(n*128*.9);return math.ceil(max(1.5*W+900,need+900)/900)*900
    rp=pr.reproject(c,fe,{'seconds_per_point':spp},1.2,{'free':{'R':8},'power':{'R':8}},o,{})
    assert not rp['evaluated']and rp['not_evaluated_because']and all(b['within_line']is None for b in rp['branches'].values())
    peaks={}
    for name,R8 in (('PF R=8',8),('PF R=16 at L8',16)):
        b8=.01*4096*R8*2*1300;busy=b8+.002*4096*8*2*100;pc=.25*1.1*b8
        Tpf=T(1.1*busy,4);Tpc=T(1.1*pc,2);x=rp['branches'][name]
        assert abs(x['pf']['busy_core_hours_model']-busy/3600)<=1e-9 and abs(x['pf']['lane_reservation_su']-4*128*Tpf/3600)<=1e-9,(name,x['pf'],Tpf)
        assert abs(x['pc']['busy_core_hours_model']-pc/3600)<=1e-9 and abs(x['pc']['lane_reservation_su']-2*128*Tpc/3600)<=1e-9,(name,x['pc'],Tpc)
        spend_pf=1.1*busy*1.2/3600;spend_pc=1.1*pc*1.2/3600;res_pf=max(4*128*Tpf/3600,spend_pf);res_pc=max(2*128*Tpc/3600,spend_pc)
        hand=[12.5+8,12.5+8+res_pf+48,12.5+8+spend_pf+48+16,12.5+8+spend_pf+48+16+8,12.5+8+spend_pf+48+16+8+res_pc+24,12.5+8+spend_pf+48+16+8+spend_pc+24+64]
        assert np.allclose([s['peak_su']for s in x['steps']],hand,rtol=1e-12),([s['peak_su']for s in x['steps']],hand)
        assert abs(x['expected_total_su']-(hand[-1]))<=1e-9 and abs(x['peak_su']-max(hand))<=1e-9;peaks[name]=x['peak_su']
    assert peaks['PF R=16 at L8']>peaks['PF R=8']+100,peaks
    o.line_cap=(peaks['PF R=8']+peaks['PF R=16 at L8'])/2
    rp=pr.reproject(c,fe,{'seconds_per_point':spp},1.2,{'free':{'R':16},'power':{'R':8}},o,{})
    assert rp['evaluated']and abs(rp['remaining_su']-(o.line_cap-12.5))<=1e-9
    w={n:b['within_line']for n,b in rp['branches'].items()};assert w['PF R=8']is True and w['PF R=16 at L8']is False and len(w)==3,w
    mixed=[n for n in w if n.startswith('PF action 4')][0];assert rp['branches'][mixed]['R']=={'free':16,'power':8}
    # symmetry (Amendment A1; repair round 1): the lanes on the site's lane shape (amdq: 64 cores, f_class 1, at most
    # 23:30:00, 64 core-h per node-hour; defq: 40 cores, f_class 1.5, 80 per node-hour), the runbook's jobs as whole
    # nodes (plans, selection, report on amdq; merges on the lanes' vendor); an arrays/debug C8_SBATCH_ARGS falls back
    # to the site's lane partition; Expanse's numbers above are unchanged
    def Ts(est,n,cores,fc,tmax=84600):
        k=max(1,math.ceil(est/(.25*3600*16*.9)));need=est/k*fc/(16*.9)*1.5+300;W=est*fc/(n*cores*.9);return min(tmax,math.ceil(max(1.5*W+900,need+900)/900)*900)
    o2=pr.StageAOptions(line_cap=None,spent=12.5);sym={}
    for label,env,part,cores,fc,node,merge_node in (('amdq',{'C8_SITE':'symmetry'},'amdq',64,1.,64.,64.),
                                                    ('amddebugq profile',{'C8_SITE':'symmetry','C8_SBATCH_ARGS':'-p amddebugq --mem=240G -t 00:59:00'},'amdq',64,1.,64.,64.),
                                                    ('defq',{'C8_SITE':'symmetry','C8_SBATCH_ARGS':'-p defq'},'defq',40,1.5,80.,80.)):
        rp=pr.reproject(c,fe,{'seconds_per_point':spp},1.2,{'free':{'R':8},'power':{'R':8}},o2,env)
        a=rp['assumptions'];assert a['site']=='symmetry'and a['unit']=='core-h'and a['lane_shape']['partition']==part and a['lane_shape']['tmax']==84600,(label,a)
        assert a['runbook_job_su']=={'pf_plan':64.,'select':64.,'pc_plan':64.,'report':128.,'pf_merge':2*merge_node,'pc_merge':merge_node},(label,a['runbook_job_su'])
        x=rp['branches']['PF R=8'];b8=.01*4096*8*2*1300;busy=b8+.002*4096*8*2*100;pc=.25*1.1*b8
        Tpf=Ts(1.1*busy,4,cores,fc);Tpc=Ts(1.1*pc,2,cores,fc)
        assert x['pf']['partition']==part and x['pf']['T_lane_max']=='23:30:00'and abs(x['pf']['lane_reservation_su']-4*node*Tpf/3600)<=1e-9,(label,x['pf'],Tpf)
        assert abs(x['pc']['lane_reservation_su']-2*node*Tpc/3600)<=1e-9,(label,x['pc'],Tpc)
        spend_pf=1.1*busy*1.2/3600;spend_pc=1.1*pc*1.2/3600;res_pf=max(4*node*Tpf/3600,spend_pf);res_pc=max(2*node*Tpc/3600,spend_pc)
        hand=[12.5+64,12.5+64+res_pf+2*merge_node,12.5+64+spend_pf+2*merge_node+64,12.5+64+spend_pf+2*merge_node+64+64,
              12.5+64+spend_pf+2*merge_node+128+res_pc+merge_node,12.5+64+spend_pf+2*merge_node+128+spend_pc+merge_node+128]
        assert np.allclose([s_['peak_su']for s_ in x['steps']],hand,rtol=1e-12),(label,[s_['peak_su']for s_ in x['steps']],hand);sym[label]=x['peak_su']
    rp=pr.reproject(c,fe,{'seconds_per_point':spp},1.2,{'free':{'R':8},'power':{'R':8}},o2,{});assert rp['assumptions']['runbook_job_su']['pf_merge']==48.0 and rp['assumptions']['site']=='expanse'
    assert abs(rp['branches']['PF R=8']['peak_su']-peaks['PF R=8'])<=1e-9
    ok('A-PIL-2 on symmetry: lanes on the site\'s shape (amdq 64 cores, f 1, 64 core-h per node-hour; defq 40 cores, f 1.5, 80; at most 23:30:00) and '
       'the runbook\'s jobs as whole nodes (merges on the lanes\' vendor) equal hand values; a debug C8_SBATCH_ARGS falls back to amdq; peaks %s core-h'
       %({k:round(v,1)for k,v in sym.items()}),peaks=sym)
    ok('A-PIL-2: the re-projection equals hand values (PF busy %.1f / %.1f core-h at R = 8 / 16, T_lane %s / %s, peaks %.1f / %.1f SU with the '
       'runbook\'s shared jobs at F39 billing); a line between the two peaks leaves only the R = 16 branch outside; action 4\'s mixed R adds its '
       'branch; without a line it is not evaluated'%(rp['branches']['PF R=8']['pf']['busy_core_hours_model'],rp['branches']['PF R=16 at L8']['pf']['busy_core_hours_model'],
                                                  rp['branches']['PF R=8']['pf']['T_lane'],rp['branches']['PF R=16 at L8']['pf']['T_lane'],peaks['PF R=8'],peaks['PF R=16 at L8']),peaks=peaks)

def zero_channel_actions():
    """The zero-channel host refinement (Stage 3a repair round 3): an L8 graph with s_G = 4 (3 w_B = w_A; the C8 Jacobian row
    at L8 is proportional to (-1, 3), checked on the vendored jacobians) is reported as "zero-channel heavy tail, not
    confirmed" and takes part in no action: screen_graph never flags it and confirm_graph never confirms it (the same
    heavy graph with s_G = 6 is flagged and confirmed); the real power-L7 G1601 rows of the pinned fixture, standing in
    for an L8 graph, are flagged without the rule and reported with it; pilot_select.confirm drops it from a screen file
    and never draws it for the 2b extension; action 3 does not count it (the shares equal the no-confirmation hand
    values); action 5, alpha_p1c and item 12 leave its replicate values out."""
    import assemble as asm
    means={L:np.random.default_rng(L).normal(0,1,2*(9-L))for L in range(3,9)};B2,_=asm.two_loop(8)
    j8=np.asarray(asm.vendored().jacobians(means,B2,8,asm.HALF_D)[8])[8];assert abs(j8[1]/j8[0]+3)<=1e-12,j8
    assert ps.zero_channel({'s_G':4})and not ps.zero_channel({'s_G':6})and ps.zero_channel_l8({'free':{'8':[{'id':1,'s_G':4},{'id':2,'s_G':0}],'7':[{'id':3,'s_G':4}]}})=={('free',1)}
    rng=np.random.default_rng(17);c=FakeCamp()
    for t in 'ab':
        U=np.clip(rng.random((R8,N2)),1e-300,1.);X=U**(-1/1.5)
        for n in (N1,N2):c.data[((t,'free',8),3,n)]=([[0.,float(x.mean())]for x in X],tails_of(X,n))
    c.inv={'free':{'8':[{'id':3,'s_G':6}]}};sc=pr.screen_graph(c,'free',3,N1);cf=pr.confirm_graph(c,'free',3)
    assert sc['flag']and cf['confirmed']and 'zero_channel'not in sc
    c.inv={'free':{'8':[{'id':3,'s_G':4}]}};c._zc=None;sc=pr.screen_graph(c,'free',3,N1);cf=pr.confirm_graph(c,'free',3)
    assert not sc['flag']and sc['heavy_tail']and sc['status']==ps.ZC_NOTE and not cf['confirmed']and not cf['possible_infinite_variance']and cf['status']==ps.ZC_NOTE,(sc,cf)
    assert pr.zc_entries([sc],'x')[0]['status']==ps.ZC_NOTE and pr.zc_entries([cf],'y')[0]['xi_mean_32768']==cf['xi_mean_32768']
    # the real G1601 rows (pinned fixture, Expanse 54672564) under an L8 key
    doc=json.loads(ZC_FIXTURE.read_bytes());k=next(x for x in doc['kernels']if x['graph']==1601);g1601,P_,N_=zc_camp(k,doc)
    s0=pr.screen_graph(g1601,'power',1601,P_);c0=pr.confirm_graph(g1601,'power',1601)
    g1601.inv={'power':{'8':[{'id':1601,'s_G':4}]}};g1601._zc=None;s1=pr.screen_graph(g1601,'power',1601,P_);c1=pr.confirm_graph(g1601,'power',1601)
    assert s0['flag']and c0['confirmed']and not s1['flag']and s1['status']==ps.ZC_NOTE and not c1['confirmed']and c1['status']==ps.ZC_NOTE,(s0['flag'],c0.get('confirmed'),s1,c1)
    # pilot_select.confirm: dropped from a screen file, never drawn for 2b
    inv={'free':{'8':[{'id':i,'terms':1+i%90,'monomials':10+i,'s_G':4 if i%2 else 6}for i in range(200)]},'power':{'8':[]}}
    cost={('free',i):{'a':1e-4,'b':1e-4}for i in range(200)}
    scr={'flagged':[{'sector':'free','graph':1},{'sector':'free','graph':2}],'p1c_unscreened_confirmed':[{'sector':'free','graph':4},{'sector':'free','graph':5}],'l8_graphs':200,'p1c_graphs':4}
    d=ps.confirm(scr,'f'*64,7,cost,inv,1e9);rows=d['groups']['free:8']
    assert [r['id']for r in rows if r['label']=='screen']==[2]and all(r['id']%2==0 for r in rows)and len([r for r in rows if r['label']=='ext_2b'])>10,rows[:5]
    assert {(x['sector'],x['graph'])for x in d['zero_channel']['dropped_from_screen']}=={('free',1),('free',5)}and d['zero_channel']['status']==ps.ZC_NOTE
    e=ps.confirm({**scr,'flagged':[{'sector':'free','graph':1}],'p1c_unscreened_confirmed':[{'sector':'free','graph':5}]},'f'*64,7,cost,inv,1e9)
    assert e['groups']=={}and '0 of 200'in e['empty_reason']and len(e['zero_channel']['heavy_tail'])==2
    # action 3: a zero-channel graph never counts as confirmed (hand values = no confirmation); action 5, alpha, item 12 leave it out
    J8={8:np.array([0.,1.])};grp={}
    for t in 'ab':grp[(t,'free',8)]={g:(N1,[[0.,v]for v in pm(5. if g==1 else 1.,N1)],[(1.,[1.]*16)]*R8,1e-4)for g in range(40)}
    P3=camp_of(grp);P3.inv={'free':{'8':[{'id':g,'s_G':4 if g==1 else 6}for g in range(40)]}};pop=pr.per_graph_sigma(P3,J8)
    h=pr.action3_hold(P3,None,None,J8,[{'sector':'free','graph':1,'confirmed':True}],pop);h0=pr.action3_hold(P3,None,None,J8,[],pop)
    assert h['free']['confirmed']==0 and h['free']['variance_share']==h0['free']['variance_share']==0. and not h['free']['hold']and h['free']['zero_channel_excluded']==[1],h
    st,pooled=pr.action5(P3,J8,{('free',0,0):list(range(40))});assert pooled['free|L8']['graphs']==39 and st['free|T0-8|M0']['graph_campaign_Q']==78,(pooled,st)
    A=FakeCamp();A.inv=P3.inv
    for g in (1,2):
        for t in 'ab':
            for n in (N1,N2):A.data[((t,'free',8),g,n)]=([[0.,y]for y in pm(1.+g,n)],[(1.,[1.]*16,n)]*R8)
    al=pr.alpha_p1c(A,[('free',1),('free',2)]);assert al['by_sector']['free']['graphs']==1 and al['zero_channel_excluded']==['free:1'],al
    A2=camp_of({(t,'free',8):{g:(N1,[[0.,v]for v in pm(1.,N1)],[(1.,[1.]*16)]*R8,1e-4)for g in (1,2)}for t in 'ab'});A2.inv=P3.inv
    A2.sel={'groups':{'free:8':[{'id':1,'label':'stratified'},{'id':2,'label':'stratified'}]}};ho=pr.heldout_by_sector(A2,P3,J8);assert ho['free']['graphs']==2,ho
    ok('zero-channel host refinement: the C8 Jacobian row at L8 is (-1, 3) x const (vendored jacobians); an L8 graph with s_G = 4 is reported as '
       '"zero-channel heavy tail, not confirmed": never flagged or confirmed (flagged and confirmed with s_G = 6); the real G1601 rows are flagged '
       'without the rule and reported with it; pilot_select.confirm drops it from a screen file (recorded) and never draws it for 2b; action 3 '
       'ignores its confirmation (hand shares unchanged); action 5 (39 of 40 graphs), alpha_p1c and item 12 leave it out')

# ---------------------------------------------------------------- A-DES-4
def inventory(rng)->dict:
    inv={}
    for s,N in (('free',16064),('power',4336)):
        inv[s]={'8':[{'id':i,'terms':int(rng.integers(1,160)),'monomials':int(rng.integers(5,4000))}for i in range(N)]}
    return inv

def select_checks():
    rng=np.random.default_rng(3);inv=inventory(rng)
    cost={(s,r['id']):{'a':float(x),'b':3*float(x)}for s in inv for r,x in zip(inv[s]['8'],np.exp(rng.normal(-7,1,len(inv[s]['8']))))}
    d1=ps.stage_a(inv,'f'*64,1234,cost);d2=ps.stage_a(inv,'f'*64,1234,cost);d3=ps.stage_a(inv,'f'*64,1235,cost)
    assert json.dumps(d1,sort_keys=True)==json.dumps(d2,sort_keys=True)and json.dumps(d1['groups'])!=json.dumps(d3['groups'])
    st=ps.strata(inv);where={(k[0],g):k for k,ids in st.items()for g in ids}
    for s in ('free','power'):
        rows=d1['groups'][f'{s}:8'];by={r['id']:r for r in rows};ids=[r['id']for r in inv[s]['8']]
        heavy=sorted(ids,key=lambda g:(-(cost[(s,g)]['a']+cost[(s,g)]['b']),g))[:math.ceil(0.01*len(ids))]
        assert all(g in by for g in heavy)
        strat=[g for g,r in by.items()if r['label']in('stratified','p1c')];p1c=[g for g,r in by.items()if r['label']=='p1c']
        assert all(by[g]['label']=='heaviest_1pct'for g in by if g not in strat)and set(by)-set(strat)<=set(heavy)
        for k,v in st.items():
            if k[0]!=s:continue
            n_a=sum(1 for g in strat if where[(s,g)]==k);n_p=sum(1 for g in p1c if where[(s,g)]==k)
            assert abs(n_a-len(v)/8)<=1 and abs(n_p-n_a/32)<=1,(k,len(v),n_a,n_p)
        assert set(p1c)<=set(strat)and all(by[g]['points']==32768 and by[g]['nest']==[4096]for g in p1c)
        assert all(r['points']==4096 and 'nest'not in r for r in rows if r['label']!='p1c')
    # confirm: flagged under and over the cap, the 2b extension, the empty PC
    pcc=lambda s,g:(cost[(s,g)]['a']+cost[(s,g)]['b'])*32768*8
    flagged=[{'sector':'free','graph':g}for g in range(0,16064,7)]
    tot_fl=sum(pcc('free',x['graph'])for x in flagged)
    for cap_total,expect_all in ((8*tot_fl,True),(tot_fl,False)):
        scr={'flagged':flagged,'p1c_unscreened_confirmed':[{'sector':'power','graph':5}],'l8_graphs':20400,'p1c_graphs':80}
        doc=ps.confirm(scr,'f'*64,99,cost,inv,cap_total);cap=0.25*cap_total;rows=[r for v in doc['groups'].values()for r in v]
        assert all(r['points']==32768 and r['nest']==[4096]for r in rows)and doc['cap']['used_seconds']<=cap*(1+1e-12)
        used=sum(pcc(k.split(':')[0],r['id'])for k,v in doc['groups'].items()for r in v);assert abs(used-doc['cap']['used_seconds'])<=1e-6*used
        scr_rows=[r['id']for r in doc['groups']['free:8']if r['label']=='screen']
        if expect_all:assert sorted(scr_rows)==sorted(x['graph']for x in flagged)
        else:
            assert len(scr_rows)<len(flagged)and cap-used<=max(pcc('free',x['graph'])for x in flagged)   # the cap is filled
            frac=cap/tot_fl;byk={}
            for x in flagged:byk.setdefault(where[('free',x['graph'])],[]).append(x['graph'])
            for k,v in byk.items():assert sum(1 for g in scr_rows if g in v)>=math.floor(frac*len(v)),(k,len(v))
        ext=[r for r in doc['groups'].get('power:8',[])if r['label']=='ext_2b'];assert all(r['label']=='ext_2b'for r in doc['groups'].get('power:8',[]))
        assert doc['counts']['power']['ext_2b']==len(ext)
    e=ps.confirm({'flagged':[],'p1c_unscreened_confirmed':[],'l8_graphs':20400,'p1c_graphs':80},'f'*64,99,cost,inv,1e6)
    assert e['groups']=={}and '0 of 20400'in e['empty_reason']and '0 of 80'in e['empty_reason']
    with tempfile.TemporaryDirectory(prefix='c8d3_ps_')as td:
        log=Path(td)/'seeds.json';log.write_text('[]')
        for args in ((1234,None),(1234,log)):
            try:ps.registered(*args);raise AssertionError('unregistered seed accepted')
            except Refuse as x:assert x.code==64
        log.write_text('[1234]');ps.registered(1234,log)
    ok('A-DES-4: pilot_select at full scale (16,064 + 4,336 L8 graphs): deterministic from the seed; stage A 1/8 of each stratum (+-1) plus the '
       'heaviest 1% (heaviest_1pct unless drawn); P1c within the stratified part, 1/32 of each stratum\'s draw (+-1), at 32,768 nest [4096]; confirm: '
       'all PC graphs at 32,768 nest [4096], every flagged graph under the cap, the cap filled proportionally within strata above it, the 2b '
       'extension labelled ext_2b; the empty PC with both counts; an unregistered seed refused (64)')

# ---------------------------------------------------------------- A-DES-3, the run1 part (J-RUN1, Expanse)
RUN1='run1-20260930-m4096';RUN1_SHA256='08969c109598e31173fefb003e3703b2433fccb404ca1476646db0805130fc80'
# reference/c8d3_recon/out/tail_calib.log:70-77 ([B2]) and :140 ([B3]), the values this part reproduces
RUN1_B2={'a_free_L6':(395,1.841,1.084),'b_free_L6':(395,1.873,1.087),'a_power_L6':(107,1.833,1.083),'b_power_L6':(107,1.778,1.078),
         'a_free_L7':(2298,1.878,1.087),'b_free_L7':(2298,1.874,1.087),'a_power_L7':(590,2.035,1.103),'b_power_L7':(590,1.882,1.088)}
RUN1_B3={'graphs':590,'gt038':(34,37,33),'gt042':(33,28,27)}

def xi_block_maxima(m:list)->float:
    """tail_calib.py [B3]: xi_sd = sd(ln max, ddof 1) sqrt(6)/pi over a graph's replicate maxima (1/a for Frechet maxima)."""
    return float(np.log(np.asarray(m,float)).std(ddof=1)*math.sqrt(6)/math.pi)

def run1_part(archive:Path,sha:str)->dict:
    import hashlib,tarfile,time
    import assemble as asm
    t0=time.time();h=hashlib.sha256()
    with open(archive,'rb')as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    if h.hexdigest()!=sha:raise AssertionError(f'{archive}: sha256 {h.hexdigest()} is not the pinned {sha}')
    mx={};samples={};reps={};res=None;want=set(RUN1_B2)
    with tarfile.open(archive,'r:gz')as tf:
        for m in tf:
            if not m.isfile():continue
            if m.name==f'{RUN1}/C7_result.json':res=json.load(tf.extractfile(m));continue
            if not m.name.startswith(f'{RUN1}/groups/'):continue
            grp=m.name.split('/groups/')[1].split('/')[0]
            if '/checkpoints/'in m.name and m.name.endswith('.json'):
                for r in json.load(tf.extractfile(m))['native']['rows']:
                    d=mx.setdefault(grp,{}).setdefault(int(r['graph']),{});k=int(r['rep']);d[k]=max(d.get(k,0.),float(r['max_abs']))
                    samples[(grp,int(r['graph']))]=samples.get((grp,int(r['graph'])),0)+int(r['end'])-int(r['begin'])
            elif m.name.endswith('/graph_replicates.csv')and grp in want:
                lines=tf.extractfile(m).read().decode().splitlines();head=lines[0].split(',');assert head[:2]==['replicate','graph'],head
                d={}
                for line in lines[1:]:
                    x=line.split(',');d.setdefault(int(x[1]),{})[int(x[0])]=[float(v)for v in x[2:]]
                reps[grp]=d
    if res is None or set(reps)!=want:raise AssertionError(f'archive: C7_result.json {res is not None}, graph_replicates.csv of {sorted(reps)}')
    # (1) block maxima of power L7, both campaigns
    xi={}
    for c in 'ab':
        xi[c]={g:xi_block_maxima([v[k]for k in sorted(v)])for g,v in mx[f'{c}_power_L7'].items()if len(v)==64 and min(v.values())>0}
    gs=sorted(set(xi['a'])&set(xi['b']));xa=np.array([xi['a'][g]for g in gs]);xb=np.array([xi['b'][g]for g in gs])
    b3={'graphs':len(gs),'gt038':(int((xa>.38).sum()),int((xb>.38).sum()),int(((xa>.38)&(xb>.38)).sum())),
        'gt042':(int((xa>.42).sum()),int((xb>.42).sum()),int(((xa>.42)&(xb>.42)).sum()))}
    assert b3==RUN1_B3,(b3,RUN1_B3)
    both=[g for g,u,v in zip(gs,xa,xb)if u>.42 and v>.42]
    # (2) P8_hat on the L6/L7 groups with pilot_report's estimator, on the old slots of the C8 Jacobian
    m7={L:np.asarray(res['means']['free'][str(L)],float)+np.asarray(res['means']['power'][str(L)],float)for L in range(3,8)}
    def ext(v,L):k=8-L;return np.concatenate([v[:k],[0.],v[k:],[0.]])
    m8={L:ext(m7[L],L)for L in range(3,8)};m8[8]=np.zeros(2);B2,b2sha=asm.two_loop(8)
    J8={L:np.asarray(v)[8]for L,v in asm.vendored().jacobians(m8,B2,8,asm.HALF_D).items()}
    b2={}
    for grp,(n_want,vq_want,p8_want)in RUN1_B2.items():
        L=int(grp[-1]);k=8-L;j8=J8[L][list(range(k))+list(range(k+1,2*k+1))];qs=[];n=0
        for g,v in reps[grp].items():
            if samples.get((grp,g),0)<=0:continue
            y=np.array([v[r]for r in sorted(v)])@j8
            if len(y)!=64 or not y.std()>0:continue
            n+=1;qs+=pr.split_q(y)
        vq=float(np.var(qs,ddof=1));p8=pr.p8_pooled(qs)
        assert n==n_want and len(qs)==8*n and abs(vq-vq_want)<=6e-4 and abs(p8-p8_want)<=6e-4,(grp,n,len(qs),vq,vq_want,p8,p8_want)
        b2[grp]={'graphs':n,'Q':len(qs),'VarQ':vq,'P8_hat':p8,'log_VarQ':vq_want,'log_P8_hat':p8_want}
    lo,hi=min(round(x['P8_hat'],3)for x in b2.values()),max(round(x['P8_hat'],3)for x in b2.values())
    assert (lo,hi)==(1.078,1.103),(lo,hi)
    ok(f'A-DES-3 run1 part (J-RUN1): from the pinned archive ({sha[:12]}), power L7 block maxima: {b3["graphs"]} graphs, xi_sd > 0.38 in '
       f'{b3["gt038"]} and > 0.42 in {b3["gt042"]} (a, b, both): run1\'s 27 of 590; pilot_report P8_hat on the eight L6/L7 groups '
       f'{lo:.3f}-{hi:.3f}, every graph count, Var(Q) and P8_hat equal to tail_calib.log to its printed decimals',
       block_maxima={**b3,'both_042':both},p8=b2,two_loop_sha256=b2sha,archive={'path':str(archive),'sha256':sha},seconds=round(time.time()-t0,1))
    return {'status':'passed','tests':len(RESULTS),'results':RESULTS,'numpy':np.__version__}

def pc_selection_fixes():
    """S3-001, S3-002 and S3-003 on pilot_select, and the PC planner's cap refusal (production.read_selection)."""
    import production as prod
    # S3-001, Codex's case: one stratum, PC costs 1 and 99 s, a 50 s budget: the selection never exceeds it, at any seed
    cst={1:1.,2:99.};first99=0
    for seed in range(64):
        got=ps.proportional(np.random.default_rng(seed),{0:[1,2]},cst.get,50.);assert got==[1],(seed,got)
        first99+=int(np.random.default_rng(seed).permutation(2)[0])==1   # the seeds at which the first allocation draws the 99-s graph
    assert first99>0
    # through confirm: one free stratum (equal terms and monomials), flagged graphs 1 (cheap) and 2 (dear), cap 50% of their cost
    inv={'free':{'8':[{'id':g,'terms':5,'monomials':50}for g in range(1,9)]},'power':{'8':[{'id':g,'terms':5,'monomials':50}for g in range(1,9)]}}
    u=2.**-18   # c_a + c_b = u gives a PC cost of u x 32,768 x 8 = 1 s
    cost={(s,g):{'a':u*(99. if g==2 else 1.)/2,'b':u*(99. if g==2 else 1.)/2}for s in ('free','power')for g in range(1,9)}
    scr={'flagged':[{'sector':'free','graph':1},{'sector':'free','graph':2}],'p1c_unscreened_confirmed':[],'l8_graphs':16,'p1c_graphs':0}
    for seed in range(32):
        d=ps.confirm(scr,'f'*64,seed,cost,inv,200.);pc=sum((cost[('free',r['id'])]['a']+cost[('free',r['id'])]['b'])*32768*8 for r in d['groups'].get('free:8',[]))
        assert d['cap']['cap_seconds']==50. and pc<=50.and abs(pc-d['cap']['used_seconds'])<=1e-9 and [r['id']for r in d['groups']['free:8']]==[1],(seed,d['groups'],d['cap'])
    # production.read_selection (the PC planner): a confirm selection over its recorded cap, or without a cap record, is refused
    with tempfile.TemporaryDirectory(prefix='c8d3_sel_')as td:
        f=Path(td)/'pc.json';f.write_text(json.dumps(d));doc,_=prod.read_selection(f,'f'*64,inv,False,256);assert doc['cap']['used_seconds']==1.
        for name,mod,why in (('over the cap',lambda x:x['cap'].__setitem__('used_seconds',51.),'over its recorded PC cap'),('a cap above 25%',lambda x:x['cap'].__setitem__('cap_seconds',60.),'over its recorded PC cap'),
                             ('no cap',lambda x:x.pop('cap'),'no valid PC cap record'),('a fraction above 25%',lambda x:x['cap'].__setitem__('fraction',0.5),'no valid PC cap record')):
            x=json.loads(json.dumps(d));mod(x);g=Path(td)/'bad.json';g.write_text(json.dumps(x))
            try:prod.read_selection(g,'f'*64,inv,False,256);raise AssertionError(f'read_selection accepted a confirm selection with {name}')
            except ValueError as e:assert why in str(e),(name,str(e))
    # S3-002: ten equally costly flagged graphs per sector (one stratum each) and room for ten: 5 + 5 at every seed (old: 10 + 0)
    inv2={s:{'8':[{'id':g,'terms':5,'monomials':50}for g in range(10)]}for s in ('free','power')}
    cost2={(s,g):{'a':u/2,'b':u/2}for s in ('free','power')for g in range(10)}
    scr2={'flagged':[{'sector':s,'graph':g}for s in ('free','power')for g in range(10)],'p1c_unscreened_confirmed':[],'l8_graphs':20,'p1c_graphs':0}
    for seed in range(16):
        d=ps.confirm(scr2,'f'*64,seed,cost2,inv2,40.);assert d['cap']['cap_seconds']==10.
        assert d['counts']['free']['screen']==d['counts']['power']['screen']==5 and d['cap']['used_seconds']==10.,(seed,d['counts'])
    # ... and the 2b extension (free, from an unscreened P1c confirmation) never displaces the screened power graphs
    scr3={'flagged':[{'sector':'power','graph':g}for g in range(4)],'p1c_unscreened_confirmed':[{'sector':'free','graph':0}],'l8_graphs':20,'p1c_graphs':1}
    for seed in range(16):
        d=ps.confirm(scr3,'f'*64,seed,cost2,inv2,40.)
        assert d['counts']['power']['screen']==4 and d['counts']['free']['ext_2b']==6 and d['cap']['used_seconds']==10.,(seed,d['counts'])
    # S3-R2-002: sector-symmetric strata with heterogeneous costs through confirm: identical free and power strata, each
    # with PC costs 1 and 99 s, and a 100 s cap. Both strata propose one graph; before S3-R2-002 free (sorted first) was
    # served first, so its 99-s graph was selected at 1/2 of the seeds and power's at 1/4; jointly resolved, 3/8 each
    inv4={s:{'8':[{'id':g,'terms':5,'monomials':50}for g in (1,2)]}for s in ('free','power')}
    cost4={(s,g):{'a':u*(99. if g==2 else 1.)/2,'b':u*(99. if g==2 else 1.)/2}for s in ('free','power')for g in (1,2)}
    scr4={'flagged':[{'sector':s,'graph':g}for s in ('free','power')for g in (1,2)],'p1c_unscreened_confirmed':[],'l8_graphs':4,'p1c_graphs':0}
    NS=3000;freq={};hit={'free':0,'power':0}
    for seed in range(NS):
        d=ps.confirm(scr4,'f'*64,seed,cost4,inv4,400.);assert d['cap']['cap_seconds']==100. and d['cap']['used_seconds']<=100.,(seed,d['cap'])
        for s in hit:hit[s]+=any(r['id']==2 for r in d['groups'].get(f'{s}:8',[]))
    freq['confirm']={s:v/NS for s,v in hit.items()}
    # ... and proportional itself with the two strata keyed so that either sector sorts first (the decision must not follow the key order)
    c4={('free',1):1.,('free',2):99.,('power',1):1.,('power',2):99.}
    for name,keys in (('free first',(('a',),('b',))),('power first',(('b',),('a',)))):
        by={keys[0]:[('free',1),('free',2)],keys[1]:[('power',1),('power',2)]};hit={'free':0,'power':0}
        for seed in range(NS):
            got=ps.proportional(np.random.default_rng(seed),by,c4.get,100.);assert sum(c4[x]for x in got)<=100.,(seed,got)
            for s in hit:hit[s]+=(s,2)in got
        freq[name]={s:v/NS for s,v in hit.items()}
    for name,fr in freq.items():
        assert abs(fr['free']-fr['power'])<=0.05 and all(abs(v-3/8)<=0.05 for v in fr.values()),('S3-R2-002: the 99-s graph\'s inclusion depends on the sector or its key order',name,fr)
    freq={k:{s:round(v,3)for s,v in fr.items()}for k,fr in freq.items()}
    # S3-003: pc_costs prices PC in PF's MP mode and checks the model's whole identity against PF (the campaign reader stubbed)
    CPU='AMD EPYC 7543 32-Core Processor';m={'backend':'gmp','executable_sha256':'e'*64,'fingerprint':{'cpu_model':CPU},'mp_check':'on'}
    def model(path,**kw):
        x={'schema':prod.COST_SCHEMA,'dimension':3,'order':8,'measured':True,'backend':'gmp','executable_sha256':'e'*64,'cpu_model':CPU,'mp_check':'on',
           'seconds_per_point':{'a:free:8:1':1e-3,'b:free:8:1':2e-3,'a:free:7:1':5.}};x.update(kw);path.write_text(json.dumps(x));return path
    orig=prod.verify_base;seen=[]
    def fake_vb(run,**kw):seen.append(kw);return m,None,'m'*64,{}
    prod.verify_base=fake_vb
    try:
        with tempfile.TemporaryDirectory(prefix='c8d3_pcc_')as td:
            c1,r1=ps.pc_costs(model(Path(td)/'on.json'),Path(td));c2,r2=ps.pc_costs(model(Path(td)/'off.json',mp_check='off',mp_check_overhead={'on':2.}),Path(td))
            assert c1=={('free',1):{'a':1e-3,'b':2e-3}}and c2=={('free',1):{'a':2e-3,'b':4e-3}}and r1['mp_check_factor']==1. and r2['mp_check_factor']==2.,(c1,c2)
            assert all(k.get('scheduling_copies')is False for k in seen),seen
            for name,kw in (('executable_sha256',{'executable_sha256':'f'*64}),('cpu_model',{'cpu_model':'AMD EPYC 7742 64-Core Processor'}),('mp_check',{'mp_check':'off'})):
                try:ps.pc_costs(model(Path(td)/f'{name}.json',**kw),Path(td));raise AssertionError(f'pc_costs accepted another {name}')
                except ValueError as e:assert name in str(e)and 'identity'in str(e),(name,str(e))
    finally:prod.verify_base=orig
    ok('S3-001/S3-002/S3-003 (pilot_select confirm): the PC cap holds at every step (one stratum with PC costs 1 and 99 s and a 50 s budget: '
       'only the 1-s graph at every one of 64 seeds, %d of which drew the 99-s graph first; confirm\'s rows recomputed within the cap) and '
       'production.read_selection refuses a confirm selection over its recorded cap, with a cap above 25%%, or without a cap record; flagged graphs '
       'of both sectors share the cap jointly (10 + 10 equally costly, room for 10: 5 + 5 at every seed) and a free 2b extension never displaces the '
       'screened power graphs; pc_costs prices PC in PF\'s MP mode (overhead on = 2 doubles every cost), reads PF with scheduling_copies=False and '
       'refuses a model of another executable, CPU model or mode; S3-R2-002: identical free and power strata of PC costs 1 and 99 s under a 100 s '
       'cap select the 99-s graph equally often in both sectors (%s; 3/8 each; before 1/2 and 1/4), also with the strata relabelled power-first'%(first99,freq))

def site_projection():
    """S3-010: the cost table on the target site's lane node, the target site and CPUs recorded, a cross-CPU projection refused
    without target-site measurements and scaled with them."""
    import re,budget,production as prod
    sh=(ROOT/'slurm/site.sh').read_text()
    for prof in (budget.EXPANSE,budget.SYMMETRY):
        mm=re.search(rf"^\s*{prof.name}\)\s+C8_CPU_EXPECT='([^']+)'",sh,re.M);assert mm and mm.group(1)==prof.cpu,(prof.name,prof.cpu,mm and mm.group(1))
    spec={('a','free',6):(8,40),('b','free',6):(8,40),('a','power',7):(8,30),('b','power',7):(8,30),('a','free',8):(8,50),('b','free',8):(8,50),('a','power',8):(8,20),('b','power',8):(8,20)}
    P=FakePF(spec,np.random.default_rng(81));J8={L:np.array([0.]*(2*(9-L)-1)+[1.])for L in range(3,9)};p8={(s,c):1.0 for s in ('free','power')for c in ('L8','L<=7')};eta=.9
    S7543,S7742='AMD EPYC 7543 32-Core Processor','AMD EPYC 7742 64-Core Processor'
    with tempfile.TemporaryDirectory(prefix='c8d3_site_')as td:
        td=Path(td);P.run=td;keys={f'{t}:{s}:{L}:{g}':1e-3*(1+g%3)for (t,s,L),G in P.g.items()for g in G['total']}
        def model(path,cpu,factor=1.,**kw):
            x={'schema':prod.COST_SCHEMA,'dimension':3,'order':8,'measured':True,'backend':'gmp','executable_sha256':'e'*64,'cpu_model':cpu,'mp_check':'on',
               'seconds_per_point':{k:v*factor for k,v in keys.items()}};x.update(kw);path.write_text(json.dumps(x));return path
        model(td/'cost_model.json',S7543)
        P.m={'mp_check':'on','backend':'gmp','cost_basis':'measured','cost_model_sha256':'x'*64,'fingerprint':{'cpu_model':S7543}}
        sym=pr.target_site(P,{'C8_SITE':'symmetry'});fake=pr.target_site(P,{'C8_SITE':'fake'})
        assert sym['site']=='symmetry'and sym['allocated_cpus_per_node']==64 and sym['cores_per_node']==64 and sym['target_cpu']==sym['measured_cpu']==S7543 and sym['unit']=='core-h'
        assert fake['site']=='expanse'and fake['target_cpu']is None and fake['cpu_check'].startswith('not evaluated')and fake['allocated_cpus_per_node']==128
        ts=pr.cost_table(P,J8,eta,{'central':0.5},p8,None,100.,site=sym);te=pr.cost_table(P,J8,eta,{'central':0.5},p8,None,100.)
        for a,b in zip(ts['rows'],te['rows']):
            if a.get('SE')is None:continue
            assert abs(a['wall_hours_4_nodes']-a['allocated_su']/(4*64))<=1e-12*a['wall_hours_4_nodes']and abs(a['wall_hours_22_nodes']-a['allocated_su']/(22*64))<=1e-12*a['wall_hours_22_nodes'],\
                ('symmetry wall hours',a['wall_hours_4_nodes'],a['allocated_su']/(4*64))
            assert abs(b['wall_hours_22_nodes']-b['allocated_su']/(22*128))<=1e-12*b['wall_hours_22_nodes']and abs(a['wall_hours_4_nodes']-2*b['wall_hours_4_nodes'])<=1e-12*a['wall_hours_4_nodes']
            assert abs(a['band']['wall_hours_4_nodes'][1]-a['band']['allocated_su'][1]/(4*64))<=1e-12*a['band']['wall_hours_4_nodes'][1]
        assert ts['site']['site']=='symmetry'and ts['site']['target_cpu']==S7543 and ts['site']['measured_cpu']==S7543 and not ts['site']['cost_scaled']and te['site']['allocated_cpus_per_node']==128
        # an Expanse projection of the symmetry-measured PF: refused without target-site measurements, scaled with them
        try:pr.target_site(P,{'C8_SITE':'expanse'});raise AssertionError('an Expanse projection from EPYC 7543 measurements accepted')
        except ValueError as e:assert 'target-site measurements'in str(e)and S7742 in str(e),str(e)
        try:pr.target_site(P,{},model(td/'T_wrong.json',S7543,2.));raise AssertionError('a target model on the wrong CPU accepted')
        except ValueError as e:assert 'not the target site'in str(e),str(e)
        try:pr.target_site(P,{'C8_SITE':'expanse'},model(td/'T_mode.json',S7742,2.,mp_check='off'));raise AssertionError('a target model without PF\'s MP mode accepted')
        except ValueError as e:assert 'overhead factor'in str(e),str(e)
        exp=pr.target_site(P,{'C8_SITE':'expanse'},model(td/'T.json',S7742,1.,mp_check='off',mp_check_overhead={'on':2.}))
        assert exp['site']=='expanse'and exp['allocated_cpus_per_node']==128 and exp['target_cost_model']['cpu_model']==S7742 and set(exp['cost_scale'].values())=={2.}
        tx=pr.cost_table(P,J8,eta,{'central':0.5},p8,None,100.,site=exp)
        for a,b in zip(tx['rows'],te['rows']):
            if a.get('SE')is None:continue
            assert abs(a['plugin_busy_core_hours']-2*b['plugin_busy_core_hours'])<=1e-9*a['plugin_busy_core_hours']and abs(a['allocated_su']-2*b['allocated_su'])<=1e-9*a['allocated_su']
        assert tx['site']['cost_scaled']and 'cost_scale'not in tx['site']
        # S3-R2-004: the target CPU is the lane partition's: symmetry defq is Intel Gold 6148 (budget.partition_cpu), so an
        # EPYC 7543 PF is refused there without target measurements (before: the site CPU, "the target CPU is PF's")
        INTEL=budget.INTEL_GOLD_6148;dq={'C8_SITE':'symmetry','C8_SBATCH_ARGS':'-p defq'}
        assert budget.partition_cpu(budget.SYMMETRY,'defq')==budget.partition_cpu(budget.SYMMETRY,'debugq')==INTEL and budget.partition_cpu(budget.SYMMETRY,'amdq')==S7543
        try:pr.target_site(P,dq);raise AssertionError('a defq projection of EPYC 7543 measurements accepted without target measurements')
        except ValueError as e:assert 'target-site measurements'in str(e)and INTEL in str(e)and 'defq'in str(e),str(e)
        try:pr.target_site(P,dq,model(td/'T_amd.json',S7543,2.));raise AssertionError('an AMD target model accepted for defq')
        except ValueError as e:assert 'not the target site'in str(e),str(e)
        di=pr.target_site(P,dq,model(td/'T_intel.json',INTEL,1.5))
        assert di['partition']=='defq'and di['target_cpu']==INTEL and di['measured_cpu']==S7543 and di['allocated_cpus_per_node']==80 and di['cores_per_node']==40 \
            and all(abs(v-1.5)<=1e-12 for v in di['cost_scale'].values())and di['target_cost_model']['cpu_model']==INTEL,{k:v for k,v in di.items()if k!='cost_scale'}
        am=pr.target_site(P,{'C8_SITE':'symmetry','C8_SBATCH_ARGS':'-p amdq'});assert am['partition']=='amdq'and am['target_cpu']==S7543 and am['cost_scale']is None
        # S3-R2-005: a projected table's MP self-check columns use the TARGET model's measured overheads (PF: off/on 0.5;
        # the Expanse target: 0.9), not PF's; an explicit ratio model must be on the target CPU; unprojected, PF's model
        model(td/'cost_model.json',S7543,1.,mp_check_overhead={'off':.5})
        T9=model(td/'T9.json',S7742,2.,mp_check_overhead={'off':.9});e9=pr.target_site(P,{'C8_SITE':'expanse'},T9)
        m9,src9=pr.model_for_ratios(P,None,e9);rat=pr.mp_ratios(m9,'on',src9)
        assert abs(rat['off']-.9)<=1e-15 and '--target-cost-model'in src9 and e9['target_cost_model']['sha256']in src9,(rat,src9)
        t9=pr.cost_table(P,J8,eta,{'central':0.5},p8,None,100.,mp_ratio=rat,site=e9)
        for a in t9['rows']:
            if a.get('SE')is None:continue
            x=a['allocated_su_by_mp_check'];assert abs(x['off']-.9*x['on'])<=1e-12*x['on']and x['on']==a['allocated_su'],x
        mx,sx=pr.model_for_ratios(P,T9,e9);assert pr.mp_ratios(mx,'on',sx)['off']==.9   # an explicit model on the target CPU
        try:pr.model_for_ratios(P,td/'cost_model.json',e9);raise AssertionError('an explicit ratio model on PF\'s CPU accepted for an Expanse projection')
        except ValueError as e:assert 'target CPU'in str(e),str(e)
        ms,ss=pr.model_for_ratios(P,None,sym);assert pr.mp_ratios(ms,'on',ss)['off']==.5 and 'PF'in ss,(ss,)   # unprojected: PF's own model
    ok('S3-010: the site CPUs of tools/budget.py equal slurm/site.sh\'s C8_CPU_EXPECT; on symmetry (C8_SITE=symmetry, amdq) every wall hour of the '
       'cost table, rows and bands, is allocated / (N x 64), twice Expanse\'s / (N x 128); the table records the target site, its unit and both '
       'CPUs; an Expanse projection of EPYC 7543 measurements is refused without a target-site model, a model on the wrong CPU or without PF\'s MP '
       'mode is refused, and an EPYC 7742 model (off mode, overhead on = 2) scales every per-graph cost by 2 (busy and allocated hours x2); '
       'S3-R2-004: on symmetry defq the target CPU is Intel Gold 6148 (80 allocated CPUs per node): an EPYC 7543 PF is refused without target '
       'measurements and with an AMD model, and scaled (x1.5) with an Intel one, amdq keeping EPYC 7543; S3-R2-005: the MP self-check columns of '
       'the Expanse projection use the target model\'s overhead (off = 0.9 x on, PF\'s 0.5 unused), an explicit ratio model on PF\'s CPU is '
       'refused, one on the target CPU accepted, and without a projection PF\'s model gives them')

def run()->dict:
    p8_formula();kappa_and_realism();injected_pilot();zero_channel_synthetic();zero_channel_fixture();actions_hand();hill_and_rates();realism_mc();cost_table_checks();heldout_oracle();heldout_per_sector();select_checks()
    graph_bootstrap();cost_table_bands();reproject_hand();zero_channel_actions();pc_selection_fixes();site_projection()
    return {'status':'passed','tests':len(RESULTS),'results':RESULTS,'numpy':np.__version__}
if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter);ap.add_argument('--output',type=Path)
    ap.add_argument('--run1',action='store_true',help='the run1 part only (A-DES-3, J-RUN1): the archive\'s tail facts')
    ap.add_argument('--zero-channel',type=Path,help='only the zero-channel check on FILE (tests/class_b.py --zero-channel-tails; Expanse)')
    ap.add_argument('--archive',type=Path,default=Path(os.environ.get('C8_STORE','.'))/f'{RUN1}_full.tgz');ap.add_argument('--sha256',default=RUN1_SHA256)
    a=ap.parse_args()
    if a.zero_channel:
        zero_channel_check(json.loads(a.zero_channel.read_text()),str(a.zero_channel));r={'status':'passed','tests':len(RESULTS),'results':RESULTS,'numpy':np.__version__}
    else:r=run1_part(a.archive,a.sha256)if a.run1 else run()
    if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=1)+'\n')
    print(json.dumps({'status':r['status'],'tests':r['tests']}))
