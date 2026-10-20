#!/usr/bin/env python3
"""Full replay of the d = 1 resummation: rerun the verbatim chain and compare with the shipped outputs (new tool, 2026-10-14).

Copies this package (without public/ and .work/) to <work>/full/, deletes the 40 outputs the chain writes, runs the
verbatim driver there (LRI_C8_1=final bash update_2026-10-13/C8_1_ext/run_chain.sh; about 2 min on one core; the
'python3' it calls is the interpreter running this script), then compares every regenerated output with the shipped
one and recomputes the quoted numbers from the rerun (public/replay_d1.py --tree <work>/full/resum_d1).
Tolerances (the chain is deterministic; differences come from numpy/BLAS/libm builds): curves and residuals
|diff| <= 1e-12 + 1e-12 |value|; JSON records the same, ignoring provenance keys (sha256, elapsed time, versions);
the coefficient-model fits of instanton_mismatch/analysis.json 1e-6 relative, the budget ratios of
precision_summary.json 1e-9 relative (ratios of values near 1e-15), the residuals of fig05_*_inputs.json
(stored in units of 1e-3) 1e-9 absolute; the PNG/PDF diagnostics are not compared.
Known platform difference (INFO, not FAIL): precision_budget_K.csv 'reduction_factor' at Delta_sigma = 0.2495 is a ratio
of two values below 1e-15, empty on the production machine and finite elsewhere.
Measured on symmetry (Xeon 6148, Python 3.12.9, numpy 2.3.5, scipy 1.17.1): chain 1 min 53 s; all values within
5e-15 absolute except the fits of analysis.json (2e-6 relative).
Usage: python3 public/replay_full_d1.py [--work DIR]
"""
import argparse, os, shutil, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
sys.path.insert(0, str(PKG.parent.parent/'verify'))
sys.path.insert(0, str(HERE))
import rsum_lib as L
import replay_d1

EXT = Path('update_2026-10-13')/'C8_1_ext'
OUTPUTS = ([EXT/f for f in ('fig04_c9_inputs.json', 'fig05_K8_inputs.json', 'fig05_gff_only_inputs.json')] +
           [EXT/'instanton_mismatch'/f for f in ('analysis.json', 'ratio_table.csv', 'ratio_table_KI.csv')] +
           [EXT/'pipeline_K8'/'plot_data_1d_K8.json'] +
           [EXT/'pipeline_K8'/'results'/f for f in (
               'ablation_K.csv', 'ablation_validation.json', 'c9_inherited_K.csv', 'c9_inherited_dense_K.csv',
               'c9_predictions_K.csv', 'c9_sensitivity_K.csv', 'c9_sensitivity_dense_K.csv', 'c9_validation.json',
               'c9cb8_inherited_K.csv', 'c9cb8_inherited_dense_K.csv', 'c9cb8_predictions.json', 'c9cb8_sensitivity_K.csv',
               'c9cb8_sensitivity_dense_K.csv', 'c9cb8_validation.json', 'comparison_points_K.csv', 'curve_K.csv',
               'curve_metadata.json', 'curve_validation.json', 'held_out_K.csv', 'key_points_K.csv', 'matched_comparison_K.csv',
               'mismatch_check.json', 'pade_admissibility_K.json', 'parameter_scan_K.csv', 'precision_budget_K.csv',
               'precision_summary.json', 'refs_validation.json')] +
           [EXT/'sr_endpoint'/f for f in ('reference_residuals_K8.csv', 'sr_endpoint_keypoints.csv', 'sr_endpoint_results.json')])
NOT_COMPARED = [EXT/'instanton_mismatch'/'ratio_diagnostics.png', EXT/'sr_endpoint'/'fig_1d_srK_residuals.pdf',
                EXT/'sr_endpoint'/'fig_1d_srK_residuals.png']
PROVENANCE_KEYS = ('sha256', 'elapsed_seconds', 'inputs_sha256', 'sources', 'versions', 'python', 'numpy', 'scipy', 'mpmath',
                   'matplotlib', 'time', 'date', 'host', 'output_root')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--work', default=str(PKG/'.work'))
    a = ap.parse_args()
    work = Path(a.work).resolve()
    full = work/'full'/'resum_d1'
    shutil.rmtree(work/'full', ignore_errors=True)
    shutil.copytree(PKG, full, ignore=shutil.ignore_patterns('public', '.work', '__pycache__'))
    for rel in OUTPUTS + NOT_COMPARED:
        (full/rel).unlink(missing_ok=True)
    shim = work/'full'/'bin'
    shim.mkdir(parents=True, exist_ok=True)
    (shim/'python3').write_text('#!/bin/sh\nexec "%s" "$@"\n' % sys.executable)
    (shim/'python3').chmod(0o755)
    env = dict(os.environ, LRI_C8_1='final', PATH=str(shim) + os.pathsep + os.environ.get('PATH', ''),
               MPLBACKEND='Agg', MPLCONFIGDIR=str(work/'full'/'mpl'), PYTHONDONTWRITEBYTECODE='1')
    env.pop('LRI_C8_1_OUT', None)
    log = work/'full'/'chain.log'
    with log.open('w') as fh:
        r = subprocess.run(['bash', str(EXT/'run_chain.sh')], cwd=full, env=env, stdout=fh, stderr=subprocess.STDOUT)
    T = L.Table('resum_d1 replay-full (chain rerun vs shipped outputs)')
    T.check('chain exit status', r.returncode == 0, 'exit %d' % r.returncode, 'exit 0', 'verbatim run_chain.sh (log %s)' % log)
    for rel in OUTPUTS:
        new, old = full/rel, PKG/rel
        if not new.exists():
            T.check(str(rel), False, 'missing', 'regenerated', 'output of the chain'); continue
        if rel.suffix == '.csv':
            ignore = ('reduction_factor',) if rel.name == 'precision_budget_K.csv' else ()
            ok, how, bad = L.compare_csv(old, new, ignore=ignore)
            if ignore:
                T.add('precision_budget_K.csv reduction_factor', 'INFO', 'not compared', '-',
                      'ratio of two values < 1e-15 at Delta_sigma = 0.2495: platform-dependent (see docstring)')
        else:
            rtol = {'analysis.json': 1e-6, 'precision_summary.json': 1e-9}.get(rel.name, 1e-12)
            atol = 1e-9 if rel.name.startswith('fig05_') else 1e-12     # fig05 inputs hold residuals in units of 1e-3
            ok, how, bad = L.compare_json(old, new, atol=atol, rtol=rtol, ignore_keys=PROVENANCE_KEYS)
        T.check(str(rel), ok, how + ('' if ok else ' e.g. %s' % (bad[:2],)), 'within tolerance',
                'regenerated vs shipped (by column name / JSON path)')
    for rel in NOT_COMPARED:
        T.add(str(rel), 'INFO', 'regenerated' if (full/rel).exists() else 'missing', '-', 'figure diagnostics: not compared')
    status = T.report(work/'replay_full_d1.txt')
    print()
    status |= replay_d1.main(['--tree', str(full), '--work', str(work/'full_quoted'), '--out', str(work/'replay_full_d1_quoted.txt')])
    return status


if __name__ == '__main__':
    sys.exit(main())
