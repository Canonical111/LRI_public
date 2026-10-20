#!/usr/bin/env python3
"""Sector-pooled statistical errors of every assembled output (assembly phase, 2026-10-03).

The per-replicate standard error (R = 6, 5 dof) of a QMC estimate is itself uncertain by ~30%.  The engine
also writes, for every sector and every random shift, the sector's own estimate (`per_sector[].rep`).
Shifts of different sectors are independent, so the variance of a job's total can also be estimated as
    E_pool^2 = sum_s var_r(x_sr) / R              (hundreds of degrees of freedom),
the 'sector-pooled' estimator of engine/tests/production_checks.py.  This module applies it to the
projection D_sr = sum_i (dO/dx_i) x_{i,s,r} of every job onto every output O (exact correlations inside a
job), with the signed gradients dO/dx_i of the framework's central assembly, and sums the independent jobs
in quadrature.  Statistical only (the precision floors are added by the caller).

The coefficient map from channel Laurent coefficients to eps^k l^j coefficients is the engine's own
(`engine/py/lri_moments.coefficient_map`); the run layout (manifest.json, <cfg>.json) is the engine's
`campaign.py` layout.  Nothing from the archive is read.
"""
import json
import math
import os
import re
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.normpath(os.path.join(HERE, '..', 'engine'))
sys.path.insert(0, os.path.join(ENGINE, 'py'))
from lri_moments import coefficient_map          # noqa: E402
from campaign import decode_job                  # noqa: E402


def raw_name(group, k, j):
    """engine group + (k, j) -> framework flat name (A3_base -> A3, A5_vE -> A5_vE)"""
    return f"{re.sub(r'_N[0-9]+$', '', group).replace('_base', '')}[eps^{k} l^{j}]"


def job_sector_values(rundir, groups=None, all_coeffs=False, keep=None, tag='', allow_missing=False):
    """{(tag, moment, k): {'R': R, 'sectors': {sid: {name: [x_r]}}}} for the NEEDED coefficients of every job
    (all coefficients of the job if all_coeffs; only names in `keep` if given), refined sectors substituted
    exactly as campaign.py collect does."""
    manifest = json.load(open(os.path.join(rundir, 'manifest.json')))
    out = {}
    for m in manifest:
        if groups is not None and m['moment'] not in groups:
            continue
        job = decode_job(m['job'])
        k = job['k']
        need = m.get('need') or []
        if not need and not all_coeffs:
            continue
        refined = {x['sector']: x['cfg'] for x in m.get('refine', [])}
        persec = {}
        R = None
        for cfg, only in [(c, None) for c in m['cfgs']] + [(c, s) for s, c in refined.items()]:
            path = os.path.join(rundir, cfg + '.json')
            if not os.path.exists(path) and allow_missing:
                print(f'WARNING: {path} missing (allow_missing): job skipped in the pooled errors')
                persec = None
                break
            r = json.load(open(path))
            if not r.get('complete', False):
                raise RuntimeError(f'{rundir}/{cfg}.json is not complete')
            orders = {c: ch['orders'] for c, ch in r['channels'].items()}
            cmap, _ = coefficient_map(job, orders)
            chans = r['channels']
            first = next(iter(chans.values()))
            for i, sec in enumerate(first['per_sector']):
                sid = sec['id']
                if (only is None and sid in refined) or (only is not None and sid != only):
                    continue
                R = len(sec['rep'])
                vals = {}
                jjs = sorted(j2 for (k2, j2) in cmap if k2 == k) if all_coeffs else need
                for jj in jjs:
                    if keep is not None and raw_name(m['moment'], k, jj) not in keep:
                        continue
                    lst = cmap.get((k, jj))
                    if not lst:
                        continue
                    x = [0.0] * R
                    for c, o2, w in lst:
                        io = orders[c].index(o2)
                        rep = chans[c]['per_sector'][i]['rep']
                        for t in range(R):
                            x[t] += w * rep[t][io]
                    vals[raw_name(m['moment'], k, jj)] = x
                persec[sid] = vals
        if persec is None:
            continue
        out[(tag, m['moment'], k)] = {'R': R, 'sectors': persec}
    return out


def pooled_projection(jobs, grad):
    """grad: {raw name: dO/dx (input convention)} -> (sigma_rep, sigma_pool, per-job list)"""
    per = []
    v_rep = v_pool = 0.0
    for (tag, mom, k), d in jobs.items():
        R = d['R']
        Ds = []
        hit = False
        for vals in d['sectors'].values():
            row = [0.0] * R
            for nm, x in vals.items():
                g = grad.get(nm, 0.0)
                if g:
                    hit = True
                    for t in range(R):
                        row[t] += g * x[t]
            Ds.append(row)
        if not hit or R is None or R < 2:
            continue
        tot = [sum(r[t] for r in Ds) for t in range(R)]
        e_rep = st.stdev(tot) / math.sqrt(R)
        e_pool = math.sqrt(sum(st.variance(r) for r in Ds) / R)
        per.append({'job': f'{tag}{mom}|k={k}', 'rep': e_rep, 'pool': e_pool, 'nsec': len(Ds)})
        v_rep += e_rep ** 2
        v_pool += e_pool ** 2
    return math.sqrt(v_rep), math.sqrt(v_pool), sorted(per, key=lambda x: -x['pool'])


def final_jobs(tier1_dir, topup_dir, replaced, all_coeffs=False):
    """the job set of results_final.json: tier-1 jobs, with the replaced groups taken from the top-up run"""
    jobs = {key: v for key, v in job_sector_values(tier1_dir, all_coeffs=all_coeffs).items()
            if key[1] not in replaced}
    jobs.update(job_sector_values(topup_dir, groups=set(replaced), all_coeffs=all_coeffs, tag='topup1:'))
    return jobs


def input_gradient(val, inp):
    """framework Val gradient (internal = Taylor units) -> {name: d/d input} in the derivative convention"""
    return {nm: float(g / inp.scale.get(nm, 1)) for nm, g in val.g.items() if g != 0}
