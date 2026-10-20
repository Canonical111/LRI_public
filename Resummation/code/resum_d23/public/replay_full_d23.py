#!/usr/bin/env python3
"""Full replay of the d = 2, 3 resummation: rerun the verbatim scripts and compare with the shipped outputs (new tool,
2026-10-14). Run from code/resum_d23/.

Copies 2d/, 3d/ and combined/ to <work>/full/, deletes the outputs, and runs the production order of each dimension's
run script (calculate, supplement, compare_ht | compare_l20, update_comparison, package_results), then
combined/make_cb3_gff_only.py. package_results.py hashes the provenance snapshots of the GFF and SRI notes in
2d/inputs/sources/, which are not shipped (they are other folders' notes; see DATA); empty stand-ins are created in the
copy, so only the manifest it writes differs (not compared). Then every regenerated output is compared with the shipped
one (CSV by column name, since the column order of curves.csv depends on dict iteration; JSON by path, ignoring job
ids and software versions) with |diff| <= 1e-12 + 1e-12 |value|, and the quoted numbers are recomputed from the rerun.
Measured on symmetry (Xeon 6148, Python 3.12.9, numpy 2.3.5, scipy 1.17.1, mpmath 1.3.0): 51 s in total; all values
within 2e-14.
Usage: python3 public/replay_full_d23.py [--work DIR]
"""
import argparse, os, shutil, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
sys.path.insert(0, str(PKG.parent.parent/'verify'))
sys.path.insert(0, str(HERE))
import rsum_lib as L
import replay_d23

COMMON = ['C8_forecast_assessment.csv', 'C9_forecasts.csv', 'curves.csv', 'held_out.csv', 'key_points.csv', 'metadata.json',
          'pade_b0_poles.json', 'pade_poles.json', 'parameter_scan.csv', 'ratios.csv', 'supplement_validation.json',
          'update_comparison.csv', 'update_summary.json', 'validation.json']
OUTPUTS = ([Path('2d/results')/f for f in COMMON + ['ht_prod1_all_comparison.csv', 'ht_prod1_comparison.json', 'ht_prod1_latest.csv',
                                                    'ht_prod1_moving_reference.csv', 'reference_comparison.csv']] +
           [Path('3d/results')/f for f in COMMON + ['ht_l20_comparison.csv', 'ht_l20_comparison.json', 'comparison_summary.json']] +
           [Path('2d/inputs/plot_data.json'), Path('3d/inputs/plot_data.json'), Path('combined/cb3_gff_only.csv'),
            Path('combined/cb3_gff_only.json')])
STEPS = {'2d': ['calculate.py', 'supplement.py', 'compare_ht.py', 'update_comparison.py', 'package_results.py'],
         '3d': ['calculate.py', 'supplement.py', 'compare_l20.py', 'update_comparison.py', 'package_results.py']}
IGNORE = ('job_id', 'versions', 'sha256', 'script_sha256', 'source_index_sha256', 'input_index_sha256', 'inputs_sha256',
          'elapsed_seconds', 'date', 'time')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--work', default=str(PKG/'.work'))
    a = ap.parse_args()
    work = Path(a.work).resolve()
    full = work/'full'/'resum_d23'
    shutil.rmtree(work/'full', ignore_errors=True)
    for d in ('2d', '3d', 'combined'):
        shutil.copytree(PKG/d, full/d, ignore=shutil.ignore_patterns('__pycache__'))
    for rel in OUTPUTS:
        (full/rel).unlink(missing_ok=True)
    (full/'2d'/'inputs'/'sources').mkdir(parents=True, exist_ok=True)
    for f in ('long_range_ising_condensed.tex', 'C2_final_method.tex'):
        (full/'2d'/'inputs'/'sources'/f).write_text('% stand-in: provenance snapshot not shipped (hashed into manifest.json only)\n')
    env = dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1', MPLBACKEND='Agg',
               PYTHONDONTWRITEBYTECODE='1')
    T = L.Table('resum_d23 replay-full (scripts rerun vs shipped outputs)')
    log = (work/'full'/'run.log').open('w')
    for d, steps in STEPS.items():
        for s in steps:
            r = subprocess.run([sys.executable, '-u', 'code/' + s], cwd=full/d, env=env, stdout=log, stderr=subprocess.STDOUT)
            T.check('%s %s' % (d, s), r.returncode == 0, 'exit %d' % r.returncode, 'exit 0', 'verbatim script (log %s)' % log.name)
    r = subprocess.run([sys.executable, '-u', 'combined/make_cb3_gff_only.py'], cwd=full, env=env, stdout=log, stderr=subprocess.STDOUT)
    T.check('combined make_cb3_gff_only.py', r.returncode == 0, 'exit %d' % r.returncode, 'exit 0', 'verbatim script')
    log.close()
    for rel in OUTPUTS:
        new, old = full/rel, PKG/rel
        if not new.exists():
            T.check(str(rel), False, 'missing', 'regenerated', 'output'); continue
        if rel.suffix == '.csv':
            ok, how, bad = L.compare_csv(old, new)
        else:
            ok, how, bad = L.compare_json(old, new, ignore_keys=IGNORE)
        T.check(str(rel), ok, how + ('' if ok else ' e.g. %s' % (bad[:2],)), 'within tolerance', 'regenerated vs shipped')
    status = T.report(work/'replay_full_d23.txt')
    print()
    status |= replay_d23.main(['--tree', str(full), '--work', str(work/'full_quoted'), '--out', str(work/'replay_full_d23_quoted.txt')])
    return status


if __name__ == '__main__':
    sys.exit(main())
