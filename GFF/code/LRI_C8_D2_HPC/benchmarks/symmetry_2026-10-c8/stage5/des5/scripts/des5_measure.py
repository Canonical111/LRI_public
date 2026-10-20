#!/usr/bin/env python3
"""J-DES-5 (A-DES-5) measurement of one planned (never submitted) campaign of a design bundle.

  des5_measure.py PLAN_DIR BUNDLE_DIR --time TIME_V_FILE --wall SECONDS --out FILE.json

Records what A-DES-5 asks for, from the files on disk and the plan's manifest (no package import):
  task and checkpoint counts (and tasks per campaign), the tasks.sqlite sizes (total, largest group), the number and
  total size of the per-index task files, the manifest size, the plan's wall time and peak RSS (GNU time -v), the
  index count, the predicted largest index wall, the merge passes per group and the projected merge time; and every
  cap: tasks per campaign <= 5e7, checkpoint blocks <= 2e5, replicates <= 128, predicted task seconds <= 120,
  projected merge <= 12 h, Sobol period (counts <= 2^bits), and the bundle's own cap record (design.json caps).
"""
import argparse, json, os, re
from pathlib import Path

MAX_TASKS = 5 * 10**7; MAX_CHECKPOINTS = 2 * 10**5; MAX_REPS = 128; MAX_TASK_SECONDS = 120.; MERGE_MAX_HOURS = 12.
NET_BITS = {'a': 52, 'b': 60}


def time_v(path: Path) -> dict:
    out = {}
    if not path.exists():
        return out
    for line in path.read_text(errors='replace').splitlines():
        line = line.strip()
        m = re.match(r'Maximum resident set size \(kbytes\): (\d+)', line)
        if m: out['max_rss_kb'] = int(m.group(1))
        m = re.match(r'Elapsed \(wall clock\) time \(h:mm:ss or m:ss\): (.+)', line)
        if m: out['elapsed'] = m.group(1)
        m = re.match(r'Exit status: (\d+)', line)
        if m: out['exit_status'] = int(m.group(1))
        m = re.match(r'User time \(seconds\): ([\d.]+)', line)
        if m: out['user_seconds'] = float(m.group(1))
        m = re.match(r'System time \(seconds\): ([\d.]+)', line)
        if m: out['system_seconds'] = float(m.group(1))
    return out


def main() -> int:
    p = argparse.ArgumentParser(); p.add_argument('plan', type=Path); p.add_argument('bundle', type=Path)
    p.add_argument('--time', type=Path, required=True); p.add_argument('--wall', type=float, required=True)
    p.add_argument('--out', type=Path, required=True); a = p.parse_args()
    m = json.loads((a.plan / 'manifest.json').read_bytes()); d = json.loads((a.bundle / 'design.json').read_bytes())
    meta = json.loads((a.bundle / 'design_meta.json').read_bytes())
    groups = {}
    for g in sorted((a.plan / 'groups').iterdir()):
        cfg = json.loads((g / 'config.json').read_bytes())
        tfiles = sorted((g / 'tasks').iterdir())
        groups[g.name] = {'tasks': cfg['tasks'], 'shards': cfg['shards'], 'replicates': cfg['replicates'],
                          'graphs': len(cfg['counts']), 'max_count': max(cfg['counts'].values()) if cfg['counts'] else 0,
                          'samples': cfg['samples'], 'tasks_sqlite_bytes': (g / 'tasks.sqlite').stat().st_size,
                          'sobol_bin_bytes': (g / 'sobol.bin').stat().st_size, 'task_files': len(tfiles),
                          'task_files_bytes': sum(f.stat().st_size for f in tfiles),
                          'predicted_max_task_seconds': cfg.get('predicted_max_task_seconds'),
                          'campaign': cfg['campaign'], 'net_bits': NET_BITS[cfg['campaign']]}
    nfiles = 0; nbytes = 0
    for root, dirs, files in os.walk(a.plan):
        for f in files:
            nfiles += 1; nbytes += os.lstat(os.path.join(root, f)).st_size
    jobs = m['jobs']; tasks_c = {'a': 0, 'b': 0}
    for j in jobs: tasks_c[j['campaign']] += j['tasks']
    sc = m['scale']; e = m['estimates']
    merge = {k: {'passes': v['passes'], 'runs': v['runs'], 'rows': v['rows'], 'projected_seconds': v['projected_seconds']} for k, v in sc['merge'].items()}
    pmt = [v for v in e['predicted_max_task_seconds'].values() if isinstance(v, (int, float))]
    caps = {
        'tasks_per_campaign_le_5e7': all(v <= MAX_TASKS for v in tasks_c.values()),
        'checkpoints_le_2e5': sc['checkpoints'] <= MAX_CHECKPOINTS,
        'replicates_le_128': max(g['replicates'] for g in groups.values()) <= MAX_REPS,
        'predicted_task_seconds_le_120': max(pmt) <= MAX_TASK_SECONDS,
        'merge_le_12h': sc['merge_projected_max_seconds'] <= MERGE_MAX_HOURS * 3600,
        'sobol_period': all(g['max_count'] <= 2 ** g['net_bits'] for g in groups.values()),
        'bundle_caps_ok': bool(d['caps']['ok']) and bool(d['caps']['task_ok']),
    }
    tv = time_v(a.time)
    rec = {
        'schema': 'c8-d2-des5-measure-1', 'plan': str(a.plan), 'bundle': str(a.bundle),
        'bundle_design_meta_sha256': m['design']['meta_sha256'] if m.get('design') else None,
        'target_rel': (meta.get('target') or {}).get('rel'), 'target_se': (meta.get('target') or {}).get('se'),
        'seed': m['seed'], 'test_only': m['test_only'], 'backend': m['backend'], 'numerics': m['numerics'], 'rates_identity': m['rates_identity'],
        'threads': m['threads'], 'checkpoint_tasks': m['checkpoint_tasks'], 'index_hours': m['index_sizing']['index_hours'],
        'cost_model_sha256': m['cost_model_sha256'], 'executable_sha256': m['executable_sha256'],
        'design': {'batches': d['batches'], 'batches_minimum': d['batches_minimum'], 'replicates': d['replicates'],
                   's': {k: v['s'] for k, v in d['strata'].items()}, 'predicted_se_total': d['predicted']['se_total'],
                   'allocated_core_hours_total': d['predicted']['cost_total_core_hours'],
                   'allocated_core_hours_per_batch': d['predicted']['cost_per_batch_core_hours'], 'eta_node': d['eta_node'], 'caps': d['caps']},
        'tasks': sc['tasks'], 'tasks_per_campaign': tasks_c, 'checkpoints': sc['checkpoints'], 'indices': len(jobs), 'projected_files': sc['projected_files'],
        'tasks_sqlite_bytes_total': sum(g['tasks_sqlite_bytes'] for g in groups.values()),
        'tasks_sqlite_bytes_max_group': max(g['tasks_sqlite_bytes'] for g in groups.values()),
        'task_files': sum(g['task_files'] for g in groups.values()), 'task_files_bytes': sum(g['task_files_bytes'] for g in groups.values()),
        'task_files_bytes_max': max((j['tasks_bytes'] for j in jobs), default=0),
        'manifest_bytes': (a.plan / 'manifest.json').stat().st_size, 'sobol_bin_bytes_total': sum(g['sobol_bin_bytes'] for g in groups.values()),
        'plan_dir_files': nfiles, 'plan_dir_bytes': nbytes,
        'plan_wall_seconds': a.wall, 'plan_time_v': tv, 'plan_peak_rss_bytes': tv.get('max_rss_kb', 0) * 1024 if tv else None,
        'estimated_task_core_hours': e['total_core_hours'], 'max_index_wall_seconds': e['max_index_wall_seconds'],
        'suggested_time_seconds': e['suggested_time_seconds'], 'mem_suggestion_mb': e['mem_suggestion_mb'],
        'max_index_est_peak_bytes': max(j['est_peak_bytes'] for j in jobs),
        'predicted_max_task_seconds': max(pmt), 'merge_passes_max': max(v['passes'] for v in merge.values()),
        'merge_passes': {k: v['passes'] for k, v in merge.items()}, 'merge_projected_max_seconds': sc['merge_projected_max_seconds'],
        'suggested_merge_time': sc['suggested_merge_time'], 'merge': merge, 'groups': groups, 'caps': caps, 'all_caps_hold': all(caps.values()),
    }
    a.out.write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps({k: rec[k] for k in ('target_rel', 'tasks', 'checkpoints', 'indices', 'tasks_sqlite_bytes_total', 'task_files', 'task_files_bytes',
                                         'manifest_bytes', 'plan_wall_seconds', 'plan_peak_rss_bytes', 'max_index_wall_seconds', 'merge_passes_max',
                                         'all_caps_hold')}))
    return 0 if rec['all_caps_hold'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
