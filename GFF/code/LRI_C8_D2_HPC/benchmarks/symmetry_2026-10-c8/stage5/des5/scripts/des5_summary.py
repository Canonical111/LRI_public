#!/usr/bin/env python3
"""J-DES-5 summary (A-DES-5): the four freezes and the four plans of their bundles, from the job's evidence folder.
Mac, seconds.   des5_summary.py EVIDENCE_DIR OUT.json
Per target: the freeze (batches, minimum K, predicted SE with the margin, allocated core-hours at the sweep's eta_node,
the caps of design.json, freeze wall and RSS from GNU time) and the plan's measurements (des5_measure.py): tasks and
checkpoints, the tasks.sqlite size, the number and total size of the per-index task files, the manifest size, the plan
wall and peak RSS, the index count, the predicted largest index wall, the merge passes, every cap; and the deletion of
the plan directory. Also the eta_node records (accounting.py) of the sweep and the lane campaigns."""
import json, re, sys
from pathlib import Path

TARGETS = ('1e-3', '5e-4', '2.5e-4', '1.35e-4')


def time_v(p: Path) -> dict:
    out = {}
    for line in p.read_text(errors='replace').splitlines():
        line = line.strip()
        for key, rx, cast in (('max_rss_kb', r'Maximum resident set size \(kbytes\): (\d+)', int), ('elapsed', r'Elapsed \(wall clock\) time \(h:mm:ss or m:ss\): (.+)', str),
                              ('exit_status', r'Exit status: (\d+)', int)):
            m = re.match(rx, line)
            if m: out[key] = cast(m.group(1))
    return out


def main() -> int:
    E = Path(sys.argv[1]); out = Path(sys.argv[2])
    acc = {}
    for f in sorted(E.glob('accounting_*.json')):
        d = json.loads(f.read_text()); acc[f.stem.replace('accounting_', '')] = {k: d.get(k) for k in ('eta_node', 'complete', 'allocated_core_hours', 'work_core_hours',
                                                                                                    'busy_thread_core_hours', 'sacct_records', 'ledger_jobs')}
    rows = {}
    deleted = (E / 'deleted.txt').read_text().split('\n') if (E / 'deleted.txt').exists() else []
    for t in TARGETS:
        d = json.loads((E / f'design_{t}.json').read_text()); meas = json.loads((E / f'measure_{t}.json').read_text())
        fr = time_v(E / f'time_freeze_{t}.txt')
        rows[t] = {'freeze': {'batches': d['batches'], 'batches_minimum': d['batches_minimum'], 'replicates': d['replicates'],
                              's': {k: v['s'] for k, v in d['strata'].items()}, 'predicted_se_total': d['predicted']['se_total'],
                              'target_se': float(t) * 46000., 'allocated_core_hours_total': d['predicted']['cost_total_core_hours'],
                              'eta_node': d['eta_node'], 'caps': d['caps'], 'freeze_time_v': fr},
                   'plan': {k: meas[k] for k in ('seed', 'tasks', 'tasks_per_campaign', 'checkpoints', 'indices', 'projected_files', 'tasks_sqlite_bytes_total',
                                                 'tasks_sqlite_bytes_max_group', 'task_files', 'task_files_bytes', 'task_files_bytes_max', 'manifest_bytes',
                                                 'sobol_bin_bytes_total', 'plan_dir_files', 'plan_dir_bytes', 'plan_wall_seconds', 'plan_peak_rss_bytes',
                                                 'estimated_task_core_hours', 'max_index_wall_seconds', 'suggested_time_seconds', 'mem_suggestion_mb',
                                                 'max_index_est_peak_bytes', 'predicted_max_task_seconds', 'merge_passes_max', 'merge_projected_max_seconds',
                                                 'suggested_merge_time', 'caps', 'all_caps_hold')},
                   'plan_directory_deleted': any(l.endswith(f'des5_{t}') for l in deleted)}
    doc = {'schema': 'c8-d2-des5-summary-1', 'job': '570114', 'rule': __doc__, 'accounting': acc, 'targets': rows,
           'all_caps_hold': all(r['plan']['all_caps_hold'] and r['freeze']['caps']['ok'] and r['freeze']['caps']['task_ok'] for r in rows.values()),
           'all_plan_directories_deleted': all(r['plan_directory_deleted'] for r in rows.values())}
    out.write_text(json.dumps(doc, indent=1) + '\n')
    print('| Target | K | pred. SE | core-h (η sweep) | tasks | checkpoints | indices | tasks.sqlite | task files | manifest | plan wall | plan RSS | max index wall | merge passes |')
    print('|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|')
    for t, r in rows.items():
        f, p = r['freeze'], r['plan']
        print(f'| {t} | {f["batches"]} | {f["predicted_se_total"]:.2f} | {f["allocated_core_hours_total"]:,.0f} | {p["tasks"]:,} | {p["checkpoints"]:,} | {p["indices"]:,} | '
              f'{p["tasks_sqlite_bytes_total"] / 2**20:,.0f} MiB | {p["task_files"]:,} ({p["task_files_bytes"] / 2**20:,.0f} MiB) | {p["manifest_bytes"] / 2**10:,.0f} KiB | '
              f'{p["plan_wall_seconds"]:.0f} s | {p["plan_peak_rss_bytes"] / 2**30:.2f} GiB | {p["max_index_wall_seconds"]:,.0f} s | {p["merge_passes_max"]} |')
    print('all caps hold:', doc['all_caps_hold'], '; plan directories deleted:', doc['all_plan_directories_deleted'])
    print(json.dumps(acc, indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
