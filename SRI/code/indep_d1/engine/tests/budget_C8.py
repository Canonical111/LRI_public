#!/usr/bin/env python3
"""Achieved vs planned error of a C8 production tier (phase 3, 2026-10-04).

usage: budget_C8.py RUNDIR [RUNDIR ...] [--plan results/plan_C8.json] [--miss 1.5] [--json OUT.json]

For every job (group, eps power) of the collected run(s) the projection of its needed coefficients on the signed
dC8/dx (specs/production_C8.json) is formed exactly as the planner does it (py/plan_C8.load_refs): replicate error
of the whole job and sector-pooled error, plus the floor; achieved sigma = sqrt(max(var_rep, var_pool) + floor^2).
It is compared with the planner's predicted sigma_C8 of the same job at the planned N (results/plan_C8.json).
The same is done for each of the ten new beta inputs (d input / dx, specs/framework_sensitivities_C8.json).
A job MISSES its budget if achieved > miss x planned; such jobs are the refine/top-up candidates (the caller
decides whether a miss matters for the tier total).  No archive data is read.
Exit status 0 always (report tool); the JSON lists the misses.
"""
import argparse, json, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'py'))
from plan_C8 import load_refs, INPUTS_NEW, SIGMA_BOLD   # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('rundirs', nargs='+')
    ap.add_argument('--plan', default=os.path.join(ROOT, 'results', 'plan_C8.json'))
    ap.add_argument('--miss', type=float, default=1.5)
    ap.add_argument('--json', default=None)
    a = ap.parse_args()
    plan = json.load(open(a.plan))
    pj = {(j['group'], j['k']): j for j in plan['jobs']}
    prod, G, refs = load_refs(a.rundirs)
    rows, tot = [], {'plan': 0.0, 'rep': 0.0, 'pool': 0.0, 'ach': 0.0}
    tot_in = {o: 0.0 for o in INPUTS_NEW}
    for (g, k), rs in sorted(refs.items()):
        r = max(rs, key=lambda x: x['N'])
        p = pj.get((g, k), {})
        s_rep = math.sqrt(r['var_rep'] + r['floor2'])
        s_pool = math.sqrt(r['var_pool'] + r['floor2'])
        s_ach = math.sqrt(max(r['var_rep'], r['var_pool']) + r['floor2'])
        s_plan = p.get('sigma_C8')
        ratio = s_ach / s_plan if s_plan else None
        row = {'group': g, 'k': k, 'tier': p.get('tier'), 'N': r['N'], 'N_plan': p.get('N'), 'src': r['src'],
               'sigma_C8_rep': s_rep, 'sigma_C8_pool': s_pool, 'sigma_C8': s_ach, 'sigma_C8_plan': s_plan,
               'ratio': ratio, 'miss': bool(ratio is not None and ratio > a.miss), 'cpu_h': r['cpu_h'],
               'core_h_plan': p.get('core_h'),
               'sigma_in': {o: math.sqrt(r['var_in'][o] + r['floor2_in'][o]) for o in INPUTS_NEW}}
        rows.append(row)
        tot['plan'] += (s_plan or 0.0) ** 2
        tot['rep'] += r['var_rep'] + r['floor2']
        tot['pool'] += r['var_pool'] + r['floor2']
        tot['ach'] += s_ach ** 2
        for o in INPUTS_NEW:
            tot_in[o] += r['var_in'][o] + r['floor2_in'][o]
    tot = {kk: math.sqrt(v) for kk, v in tot.items()}
    tot_in = {o: math.sqrt(v) for o, v in tot_in.items()}
    print('%-10s %3s %4s %8s %8s %11s %11s %11s %11s %7s %8s %8s' % (
        'group', 'k', 'tier', 'N', 'N_plan', 'sig_rep', 'sig_pool', 'sig_ach', 'sig_plan', 'ratio', 'cpu_h',
        'plan_h'))
    for r in sorted(rows, key=lambda x: -x['sigma_C8']):
        print('%-10s %3d %4s %8d %8s %11.3e %11.3e %11.3e %11s %7s %8.2f %8s %s' % (
            r['group'], r['k'], r['tier'], r['N'], r['N_plan'], r['sigma_C8_rep'], r['sigma_C8_pool'], r['sigma_C8'],
            '%.3e' % r['sigma_C8_plan'] if r['sigma_C8_plan'] else '-',
            '%.2f' % r['ratio'] if r['ratio'] is not None else '-', r['cpu_h'],
            '%.2f' % r['core_h_plan'] if r['core_h_plan'] is not None else '-', 'MISS' if r['miss'] else ''))
    print('\ntotal sigma(C8 part), statistical + floor, summed over the jobs above: achieved %.3e (rep %.3e, pool '
          '%.3e), planned %.3e' % (tot['ach'], tot['rep'], tot['pool'], tot['plan']))
    print('with B_old (%.2e) in quadrature: %.3e' % (SIGMA_BOLD, math.sqrt(tot['ach'] ** 2 + SIGMA_BOLD ** 2)))
    print('sigma of the new inputs (engine part, these jobs only): ' +
          ', '.join('%s %.2e' % (o, tot_in[o]) for o in INPUTS_NEW))
    print('jobs missing their budget by > %.2fx: %s' % (a.miss, [(r['group'], r['k'], round(r['ratio'], 2))
                                                                  for r in rows if r['miss']] or 'none'))
    if a.json:
        json.dump({'rundirs': a.rundirs, 'miss_factor': a.miss, 'jobs': rows, 'total': tot, 'sigma_inputs': tot_in,
                   'sigma_B_old': SIGMA_BOLD}, open(a.json, 'w'), indent=1)


if __name__ == '__main__':
    main()
