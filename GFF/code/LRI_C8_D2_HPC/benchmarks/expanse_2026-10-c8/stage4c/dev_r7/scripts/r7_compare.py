#!/usr/bin/env python3
"""R7 (opt-in rates) statistical validation, A-FLAG-6: an UNPAIRED comparison of a campaign under the rate map with an
exact-path (default .8/.9) campaign of fresh seeds, plus the change in variance x cost.

  r7_compare.py --package PKG --map RUN --exact RUN [--map-pilot RUN --exact-pilot RUN] [--source RUN]
                [--fresh-bundles DIR... --exact-bundles DIR...] [--boot 1000] --out JSON

Both campaigns are merged (production.py merge) and read through tools/design.py's load_pilot (every table verified
through merged.json). y = J8 . jet is a graph-replicate's C8 projection, J8 the vendored order-8 Jacobian at the EXACT
sweep's loop means (as numerics_flags.py F2), the same J8 for every campaign compared.

Agreement (per (sector, L), per (campaign, sector, L) as a diagnostic, and the total):
  contribution = (mean_a + mean_b) / 2 of the graph-summed replicate means of y; its variance from the per-graph
  replicate variances, (Var_a + Var_b) / 4 with Var_c = sum_g Var_rep(y_g) / R (graphs are independent randomized nets);
  Delta = map - exact, SE = sqrt(var_map + var_exact) (unpaired), z = Delta / SE; nu = Welch-Satterthwaite over every
  graph-campaign term of both campaigns (R - 1 degrees of freedom each).
  Verdicts: "3 sigma" |z| <= 3 (A-FLAG-6 as written); "dof-aware" the two-sided t_nu p-value >= 0.0027 (the 3-sigma
  level), because at 2 replicates a stratum of a few graphs has an SE of very few degrees of freedom. The nonlinear C8 of
  each campaign (assemble.py, C8_test_result.json test_partial) is compared too, with assemble's own SEs.
  --map-pilot/--exact-pilot: the many-replicate complement (plan --pilot, L3-L6 complete and the 400 cheapest L7/L8
  graphs per group, the same graphs in both) is compared the same way, over its own graph sets.
Variance x cost (the sweeps, every graph): per (campaign, sector, L) W = sum_g sigma_g sqrt(c_g) (sigma_g^2 = n Var_rep(y_g),
  c_g = row seconds per point), W^2 the Neyman variance x cost of the stratum, V = sum sigma^2, C = sum c; the projected
  total at a fixed target F = (sum over (c, s, L) of W / 2)^2 (continuous Neyman allocation over all strata); ratios
  map / exact with a graph bootstrap (graphs resampled jointly in both campaigns, seed 7082026). Strata whose rates the
  map keeps are the node/run control. The plain variance x cost of the sweeps themselves (their equal allocation):
  Var(C8 lin) x total row seconds. --source (J-SWEEP-1) adds the same W table of the map's source for reference.
Freeze table: --exact-bundles / --fresh-bundles (design.py freeze --test-only at the same targets, in the same order):
  predicted SE, allocated core-hours and batches, and the core-hour ratio fresh / exact per target.
"""
from __future__ import annotations
import argparse,json,math,sys
from pathlib import Path
import numpy as np

P3S=0.0027  # two-sided tail probability of 3 sigma
DEFAULTS={'a':'.8','b':'.9'}

def tdist():
    from scipy import stats
    return stats

def campaign(Dz,run:Path,jacobian=True):
    if not jacobian:
        saved=Dz.jacobian_rows;Dz.jacobian_rows=lambda *a,**k:None
        try:return Dz.load_pilot(run)
        finally:Dz.jacobian_rows=saved
    return Dz.load_pilot(run)

def group_stats(G,J):
    y=np.einsum('rgj,j->rg',G.Y,J);R=G.reps
    mean=float(y.mean(0).sum());terms=y.var(0,ddof=1)/R;n=np.array([G.points[g]for g in G.graphs],float)
    sig=np.sqrt(n*y.var(0,ddof=1));cost=np.array([G.seconds.get(g,0.)for g in G.graphs])/(R*n)
    return dict(mean=mean,var=float(terms.sum()),terms=terms,dof=R-1,sigma=sig,cost=cost,seconds=float(sum(G.seconds.values())),graphs=list(G.graphs))

def welch(terms_dofs):
    num=sum(float(t.sum())for t,_ in terms_dofs)**2;den=sum(float((t**2).sum())/d for t,d in terms_dofs)
    return num/den if den>0 else math.inf

def verdicts(delta,se,nu):
    st=tdist();z=delta/se if se>0 else math.inf
    p_n=float(2*st.norm.sf(abs(z)));p_t=float(2*st.t.sf(abs(z),nu))if math.isfinite(nu)else p_n
    return dict(delta=delta,se=se,z=z,nu_eff=nu,p_normal=p_n,p_t=p_t,within_3sigma=abs(z)<=3,dof_aware_pass=p_t>=P3S,
                t_crit_3sigma=float(st.t.isf(P3S/2,nu))if math.isfinite(nu)else 3.0)

def agreement(X,Y,J,label):
    """X map, Y exact (or two arms of one kind); identical graph sets per group are required."""
    rows=[];camp_rows=[];tot_d=0.;tot_v=0.;tot_terms=[]
    for s in ('free','power'):
        for L in range(3,9):
            parts={};terms=[]
            for c in ('a','b'):
                gx,gy=X.groups[(c,s,L)],Y.groups[(c,s,L)]
                if gx.graphs!=gy.graphs:raise SystemExit(f'{label}: {c}_{s}_L{L}: the two campaigns have different graph sets')
                sx,sy=group_stats(gx,J[L]),group_stats(gy,J[L]);parts[c]=(sx,sy)
                d=sx['mean']-sy['mean'];v=sx['var']+sy['var']
                camp_rows.append(dict(campaign=c,sector=s,L=L,graphs=len(gx.graphs),map=sx['mean'],exact=sy['mean'],
                                      **verdicts(d,math.sqrt(v),welch([(sx['terms'],sx['dof']),(sy['terms'],sy['dof'])]))))
                terms+=[(sx['terms']/4,sx['dof']),(sy['terms']/4,sy['dof'])]
            cx=sum(parts[c][0]['mean']for c in parts)/2;cy=sum(parts[c][1]['mean']for c in parts)/2
            v=sum(parts[c][0]['var']+parts[c][1]['var']for c in parts)/4;nu=welch(terms)
            rows.append(dict(sector=s,L=L,graphs=len(X.groups[('a',s,L)].graphs),map=cx,exact=cy,se_map=math.sqrt(sum(parts[c][0]['var']for c in parts)/4),
                             se_exact=math.sqrt(sum(parts[c][1]['var']for c in parts)/4),**verdicts(cx-cy,math.sqrt(v),nu)))
            tot_d+=cx-cy;tot_v+=v;tot_terms+=terms
    total=dict(map=sum(r['map']for r in rows),exact=sum(r['exact']for r in rows),**verdicts(tot_d,math.sqrt(tot_v),welch(tot_terms)))
    return dict(label=label,per_sector_L=rows,per_campaign_sector_L=camp_rows,total_linear=total,
                all_within_3sigma=all(r['within_3sigma']for r in rows)and total['within_3sigma'],
                all_dof_aware_pass=all(r['dof_aware_pass']for r in rows)and total['dof_aware_pass'],
                campaign_level_beyond_3sigma=[f"{r['campaign']}_{r['sector']}_L{r['L']}"for r in camp_rows if not r['within_3sigma']])

def nonlinear(map_run:Path,exact_run:Path):
    out={}
    for k,run in (('map',map_run),('exact',exact_run)):
        f=run/'C8_test_result.json'
        if not f.exists():return None
        tp=json.loads(f.read_text())['test_partial'];out[k]=dict(C8=tp['C8_full'],se=tp['sampling_standard_error'],campaigns=tp.get('campaigns'))
    d=out['map']['C8']-out['exact']['C8'];se=math.hypot(out['map']['se'],out['exact']['se'])
    return dict(**out,delta=d,se=se,z=d/se,within_3sigma=abs(d/se)<=3,
                note='assemble.py SEs come from the replicate-level covariance of each group (R = 2 replicates: 1 degree of freedom per group)')

def work_tables(X,Y,J,boot,rng,keep,rate_of=None):
    """W, V, C per (campaign, sector, L) of X (map) and Y (exact) with the same J8; F and its bootstrap."""
    rows=[];FX=FY=0.;bootF=np.zeros((boot,2));bx={};by={}
    for s in ('free','power'):
        for L in range(3,9):
            idx=None
            for c in ('a','b'):
                sx,sy=group_stats(X.groups[(c,s,L)],J[L]),group_stats(Y.groups[(c,s,L)],J[L])
                wx=sx['sigma']*np.sqrt(sx['cost']);wy=sy['sigma']*np.sqrt(sy['cost'])
                WX,WY=float(wx.sum()),float(wy.sum());FX+=WX/2;FY+=WY/2
                ng=len(wx)
                if idx is None:idx=[rng.integers(ng,size=ng)for _ in range(boot)]if ng>1 else None
                qs=None
                if idx is not None:
                    rb=np.array([(wx[i].sum()/wy[i].sum())**2 if wy[i].sum()>0 else np.nan for i in idx])
                    for b,i in enumerate(idx):bootF[b]+=(wx[i].sum()/2,wy[i].sum()/2)
                    qs={k:float(np.nanquantile(rb,q))for k,q in (('p2.5',.025),('p16',.16),('p50',.5),('p84',.84),('p97.5',.975))}
                else:
                    for b in range(boot):bootF[b]+=(WX/2,WY/2)
                VX,VY=float((sx['sigma']**2).sum()),float((sy['sigma']**2).sum());CX,CY=float(sx['cost'].sum()),float(sy['cost'].sum())
                rows.append(dict(campaign=c,sector=s,L=L,graphs=ng,rate_changed=(c,s,L)not in keep,W_map=WX,W_exact=WY,
                                 ratio_W2=(WX/WY)**2 if WY>0 else None,ratio_V=VX/VY if VY>0 else None,ratio_C=CX/CY if CY>0 else None,
                                 C_map_seconds_per_point_sum=CX,C_exact_seconds_per_point_sum=CY,bootstrap_ratio_W2=qs))
    rF=(bootF[:,0]/bootF[:,1])**2
    # same-rate cross check: in a stratum the map steps up, map campaign a runs at .9 like exact campaign b (and map b
    # at 1); in one it steps down, map b runs at .8 like exact a. Their W^2 should agree within the noise.
    same=[]
    if rate_of:
        for s in ('free','power'):
            for L in range(3,9):
                for cx in ('a','b'):
                    for cy in ('a','b'):
                        if (cx,s,L)in keep or rate_of[(cx,s,L)]!=DEFAULTS[cy]:continue
                        sx,sy=group_stats(X.groups[(cx,s,L)],J[L]),group_stats(Y.groups[(cy,s,L)],J[L])
                        WX,WY=float((sx['sigma']*np.sqrt(sx['cost'])).sum()),float((sy['sigma']*np.sqrt(sy['cost'])).sum())
                        same.append(dict(sector=s,L=L,rate=rate_of[(cx,s,L)],map_campaign=cx,exact_campaign=cy,ratio_W2=(WX/WY)**2,
                                         ratio_V=float((sx['sigma']**2).sum()/(sy['sigma']**2).sum()),ratio_C=float(sx['cost'].sum()/sy['cost'].sum())))
    share={f"{r['campaign']}_{r['sector']}_L{r['L']}":r['W_exact']/2/FY for r in rows}
    ctrl=[r for r in rows if not r['rate_changed']];chg=[r for r in rows if r['rate_changed']]
    agg=lambda rs,k:(sum(r[f'C_map_seconds_per_point_sum']for r in rs)/sum(r['C_exact_seconds_per_point_sum']for r in rs))if rs else None
    return dict(per_campaign_sector_L=rows,same_rate_cross_check=same,F_map=FX**2,F_exact=FY**2,ratio_F=(FX/FY)**2,
                bootstrap_ratio_F={k:float(np.quantile(rF,q))for k,q in (('p2.5',.025),('p16',.16),('p50',.5),('p84',.84),('p97.5',.975))},
                exact_share_of_sqrtF=share,cost_ratio_changed_strata=agg(chg,'C'),cost_ratio_control_strata=agg(ctrl,'C'),
                control_strata=[f"{c}_{s}_L{L}"for (c,s,L) in sorted(set((r['campaign'],r['sector'],r['L'])for r in ctrl))])

def plain_vc(P,J):
    v=sum(group_stats(G,J[L])['var']/4 for (c,s,L),G in P.groups.items());sec=sum(sum(G.seconds.values())for G in P.groups.values())
    return dict(var_C8_linear=v,row_seconds=sec,product=v*sec)

def freeze_table(exact_dirs,fresh_dirs):
    out=[]
    for e,f in zip(exact_dirs,fresh_dirs):
        me,mf=(json.loads((Path(d)/'design_meta.json').read_text())for d in (e,f))
        pe,pf=me['predictions'],mf['predictions']
        out.append(dict(target_rel=me['target']['rel'],target_se=me['target']['se'],exact_bundle=str(e),fresh_bundle=str(f),
                        exact=dict(se=pe['se_total'],core_hours=pe['cost_total_core_hours'],batches=me['batches'],eta_node=me['eta_node'],rates_identity=me['rates_identity']),
                        fresh=dict(se=pf['se_total'],core_hours=pf['cost_total_core_hours'],batches=mf['batches'],eta_node=mf['eta_node'],rates_identity=mf['rates_identity'],
                                   provisional=mf['provisional'],rates_bundle=mf['rates_bundle']),
                        ratio_core_hours=pf['cost_total_core_hours']/pe['cost_total_core_hours']))
    return out

def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--package',type=Path,required=True);p.add_argument('--map',type=Path,required=True);p.add_argument('--exact',type=Path,required=True)
    p.add_argument('--map-pilot',type=Path);p.add_argument('--exact-pilot',type=Path);p.add_argument('--source',type=Path)
    p.add_argument('--rates',type=Path,help='the map (rates.json): which strata it changes');p.add_argument('--fresh-bundles',type=Path,nargs='*',default=[])
    p.add_argument('--exact-bundles',type=Path,nargs='*',default=[]);p.add_argument('--boot',type=int,default=1000);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args(argv)
    sys.path.insert(0,str(a.package.resolve()/'tools'));import design as Dz
    Y=campaign(Dz,a.exact);X=campaign(Dz,a.map,jacobian=False);J=Y.J8
    keep=set();rate_of={}
    if a.rates:
        from decimal import Decimal as Dd
        rm=json.loads(a.rates.read_text())['rates']
        for c,dflt in DEFAULTS.items():
            for s in ('free','power'):
                for L in range(3,9):
                    vals={Dd(v)for v in rm[c][s][str(L)].values()}
                    if vals=={Dd(dflt)}:keep.add((c,s,L))
                    rate_of[(c,s,L)]=format(vals.pop(),'f').lstrip('0')if len(vals)==1 else'per-graph'
    rec=dict(schema='c8-d2-r7-compare-1',package=str(a.package.resolve()),map=X.meta,exact=Y.meta,J8_from='exact sweep loop means',
             rates_kept_strata=sorted(f'{c}_{s}_L{L}'for c,s,L in keep))
    rec['agreement_sweeps']=agreement(X,Y,J,'sweeps (all graphs, 2 x 512 points)')
    rec['nonlinear_C8_sweeps']=nonlinear(a.map,a.exact)
    if a.map_pilot and a.exact_pilot:
        XP=campaign(Dz,a.map_pilot,jacobian=False);YP=campaign(Dz,a.exact_pilot,jacobian=False);rec['map_pilot']=XP.meta;rec['exact_pilot']=YP.meta
        rec['agreement_pilots']=agreement(XP,YP,J,'many-replicate complement (L3-L6 complete, 400 cheapest L7/L8 per group)')
    rng=np.random.default_rng(7082026)
    rec['variance_x_cost']=work_tables(X,Y,J,a.boot,rng,keep,rate_of)
    rec['plain_variance_x_cost']=dict(map=plain_vc(X,J),exact=plain_vc(Y,J));rec['plain_variance_x_cost']['ratio']=rec['plain_variance_x_cost']['map']['product']/rec['plain_variance_x_cost']['exact']['product']
    if a.source:
        S=campaign(Dz,a.source,jacobian=False);rec['source_vs_exact']=dict(source=S.meta,note='J-SWEEP-1 (Stage-3 binary, default rates) against the fresh exact sweep (current binary): agreement only; its costs are the Stage-3 binary\'s',
                                                                          agreement=agreement(S,Y,J,'J-SWEEP-1 vs the fresh exact sweep (both default rates)'))
    if a.fresh_bundles:rec['freeze']=freeze_table(a.exact_bundles,a.fresh_bundles)
    a.out.write_text(json.dumps(rec,indent=1,default=lambda o:o.tolist()if hasattr(o,'tolist')else str(o))+'\n')
    # ---- text summary
    def show(ag):
        print(f"== {ag['label']}");print('sector L  graphs          map        exact      Delta         SE       z    nu_eff  3sig  dof-aware')
        for r in ag['per_sector_L']+[dict(sector='TOTAL',L='',graphs='',**ag['total_linear'])]:
            print(f"{r['sector']:6s}{str(r['L']):>2s} {str(r['graphs']):>6s} {r['map']:12.3f} {r['exact']:12.3f} {r['delta']:10.3f} {r['se']:10.3f} {r['z']:7.2f} {r['nu_eff']:9.1f}  "
                  f"{'ok'if r['within_3sigma']else'FAIL':4s}  {'ok'if r['dof_aware_pass']else'FAIL'}")
        print(f"campaign-level |z| > 3: {ag['campaign_level_beyond_3sigma'] or 'none'}")
    show(rec['agreement_sweeps'])
    if 'agreement_pilots'in rec:show(rec['agreement_pilots'])
    if 'source_vs_exact'in rec:show(rec['source_vs_exact']['agreement'])
    nl=rec['nonlinear_C8_sweeps']
    if nl:print(f"nonlinear C8: map {nl['map']['C8']:.2f} +- {nl['map']['se']:.2f}, exact {nl['exact']['C8']:.2f} +- {nl['exact']['se']:.2f}, z {nl['z']:.2f}")
    vc=rec['variance_x_cost'];print('== variance x cost (map / exact)')
    for r in vc['per_campaign_sector_L']:
        b=r['bootstrap_ratio_W2'];bi=f"[{b['p2.5']:.3f}, {b['p97.5']:.3f}]"if b else''
        print(f"{r['campaign']} {r['sector']:5s} L{r['L']} {'changed'if r['rate_changed']else'kept   '} W2 {r['ratio_W2']:.3f} {bi:18s} V {r['ratio_V']:.3f} C {r['ratio_C']:.3f}")
    print(f"F ratio {vc['ratio_F']:.4f} {vc['bootstrap_ratio_F']}; cost ratio changed strata {vc['cost_ratio_changed_strata']:.4f}, control {vc['cost_ratio_control_strata']:.4f}")
    for r in vc['same_rate_cross_check']:print(f"same rate {r['rate']}: map {r['map_campaign']} vs exact {r['exact_campaign']} {r['sector']} L{r['L']}: W2 {r['ratio_W2']:.3f} V {r['ratio_V']:.3f} C {r['ratio_C']:.3f}")
    print(f"plain variance x cost ratio {rec['plain_variance_x_cost']['ratio']:.4f}")
    for f in rec.get('freeze',[]):print(f"freeze target {f['target_rel']}: exact {f['exact']['core_hours']:.1f} core-h (SE {f['exact']['se']:.3f}), fresh {f['fresh']['core_hours']:.1f} (SE {f['fresh']['se']:.3f}), ratio {f['ratio_core_hours']:.4f}")
    return 0
if __name__=='__main__':sys.exit(main())
