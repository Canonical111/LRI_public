#!/usr/bin/env python3
"""Cross-campaign independence and coverage check of a snapshot's completion evidence (FIT_MODEL_V3.md §4.7, V3-015; IR14-001).

Usage: union_check.py campaigns.json --tag T [--point-dir DIR] [--out union_check_T.json]
Reads every completion_<T>_<host>.json in the point directory (default: the registry's directory), requires every record to be PASS,
aggregates their task records and REFUSES (exit 1) if: any active campaign of the registry has no PASS evidence; a (campaign, task) appears
in two records; two chains of the whole active union share (seed, N, beta); two samples.bin archives share a SHA-256; a task's seed or
coordinates disagree with its campaign manifest. Writes a JSON record of the check (counts, hosts, campaigns, decision).
"""
from __future__ import annotations
import argparse, glob, hashlib, json, os, sys
from collections import Counter, defaultdict
from pathlib import Path
from registry import load, validate, active_names
from independence import check_independence

def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('registry', type=Path); p.add_argument('--tag', required=True); p.add_argument('--point-dir', type=Path); p.add_argument('--out', type=Path)
    a = p.parse_args(); r = load(a.registry); root = Path(r['root']); pairs = validate(r, root, 'all'); D = a.point_dir or a.registry.resolve().parent
    active = active_names(r); files = sorted(glob.glob(str(D / f'completion_{a.tag}_*.json'))); problems = []
    if not files: raise SystemExit(f'no completion evidence completion_{a.tag}_*.json in {D}')
    covered = {}; tasks = {}; seen_task = Counter(); manifests = {c['name']: {t['id']: t for t in json.loads((root / c['dir'] / 'manifest.json').read_text())['tasks']} for c in r['campaigns'] if c['name'] in active}
    for f in files:
        E = json.loads(Path(f).read_text())
        if E.get('result') != 'PASS': problems.append(f'{os.path.basename(f)}: result {E.get("result")!r}')
        for name, c in (E.get('campaigns') or {}).items():
            if name in covered: problems.append(f'campaign {name} appears in two evidence records ({covered[name]} and {os.path.basename(f)})')
            covered[name] = os.path.basename(f)
        for t in E.get('tasks', []):
            k = (t['campaign'], int(t['task'])); seen_task[k] += 1
            if seen_task[k] > 1: continue
            tasks[k] = t
            m = manifests.get(t['campaign'], {}).get(int(t['task']))
            if m is None: problems.append(f'{k}: task not in the manifest of an active campaign'); continue
            if m['seed'] != t['seed'] or m['N'] != t['N'] or abs(m['beta'] - t['beta']) > 1e-15: problems.append(f'{k}: evidence seed/coordinates differ from the manifest')
    dup_tasks = [k for k, n in seen_task.items() if n > 1]
    if dup_tasks: problems.append(f'{len(dup_tasks)} (campaign, task) records duplicated across evidence files, e.g. {dup_tasks[:3]}')
    missing = [n for n in active if n not in covered]
    if missing: problems.append(f'active campaigns without PASS evidence for tag {a.tag}: {missing}')
    # independence across the whole active union (V3-015): the shared validator of select_model_v3.verify_lineage (IR5-001)
    problems += check_independence(list(tasks.values()))
    by_seed = {(t.get('s'), t['N'], round(float(t['beta']), 12), t['seed']) for t in tasks.values()}; by_hash = {t.get('samples_sha256') for t in tasks.values()}
    # every active (pair, campaign) must be fully represented
    for pair, lst in pairs.items():
        for c, mtasks in lst:
            got = sum(1 for t in mtasks if (c['name'], t['id']) in tasks)
            if got != len(mtasks): problems.append(f'{pair} {c["name"]}: {got}/{len(mtasks)} chains in the evidence')
    rec = dict(registry=str(a.registry.resolve()), registry_sha256=hashlib.sha256(a.registry.read_bytes()).hexdigest(), tag=a.tag, evidence_files=[os.path.basename(f) for f in files],
               active_campaigns=active, tasks=len(tasks), distinct_seed_coordinates=len(by_seed), distinct_samples_hashes=len(by_hash), problems=problems, result='PASS' if not problems else 'FAIL')
    out = a.out or (D / f'union_check_{a.tag}.json'); out.write_text(json.dumps(rec, indent=1) + '\n')
    print(f"union check {rec['result']}: {len(tasks)} chains of {len(active)} active campaigns from {len(files)} evidence records; {len(problems)} problems"); [print('  -', q) for q in problems[:20]]
    raise SystemExit(0 if not problems else 1)
if __name__ == '__main__': main()
