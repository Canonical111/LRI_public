#!/usr/bin/env python3
"""C8 assembly with engine tiers A + B + C (2026-10-07), steps 1-2: archive-free.
Writes ../RESULTS_C8_independent.json (+ .sha256) and out/C8_ABC/run_assembly_C8.log.
(The tier-A version of 2026-10-04 is run_assembly_C8_tierA.py -> ../RESULTS_C8_independent_tierA.json.)

C8 = 8 T4 = B_old + 4W + 2S + 3/4 U + 1/4 J9 + 3/32 L3 - 1/4 M21 + 1/2 M12 - 1/16 N2 + 1/8 Ndelta + 1/32 Kv
(note eq:C8assembly; the framework derives it, framework/derive_C8.py).

Step 1  framework, strict on EVERY output (the 35 inputs, C3..C8, T4, B_old, B_done, C8_asm), per-replicate assembly at
        order C8, dps 50, on
          engine/runs/prod_6digit/framework_input_final.json   (the 116 order-D4 scalars, phase 2)
        + engine/runs/c8tiersABC/framework_input_final.json    (tiers A + B + C merged per scalar: 85 scalars)
        merged as independent runs (R = 6 everywhere).  SHA-256 of every input checked against the engine records.
        Outputs: the ten new inputs; B_old, B_done, C8_asm, C8 = 8 T4, T4, C8 without the J9 term; the sub-pieces of
        U, Kv, J9 (and Ndelta, C_fixed) as linear functionals (exact gradients, per-replicate values); three error
        estimators (sigma_cov, sigma_rep, sigma_pool; quoted = max) plus the per-job-max combination for reference;
        error budgets of C8 by job, by tier and by term.  Cross-checks: the three tier files fed separately; old
        outputs unchanged (B_old vs phase 3, C3..C7 vs phase 2, the seven tier-A inputs vs the tier-A assembly);
        the note's raw structure of U, Kv, J9, Ndelta and C8 (exact gradients).
        Tier consistency (independent runs, disjoint seeds): tier B/C scalars swapped for the pilots' all-sector values
        (input level); the heavy 6-9 kink jobs against the probe c8probeBC and the conv pilots c8conv on the same sector
        samples (sector-subset sums); the Z8 and A5_dE runs replaced by top-ups; U at pilot level; the C9 check at
        N = 1009 vs N = 4001; the engine's tier_vs_pilot summaries.
Step 2  archive-free checks read from tools run first (same Slurm job, in the same project copy):
          out/C8_ABC/validate_C8_ABC.{json,txt}   engine/tests/validate_C8.py, production tiers first (raw targets incl.
                                                  the note's leading log of d_delta A7; pole cancellation of all jets incl.
                                                  C9[v0d0], K8[v1d0], C7[v0d1]; zeros; C3/K4 higher logs; RG logs)
          out/C8_ABC/direct_C8_ABC*               engine/tests/direct_C8.py, production tiers first
No archive file is read (the run copy contains no sealed directory; it runs under an audit hook).
"""
import hashlib
import json
import math
import os
import re
import statistics as stt
import sys
import time

import mpmath as mp

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import common as CM  # noqa: E402
from common import L  # noqa: E402
import pooled_errors as PE  # noqa: E402

DPS = 50
OUT8 = os.path.join(CM.OUT, 'C8_ABC')
RUNS = os.path.join(CM.ENG_DIR, 'runs')
REPLACED = ['Q6_E', 'A7_v', 'A7_base', 'A5_vE']          # phase-2 top-up groups (production)
TIER_FILES = {'A': os.path.join(RUNS, 'c8tierA', 'framework_input_final.json'),
              'B': os.path.join(RUNS, 'c8tierB_s0.01_r1', 'framework_input_final.json'),
              'C': os.path.join(RUNS, 'c8tierC_s3_r2', 'framework_input_final.json')}
ABC_FILE = os.path.join(RUNS, 'c8tiersABC', 'framework_input_final.json')
PILOT_RUNS = [os.path.join(RUNS, x) for x in ('c8val', 'c8conv', 'c8kplus1', 'poles1', 'kplus1')]
NEW10 = ['W', 'S', 'U', 'J9', 'L3', 'M21', 'M12', 'N2', 'Ndelta', 'Kv']
NEW_A = ['W', 'S', 'L3', 'M21', 'M12', 'N2', 'Ndelta']
NEW_BC = ['U', 'J9', 'Kv']
PARTS = ['B_old8', 'B_done8', 'C8_asm', 'T4', 'C8']
RESULTS = os.path.join(CM.ROOT, 'RESULTS_C8_independent.json')
TIERA_RESULTS = os.path.join(CM.ROOT, 'RESULTS_C8_independent_tierA.json')
LOG = []

# sub-pieces (input = derivative convention): linear functionals of outputs ('out') and raw scalars ('raw')
SUB = {
    'A7_d_1': ('U package: A7_d_1 = [eps^0 l^1] d_delta A7', [(1, 'raw', 'A7_d[eps^0 l^1]')]),
    'D_known': ('U package: D_known = U - A7_d_1 (everything in U except A7_d_1)', [(1, 'out', 'U'), (-1, 'raw', 'A7_d[eps^0 l^1]')]),
    'Z6_d_1': ('U package: [eps^0 l^1] d_delta Z6', [(1, 'raw', 'Z6_d[eps^0 l^1]')]),
    'EA5_d_0': ('U package: (EE A5_d)_0 = [eps^0 l^0] d_delta E A5', [(1, 'raw', 'A5_dE[eps^0 l^0]')]),
    'EZ4_d_0': ('U package: (EE Z4_d)_0 = [eps^0 l^0] d_delta E Z4', [(1, 'raw', 'Z4_dE[eps^0 l^0]')]),
    'D_lower': ('U package: D_lower = U - A7_d_1 + Z6_d_1 - 2 (EE A5_d)_0 + 2 (EE Z4_d)_0 (note l.1344-1347)',
                [(1, 'out', 'U'), (-1, 'raw', 'A7_d[eps^0 l^1]'), (1, 'raw', 'Z6_d[eps^0 l^1]'),
                 (-2, 'raw', 'A5_dE[eps^0 l^0]'), (2, 'raw', 'Z4_dE[eps^0 l^0]')]),
    'P8': ('Kv package: P8 = [eps^0 l^1] Q8_v', [(1, 'raw', 'Q8_v[eps^0 l^1]')]),
    'X_vv': ('Kv package: X_vv = [eps^0 l^0] Q6_vv', [(1, 'raw', 'Q6_vv[eps^0 l^0]')]),
    'X_E': ('Kv package: X_E = [eps^0 l^0] d_v E Q6', [(1, 'raw', 'Q6_vE[eps^0 l^0]')]),
    'F3_known': ('Kv package: F3_known = Kv + 4 P8 = 16 X_vv - 8 X_E + S3', [(1, 'out', 'Kv'), (4, 'raw', 'Q8_v[eps^0 l^1]')]),
    'S3': ('Kv package: S3 = Kv + 4 P8 - 16 X_vv + 8 X_E (note l.1363-1366)',
           [(1, 'out', 'Kv'), (4, 'raw', 'Q8_v[eps^0 l^1]'), (-16, 'raw', 'Q6_vv[eps^0 l^0]'), (8, 'raw', 'Q6_vE[eps^0 l^0]')]),
    'A9_1': ('J9 package: A9_1 = [eps^0 l^1] A9', [(1, 'raw', 'A9[eps^0 l^1]')]),
    'Z8_1': ('J9 package: Z8_1 = [eps^0 l^1] Z8', [(1, 'raw', 'Z8[eps^0 l^1]')]),
    'EA7_0': ('J9 package: (EE A7)_0 = [eps^0 l^0] E A7', [(1, 'raw', 'A7_E[eps^0 l^0]')]),
    'EZ6_0': ('J9 package: (EE Z6)_0 = [eps^0 l^0] E Z6', [(1, 'raw', 'Z6_E[eps^0 l^0]')]),
    'D9_lower': ('J9 package: D9_lower = J9 - A9_1 + Z8_1 - 2 (EE A7)_0 + 2 (EE Z6)_0 (note l.1388-1391)',
                 [(1, 'out', 'J9'), (-1, 'raw', 'A9[eps^0 l^1]'), (1, 'raw', 'Z8[eps^0 l^1]'),
                  (-2, 'raw', 'A7_E[eps^0 l^0]'), (2, 'raw', 'Z6_E[eps^0 l^0]')]),
    'P6': ('Ndelta package: P6 = [eps^0 l^1] Q6_vd', [(1, 'raw', 'Q6_vd[eps^0 l^1]')]),
    'F1_known': ('Ndelta package: F1_known = Ndelta + 4 P6 (eq:NdP6)', [(1, 'out', 'Ndelta'), (4, 'raw', 'Q6_vd[eps^0 l^1]')]),
    'C_fixed': ('C_fixed = C8 + P6/2 (eq:C8short: C8 = C_fixed - P6/2)', [(1, 'out', 'C8'), (mp.mpf(1) / 2, 'raw', 'Q6_vd[eps^0 l^1]')]),
    'C8_without_J9': ('C8 - J9/4: C8 without its J9 term (the tier-B target quantity)', [(1, 'out', 'C8'), (-mp.mpf(1) / 4, 'out', 'J9')]),
}
# expected exact gradients d(output)/d(raw) in the derivative convention (note structure; spec definition_chain_C8.json)
STRUCT = [('U', 'A7_d[eps^0 l^1]', 1, 'l.1344-1347'), ('U', 'Z6_d[eps^0 l^1]', -1, 'l.1344-1347'),
          ('U', 'A5_dE[eps^0 l^0]', 2, 'l.1344-1347'), ('U', 'Z4_dE[eps^0 l^0]', -2, 'l.1344-1347'),
          ('Kv', 'Q8_v[eps^0 l^1]', -4, 'l.1363-1366'), ('Kv', 'Q6_vv[eps^0 l^0]', 16, 'l.1363-1366'),
          ('Kv', 'Q6_vE[eps^0 l^0]', -8, 'l.1363-1366'), ('J9', 'A9[eps^0 l^1]', 1, 'l.1388-1391'),
          ('J9', 'Z8[eps^0 l^1]', -1, 'l.1388-1391'), ('J9', 'A7_E[eps^0 l^0]', 2, 'l.1388-1391'),
          ('J9', 'Z6_E[eps^0 l^0]', -2, 'l.1388-1391'), ('Ndelta', 'Q6_vd[eps^0 l^1]', -4, 'eq:NdP6 l.1328'),
          ('Ndelta', 'Q4_vvd[eps^0 l^0]', 16, 'l.1319-1321'), ('Ndelta', 'Q4_vdE[eps^0 l^0]', -8, 'l.1319-1321'),
          ('C8', 'Q6_vd[eps^0 l^1]', mp.mpf(-1) / 2, 'eq:C8short'), ('C8', 'A9[eps^0 l^1]', mp.mpf(1) / 4, 'eq:C8assembly'),
          ('C8', 'Q8_v[eps^0 l^1]', mp.mpf(-1) / 8, 'eq:C8assembly'), ('C8', 'A7_d[eps^0 l^1]', mp.mpf(3) / 4, 'eq:C8assembly')]
# heavy jobs: production run dir, group, needed scalar; probe/pilot runs on the same sector samples (c8conv sample)
HEAVY = [('B', 'c8tierB_s0.01_r1', 'Q8_v', 'Q8_v[eps^0 l^1]', 'S84'),
         ('B', 'c8tierB_s0.01_r1', 'Q6_vE', 'Q6_vE[eps^0 l^0]', 'S42'),
         ('B', 'c8tierB_s0.01_r1', 'A7_d', 'A7_d[eps^0 l^1]', 'S12'),
         ('C', 'c8tierC_s3_r2', 'A9_base', 'A9[eps^0 l^1]', 'S672'),
         ('C', 'c8tierC_s3_r2', 'A7_E', 'A7_E[eps^0 l^0]', 'S336'),
         ('C', 'c8tierC_s3_topup1', 'Z8_base', 'Z8[eps^0 l^1]', 'S84'),
         ('C', 'c8tierC_s3_can', 'Z6_E', 'Z6_E[eps^0 l^0]', 'S42')]
RELEVANT = {  # jets through which the new inputs enter (normalized responses; derivative order v, delta)
    'W': ['C3[v0d3]', 'C3[ddd]'], 'S': ['C5[v0d2]', 'C5_2[v0d2]', 'EC3[v0d2]', 'C3[dd]'],
    'L3': ['K4[v3d0]', 'K4[vvv]'], 'M21': ['K4[v2d1]', 'K4[vvd]'], 'M12': ['K4[v1d2]', 'K4[vdd]'],
    'N2': ['K6[v2d0]', 'K6_2[v2d0]', 'EK4[v2d0]', 'K4[vv]'], 'Ndelta': ['K6[v1d1]', 'K6_2[v1d1]', 'EK4[v1d1]', 'K4[vd]'],
    'U': ['C7[v0d1]', 'C7_2[v0d1]', 'EC5[v0d1]'], 'Kv': ['K8[v1d0]', 'K8_2[v1d0]', 'EK6[v1d0]'],
    'J9': ['C9[v0d0]', 'C9_2[v0d0]', 'EC7[v0d0]']}


def log(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)


def fl(x):
    return None if x is None else float(x)


def sha256(path):
    with open(path, 'rb') as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def frac(c):
    return mp.mpf(c.numerator) / c.denominator


def cn(nm):
    return L.canonical_raw_name(nm)


def rel(p):
    return os.path.relpath(p, CM.ROOT)


# ======================================================================================================
# per-sector replicate data of every job of the final inputs (production, tiers A, B, C)
# ======================================================================================================
def tier_job_sets(final_file, tagp):
    """jobs of one tier deliverable: the main run of its producer, the groups merged from other runs (merge_runs)"""
    prod = json.load(open(final_file))['producer']
    main = os.path.join(RUNS, os.path.basename(os.path.normpath(prod['run'])))
    merged = {g: os.path.join(RUNS, os.path.basename(os.path.normpath(p))) for g, p in (prod.get('merged') or {}).items()}
    jobs = {}
    for k, v in PE.job_sector_values(main, tag=f'{tagp}{os.path.basename(main)}:').items():
        if k[1] not in merged:
            jobs[k] = v
    by_dir = {}
    for g, d in merged.items():
        by_dir.setdefault(d, set()).add(g)
    for d, gs in by_dir.items():
        jobs.update(PE.job_sector_values(d, groups=gs, tag=f'{tagp}{os.path.basename(d)}:'))
    return jobs, {'main': rel(main), 'merged': {g: rel(d) for g, d in merged.items()}}


def all_jobs():
    jobs = {('P:' + k[0],) + k[1:]: v for k, v in PE.final_jobs(CM.PROD, CM.TOPUP, REPLACED).items()}
    srcs = {'P': {'main': rel(CM.PROD), 'merged': {g: rel(CM.TOPUP) for g in REPLACED}}}
    for t, f in TIER_FILES.items():
        j, s = tier_job_sets(f, f'{t}:')
        jobs.update(j)
        srcs[t] = s
    return jobs, srcs


def tier_of_job(key):
    return key[0].split(':')[0]


# ======================================================================================================
# estimators
# ======================================================================================================
class Est:
    def __init__(self, inp, jobs):
        self.inp = inp
        self.jobs = jobs
        fixed = inp.fixed_names
        self.extra = inp.errmodel.restricted(keep_sig=inp.errmodel.sig, keep_blocks=fixed, keep_reps=None)

    def stats(self, x, per, tiers=None):
        """x: Val (internal gradient); per: per-replicate values (input convention of the quantity)"""
        g = PE.input_gradient(x, self.inp)
        s_cov = mp.sqrt(self.inp.errmodel.variance(x.g))
        R = len(per)
        m = sum(per) / R
        se = mp.sqrt(sum((v - m) ** 2 for v in per) / (R - 1)) / mp.sqrt(R)
        sx = mp.sqrt(self.extra.variance(x.g))
        s_rep = mp.sqrt(se ** 2 + sx ** 2)
        r_stat, p_stat, per_job = PE.pooled_projection(self.jobs, g)
        s_pool = mp.sqrt(mp.mpf(p_stat) ** 2 + sx ** 2)
        jm = math.sqrt(sum(max(j['rep'], j['pool']) ** 2 for j in per_job))
        s_jm = mp.sqrt(mp.mpf(jm) ** 2 + sx ** 2)
        q = max(s_cov, s_rep, s_pool)
        which = ['sigma_cov', 'sigma_rep', 'sigma_pool'][[s_cov, s_rep, s_pool].index(q)]
        out = {'value': mp.nstr(x.v, 30), 'rep_mean': mp.nstr(m, 30), 'nonlinearity': fl(m - x.v),
               'sigma_cov': fl(s_cov), 'sigma_rep': fl(s_rep), 'rep_se_stat': fl(se), 'sigma_pool': fl(s_pool),
               'sigma_pool_stat': p_stat, 'sigma_rep_stat_projection': r_stat, 'sigma_floor': fl(sx),
               'sigma_jobmax': fl(s_jm), 'sigma': fl(q), 'quoted_estimator': which,
               'rel_sigma': fl(q / abs(x.v)) if x.v != 0 else None,
               'per_replicate': [mp.nstr(v, 25) for v in per],
               'top_jobs': [{'job': j['job'], 'pool': j['pool'], 'rep': j['rep'], 'nsec': j['nsec']} for j in per_job[:8]]}
        if tiers:
            tp = {}
            for t, names in tiers.items():
                em = self.inp.errmodel.restricted(keep_sig=names, keep_blocks=names, keep_reps=names)
                tj = {k: v for k, v in self.jobs.items() if tier_of_job(k) == t}
                rr_, pp_, pj_ = PE.pooled_projection(tj, g)
                tp[t] = {'sigma_cov': fl(mp.sqrt(em.variance(x.g))), 'sigma_pool_stat': pp_, 'sigma_rep_stat': rr_,
                         'sigma_jobmax_stat': math.sqrt(sum(max(j['rep'], j['pool']) ** 2 for j in pj_))}
            out['by_tier'] = tp
        return out, per_job


# ======================================================================================================
# step 1
# ======================================================================================================
def verify_inputs():
    recs = {}
    for f in (os.path.join(RUNS, 'c8tierA', 'SHA256SUMS_results.txt'), os.path.join(RUNS, 'c8BC_SHA256SUMS.txt')):
        for line in open(f):
            if line.startswith('#') or not line.strip():
                continue
            h, p = line.split()[:2]
            recs[p] = h
    checked = {}
    for p, h in recs.items():
        full = os.path.join(CM.ENG_DIR, p)
        got = sha256(full)
        assert got == h, f'{p}: SHA-256 {got} differs from the engine record {h}'
        checked[p] = h
    for f in list(TIER_FILES.values()) + [ABC_FILE]:
        assert rel(f).replace('engine/', '', 1) in checked, f'{f} has no engine SHA-256 record'
    log(f'  engine SHA-256 records verified: {len(checked)} files (tier A, tiers B/C, merged A+B+C)')
    return checked


def subpiece(name, cen, per_rep, inp, R):
    """Val (internal gradient, input-convention value) and per-replicate values of a sub-piece"""
    _, terms = SUB[name]
    v, g, per = mp.mpf(0), {}, [mp.mpf(0)] * R
    for c, kind, nm in terms:
        c = mp.mpf(c)
        if kind == 'out':
            x = cen.get(nm)
            xs = per_rep[nm]
        else:
            k = cn(nm)
            f = mp.mpf(inp.scale[k])
            x = L.Val(inp.values[k] * f, {k: f})
            xs = [(inp.reps[k][r] if k in inp.reps else inp.values[k]) * f for r in range(R)]
        v += c * x.v
        for kk, gg in x.g.items():
            g[kk] = g.get(kk, 0) + c * gg
        per = [per[r] + c * xs[r] for r in range(R)]
    return L.Val(v, g), per


def step1():  # noqa: C901
    log('=' * 110)
    log('STEP 1: framework at order C8 (strict on every output, per replicate) on production + tiers A + B + C')
    log('=' * 110)
    checked = verify_inputs()
    prod = L.load_inputs(CM.FINAL_CANON)
    abc = L.load_inputs(ABC_FILE)
    tiers = {t: L.load_inputs(f) for t, f in TIER_FILES.items()}
    names = {'P': {cn(k) for k in prod['scalars']}}
    for t, d in tiers.items():
        names[t] = {cn(k) for k in d['scalars']}
    assert names['A'] | names['B'] | names['C'] == {cn(k) for k in abc['scalars']}
    merged = L.merge_inputs([prod, abc], independent=True)
    fw = L.Framework('C8', dps=DPS)
    strict_outputs = CM.BETA_D4 + NEW10 + CM.CS + PARTS + ['C8_partial']
    t0 = time.time()
    rr = fw.from_replicates(merged, strict=True, outputs=strict_outputs)
    t_asm = time.time() - t0
    log(f'  per-replicate assembly at order C8: {t_asm:.1f} s; R = {rr.meta["n_replicates"]}, {rr.meta["n_inputs"]} '
        f'inputs ({rr.meta["n_replicated"]} replicated in {rr.meta["replicate_blocks"]} blocks), exact '
        f'{rr.meta["exact_inputs"]}; strict outputs {len(strict_outputs)}; warnings {rr.warnings}')
    assert rr.meta['strict'] and rr.meta['n_replicates'] == 6
    need = fw.required_inputs()
    have = {cn(x) for x in merged['scalars']}
    missing_all = {o: sorted(set(v) - have) for o, v in need.items() if set(v) - have}
    assert not missing_all, missing_all
    n_required = len(set().union(*[set(v) for v in need.values()]))
    log(f'  strictness: every raw scalar of every output is supplied ({n_required} required, {len(have)} supplied)')
    cen = rr.central
    inp, _ = fw._parse(merged, 'raw', None, None, None)
    R = rr.meta['n_replicates']
    t0 = time.time()
    jobs, job_sources = all_jobs()
    rep_names = set(inp.reps)
    owner = {}
    for key, d in jobs.items():
        for sec in d['sectors'].values():
            for nm in sec:
                if nm in rep_names:
                    if nm in owner and owner[nm] != key:
                        raise AssertionError(f'{nm} in two jobs {owner[nm]} and {key}')
                    owner[nm] = key
    assert rep_names <= set(owner), sorted(rep_names - set(owner))[:5]
    for nm, key in owner.items():
        t = tier_of_job(key)
        assert nm in names[t], (nm, key)
    log(f'  sector-pooled data: {len(jobs)} jobs ' +
        str({t: sum(1 for k in jobs if tier_of_job(k) == t) for t in 'PABC'}) +
        f'; every replicated scalar in exactly one job of its own tier; {time.time() - t0:.1f} s')
    E = Est(inp, jobs)
    res, perjob = {}, {}
    outs = NEW10 + PARTS + ['C8_partial']
    for o in outs:
        st, pj = E.stats(cen.get(o), rr.per_rep[o], tiers=names)
        fs = rr.stats[o]
        assert abs(mp.mpf(st['sigma_cov']) - fs['sigma_linear']) <= 1e-12 * fs['sigma_linear'] + mp.mpf(10) ** -40
        assert abs(mp.mpf(st['sigma_rep']) - fs['sigma_rep_total']) <= 1e-12 * fs['sigma_rep_total'] + mp.mpf(10) ** -40
        res[o] = st
        perjob[o] = pj
    sub = {}
    for nm in SUB:
        x, per = subpiece(nm, cen, rr.per_rep, inp, R)
        st, pj = E.stats(x, per, tiers=names)
        st['definition'] = SUB[nm][0]
        sub[nm] = st
        perjob[nm] = pj
    # strict completeness of C8 and C8_asm vs 8 T4
    info = {k: (mp.nstr(v, 5) if isinstance(v, mp.mpf) else v) for k, v in cen.c8_info.items()}
    assert not cen.c8_info.get('partial_missing'), cen.c8_info.get('partial_missing')
    d_asm = mp.mpf(res['C8_asm']['value']) - mp.mpf(res['C8']['value'])
    d_part = mp.mpf(res['C8_partial']['value']) - mp.mpf(res['C8_asm']['value'])
    assert d_part == 0
    log(f'  C8 = 8 T4 = {mp.nstr(mp.mpf(res["C8"]["value"]), 20)}; C8_asm (eq:C8assembly) - 8 T4 = {mp.nstr(d_asm, 3)} '
        f'(the engine tree data A3[eps^0 l^1] = 6 to double precision; c8_info {info})')
    log('\n  %-14s %30s %10s %10s %10s %10s %10s %9s' % ('output', 'value (central)', 'sig_cov', 'sig_rep', 'sig_pool',
                                                        'sig_jobmax', 'sigma', 'rel'))
    for o in outs + list(SUB):
        e = res.get(o) or sub[o]
        log('  %-14s %30s %10.3e %10.3e %10.3e %10.3e %10.3e %9.1e' % (
            o, mp.nstr(mp.mpf(e['value']), 22), e['sigma_cov'], e['sigma_rep'], e['sigma_pool'], e['sigma_jobmax'],
            e['sigma'], e['rel_sigma'] or 0))
    # ---- gradients: the note's raw structure
    struct = []
    for o, nm, exp, where in STRUCT:
        g = cen.gradient(o).get(cn(nm), mp.mpf(0))
        ok = bool(abs(g - exp) < mp.mpf(10) ** -30)
        struct.append({'output': o, 'raw': nm, 'd_output_d_raw': mp.nstr(g, 20), 'expected': mp.nstr(mp.mpf(exp), 10),
                       'agree': ok, 'note': where})
        assert ok, (o, nm, g, exp)
    # sub-piece remainders have no gradient on the explicit raw scalars
    for nm in ('D_known', 'D_lower', 'S3', 'D9_lower', 'F1_known', 'C_fixed'):
        x, _ = subpiece(nm, cen, rr.per_rep, inp, R)
        gi = {k: v / inp.scale.get(k, 1) for k, v in x.g.items()}
        for c_, kind, raw in SUB[nm][1]:
            if kind == 'raw':
                assert abs(gi.get(cn(raw), 0)) < mp.mpf(10) ** -30, (nm, raw, gi.get(cn(raw)))
    log('  raw structure (exact gradients, derivative convention) agrees with the note for all '
        f'{len(struct)} entries; the remainders D_known, D_lower, S3, D9_lower, F1_known, C_fixed have zero gradient on '
        'the explicit raw scalars')
    # ---- unchanged earlier results
    p3 = json.load(open(os.path.join(CM.FW_DIR, 'out', 'C8_production.json')))
    d_bold = mp.mpf(res['B_old8']['value']) - mp.mpf(p3['B_old']['value'])
    assert abs(d_bold) < mp.mpf(10) ** -20, d_bold
    ind = json.load(open(os.path.join(CM.ROOT, 'RESULTS_independent.json')))['step1']['outputs']
    d_old = {o: fl(cen.get(o).v - mp.mpf(ind[o]['value'])) for o in CM.CS + CM.BETA_D4}
    assert all(abs(v) < 1e-20 * (1 + abs(float(ind[o]['value']))) for o, v in d_old.items()), d_old
    ta = json.load(open(TIERA_RESULTS))['step1']['outputs']
    d_ta = {}
    for o in NEW_A + ['B_old8', 'B_done8']:
        d_ta[o] = {'value': fl(mp.mpf(res[o]['value']) - mp.mpf(ta[o]['value'])),
                   'sigma_rel': fl((res[o]['sigma'] - ta[o]['sigma']) / ta[o]['sigma'])}
        assert abs(d_ta[o]['value']) < 1e-20 * (1 + abs(float(ta[o]['value']))), (o, d_ta[o])
        assert abs(d_ta[o]['sigma_rel']) < 1e-9, (o, d_ta[o])
    log(f'  unchanged: B_old = phase 3 (diff {mp.nstr(d_bold, 2)}); C3..C7 and the 25 old inputs = phase 2 (max |diff| '
        f'{max(abs(v) for v in d_old.values()):.1e}); the seven tier-A inputs, B_old, B_done = the tier-A assembly '
        f'(values and quoted sigmas)')
    # ---- composition of C8: the terms of eq:C8assembly
    terms = {}
    for nm, c in L.C8_LINEAR.items():
        v = mp.mpf(res[nm]['value'])
        terms[nm] = {'coefficient': str(c), 'input': res[nm]['value'], 'contribution': mp.nstr(v * frac(c), 25),
                     'sigma_contribution': abs(float(frac(c))) * res[nm]['sigma'],
                     'tier': 'B' if nm in ('U', 'Kv') else ('C' if nm == 'J9' else 'A')}
    s = mp.mpf(res['B_old8']['value']) + sum(mp.mpf(t['contribution']) for t in terms.values())
    assert abs(s - mp.mpf(res['C8_asm']['value'])) < mp.mpf(10) ** -18
    log('  C8_asm = B_old + ' + ' + '.join(f'({terms[nm]["coefficient"]}) {nm}' for nm in L.C8_LINEAR))
    for nm, t in terms.items():
        log(f'    {nm:7s} x {t["coefficient"]:>5s} = {mp.nstr(mp.mpf(t["contribution"]), 20):>26s}  +- {t["sigma_contribution"]:.2e}')
    # ---- error budget of C8 by job (all three estimators per job; jobmax = max(rep, pool) per job)
    budget = {}
    for o in ('C8', 'C8_without_J9', 'U', 'Kv', 'J9'):
        pj = perjob[o]
        tot_jm = sum(max(j['rep'], j['pool']) ** 2 for j in pj)
        rows = []
        for j in sorted(pj, key=lambda j: -max(j['rep'], j['pool']))[:12]:
            jm = max(j['rep'], j['pool'])
            rows.append({'job': j['job'], 'tier': j['job'].split(':')[0], 'rep': j['rep'], 'pool': j['pool'],
                         'max': jm, 'share_of_variance': jm ** 2 / tot_jm if tot_jm else None, 'nsec': j['nsec']})
        by_t = {}
        for j in pj:
            t = j['job'].split(':')[0]
            b = by_t.setdefault(t, {'rep2': 0.0, 'pool2': 0.0, 'max2': 0.0, 'njobs': 0})
            b['rep2'] += j['rep'] ** 2
            b['pool2'] += j['pool'] ** 2
            b['max2'] += max(j['rep'], j['pool']) ** 2
            b['njobs'] += 1
        by_t = {t: {'sigma_rep_stat': math.sqrt(b['rep2']), 'sigma_pool_stat': math.sqrt(b['pool2']),
                    'sigma_jobmax_stat': math.sqrt(b['max2']), 'share_of_jobmax_variance': b['max2'] / tot_jm if tot_jm else None,
                    'njobs': b['njobs']} for t, b in sorted(by_t.items())}
        e = res.get(o) or sub[o]
        budget[o] = {'largest_jobs': rows, 'by_tier': by_t, 'sigma_floor': e['sigma_floor'], 'sigma': e['sigma'],
                     'note': 'per job: replicate (rep) and sector-pooled (pool) projections of the job on the gradient; '
                             'max = the larger of the two; shares of sum(max^2). Tier P = phase-2 production.'}
        log(f'\n  error budget of {o}: sigma {e["sigma"]:.3e} (cov {e["sigma_cov"]:.3e}, rep {e["sigma_rep"]:.3e}, pool '
            f'{e["sigma_pool"]:.3e}, jobmax {e["sigma_jobmax"]:.3e}); by tier ' +
            ', '.join(f'{t} {b["sigma_jobmax_stat"]:.2e} ({100 * (b["share_of_jobmax_variance"] or 0):.1f} %)' for t, b in by_t.items()))
        for r in rows[:6]:
            log(f'    {r["job"]:42s} rep {r["rep"]:.3e} pool {r["pool"]:.3e} share {100 * r["share_of_variance"]:.2f} % ({r["nsec"]} sectors)')
    meta = {'framework': 'framework/lri_framework.py Framework("C8", dps=50).from_replicates(strict=True, outputs=the 35 '
                         'inputs, C3..C7, B_old8, B_done8, C8_asm, T4, C8, C8_partial)',
            'inputs': {'production': {'path': rel(CM.FINAL_CANON), 'sha256': sha256(CM.FINAL_CANON)},
                       'tiers_ABC': {'path': rel(ABC_FILE), 'sha256': sha256(ABC_FILE),
                                     'note': 'tiers A + B + C merged per scalar by the engine (tests/merge_tiers_C8.py)'},
                       'tier_files': {t: {'path': rel(f), 'sha256': sha256(f), 'n_scalars': len(names[t])}
                                      for t, f in TIER_FILES.items()}},
            'engine_sha256_records_verified': checked,
            'n_inputs': rr.meta['n_inputs'], 'n_required': n_required, 'R': R,
            'replicate_blocks': rr.meta['replicate_blocks'], 'exact_inputs': rr.meta['exact_inputs'],
            'warnings': rr.warnings, 'c8_info': info, 'C8_asm_minus_8T4': fl(d_asm), 'assembly_seconds': round(t_asm, 1),
            'pooled_jobs': {t: sum(1 for k in jobs if tier_of_job(k) == t) for t in 'PABC'}, 'job_sources': job_sources,
            'unchanged': {'B_old_minus_phase3': fl(d_bold), 'old_inputs_C3_C7_minus_phase2_max': max(abs(v) for v in d_old.values()),
                          'tierA_inputs_minus_tierA_assembly': d_ta},
            'sigma_definitions': {
                'sigma_cov': 'linear propagation with the per-job replicate sample covariance / R, plus precision '
                             'floors (framework sigma_linear)',
                'sigma_rep': 'sd of the R=6 per-replicate assemblies / sqrt(R), plus floors (framework sigma_rep_total)',
                'sigma_pool': 'sector-pooled projection of every job on the output gradient (pooled_errors.py), plus '
                              'floors in quadrature',
                'sigma': 'max(sigma_cov, sigma_rep, sigma_pool): quoted error',
                'sigma_jobmax': 'reference only: per job the larger of its replicate and sector-pooled projection, summed '
                                'in quadrature over jobs, plus floors (the engine budget_C8.py combination)',
                'by_tier': 'error carried by the scalars of one tier alone (P = phase-2 production, A, B, C)'}}
    return res, sub, terms, budget, struct, meta, fw, merged, inp, cen, names, prod, abc, tiers, jobs, E


def w_three_ways(res):
    sys.path.insert(0, CM.FW_DIR)
    import c8_production as C8P
    W50 = C8P.semi_analytic_W(50)
    vt = json.load(open(os.path.join(CM.SPEC_DIR, 'out', 'C8', 'validation_targets_C8.json')))
    Wsp = next(t for t in vt['independent_values'] if t['id'] == 'input.W')
    We, sW = mp.mpf(res['W']['value']), res['W']['sigma']
    out = {'engine': res['W']['value'], 'engine_sigma': sW, 'framework_semi_analytic_50digit': mp.nstr(W50, 40),
           'spec_three_kink': Wsp['value'], 'engine_minus_semi_analytic': fl(We - W50),
           'pull_engine_vs_semi_analytic': fl((We - W50) / sW), 'spec_minus_semi_analytic': fl(mp.mpf(Wsp['value']) - W50),
           'C8_with_semi_analytic_W': mp.nstr(mp.mpf(res['C8']['value']) + 4 * (W50 - We), 25)}
    log(f'  W three ways: engine - semi-analytic {out["engine_minus_semi_analytic"]:+.2e} (pull '
        f'{out["pull_engine_vs_semi_analytic"]:+.2f}); spec - semi-analytic {out["spec_minus_semi_analytic"]:+.1e}')
    return out


def separate_files_check(fw, cen, prod, tiers):
    """the three tier deliverables fed separately (blocks renamed per file) must give the merged result"""
    m3 = L.merge_inputs([prod] + [tiers[t] for t in 'ABC'], independent=True)
    r3 = fw.from_raw(m3, strict=True)
    rows = {}
    for o in NEW10 + ['B_old8', 'B_done8', 'C8_asm', 'C8']:
        a, b = cen.get(o), r3.get(o)
        rows[o] = {'value_diff': fl(a.v - b.v), 'sigma_linear_merged': fl(cen.sigma(a)), 'sigma_linear_separate': fl(r3.sigma(b))}
        assert abs(a.v - b.v) < mp.mpf(10) ** -30 * (1 + abs(a.v)), (o, a.v - b.v)
        assert abs(cen.sigma(a) - r3.sigma(b)) < mp.mpf(10) ** -12 * cen.sigma(a), o
    log(f'  three tier files fed separately: identical values and linear sigmas for {len(rows)} outputs')
    return rows


# ------------------------------------------------------------------------------------------------------
# tier consistency
# ------------------------------------------------------------------------------------------------------
def restricted_var(inp, nms, val):
    return inp.errmodel.restricted(keep_sig=nms, keep_blocks=nms, keep_reps=nms).variance(val.g)


def pilot_swap(fw, cen, inp, prod, abc, names):
    """tier B/C scalars replaced by the pilots' all-sector values where these exist (input level)"""
    sys.path.insert(0, os.path.join(CM.ENG_DIR, 'tests'))
    from preview_C8 import pilot_scalars
    bc = names['B'] | names['C']
    best = pilot_scalars(PILOT_RUNS, bc)
    swap = sorted(nm for nm, (_, ent, _) in best.items() if not ent.get('exact'))
    kept = sorted(bc - set(swap))
    sc = {}
    for k, v in abc['scalars'].items():
        c = cn(k)
        sc[k] = best[c][1] if c in swap else v
    alt = dict(abc)
    alt['scalars'] = sc
    alt['sources'] = ['c8pilot_swapBC']
    m = L.merge_inputs([prod, alt], independent=True)
    r = fw.from_raw(m, strict=True)
    inpa, _ = fw._parse(m, 'raw', None, None, None)
    sw = set(swap)
    rows = {}
    for o in NEW_BC + ['C8']:
        x, y = cen.get(o), r.get(o)
        d = x.v - y.v
        sp, sa = mp.sqrt(restricted_var(inp, sw, x)), mp.sqrt(restricted_var(inpa, sw, y))
        sd = mp.sqrt(sp ** 2 + sa ** 2)
        rows[o] = {'production': mp.nstr(x.v, 20), 'pilot_swap': mp.nstr(y.v, 20), 'diff': fl(d), 'sigma_production_part': fl(sp),
                   'sigma_pilot_part': fl(sa), 'sigma_diff': fl(sd), 'pull': fl(d / sd) if sd > 0 else None}
    # which swapped scalars carry the comparison (largest pilot-side error contributions to C8)
    gC8 = cen.gradient('C8')
    big = sorted(((abs(float(gC8.get(nm, 0))) * float(best[nm][0]), nm) for nm in swap), reverse=True)[:6]
    log('  tier B/C vs pilots (input level, ' + f'{len(swap)} scalars swapped, {len(kept)} without an all-sector pilot value): ' +
        ', '.join(f'{o} {v["diff"]:+.3e} +- {v["sigma_diff"]:.2e} ({v["pull"]:+.2f})' for o, v in rows.items()))
    return {'what': 'U, Kv, J9, C8 from production + tiers A, B, C minus the same with the tier-B/C scalars replaced by '
                    'the pilots\' all-sector values (c8val, c8conv, c8kplus1, poles1, kplus1; independent seeds) where '
                    'they exist; sigma = the swapped scalars of both runs (linear, replicate covariance + floors)',
            'swapped': swap, 'not_swapped_no_all_sector_pilot': kept,
            'pilot_sources': {nm: best[nm][2] for nm in swap},
            'largest_pilot_side_C8_errors': [{'scalar': nm, 'abs_dC8_x_err': v} for v, nm in big], 'rows': rows}


def per_sector_sums(rundir, group, name, stride_off=None):
    """{global sector id: (mean, var/R)} of one coefficient of one job (probe/pilot local ids mapped to global ones)"""
    js = PE.job_sector_values(rundir, groups={group}, all_coeffs=True)
    assert len(js) == 1, (rundir, group, list(js))
    (_, d), = js.items()
    out = {}
    key = None
    want = name.split('[')[1]                       # 'eps^0 l^1]'
    for sid, vals in d['sectors'].items():
        if key is None:
            keys = [k for k in vals if k.split('[')[1] == want]
            assert len(keys) == 1, (rundir, group, name, list(vals))
            key = keys[0]
        xs = vals[key]
        R = len(xs)
        m = sum(xs) / R
        v = stt.variance(xs) / R
        g = sid if stride_off is None else stride_off[1] + sid * stride_off[0]
        out[g] = (m, v)
    return out


def heavy_subset_checks(cen):
    """sector-subset comparison: production vs the probe c8probeBC and the conv pilot c8conv (N = 1009, 4001) on the
    sector sample of the conv pilot; independent seeds; sum over the common sectors"""
    gC8 = cen.gradient('C8')
    rows = []
    for tier, rd, group, name, S in HEAVY:
        prod = per_sector_sums(os.path.join(RUNS, rd), group, name)
        g8 = float(gC8.get(cn(name), 0))
        for ref in ('c8probeBC', 'c8conv'):
            man = json.load(open(os.path.join(RUNS, ref, 'manifest.json')))
            for m in man:
                mo = m['moment']
                if not re.fullmatch(re.escape(group) + r'_N\d+_' + S, mo):
                    continue
                ss = next(e for e in m['extra'] if 'sectorstride' in e).split()
                stride, off = int(ss[1]), int(ss[2])
                assert stride * m['nsec_total'] == next(x for x in json.load(open(os.path.join(RUNS, rd, 'manifest.json')))
                                                        if x['moment'] == group)['nsec_total']
                pr = per_sector_sums(os.path.join(RUNS, ref), mo, name, (stride, off))
                common = sorted(set(pr) & set(prod))
                assert len(common) == len(pr), (mo, len(common), len(pr))
                xp = sum(prod[s][0] for s in common)
                vp = sum(prod[s][1] for s in common)
                xr = sum(pr[s][0] for s in common)
                vr = sum(pr[s][1] for s in common)
                d = xp - xr
                sd = math.sqrt(vp + vr)
                rows.append({'tier': tier, 'job': group, 'scalar': name, 'reference': f'{ref}:{mo}', 'N_ref': m['N'],
                             'n_sectors': len(common), 'sum_production': xp, 'sum_reference': xr, 'diff': d,
                             'sigma_production': math.sqrt(vp), 'sigma_reference': math.sqrt(vr), 'sigma_diff': sd,
                             'pull': d / sd if sd > 0 else None, 'dC8_dx': g8, 'diff_in_C8': g8 * d, 'sigma_in_C8': abs(g8) * sd})
    log('  heavy jobs vs probe/conv pilots on the same sector samples (sector-pooled errors of both sides):')
    for r in rows:
        log(f"    {r['scalar']:18s} vs {r['reference']:28s} {r['n_sectors']:3d} sectors: diff {r['diff']:+.3e} +- "
            f"{r['sigma_diff']:.2e} (pull {r['pull']:+.2f}); in C8 {r['diff_in_C8']:+.2e} +- {r['sigma_in_C8']:.1e}")
    return {'what': 'for each heavy job, the sum over the sector sample of the conv pilot (every S-th sector, offset S/2) '
                    'of the production per-sector estimates vs an independent run on exactly those sectors: the probe '
                    '(c8probeBC, planned production N) and the conv pilot (N = 1009, 4001; pre-asymptotic). Each side '
                    'sum_s mean_r x_sr with variance sum_s var_r(x_sr)/R. Disjoint seeds (different tier names).',
            'rows': rows}


def raw_run_coef(rundir, group, kj, name):
    R = json.load(open(os.path.join(rundir, 'results.json')))
    v, _ = R['results'][group][kj]
    ex = R['errors'][group][kj]
    jobs = PE.job_sector_values(rundir, groups={group}, all_coeffs=True, keep={name})
    jobs = {k: j for k, j in jobs.items() if k[2] == int(kj.split(',')[0])}
    rep, pool, _ = PE.pooled_projection(jobs, {name: 1.0})
    return {'value': v, 'sigma_rep': rep, 'sigma_pool': pool, 'floor': ex['floor'],
            'sigma': math.sqrt(max(rep, pool) ** 2 + ex['floor'] ** 2)}


def replaced_run_checks(cen):
    """runs replaced by top-ups (fresh seeds): the old run vs the delivered one, raw and in C8 units"""
    gC8 = cen.gradient('C8')
    out = []
    for lab, old, new, grp, kj, name, out_in in (
            ('Z8 (tier C): N = 4001 (r2) vs top-up N = 11321', 'c8tierC_s3_r2', 'c8tierC_s3_topup1', 'Z8_base', '0,1', 'Z8[eps^0 l^1]', 'J9'),
            ('A5_dE (tier B): N = 64007 (_can) vs top-up N = 262139', 'c8tierB_s0.01_can', 'c8tierB_s0.01_topup1', 'A5_dE', '0,0', 'A5_dE[eps^0 l^0]', 'U')):
        a = raw_run_coef(os.path.join(RUNS, old), grp, kj, name)
        b = raw_run_coef(os.path.join(RUNS, new), grp, kj, name)
        d = b['value'] - a['value']
        sd = math.sqrt(a['sigma'] ** 2 + b['sigma'] ** 2)
        g8 = float(gC8.get(cn(name), 0))
        gI = float(cen.gradient(out_in).get(cn(name), 0))
        out.append({'check': lab, 'scalar': name, 'old': a, 'delivered': b, 'delivered_minus_old': d, 'sigma': sd,
                    'pull': d / sd, 'enters': out_in, 'd_input_dx': gI, 'diff_in_input': gI * d,
                    'dC8_dx': g8, 'diff_in_C8': g8 * d, 'sigma_in_C8': abs(g8) * sd})
        log(f'  {lab}: {name} delivered - old {d:+.3e} +- {sd:.2e} (pull {d / sd:+.2f}; max(rep, pool) each); in C8 '
            f'{g8 * d:+.2e} +- {abs(g8) * sd:.1e}')
    return out


def independent_reruns(cen):
    """the tier-C scalars without any independent all-sector reference, rerun in this phase with fresh seeds at a
    different N (engine/specs/checks_C8_A7v_A7k1.json, runs/c8chkA7, symmetry amdq)"""
    gC8 = cen.gradient('C8')
    gJ9 = cen.gradient('J9')
    out = []
    for name, grp, kj in (('A7_v[eps^0 l^0]', 'A7_v', '0,0'), ('A7[eps^1 l^1]', 'A7_base', '1,1')):
        a = raw_run_coef(os.path.join(RUNS, 'c8tierC_s3_can'), grp, kj, name)
        b = raw_run_coef(os.path.join(RUNS, 'c8chkA7'), grp, kj, name)
        d = a['value'] - b['value']
        sd = math.sqrt(a['sigma'] ** 2 + b['sigma'] ** 2)
        g8, g9 = float(gC8.get(cn(name), 0)), float(gJ9.get(cn(name), 0))
        Na = json.load(open(os.path.join(RUNS, 'c8tierC_s3_can', 'manifest.json')))
        Nb = json.load(open(os.path.join(RUNS, 'c8chkA7', 'manifest.json')))
        k = int(kj.split(',')[0])
        na = next(m['N'] for m in Na if m['moment'] == grp and m['job']['k'] == k)
        nb = next(m['N'] for m in Nb if m['moment'] == grp and m['job']['k'] == k)
        out.append({'scalar': name, 'tierC': a, 'tierC_N': na, 'check': b, 'check_N': nb, 'tierC_minus_check': d,
                    'sigma': sd, 'pull': d / sd if sd > 0 else None, 'dJ9_dx': g9, 'dC8_dx': g8,
                    'diff_in_C8': g8 * d, 'sigma_in_C8': abs(g8) * sd})
        log(f'  {name} tier C (N = {na}) - check run c8chkA7 (N = {nb}, fresh seeds): {d:+.4e} +- {sd:.2e} '
            f'(pull {d / sd:+.2f}); in C8 {g8 * d:+.2e} +- {abs(g8) * sd:.1e}')
    # the same tier-C A7_v job, its higher logs against the independent phase-2 production top-up (N = 131071)
    for j in (1, 2, 3, 4):
        name = f'A7_v[eps^0 l^{j}]'
        a = raw_run_coef(os.path.join(RUNS, 'c8tierC_s3_can'), 'A7_v', f'0,{j}', name)
        b = raw_run_coef(CM.TOPUP, 'A7_v', f'0,{j}', name)
        d = a['value'] - b['value']
        sd = math.sqrt(a['sigma'] ** 2 + b['sigma'] ** 2)
        out.append({'scalar': name, 'tierC': a, 'tierC_N': 11321, 'check': b, 'check_N': 131071,
                    'check_run': 'prod_6digit_topup1 (phase 2)', 'tierC_minus_check': d, 'sigma': sd,
                    'pull': d / sd if sd > 0 else None, 'dJ9_dx': None, 'dC8_dx': None, 'diff_in_C8': None,
                    'sigma_in_C8': None, 'note': 'job consistency: the tier-C A7_v job\'s higher logs (not used in C8; '
                                                 'production supplies them) against the independent phase-2 run'})
        log(f'  {name} tier C (N = 11321) - phase-2 production top-up (N = 131071): {d:+.3e} +- {sd:.2e} (pull {d / sd:+.2f})')
    return out


def c9_check_runs():
    """C9 pole check inputs: A9, Z8 at eps^-1 (all logs, all sectors) at N = 1009 (c8chkBC) and N = 4001
    (c8chkBC_N4001, fresh seeds)"""
    rows = []
    for grp, pref in (('A9_base', 'A9'), ('Z8_base', 'Z8')):
        R1 = json.load(open(os.path.join(RUNS, 'c8chkBC', 'results.json')))['results'][grp]
        R4 = json.load(open(os.path.join(RUNS, 'c8chkBC_N4001', 'results.json')))['results'][grp]
        for kj in sorted(set(R1) & set(R4), key=lambda s: tuple(int(x) for x in s.split(','))):
            if not kj.startswith('-1,'):
                continue
            nm = f'{pref}[eps^-1 l^{kj.split(",")[1]}]'
            e1 = json.load(open(os.path.join(RUNS, 'c8chkBC', 'results.json')))['errors'][grp][kj]
            if e1.get('zero'):
                continue
            a = raw_run_coef(os.path.join(RUNS, 'c8chkBC'), grp, kj, nm)
            b = raw_run_coef(os.path.join(RUNS, 'c8chkBC_N4001'), grp, kj, nm)
            d = b['value'] - a['value']
            sd = math.sqrt(a['sigma'] ** 2 + b['sigma'] ** 2)
            rows.append({'scalar': nm, 'N1009': a, 'N4001': b, 'diff_4001_minus_1009': d, 'sigma': sd,
                         'pull': d / sd if sd > 0 else None,
                         'pull_vs_rep_1009': d / a['sigma_rep'] if a['sigma_rep'] > 0 else None,
                         'pull_vs_pool_1009': d / a['sigma_pool'] if a['sigma_pool'] > 0 else None})
    big = sorted(rows, key=lambda r: -abs(r['pull'] or 0))[:4]
    log('  C9 check runs, N = 4001 minus N = 1009 (fresh seeds): ' + ', '.join(
        f"{r['scalar']} {r['diff_4001_minus_1009']:+.2e} ({r['pull']:+.2f}; vs the 1009 rep error {r['pull_vs_rep_1009']:+.2f})" for r in big))
    return rows


def engine_tier_vs_pilot():
    out = {}
    for rd in ('c8tierB_s0.01_r1', 'c8tierB_s0.01_can', 'c8tierB_s0.01_topup1', 'c8tierC_s3_r2', 'c8tierC_s3_can', 'c8tierC_s3_topup1'):
        p = os.path.join(RUNS, rd, 'tier_vs_pilot.json')
        if not os.path.exists(p):
            continue
        rows = json.load(open(p))['rows']
        pt = [r['pull_tot'] for r in rows if r.get('pull_tot') is not None and not r.get('zero')]
        w = max(rows, key=lambda r: abs(r.get('pull_tot') or 0)) if rows else None
        out[rd] = {'source': rel(p), 'n': len(pt), 'rms_pull': math.sqrt(sum(x * x for x in pt) / len(pt)) if pt else None,
                   'max_abs_pull': max(abs(x) for x in pt) if pt else None,
                   'worst': None if w is None else {k: w.get(k) for k in ('job', 'k', 'j', 'ref', 'N_tier', 'N_ref', 'diff', 'pull_tot')}}
    return out


def check_job_cost():
    """the engine check job of this phase (runs/c8chkA7): sacct record written after it ended"""
    p = os.path.join(CM.ENG_DIR, 'logs', 'symmetry', 'sacct_c8BC_chkA7.txt')
    if not os.path.exists(p):
        return {'note': 'sacct record not found', 'path': rel(p)}
    rows = [ln.split('|') for ln in open(p).read().splitlines() if ln and not ln.startswith('JobID')]
    main = [r for r in rows if '.' not in r[0]]
    out = {'source': rel(p), 'sha256': sha256(p), 'rows': ['|'.join(r) for r in rows]}
    tot = 0.0
    for r in main:
        cpus = int(r[3])
        h, m_, s_ = (int(x) for x in r[4].split(':'))
        tot += cpus * (h + m_ / 60 + s_ / 3600)
    out['allocated_amdq_core_h'] = round(tot, 2)
    return out


def u_pilot(res):
    pv = json.load(open(os.path.join(CM.ENG_DIR, 'results', 'preview_C8.json')))['outputs']['U']
    su = max(mp.mpf(pv['sigma_linear']), mp.mpf(pv['rep_se']))
    d = mp.mpf(res['U']['value']) - mp.mpf(pv['value'])
    sd = mp.sqrt(su ** 2 + mp.mpf(res['U']['sigma']) ** 2)
    out = {'pilot_preview': pv['value'], 'pilot_sigma': fl(su), 'production': res['U']['value'], 'diff': fl(d),
           'pull': fl(d / sd), 'note': 'engine results/preview_C8.json (pilot runs c8val, c8conv, poles1, kplus1; '
                                       'all-sector A7_d at N = 1009); independent of the production seeds'}
    log(f'  U production - U pilot preview = {fl(d):+.2f} +- {fl(sd):.1f} (pull {fl(d / sd):+.2f})')
    return out


# ======================================================================================================
# step 2
# ======================================================================================================
def summarize(rows):
    p = [r['pull'] for r in rows if r.get('pull') is not None]
    if not p:
        return {'n': 0, 'n_missing': sum(1 for r in rows if r.get('status') == 'MISSING')}
    w = max(rows, key=lambda r: abs(r['pull']) if r.get('pull') is not None else -1)
    return {'n': len(p), 'max_abs_pull': max(abs(x) for x in p), 'rms_pull': math.sqrt(sum(x * x for x in p) / len(p)),
            'n_above_3': sum(1 for x in p if abs(x) > 3), 'worst': w['check'],
            'n_missing': sum(1 for r in rows if r.get('status') == 'MISSING')}


def explicit_new_input_checks(V):
    import sympy as sp
    rg = json.load(open(os.path.join(CM.SPEC_DIR, 'out', 'C8', 'rg_logs_C8.json')))
    forms = {k + ' (second log)': v['prediction'] for k, v in rg['second_log_formulas']['formulas'].items()}
    for key, jet in rg['higher_log_formulas']['jets'].items():
        for k, r in jet['logs'].items():
            forms[f'{key} l^{k}'] = r['prediction']
    new = set(NEW10)
    rows = []
    for cat in ('targets', 'rg'):
        for r in V[cat]['rows']:
            f = r.get('closed_form') if cat == 'targets' else forms.get(r['check'])
            if not f or r.get('pull') is None:
                continue
            g = re.sub(r'([A-Za-z0-9_]+)\[(v\dd\d)\]', r'\1__\2', f)
            ids = set(re.findall(r'[A-Za-z_][A-Za-z0-9_]*', g))
            if not ids & new:
                continue
            loc = {t: sp.Symbol(t) for t in ids}
            ex = sp.sympify(g, locals=loc)
            for t in sorted(ids & new):
                c = sp.diff(ex, loc[t])
                cnum = float(c) if c.is_number else None
                rows.append({'category': cat, 'check': r['check'], 'input': t, 'coefficient': str(c), 'diff': r['diff'],
                             'sigma': r['sigma'], 'pull': r['pull'],
                             'implied_abs_precision': (r['sigma'] / abs(cnum)) if cnum else None, 'formula': f})
    return rows


def step2_validate():
    path = os.path.join(OUT8, 'validate_C8_ABC.json')
    V = json.load(open(path))
    order = [os.path.basename(os.path.normpath(r)) for r in V['runs']]
    assert order[:7] == ['c8tierC_s3_topup1', 'c8tierC_s3_r2', 'c8tierC_s3_can', 'c8tierB_s0.01_topup1',
                         'c8tierB_s0.01_r1', 'c8tierB_s0.01_can', 'c8chkBC_N4001'], order
    out = {'source': rel(path), 'sha256': sha256(path), 'runs': order, 'input_info': V['input_info'], 'kmax': V['kmax'],
           'runtime_s': V.get('runtime_s')}
    for cat in ('raw', 'zeros', 'targets', 'rg'):
        out[cat] = summarize(V[cat]['rows'])
    out['poles'] = {'all': summarize(V['poles']['rows']),
                    'new_for_C8': summarize([r for r in V['poles']['rows'] if r.get('new_for_C8')]),
                    'new_nontrivial': summarize([r for r in V['poles']['rows'] if r.get('new_for_C8') and r.get('nontrivial')]),
                    'jets_not_computable': sorted({r['check'].split('[eps')[0] for r in V['poles']['rows']
                                                   if r.get('status') == 'MISSING'})}
    out['raw_rows'] = [{k: r.get(k) for k in ('check', 'value', 'target', 'diff', 'sigma', 'pull', 'source')} for r in V['raw']['rows']]
    # the note's leading log of d_delta A7: which run supplied A7_d[eps^0 l^8]
    a7 = json.load(open(os.path.join(RUNS, 'c8tierB_s0.01_r1', 'results.json')))['results']['A7_d']
    out['A7_d_leading_log'] = {'engine_tierB_A7_d[eps^0 l^8]': a7.get('0,8'), 'engine_tierB_A7_d[eps^0 l^9]': a7.get('0,9'),
                               'note': '-2362/315 (note l.1355-1358)', 'target': -2362 / 315,
                               'source_run': 'engine/runs/c8tierB_s0.01_r1 (production, N = 32003; first run with A7_d in '
                                             'the validate list)'}
    per = {}
    for o, jets in RELEVANT.items():
        sel = {}
        for cat in ('poles', 'targets', 'rg'):
            rows = [r for r in V[cat]['rows'] if any(r['check'].startswith(j) for j in jets)]
            sel[cat] = summarize(rows)
            if cat == 'poles':
                sel['poles_nontrivial'] = summarize([r for r in rows if r.get('nontrivial')])
            if cat in ('poles', 'rg') and o in NEW_BC:
                sel[cat + '_rows'] = [{k: r.get(k) for k in ('check', 'value', 'diff', 'sigma', 'pull', 'l1')} for r in rows
                                      if (cat == 'rg') or abs(r.get('l1') or 0) > 1e-12]
        per[o] = sel
    out['by_new_input'] = per
    out['explicit_new_input_checks'] = explicit_new_input_checks(V)
    out['rg_not_computable'] = sorted({r['check'].split(' ')[0] for r in V['rg']['rows'] if r.get('status') == 'MISSING'})
    # C9 eps^-1 rows (the new C9 pole check)
    out['C9_eps_minus1'] = [{k: r.get(k) for k in ('check', 'value', 'sigma', 'pull', 'l1', 'sigma_parts')}
                            for r in V['poles']['rows'] if r['check'].startswith('C9[v0d0][eps^-1')]
    c9p = os.path.join(CM.ENG_DIR, 'results', 'validate_C8_tierBC_c9pool.json')
    out['C9_eps_minus1_N1009_pooled'] = {'source': rel(c9p), 'sha256': sha256(c9p),
                                         'rows': [{k: r.get(k) for k in ('check', 'value', 'sigma_rep', 'sigma_with_pool',
                                                                          'pull_rep', 'pull_pool')} for r in json.load(open(c9p))]}
    v1009 = os.path.join(CM.ENG_DIR, 'results', 'validate_C8_tierBC.json')
    V1 = json.load(open(v1009))
    out['C9_eps_minus1_N1009'] = {'source': rel(v1009), 'sha256': sha256(v1009),
                                  'rows': [{k: r.get(k) for k in ('check', 'value', 'sigma', 'pull')}
                                           for r in V1['poles']['rows'] if r['check'].startswith('C9[v0d0][eps^-1')]}
    log('\n' + '=' * 110)
    log('STEP 2: archive-free checks (validate_C8, production tiers first; direct finite-cutoff)')
    log('=' * 110)
    log(f"  raw targets: {out['raw']}")
    log(f"  poles: all {out['poles']['all']}; new non-trivial {out['poles']['new_nontrivial']}; "
        f"not computable {out['poles']['jets_not_computable']}")
    log(f"  zeros {out['zeros']}; C3/K4 higher-log targets {out['targets']}; RG logs {out['rg']} "
        f"(not computable {out['rg_not_computable']})")
    log(f"  A7_d leading log: {out['A7_d_leading_log']}")
    for o, s in per.items():
        log(f"    {o:7s} poles n={s['poles'].get('n')} max {s['poles'].get('max_abs_pull', 0):.2f} | "
            f"targets n={s['targets'].get('n')} max {s['targets'].get('max_abs_pull', 0):.2f} | "
            f"RG n={s['rg'].get('n')} max {s['rg'].get('max_abs_pull', 0):.2f}")
    for r in out['C9_eps_minus1']:
        if r['pull'] is not None and abs(r.get('l1') or 0) > 1e-12:
            log(f"    {r['check']:24s} value {r['value']} sigma {r['sigma']:.2e} pull {r['pull']:+.2f}")
    return out


def step2_direct(groups_bc):
    base = os.path.join(OUT8, 'direct_C8_ABC')
    rows = json.load(open(base + '_offsets.json'))
    eng = json.load(open(base + '_engine.json'))
    tally = {}
    for r in rows:
        tally[r['verdict']] = tally.get(r['verdict'], 0) + 1
    sel = []
    for r in rows:
        c = r.get('central') or {}
        e = {'moment': r['name'], 'engine_name': r.get('engine_name'), 'verdict': r['verdict'],
             'verdict_raw': r.get('verdict_raw'), 'K': r.get('K'), 'npts': r.get('npts'),
             'n_competitive': r.get('n_competitive')}
        for i in ('0', '1'):
            e[f'd{i}'], e[f'u{i}'], e[f'pull{i}'], e[f'detect3_{i}'], e[f'quoted{i}'] = (
                c.get(f'd{i}'), c.get(f'u{i}'), c.get(f'pull{i}'), c.get(f'detect3_{i}'), c.get(f'quoted{i}'))
        eng_g = re.sub(r'_N\d+$', '', str(r.get('engine_name') or ''))
        e['tierBC_moment'] = eng_g in groups_bc
        sel.append(e)
    log(f'  direct finite-cutoff comparison (production tiers first): {tally}')
    for e in sel:
        if e['tierBC_moment'] or e['verdict'] != 'PASS':
            q = lambda i: ('%+.2e +- %.1e (%+.2f)' % (e[f'd{i}'], e[f'u{i}'], e[f'pull{i}'])  # noqa: E731
                           if e.get(f'quoted{i}') and e.get(f'pull{i}') is not None else 'not quoted')
            log(f"    {e['moment']:10s} {e['verdict']:12s} K={e['K']}  c00 {q('0'):30s} c01 {q('1')}"
                + ('' if e['tierBC_moment'] else '   [not a tier-B/C moment]'))
    nonpass = [{k: e[k] for k in ('moment', 'verdict', 'verdict_raw', 'pull0', 'pull1', 'tierBC_moment')}
               for e in sel if e['verdict'] != 'PASS']
    # fit-window probe of the flagged moments (direct_probe_C8.py): stable or tail-model dependent
    cen_rows = {r['name']: r for r in rows}
    probe = {}
    for em in ('0.011', '0.016', '0.051'):
        p = os.path.join(OUT8, f'direct_probe_emax{em}_offsets.json')
        if not os.path.exists(p):
            continue
        for r in json.load(open(p)):
            c = r.get('central') or {}
            probe.setdefault(r['name'], {})[em] = {'verdict': r['verdict'], 'd0': c.get('d0'), 'u0': c.get('u0'),
                                                   'pull0': c.get('pull0'), 'd1': c.get('d1'), 'u1': c.get('u1'),
                                                   'pull1': c.get('pull1'), 'joint_X2': c.get('joint_X2')}
    for nm, pr in probe.items():
        c = cen_rows[nm].get('central') or {}
        pr['0.021 (central)'] = {'verdict': cen_rows[nm]['verdict'], 'd0': c.get('d0'), 'u0': c.get('u0'),
                                 'pull0': c.get('pull0'), 'd1': c.get('d1'), 'u1': c.get('u1'), 'pull1': c.get('pull1'),
                                 'joint_X2': c.get('joint_X2')}
        verdicts = {v['verdict'] for v in pr.values() if isinstance(v, dict) and 'verdict' in v}
        moves = [abs(v['d0'] - c['d0']) > c['u0'] for k, v in pr.items()
                 if isinstance(v, dict) and v.get('d0') is not None and c.get('d0') is not None and c.get('u0')]
        pr['tail_model_dependent'] = bool(len(verdicts) > 1 or any(moves))
        log(f"    window probe {nm:10s}: " + ', '.join(f"{k.split()[0]} {v['verdict']}" + (f" d0 {v['d0']:+.3g}+-{v['u0']:.2g}" if v.get('d0') is not None else '')
                                                  for k, v in sorted(pr.items()) if isinstance(v, dict))
            + f" -> {'tail-model dependent' if pr['tail_model_dependent'] else 'STABLE'}")
    return {'source': rel(base + '_offsets.json'), 'sha256': sha256(base + '_offsets.json'), 'tally': tally,
            'non_pass': nonpass, 'rows': sel, 'engine_series_note': eng.get('note'),
            'completion_counts': {k: len(v) for k, v in eng.get('added', {}).items()},
            'window_probe': probe,
            'window_probe_rule': 'phase-2 rule (assembly/direct_check.py): a verdict that flips, or a d0 that moves by '
                                 'more than its u0, under a change of eps_max (0.011, 0.016, 0.021, 0.051) is '
                                 'tail-model dependent'}


# ======================================================================================================
def main():
    os.makedirs(OUT8, exist_ok=True)
    t_all = time.time()
    with mp.workdps(DPS):
        res, sub, terms, budget, struct, meta, fw, merged, inp, cen, names, prod, abc, tiers, jobs, E = step1()
        W3 = w_three_ways(res)
        sep = separate_files_check(fw, cen, prod, tiers)
        log('\n  tier-to-tier consistency (independent runs):')
        swap = pilot_swap(fw, cen, inp, prod, abc, names)
        heavy = heavy_subset_checks(cen)
        repl = replaced_run_checks(cen)
        reruns = independent_reruns(cen)
        upil = u_pilot(res)
    c9runs = c9_check_runs()
    etvp = engine_tier_vs_pilot()
    ta = json.load(open(TIERA_RESULTS))
    tiers_cons = {'tierBC_vs_pilot_inputs': swap, 'heavy_jobs_vs_probe_and_conv_pilot': heavy,
                  'replaced_runs_vs_topups': repl, 'independent_reruns_this_phase': reruns,
                  'U_pilot_level': upil, 'C9_check_N1009_vs_N4001': c9runs,
                  'engine_tier_vs_pilot': etvp,
                  'tierA_carried_over': {'source': rel(TIERA_RESULTS), 'sha256': sha256(TIERA_RESULTS),
                                         'note': 'tier-A data are unchanged, so the tier-A consistency results of '
                                                 '2026-10-04 stand as written there',
                                         'tierA_vs_pilot_inputs': ta['step1']['tier_consistency']['tierA_vs_pilot_inputs']['rows'],
                                         'tierA_vs_pilot_raw': ta['step1']['tier_consistency']['tierA_vs_pilot_raw'],
                                         'tierA_alone_vs_final': ta['step1']['tier_consistency']['tierA_alone_vs_final']['rows']}}
    val = step2_validate()
    groups_bc = set()
    for rd in ('c8tierB_s0.01_r1', 'c8tierB_s0.01_can', 'c8tierB_s0.01_topup1', 'c8tierC_s3_r2', 'c8tierC_s3_can', 'c8tierC_s3_topup1'):
        groups_bc |= {m['moment'] for m in json.load(open(os.path.join(RUNS, rd, 'manifest.json')))}
    direct = step2_direct(groups_bc)
    led = os.path.join(RUNS, 'c8BC_ledger.json')
    ledger = json.load(open(led))
    out = {
        'title': 'Independent C8 re-derivation, tiers A + B + C: assembly of the engine data (archive-free part)',
        'date': time.strftime('%Y-%m-%d %H:%M:%S %Z'),
        'archive_free': True,
        'note': 'Every number here comes from the project\'s own engine, framework, direct and spec components. No '
                'archive number was read or used by this script, which ran in a copy of the project without the sealed '
                'directories, under an audit hook. The claims under test are compared only afterwards '
                '(compare_archive_C8.py, ../RESULTS_C8_archive_comparison.json).',
        'definition': 'C8 = 8 T4 = B_old + 4W + 2S + 3/4 U + 1/4 J9 + 3/32 L3 - 1/4 M21 + 1/2 M12 - 1/16 N2 + 1/8 Ndelta '
                      '+ 1/32 Kv (eq:C8assembly, derived in framework/derive_C8.py); B_done = B_old + 4W + 2S + 3/32 L3 '
                      '- 1/4 M21 + 1/2 M12 - 1/16 N2; C8_asm = eq:C8assembly evaluated with our inputs (= 8 T4 up to the '
                      'tree-data rounding)',
        'status': {'tiers_run': ['A', 'B', 'C'], 'C8_complete': True, 'missing_inputs': [],
                   'precision_targets': {'tier_B': 'sigma(C8 without J9) = 0.01 (approved 2026-10-04)',
                                         'tier_C': 'gross check, total sigma(C8) ~ 3 (approved 2026-10-04)'}},
        'step1': {'meta': meta, 'outputs': res, 'sub_pieces': sub, 'C8_assembly_terms': terms, 'error_budget': budget,
                  'note_raw_structure': struct, 'W_three_ways': W3, 'separate_tier_files': sep,
                  'tier_consistency': tiers_cons},
        'step2': {'validate_C8': val, 'direct': direct},
        'independence': {
            'code': 'no archive integration or evaluation code imported, called or copied (engine, framework, direct, '
                    'spec and assembly are the project\'s own); no archived raw data (*_negative.json, *_audit.json, '
                    '*.expr, P6/P8/U/J9/Kv expression files) used as input',
            'this_script': 'reads only the project\'s engine runs, framework, spec/out (archive-free part) and the direct '
                           'table; it ran in a project copy on the personal desktop that contains neither spec/comparison*, nor the '
                           'archive-comparison result files, nor the compendium, under a Python audit hook that aborts '
                           'on any open of them (out/C8_ABC/audit_*.log)'},
        'compute': {'engine_tiers_BC': {'source': rel(led), 'sha256': sha256(led), 'total_amdq_eq': ledger['total_amdq_eq'],
                                         'by_machine': ledger['by_machine'], 'cap': ledger['cap']},
                    'engine_tierA': '183.1 allocated personal-desktop core-h = 122.2 amdq-equivalent (2026-10-03/04)',
                    'assembly_check_runs': check_job_cost(),
                    'this_assembly': 'one personal-desktop Slurm job (see out/C8_ABC/slurm_*.out); framework assembly, '
                                     'validate_C8.py and direct_C8.py',
                    'assembly_runtime_s': None},
    }
    out['compute']['assembly_runtime_s'] = round(time.time() - t_all, 1)
    CM.write_json(RESULTS, out)
    h = sha256(RESULTS)
    with open(RESULTS + '.sha256', 'w') as fh:
        fh.write(f'{h}  RESULTS_C8_independent.json  {out["date"]}\n')
    with open(os.path.join(OUT8, 'run_assembly_C8.log'), 'w') as fh:
        fh.write('\n'.join(LOG) + '\n')
    log(f'\nwrote {RESULTS}  sha256 {h}  ({time.time() - t_all:.0f} s)')


if __name__ == '__main__':
    main()
