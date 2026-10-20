#!/usr/bin/env python3
"""Verify delivery integrity or a complete numerical run; neither certifies physics.

Missing or partial outputs are reported as failed checks rather than tracebacks.
Result reports are written below the supplied results directory (or --report),
so testing a side run cannot overwrite the principal run's verification report.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['integrity', 'results'])
    parser.add_argument('--results', type=Path, default=ROOT/'outputs/reproduced')
    parser.add_argument('--report', type=Path)
    parser.add_argument('--allow-extra', action='store_true',
                        help='Permit unlisted files created after extraction; always verify listed hashes.')
    args = parser.parse_args()
    if args.mode == 'integrity':
        manifest = ROOT/'SHA256SUMS'
        if not manifest.is_file():
            raise SystemExit('Delivery SHA256SUMS is missing')
        listed = set()
        mismatches = []
        for line in manifest.read_text().splitlines():
            expected, name = line.split('  ', 1)
            listed.add(name)
            path = ROOT/name
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                mismatches.append(name)
        def generated_environment(path):
            return any(part in {'.venv', '__pycache__', '.git'} for part in path.parts) or path.suffix == '.pyc'
        extras = sorted(str(p.relative_to(ROOT)) for p in ROOT.rglob('*')
                        if p.is_file() and str(p.relative_to(ROOT)) not in listed|{'SHA256SUMS'}
                        and not generated_environment(p.relative_to(ROOT)))
        if mismatches or (extras and not args.allow_extra):
            raise SystemExit(json.dumps({'status':'failed', 'mismatches':mismatches,
                                         'unlisted_files':extras}, indent=2))
        print(f'Integrity passed for {len(listed)} files; {len(extras)} permitted extras.')
        return
    res = args.results.resolve()
    ref = ROOT/'outputs/reference'
    checks = []
    def read(path):
        return json.loads(path.read_text())
    def check(name, fn):
        try:
            ok, detail = fn()
            checks.append({'name':name, 'passed':bool(ok), 'detail':detail})
        except (OSError, KeyError, IndexError, ValueError, TypeError) as exc:
            checks.append({'name':name, 'passed':False,
                           'detail':{'error':type(exc).__name__, 'message':str(exc)}})
    def close(got, expected, tol):
        error = abs(got-expected)
        return error <= tol, {'got':got, 'expected':expected, 'absolute_error':error, 'tolerance':tol}
    def diagnostic():
        return read(res/'precision/diagnostics_results.json')
    def numeric():
        return read(res/'refinement/final_numerical_checks.json')
    for key in ['a', 'b', 'C1']:
        check('retained_'+key, lambda key=key: close(diagnostic()['central'][key], read(ref/'precision/analysis_results.json')['central'][key], 5e-10))
    check('block_analytic_and_z_series', lambda: (max(diagnostic()['validation'].values())<1e-12, diagnostic()['validation']))
    check('shared_domain_functional_consistency', lambda: close(diagnostic()['central']['C1'], diagnostic()['independent_folding']['C1'], 5e-10))
    check('numerical_stability', lambda: (max(abs(q['C1_change']) for q in diagnostic()['numerical_stability'])<5e-10, diagnostic()['numerical_stability']))
    for name in ['8_7_pad1', '8_7_pad2', '6_6_pad1']:
        def interval_test(name=name):
            got = read(res/'refinement'/f'final_{name}_summary.json')['interval']
            expected = (read(ref/'refinement/SUMMARY_RESULTS.json')['weaker_gap_sensitivity']['interval']
                        if name == '6_6_pad1' else read(ref/'refinement'/f'final_{name}_summary.json')['interval'])
            error = max(abs(x-y) for x,y in zip(got,expected))
            return len(got)==len(expected)==2 and error<2e-8, {'got':got,'expected':expected,'absolute_error':error,'tolerance':2e-8}
        check('interval_'+name, interval_test)
    def nonlinear():
        obj = read(res/'refinement/nonlinear_crossing_validation.json')
        return len(obj['cases'])==34 and obj['max_ratio']<1, {'cases':len(obj['cases']), 'max_ratio':obj['max_ratio']}
    check('34_nonlinear_crossing_tests', nonlinear)
    sys.path.insert(0, str(ROOT/'code/c1_refinement'))
    from runtime_config import OBJECTIVE_ALLOWANCE, ratio_interval
    def objective():
        obj = read(res/'refinement/validation_objective.json')
        used = obj['allowance_used']
        summary = read(res/'refinement/final_8_7_pad1_summary.json')
        ok = obj['total_sampled_remainder']<used and used==OBJECTIVE_ALLOWANCE==summary['objective_nonlinear_allowance']
        return ok, {'sampled_remainder':obj['total_sampled_remainder'],'allowance_used':used, 'shared_allowance':OBJECTIVE_ALLOWANCE}
    check('sampled_objective_and_shared_allowance', objective)
    for key in ['d0','J','pad']:
        check('crossing_descendants40_48_'+key, lambda key=key: (numeric()['descendant40_48'][key]<1e-8, numeric()['descendant40_48'][key]))
    def lp():
        v=read(res/'refinement/lp_optimality_checks.json')
        return len(v)==2 and all(q['primal_dual_gap']<1e-10 and q['max_constraint_violation']<2e-8 for q in v), v
    check('linear_program_optimality', lp)
    def radial():
        v=read(res/'refinement/validation_radial.json')['radial_positive']
        return len(v)>=9 and min(q['relative_negative'] for q in v)>-1e-10, v
    check('normalized_odd_radial_positivity', radial)
    def gff():
        v=read(res/'precision/tail_validation_results.json')['gff']
        return all(q['max_actual_over_upper']<=1+1e-10 for q in v['identical_remainder_tests']) and v['mixed_radial_prefactor_relative_error']<1e-10, v
    check('generalized_free_remainder_and_prefactor', gff)
    def tail():
        qs=numeric()['tail_quadrature'];delta=[abs(a-b) for a,b in zip(qs[0]['values'],qs[-1]['values'])]
        return len(qs)>=3 and all(math.isfinite(x) and x>=0 for q in qs for x in q['values']) and max(delta)<2e-7, {'endpoint_changes':delta,'quadratures':qs}
    check('integrated_tail_quadrature',tail)
    def angular():
        n=numeric();a,b=n['angular100'],n['angular160']
        ok=all(a[k]>=0 and b[k]>=0 for k in ['exponent_interpolation_allowance','high_spin_allowance','high_exponent_allowance'])
        ok=ok and a['upper_kernel']>=max(a['sampled_upper'],a['high_spin_allowance'],a['high_exponent_allowance'])
        ok=ok and abs(a['odd_integral_lower']-b['odd_integral_lower'])<1e-9 and abs(a['odd_integral_upper']-b['odd_integral_upper'])<1e-5
        return ok, {'coarse':a,'fine':b,'meaning':'Convergence check, not interval certification'}
    check('angular_and_continuous_exponent_envelopes',angular)
    def denominator():
        v=read(res/'precision/input_box_results.json')['two_error_box']
        db=math.ceil(max(abs(v['delta_b_min']),abs(v['delta_b_max']))*1e6)/1e6
        c=read(res/'precision/analysis_results.json')['central']
        q=ratio_interval(c['C1'],c['b'],-1e-3,1e-3,db)
        return 0<=db<c['b'] and q[0]<c['C1']<q[1], {'computed_rounded_db':db,'central':c}
    check('current_reference_and_denominator',denominator)
    def ranges():
        intervals=[read(res/'refinement'/f'final_8_7_pad{p}_summary.json')['interval'] for p in [1,2]]
        return all(.269<=v[0]<=v[1]<=.276 for v in intervals), {'scenario_range':[.269,.276], 'computed_intervals':intervals}
    check('scenario_range_contains_computed_runs',ranges)
    def counts():
        v=read(ROOT/'data/inputs/retained_spectrum.json');c={s:sum(q['sector']==s for q in v) for s in ['even','odd']}
        return c=={'even':37,'odd':23},c
    check('selected_spectrum_counts',counts)
    def receipt():
        v=read(res/'run_receipt.json')
        ok=v['status']=='passed' and v['profile']=='full' and v['from_scratch'] and not v['cached_dependencies'] and len(v['steps'])==20
        return ok, {'profile':v['profile'],'from_scratch':v['from_scratch'],'steps':len(v['steps']),'cached_dependencies':len(v['cached_dependencies'])}
    check('successful_full_clean_run',receipt)
    output={'status':'passed' if all(v['passed'] for v in checks) else 'failed', 'results_directory':str(res),
            'scope':'Numerical regression of a full run only; not certification of physical uncertainty', 'checks':checks}
    report=args.report or res/'verification/regression_checks.json';report.parent.mkdir(parents=True,exist_ok=True)
    report.write_text(json.dumps(output,indent=2)+'\n')
    print(f"{output['status']}: {sum(q['passed'] for q in checks)}/{len(checks)} numerical regression checks; {report}")
    if output['status']!='passed':
        print(json.dumps([q for q in checks if not q['passed']],indent=2))
        raise SystemExit(1)

if __name__=='__main__':
    main()
