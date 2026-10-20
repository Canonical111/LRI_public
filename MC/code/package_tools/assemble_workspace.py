#!/usr/bin/env python3
"""Assemble the working tree in which every script of this package runs unmodified.

The campaign scripts locate their inputs relative to their own file (e.g. ROOT/LRI_2d_MC/prod), and the amendment-P1 evaluators bind
themselves, the calibration script and the frozen protocols by SHA-256. They must therefore run inside the original project layout
and must be byte-identical copies. This tool recreates that layout under WORK (default: ./work):
  - code and protocol files are COPIED (Python resolves symlinks in __file__, which would move ROOT);
  - input data and reference results are SYMLINKED (relative links into ../data and ../results; nothing is duplicated).
Nothing under code/, data/ or results/ is modified. Re-running refuses to overwrite an existing WORK unless --force.

Usage: python3 code/package_tools/assemble_workspace.py [WORK] [--force]

Public-release copy (2026-10-13): the protocols are read from the top-level protocols/ folder, and the default workspace is .work/
(git-ignored). Material that is not released (the N0 and stage-0 data, exploratory prediction scripts, the analytic finite-size material)
is not linked. No copied byte changes, so all hash checks pass.
"""
import argparse, os, shutil, sys
from pathlib import Path

PKG = Path(__file__).resolve().parents[2]

def copy(src, dst):
    src = PKG / src; dst = Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir(): shutil.copytree(src, dst, ignore=shutil.ignore_patterns('__pycache__', '.DS_Store', '*.pyc'))
    else: shutil.copy2(src, dst)

def link(src, dst):
    src = PKG / src; dst = Path(dst)
    if not src.exists(): sys.exit(f'missing {src}')
    dst.parent.mkdir(parents=True, exist_ok=True)
    os.symlink(os.path.relpath(src, dst.parent), dst)

def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('work', nargs='?', default=str(PKG / '.work')); p.add_argument('--force', action='store_true'); a = p.parse_args()
    W = Path(a.work).resolve()
    if W.exists():
        if not a.force: sys.exit(f'{W} exists (use --force to rebuild it; reproduced outputs inside it are kept only if you move them first)')
        shutil.rmtree(W)
    W.mkdir(parents=True)
    # ---- 1D: lri_cluster (code copied, scan data linked)
    copy('code/1d', W / 'lri_cluster')
    link('data/1d/scan_data', W / 'lri_cluster/scanA_exp/scan_data')
    # 1D report tables/figure tool: it reads ../records and writes ../tables, ../figures
    copy('code/1d_report_tools', W / 'LRI_1d_MC_report/scripts')
    copy('results/1d/records', W / 'LRI_1d_MC_report/records')
    (W / 'LRI_1d_MC_report/tables').mkdir(); (W / 'LRI_1d_MC_report/figures').mkdir()
    # ---- 2D and 3D campaigns
    for dim in (2, 3):
        C = W / f'LRI_{dim}d_MC'
        copy(f'code/{dim}d', C)                                    # evaluate_{dim}d.py, make_plan.py
        copy('code/2d3d_engine/code', C / 'code')                  # lri_precision_v2 working copy (MC engine + analysis)
        copy('code/2d3d_engine/reference', C / 'reference')        # Makefile target bin/lri_reference expects ../reference
        copy(f'protocols/FIT_MODEL_{dim}D.md', C / f'FIT_MODEL_{dim}D.md')
        link(f'data/{dim}d/prod', C / 'prod')
    copy('protocols/FIT_MODEL_3D.md.sha256', W / 'LRI_3d_MC/FIT_MODEL_3D.md.sha256')
    copy('data/2d/production_centers.csv', W / 'LRI_2d_MC/production_centers.csv')
    copy('data/3d/production_centers_3d.csv', W / 'LRI_3d_MC/production_centers_3d.csv')
    link('data/3d/preflight', W / 'LRI_3d_MC/preflight')
    # ---- 2D/3D reanalysis, amendment P1 (calibration + tests), 1D cross-check study
    R = W / 'LRI_2d3d_reanalysis'
    for f in ('reanalyse.py', 'calibrate_p1.py'): copy(f'code/reanalysis_p1/{f}', R / f)      # reanalyse.py: reference implementation used by the P1 tests
    copy('code/reanalysis_p1/tests', R / 'tests')
    copy('protocols/AMENDMENT_PROFILED_SIGMA.md', R / 'AMENDMENT_PROFILED_SIGMA.md')
    copy('protocols/AMENDMENT_PROFILED_SIGMA.md.sha256', R / 'AMENDMENT_PROFILED_SIGMA.md.sha256')
    copy('code/oned_xcheck/check_1d_xcheck.py', R / 'oned_xcheck/check_1d_xcheck.py')
    link('results/2d3d_reanalysis/calibration/run_20260930_213748', R / 'calibration/run_20260930_213748')   # input of the P1 evaluations
    (W / 'reproduced').mkdir()
    print(f'workspace assembled at {W}')

if __name__ == '__main__': main()
