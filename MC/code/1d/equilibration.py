#!/usr/bin/env python3
"""Equilibration gate shared by accept.py (v1 criterion 2) and select_model.py (v2 prerequisite, FITV2-013).

Group rule (per (s, N, beta) entry of a merged summary): hot- and cold-start replicas agree in <m^2> within 3 sigma, no
replica drifts between its halves by more than 4 sigma, and the largest autocorrelation-time estimate is below block/20.
Population rule: at most 2 % of all replicas may have |half-chain z| > 3 (chance rate 0.27 %).
"""
from __future__ import annotations
import numpy as np

def check(entries):
    c2=[];n3=0;nrep=0
    for e in entries:
        d=e['replica_diagnostics'];blk=e['block_size']
        hot=[x for x in d if x['initialization']=='hot'];cold=[x for x in d if x['initialization']=='cold']
        if not hot or not cold:
            c2.append(dict(s=e['s'],N=e['N'],beta=e['beta'],ok=False,reason='missing hot or cold replicas'));nrep+=len(d);continue
        mh,mc=np.mean([x['m2_mean'] for x in hot]),np.mean([x['m2_mean'] for x in cold])
        err=np.sqrt(sum(x['m2_block_stderr']**2 for x in hot)/len(hot)**2+sum(x['m2_block_stderr']**2 for x in cold)/len(cold)**2)
        zhc=abs(mh-mc)/err if err else 0.0
        zs=[abs(x['first_vs_second_half_z'] or 0) for x in d];zhalf=max(zs);tau=max(max(x['tau_estimate'].values()) for x in d)
        n3+=sum(1 for z in zs if z>3);nrep+=len(zs)
        ok=zhc<=3 and zhalf<=4 and tau<blk/20
        c2.append(dict(s=e['s'],N=e['N'],beta=e['beta'],hotcold_z=float(zhc),max_half_z=float(zhalf),max_tau=float(tau),block=blk,ok=bool(ok)))
    frac3=n3/nrep if nrep else 0.0
    passed=bool(entries) and all(x['ok'] for x in c2) and frac3<=0.02
    return dict(passed=passed,failing=[x for x in c2 if not x['ok']][:20],groups=len(c2),replicas=nrep,
                replicas_half_z_over_3=n3,fraction_over_3=frac3,fraction_cap=0.02,
                rule='hot/cold |z|<=3, max half-chain |z|<=4, max tau < block/20 per group; <=2 % replicas with half-chain |z|>3')

def check_population(entries):
    """v3 population form (FIT_MODEL_V3.md §4.4): hard limits hot/cold |z| <= 4 and half-chain |z| <= 4 per group; population
    limits <= 2 % of groups with hot/cold |z| > 3 and <= 2 % of replicas with half-chain |z| > 3; tau < block/20 per group."""
    groups=[];n_hc3=0;n_half3=0;nrep=0
    for e in entries:
        d=e['replica_diagnostics'];blk=e['block_size']
        hot=[x for x in d if x['initialization']=='hot'];cold=[x for x in d if x['initialization']=='cold']
        if not hot or not cold:
            groups.append(dict(s=e['s'],N=e['N'],beta=e['beta'],ok=False,reason='missing hot or cold replicas'));nrep+=len(d);continue
        mh,mc=np.mean([x['m2_mean'] for x in hot]),np.mean([x['m2_mean'] for x in cold])
        err=np.sqrt(sum(x['m2_block_stderr']**2 for x in hot)/len(hot)**2+sum(x['m2_block_stderr']**2 for x in cold)/len(cold)**2)
        reasons=[]
        # R2-008: an unresolved diagnostic is never a silent pass — zero uncertainty gives infinite significance, a missing
        # half-chain z counts as a replica over the limit
        if err>0:zhc=abs(mh-mc)/err
        else:zhc=float('inf');reasons.append('zero hot/cold uncertainty (unresolved)')
        missing=[x for x in d if x.get('first_vs_second_half_z') is None]
        if missing:reasons.append(f'{len(missing)} replicas without a half-chain z (unresolved)')
        zs=[abs(x['first_vs_second_half_z']) for x in d if x.get('first_vs_second_half_z') is not None];zhalf=max(zs) if zs else float('inf');tau=max(max(x['tau_estimate'].values()) for x in d)
        n_hc3+=int(zhc>3);n_half3+=sum(1 for z in zs if z>3)+len(missing);nrep+=len(d)
        ok=zhc<=4 and zhalf<=4 and tau<blk/20 and not reasons
        groups.append(dict(s=e['s'],N=e['N'],beta=e['beta'],hotcold_z=float(zhc),max_half_z=float(zhalf),max_tau=float(tau),block=blk,ok=bool(ok),reasons=reasons))
    ng=len(groups);frac_hc=n_hc3/ng if ng else 0.;frac_half=n_half3/nrep if nrep else 0.
    passed=bool(groups) and all(g['ok'] for g in groups) and frac_hc<=0.02 and frac_half<=0.02
    return dict(passed=passed,failing=[g for g in groups if not g['ok']][:20],groups=ng,replicas=nrep,groups_hotcold_over_3=n_hc3,
                fraction_hotcold_over_3=frac_hc,replicas_half_z_over_3=n_half3,fraction_half_over_3=frac_half,fraction_cap=0.02,
                rule='v3 population: per group hot/cold |z|<=4, half-chain |z|<=4, tau<block/20; <=2 % groups with hot/cold |z|>3; <=2 % replicas with half-chain |z|>3')
