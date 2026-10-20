#!/usr/bin/env python3
"""Compare our direct finite-cutoff values with the archive's recorded finite-cutoff numbers.

Archive values are READ ONLY, for comparison, from the compendium (never written).
Two classes of archive record:
  * 'hyperlog'  : the archive's EXACT raw expressions (rational x hyperlog rows) evaluated
                  at finite eps without any eps expansion -- agreement with our independent
                  direct integration tests the archive's raw integration itself;
  * 'direct'    : the archive's own direct cubature (Sobol/Gauss) -- a weaker comparison.
Output: results/archive_comparison.json and a printed table.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, '..', 'results')
COMP = '<PROJECT>/LRI_SRI_research_compendium'
C6R = COMP + '/data/archived/LRI_1d_complete/stages/C6_integrals/reproducibility'
C7E = COMP + '/data/archived/C7_completion/engine'
F3D = COMP + '/data/archived/F3_six_kink_completion/data'
F1C = COMP + '/outputs/archived/F1c_completion/verification'


def jl(p):
    with open(p) as fh:
        return json.load(fh)


def archive_records():
    recs = []
    # eps = 1/8, C6 stage: exact finite-cutoff (hyperlog) evaluations
    h = jl(C6R + '/finite_cutoff_hyperlog.json')
    recs.append(('0.125', 'EA5_base', h['EA5_base'], 'hyperlog', C6R + '/finite_cutoff_hyperlog.json'))
    recs.append(('0.125', 'Q6_v', h['Q6_v'], 'hyperlog', C6R + '/finite_cutoff_hyperlog.json'))
    t = jl(C6R + '/finite_tail_hyperlog.json')
    for k, nm in (('3', 'A3_d'), ('4', 'Z4_d'), ('5', 'A5_d')):
        recs.append(('0.125', nm, t[k], 'hyperlog', C6R + '/finite_tail_hyperlog.json'))
    # A7 at 1/8: printed in the C6 stage note table (finite-cutoff hyperlog column)
    recs.append(('0.125', 'A7_base', '0.03557288770735261', 'hyperlog(note table, 16 digits)',
                 COMP + '/documentation/archived/LRI_1d_complete/stages/C6_integrals/C6_thermal_note.tex'))
    # archive direct Sobol values at 1/8
    d = jl(C6R + '/finite_cutoff_direct.json')
    for key, nm in (('A7_2^18', 'A7_base'), ('Qv6_2^18', 'Q6_v'), ('EA5_2^18', 'EA5_base')):
        recs.append(('0.125', nm, '%r' % d[key]['mean'], 'direct-Sobol(se=%.2g)' % d[key]['standard_error'],
                     C6R + '/finite_cutoff_direct.json'))
    td = jl(C6R + '/finite_tail_direct.json')
    for k, nm in (('3', 'A3_d'), ('4', 'Z4_d'), ('5', 'A5_d')):
        recs.append(('0.125', nm, '%r' % td[k]['mean'], 'direct-Sobol(se=%.2g)' % td[k]['se'],
                     C6R + '/finite_tail_direct.json'))
    # eps = 1/10, C7 stage: convergent finite-argument hyperlog ODE evaluations of the exact raw expressions
    for f, nm in (('A7_v_finite_raw_check_90.json', 'A7_v'), ('Q4_dd_finite_raw_check_80.json', 'Q4_dd'),
                  ('Q8_base_finite_raw_check_80.json', 'Q8_base')):
        x = jl(C7E + '/' + f)
        recs.append(('0.1', nm, x['value'], 'hyperlog-ODE', C7E + '/' + f))
    # F3 stage: Q6_vv ("Xvv") exact finite evaluation; EQ6_v and n=8 controls only direct Gauss
    x = jl(F3D + '/Xvv_finite_check.json')
    recs.append(('0.1', 'Q6_vv', x['value'], 'hyperlog-ODE', F3D + '/Xvv_finite_check.json'))
    x = jl(F3D + '/direct_finite_high.json')[-1]
    recs.append(('0.1', 'EQ6_v', '%r' % x['EQ_v'], 'direct-Gauss(order %d)' % x['order'], F3D + '/direct_finite_high.json'))
    recs.append(('0.1', 'Q6_vv', '%r' % x['Q_vv'], 'direct-Gauss(order %d)' % x['order'], F3D + '/direct_finite_high.json'))
    x = jl(F3D + '/direct_n8_controls.json')[-1]
    for k, nm in (('Q_base', 'Q8_base'), ('Q_v', 'Q8_v'), ('Q_vv', 'Q8_vv'), ('EQ_v', 'EQ8_v')):
        recs.append(('0.1', nm, '%r' % x[k], 'direct-Gauss(order %d)' % x['order'], F3D + '/direct_n8_controls.json'))
    for f, nm in (('A7_v_direct_gauss.json', 'A7_v'), ('Q4_dd_direct_gauss.json', 'Q4_dd'),
                  ('Q8_base_direct_gauss.json', 'Q8_base')):
        x = jl(C7E + '/' + f)[-1]
        recs.append(('0.1', nm, '%r' % x['value'], 'direct-Gauss(order %d)' % x['order'], C7E + '/' + f))
    # F1c stage at eps=0.1: the archive's direct values and their recorded difference from the exact
    # expression ("*_difference" = direct - exact); exact = direct - difference
    x = jl(F1C + '/direct_cutoff_comparison.json')['runs'][-1]
    from decimal import Decimal, getcontext
    getcontext().prec = 40
    recs.append(('0.1', 'Q4_vvd', str(Decimal(repr(x['Q4_vvd'])) - Decimal(x['Q4_difference'])),
                 'exact(reconstructed: direct - recorded difference)', F1C + '/direct_cutoff_comparison.json'))
    recs.append(('0.1', 'EQ4_vd', str(Decimal(repr(x['EQ4_vd'])) - Decimal(x['EQ4_difference'])),
                 'exact(reconstructed: direct - recorded difference)', F1C + '/direct_cutoff_comparison.json'))
    return recs


def main():
    with open(os.path.join(RES, 'direct_table.json')) as fh:
        tab = json.load(fh)
    out = []
    print('%-6s %-9s %-26s %-28s %-24s %-10s %s' % ('eps', 'moment', 'archive', 'ours', 'diff', 'our_err', 'archive type'))
    for el, nm, aval, typ, src in archive_records():
        e = tab.get(el, {}).get(nm)
        if e is None:
            print('missing ours', el, nm)
            continue
        a = float(aval)
        diff = e['value'] - a
        rel = diff / abs(a)
        out.append(dict(eps=el, name=nm, archive=aval, archive_type=typ, archive_source=src.replace(COMP, '<compendium>'),
                        ours=e['value'], ours_err=e['err'], diff=diff, rel_diff=rel))
        print('%-6s %-9s %-26s %-28.17g %-24.3e %-10.2g %s' % (el, nm, aval[:26], e['value'], diff, e['err'] or 0, typ))
    with open(os.path.join(RES, 'archive_comparison.json'), 'w') as fh:
        json.dump(out, fh, indent=1)


if __name__ == '__main__':
    main()
