"""Record-backed sector layer for the verbatim assembly (new tool, 2026-10-15; not part of the snapshot).

The verbatim assembly (assembly/pooled_errors.py) reads every engine job's per-sector, per-replicate values from the raw
chunk outputs (engine/runs/<run>/*.cfg.json, about 130 MB, not shipped; see DATA_indep_d1.md) for two things only:
  * job_sector_values(): the per-sector replicate values x_{i,s,r} of the coefficients i of a job;
  * pooled_projection(jobs, grad): per job, the replicate projection   e_rep  = sd_r(sum_s sum_i g_i x_isr) / sqrt(R)
                                  and the sector-pooled projection      e_pool = sqrt(sum_s var_r(sum_i g_i x_isr) / R).
Both are fixed by two sufficient statistics per job, which public/make_pooled_record.py computes exactly (integer
arithmetic on the stored doubles) from the raw outputs with the verbatim job_sector_values():
  T_ir = sum_s x_isr                                    (per-replicate totals),
  M_ij = sum_s cov_r(x_is, x_js)   (sample covariance)  (pooled covariance),
so that e_rep = sd_r(sum_i g_i T_ir) / sqrt(R) and e_pool = sqrt(g^T M g / R) for any gradient g. Jobs with at most
360 sectors also carry their per-sector replicate values in the record; for them the shim returns the verbatim data
structure and the verbatim pooled_projection() is used unchanged.
install(PE, record) replaces PE.job_sector_values and PE.pooled_projection by versions that read
public/pooled_sector_record.json; every other function of the verbatim modules (final_jobs, Est.stats, NormAssembler,
run_assembly.step1/main, run_assembly_C8.step1, compare_archive.main) runs unchanged on top of them.
Differences from the raw path (only for the jobs with 2520 and 20160 sectors, 6 to 9 kinks): the verbatim code forms
the projection in double precision before taking the variance, the record is exact; there the replicate spread is
statistical (1e-11 relative or more), and the two agree to about 1e-12 (make replay-raw checks this on the raw data).
"""
import json
import math
import os
import statistics as st

import mpmath as mp

_REC = None


def load(path):
    """the record, with T as floats and M as mpf (40 digits)"""
    d = json.load(open(path))
    with mp.workdps(40):
        for run in d['runs'].values():
            for j in run['jobs']:
                if j.get('missing'):
                    continue
                j['_T'] = [[float(x) for x in row] for row in j['T']]
                j['_M'] = [[mp.mpf(x) for x in row] for row in j['M']]
                j['_idx'] = {nm: i for i, nm in enumerate(j['names'])}
    return d


def install(PE, record_path, log=print):
    """patch the module object PE (assembly/pooled_errors.py) in place; returns the original functions"""
    global _REC
    _REC = load(record_path)
    runs = _REC['runs']
    orig = {'job_sector_values': PE.job_sector_values, 'pooled_projection': PE.pooled_projection}

    def job_sector_values(rundir, groups=None, all_coeffs=False, keep=None, tag='', allow_missing=False):
        run = os.path.basename(os.path.normpath(rundir))
        if run not in runs:
            raise FileNotFoundError(f'{run}: not in the pooled sector record')
        out = {}
        for j in runs[run]['jobs']:
            if groups is not None and j['moment'] not in groups:
                continue
            if not j['need'] and not all_coeffs:
                continue
            if j.get('missing'):
                if allow_missing:
                    log(f"WARNING: {run}/{j['moment']} k={j['k']} has no complete output (allow_missing): job skipped")
                    continue
                raise RuntimeError(f"{run}/{j['moment']} k={j['k']}: no complete output in the raw run")
            names = j['names'] if all_coeffs else j['need_names']
            if keep is not None:
                names = [nm for nm in names if nm in keep]
            if 'sectors' in j:            # small job: its per-sector values, for the verbatim pooled_projection
                idx = [j['_idx'][nm] for nm in names]
                out[(tag, j['moment'], j['k'])] = {'R': j['R'], 'sectors': {sid: {nm: vals[i] for nm, i in zip(names, idx)}
                                                                          for sid, vals in j['sectors']}}
                continue
            out[(tag, j['moment'], j['k'])] = {'R': j['R'], 'sectors': {'record': {nm: None for nm in names}},
                                              'record': {'job': j, 'names': names}}
        return out

    def pooled_projection(jobs, grad):
        per = []
        v_rep = v_pool = 0.0
        for key, d in jobs.items():
            tag, mom, k = key[0], key[1], key[2]
            if 'record' not in d:                     # raw per-sector data (not from the record): verbatim code
                r, p, pj = orig['pooled_projection']({key: d}, grad)
                per += pj
                v_rep += r ** 2
                v_pool += p ** 2
                continue
            j, names = d['record']['job'], d['record']['names']
            R = d['R']
            g = [grad.get(nm, 0.0) for nm in names]
            if not any(g) or R is None or R < 2:
                continue
            idx = [j['_idx'][nm] for nm in names]
            tot = [sum(gi * j['_T'][i][t] for gi, i in zip(g, idx)) for t in range(R)]
            e_rep = st.stdev(tot) / math.sqrt(R)
            with mp.workdps(40):
                q = mp.mpf(0)
                for a, ga in zip(idx, g):
                    if ga:
                        for b, gb in zip(idx, g):
                            if gb:
                                q += mp.mpf(ga) * mp.mpf(gb) * j['_M'][a][b]
                e_pool = float(mp.sqrt(max(q, 0) / R))
            per.append({'job': f'{tag}{mom}|k={k}', 'rep': e_rep, 'pool': e_pool, 'nsec': j['nsec']})
            v_rep += e_rep ** 2
            v_pool += e_pool ** 2
        return math.sqrt(v_rep), math.sqrt(v_pool), sorted(per, key=lambda x: -x['pool'])

    PE.job_sector_values = job_sector_values
    PE.pooled_projection = pooled_projection
    return orig
