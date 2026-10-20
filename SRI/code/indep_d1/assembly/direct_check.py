#!/usr/bin/env python3
"""Check 2(iv): the engine's production series against the direct finite-cutoff table, with the direct agent's
fixed GLS tool (direct/src/compare_engine.py --offset-fit; method and verdicts in direct/README.md).

Two engine inputs are tested (both written to out/):
  prod      engine/runs/prod_6digit/results_final.json as delivered (only the coefficients the framework needs);
  prod+val  the same, completed by the coefficients that production did not compute: first from the
            assembly-phase engine runs engine/runs/poles1 (negative powers of every moment, all logs) and
            engine/runs/kplus1 (eps^1 of the moments whose production series stop at eps^0, except A7, A7_v,
            Q8, Q6_E), then from the engine's earlier validation runs (engine/results/validation_d_inputs.json,
            validation_c.json).  A coefficient [eps^k l^j] is added only when no earlier source quotes it.  This is the 'complete
            series' the GLS tool needs; it is built here instead of with --merge (which keeps the smaller error).
Errors: the engine's per-coefficient err = stat (+) floor (diagonal priors; compare_engine drops covariances
on merged input anyway).  Run time: ~1 min locally.  No archive file is read (compare_engine reads only the
direct table).
"""
import json
import math
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from common import DIRECT_DIR, FINAL_RESULTS, KPLUS1_RESULTS, OUT, POLES_RESULTS, VALIDATION_FILES, write_json  # noqa: E402

CE = os.path.join(DIRECT_DIR, 'src', 'compare_engine.py')


def build_inputs():
    prod = json.load(open(FINAL_RESULTS))['results']
    p_file = os.path.join(OUT, 'direct_engine_prod.json')
    write_json(p_file, {'note': 'engine production series (results_final.json, tier 1 + top-up), [value, err]',
                        'results': prod})
    merged = {g: dict(v) for g, v in prod.items()}
    added = {'poles1': {}, 'kplus1': {}, 'validation': {}}
    sources = []
    if os.path.exists(POLES_RESULTS):
        sources.append(('poles1', json.load(open(POLES_RESULTS))['results']))
    if os.path.exists(KPLUS1_RESULTS):
        sources.append(('kplus1', json.load(open(KPLUS1_RESULTS))['results']))
    for vf in VALIDATION_FILES:
        vd = json.load(open(vf))
        sources.append(('validation', vd.get('results', vd)))
    for tag, res in sources:
        for grp, ser in res.items():
            if grp.endswith('_hl') or not isinstance(ser, dict):
                continue
            for kj, ve in ser.items():
                if ',' not in kj or kj in merged.get(grp, {}):
                    continue
                merged.setdefault(grp, {})[kj] = ve
                added[tag].setdefault(grp, []).append(kj)
    m_file = os.path.join(OUT, 'direct_engine_prod_plus_val.json')
    write_json(m_file, {'note': 'production series completed, coefficient by coefficient, by the assembly-phase '
                                'runs engine/runs/poles1 (negative powers) and engine/runs/kplus1 (eps^1), then by '
                                'the engine validation runs (production preferred, then poles1, kplus1)',
                        'added_coefficients': added, 'results': merged})
    return p_file, m_file, added


def run(engine_file, tag):
    out = os.path.join(OUT, f'direct_{tag}.json')
    with open(os.path.join(OUT, f'direct_{tag}.txt'), 'w') as fh:
        subprocess.run([sys.executable, CE, engine_file, '--offset-fit', '--quiet-raw', '--out', out],
                       stdout=fh, stderr=subprocess.STDOUT, check=True, cwd=os.path.join(DIRECT_DIR, 'src'))
    return json.load(open(out.replace('.json', '_offsets.json')))


def summarize(rows):
    s = []
    for r in rows:
        c = r.get('central') or {}
        ent = {'moment': r['name'], 'verdict': r['verdict'], 'verdict_raw': r.get('verdict_raw'), 'K': r.get('K'),
               'npts': r.get('npts'), 'n_free_missing': c.get('n_free_missing'), 'chi2_dof': c.get('chi2_dof'),
               'joint_X2': c.get('joint_X2')}
        for t in ('0', '1'):
            if 'd' + t in c:
                u, e = c.get('u' + t), c.get('e' + t)
                ent['c0' + t] = {'d': c['d' + t], 'u': u, 'e_engine': e, 'pull': c.get('pull' + t),
                                 'quoted': c.get('quoted' + t),
                                 'size3': (3 * math.sqrt(u ** 2 + (e or 0) ** 2)) if u is not None else None}
        s.append(ent)
    tally = {}
    for e in s:
        tally[e['verdict']] = tally.get(e['verdict'], 0) + 1
    return s, tally


def main():
    os.makedirs(OUT, exist_ok=True)
    p_file, m_file, added = build_inputs()
    res = {'tool': 'direct/src/compare_engine.py --offset-fit (GLS, phase 2), direct table direct/results/'
                   'direct_table.json', 'added_coefficients': added}
    for tag, f in (('prod', p_file), ('prod_plus_val', m_file)):
        rows = run(f, tag)
        s, tally = summarize(rows)
        res[tag] = {'tally': tally, 'moments': s}
        print(tag, tally)
    # fit-window probe of every flagged complete series (as in direct/review/gate2_struct_probe.py): a verdict
    # that flips, or a d0 that moves by more than its u0, under a change of eps_max is tail-model dependent
    flagged = [m['moment'] for m in res['prod_plus_val']['moments'] if m['verdict'] in ('OFFSET', 'TENSION',
                                                                                         'MODEL-FAIL')]
    probe = {}
    if flagged:
        for em in ('0.011', '0.016', '0.051'):
            out = os.path.join(OUT, f'direct_probe_emax{em}.json')
            with open(out.replace('.json', '.txt'), 'w') as fh:
                subprocess.run([sys.executable, CE, m_file, '--offset-fit', '--quiet-raw', '--only', ','.join(flagged),
                                '--fit-eps-max', em, '--out', out], stdout=fh, stderr=subprocess.STDOUT, check=True,
                               cwd=os.path.join(DIRECT_DIR, 'src'))
            sm, _ = summarize(json.load(open(out.replace('.json', '_offsets.json'))))
            for m in sm:
                probe.setdefault(m['moment'], {})[em] = {k: m.get(k) for k in ('verdict', 'K', 'npts', 'c00', 'c01',
                                                                               'joint_X2', 'chi2_dof')}
    res['flagged_window_probe'] = probe
    # the flagged moments again, with the eps^0 (and eps^-1) coefficients replaced by the convergence re-check
    # engine/runs/conv1 (4-16x the production N, fresh seeds): if the flags stay, they come from the fit
    conv = os.path.join(os.path.dirname(FINAL_RESULTS), '..', 'conv1', 'results.json')
    if flagged and os.path.exists(conv):
        cr = json.load(open(conv))['results']
        merged = json.load(open(m_file))['results']
        for grp, ser in cr.items():
            merged.setdefault(grp, {}).update(ser)
        c_file = os.path.join(OUT, 'direct_engine_prod_plus_val_conv1.json')
        write_json(c_file, {'note': 'prod_plus_val with the conv1 re-check coefficients (Z4_E k=-1,0; A3_vdE, A5_vv '
                                    'k=0) replacing production', 'results': merged})
        out = os.path.join(OUT, 'direct_conv1.json')
        with open(out.replace('.json', '.txt'), 'w') as fh:
            subprocess.run([sys.executable, CE, c_file, '--offset-fit', '--quiet-raw', '--only', ','.join(flagged),
                            '--out', out], stdout=fh, stderr=subprocess.STDOUT, check=True,
                           cwd=os.path.join(DIRECT_DIR, 'src'))
        sm, _ = summarize(json.load(open(out.replace('.json', '_offsets.json'))))
        res['flagged_with_conv1'] = {m['moment']: m for m in sm}
        pr = json.load(open(FINAL_RESULTS))['results']
        diffs = {}
        for grp, ser in cr.items():
            for kj, (v, e) in ser.items():
                if kj in pr.get(grp, {}):
                    v0, e0 = pr[grp][kj]
                    sg = math.hypot(e, e0)
                    diffs[f'{grp}:{kj}'] = {'conv1': v, 'conv1_err': e, 'production': v0, 'production_err': e0,
                                            'diff': v - v0, 'pull': (v - v0) / sg if sg > 0 else None}
        res['conv1_vs_production'] = diffs
    write_json(os.path.join(OUT, 'direct_summary.json'), res)


if __name__ == '__main__':
    main()
