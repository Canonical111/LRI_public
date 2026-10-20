#!/usr/bin/env python3
"""Run one verbatim assembly step in a work copy of the package (new tool, 2026-10-15; called by replay_indep.py).

Run with the work copy's assembly/ as the current directory:
  python3 run_step.py MODE [--record REC] [--out OUT]
MODE
  p2     assembly/run_assembly.py main(): phase 2, steps 1-2 (the 25 inputs, D2..D4, T2, T3, C3..C7 with the three error
         estimators; the archive-free checks i-iii; iv is read from out/direct_summary.json); writes
         ../RESULTS_independent.json in the work copy.
  c8     assembly/run_assembly_C8.py step1(), w_three_ways(), separate_files_check(): the C8 assembly (the ten new inputs,
         B_old, B_done, T4, C8, the sub-pieces of U, Kv, J9, error budgets, the note's raw structure); writes OUT (JSON).
  cmp2   assembly/compare_archive.py main(): phase-2 comparison with the sealed archive values and the claimed closed
         forms; writes ../RESULTS_archive_comparison.json in the work copy.
  cmp8   assembly/compare_archive_C8.py main(): C8 comparison; writes ../RESULTS_C8_archive_comparison.json.
--record REC: replace the raw per-sector layer of assembly/pooled_errors.py by the pooled sector record
(public/pooled_shim.py). Without it the raw chunk outputs must be present in engine/runs/ (make replay-raw).
"""
import argparse
import importlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', choices=['p2', 'c8', 'cmp2', 'cmp8'])
    ap.add_argument('--record', default=None)
    ap.add_argument('--out', default=None)
    a = ap.parse_args()
    sys.path.insert(0, os.getcwd())
    t0 = time.time()
    PE = importlib.import_module('pooled_errors')
    if a.record:
        sys.path.insert(0, HERE)
        import pooled_shim
        pooled_shim.install(PE, a.record)
        print(f'pooled sector layer: record {os.path.basename(a.record)}', flush=True)
    else:
        print('pooled sector layer: raw chunk outputs (verbatim pooled_errors.py)', flush=True)
    import mpmath as mp
    if a.mode == 'p2':
        importlib.import_module('run_assembly').main()
    elif a.mode == 'cmp2':
        importlib.import_module('compare_archive').main()
    elif a.mode == 'cmp8':
        importlib.import_module('compare_archive_C8').main()
    else:
        RC = importlib.import_module('run_assembly_C8')
        CM = importlib.import_module('common')
        with mp.workdps(RC.DPS):
            res, sub, terms, budget, struct, meta, fw, merged, inp, cen, names, prod, abc, tiers, jobs, E = RC.step1()
            W3 = RC.w_three_ways(res)
            sep = RC.separate_files_check(fw, cen, prod, tiers)
        CM.write_json(a.out, {'meta': meta, 'outputs': res, 'sub_pieces': sub, 'C8_assembly_terms': terms,
                              'error_budget': budget, 'note_raw_structure': struct, 'W_three_ways': W3,
                              'separate_tier_files': sep})
    print(f'run_step {a.mode}: done in {time.time() - t0:.1f} s', flush=True)


if __name__ == '__main__':
    main()
