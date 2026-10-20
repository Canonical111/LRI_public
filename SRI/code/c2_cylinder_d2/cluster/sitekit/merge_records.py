#!/usr/bin/env python3
"""Merge collected records from several sites into one index (no fitting).

  python cluster/sitekit/merge_records.py \
      --site-dir expanse=outputs/expanse/production_plan_<UTC> \
      --site-dir symmetry=outputs/symmetry/production_plan_<UTC> \
      --output outputs/merged_production_plan.json

Each DIR is what collect.sh produced (it contains outputs/<plan>/<task>/), or an
outputs/<plan> directory itself. Every task directory must be complete in the
sense of cluster/sitekit/manifests.py: a non-empty, well-formed SHA256SUMS whose
entries all verify, no unlisted files, and the required receipts
(task_receipt.json, run_receipt.json and a job receipt) plus one record per
lambda of the row. Only verified, listed files are read.

Each record is labelled with its site, node and CPU (job receipt) and carries
the provenance needed to judge comparisons: scientific source hashes, plan
sha256 and the configuration (N, order, lambda, oversample, radius_cost,
mixed/collapsed/tail cutoffs). Every pair with the same (order, lambda) is
compared on the overlapping coefficient boxes and classified as
  replica       same configuration and same scientific sources (expect agreement
                to floating-point level, also across sites and CPU vendors);
  variant       same sources, declared configuration differences (listed);
  incompatible  different scientific sources: reported under "incompatibilities"
                and as a problem (exit 1) unless --allow-mixed-sources.
Every record must carry valid source hashes and a plan sha256 and pass the
semantic record check of cluster/collect_records.py (finite sequences of the
declared length, consistent embedded cutoffs, order/lambda/N matching the file
name); more than one scientific source set in the whole collection is a
problem unless --allow-mixed-sources, whatever the (order, lambda) overlap.
Nothing is fitted and no continuum value is computed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import manifests                                     # noqa: E402
from collect_records import validate_record          # noqa: E402  (the one semantic record validator)

CONFIG_KEYS = ('cutoff', 'oversample', 'radius_cost', 'mixed_cutoff', 'collapsed_cutoff', 'tail_cutoff')
DEFAULT_TAIL_CUTOFF = 2048       # rows without tail_cutoff used the historical value (cluster/run_task.py)


def task_dirs(root: Path, plan: str) -> tuple[list[Path], list[str]]:
    """Task directories of a collection, and stray entries (anything else except the
    hidden partial directories of an interrupted publish) as problems."""
    base = root / 'outputs' / plan if (root / 'outputs' / plan).is_dir() else root
    tasks, stray = [], []
    for p in sorted(base.iterdir()):
        if p.is_dir() and not p.is_symlink() and not p.name.startswith('.'):
            tasks.append(p)
        elif not (p.is_dir() and p.name.startswith('.') and '.partial.' in p.name):
            stray.append(f'{p}: unexpected entry in the plan directory')
    return tasks, stray


def schema(record: dict) -> dict:
    return {'top': sorted(record), 'raw': sorted(record['raw']), 'two_point': sorted(record['two_point']),
            'mixed': sorted(record['mixed']), 'pairings': [p['pairing'] for p in record['raw']['parts']]}


def load_task(task: Path) -> tuple[list[dict], list[str]]:
    """Verified records of one published row, or problems."""
    try:
        receipt = json.loads((task / 'task_receipt.json').read_text())
        job = receipt['job']
    except (OSError, ValueError, KeyError) as exc:
        return [], [f'task_receipt.json unreadable: {exc}']
    entries, problems = manifests.verify_dir(
        task, required=manifests.ROW_RECEIPTS + manifests.row_record_names(job), any_of=(manifests.JOB_RECEIPTS,))
    if problems:
        return [], problems
    job_receipt = next(json.loads((task / r).read_text()) for r in manifests.JOB_RECEIPTS if r in entries)
    config = {k: job.get(k) for k in CONFIG_KEYS}
    if config['tail_cutoff'] is None:
        config['tail_cutoff'] = DEFAULT_TAIL_CUTOFF
    sources = receipt.get('source_hashes')
    plan_sha = receipt.get('plan_sha256')
    # Provenance is required for every record, whether or not it has a partner (R2-003).
    if not isinstance(sources, dict) or not sources or not all(
            isinstance(k, str) and isinstance(v, str) and re.fullmatch(r'[0-9a-f]{64}', v) for k, v in sources.items()):
        problems.append('task_receipt.json lacks valid source_hashes')
    if not isinstance(plan_sha, str) or not re.fullmatch(r'[0-9a-f]{64}', plan_sha):
        problems.append('task_receipt.json lacks a valid plan_sha256')
    if problems:
        return [], problems
    out = []
    for name in manifests.row_record_names(job):
        path = task / name
        value = json.loads(path.read_text())
        invalid = validate_record(path, value)                     # R2-004
        if invalid:
            problems += [f'{name}: {x}' for x in invalid]
            continue
        if (value.get('order'), value.get('N')) != (job['order'], job['cutoff']) or value.get('lam') not in job['lambda']:
            problems.append(f'{name} does not match task_receipt.json')
            continue
        if value['mixed']['Nmax'] != job['mixed_cutoff'] or value['two_point'].get('N') != job['collapsed_cutoff']:
            problems.append(f'{name}: embedded mixed/collapsed cutoffs differ from task_receipt.json')
            continue
        sidecar = name[:-len('.json')] + '_analysis.json'
        out.append({
            'path': str(path), 'sha256': entries[name], 'task_dir': task.name, 'order': value['order'],
            'lam': value['lam'], 'N': value['N'], 'config': config,
            'source_hashes': sources,
            'sources_sha256': hashlib.sha256(json.dumps(sources, sort_keys=True).encode()).hexdigest(),
            'plan_sha256': plan_sha, 'plan_name': receipt.get('plan_name'),
            'coefficient_file': value.get('coefficient_file'),
            'analysis_sidecar': sidecar if sidecar in entries else None,
            'site': job_receipt.get('site'), 'host': job_receipt.get('host'),
            'cpu_vendor': job_receipt.get('cpu_vendor'), 'cpu_model': job_receipt.get('cpu_model'),
            'xchain': value['raw']['Xchain'], 'schema': schema(value),
            'raw_chain_at_N': value['raw']['Xchain'][-1]})
    return (out if not problems else []), problems


def classify(a: dict, b: dict) -> tuple[str, list[str]]:
    if a['sources_sha256'] != b['sources_sha256']:
        return 'incompatible', ['source_hashes']
    differs = [k for k in CONFIG_KEYS if a['config'][k] != b['config'][k]]
    return ('variant' if differs else 'replica'), differs


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--site-dir', action='append', required=True, metavar='LABEL=DIR')
    p.add_argument('--plan-name', default='production_plan')
    p.add_argument('--allow-mixed-sources', action='store_true',
                   help='Report pairs from different scientific sources without failing.')
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    problems, records = [], []
    for item in a.site_dir:
        label, _, directory = item.partition('=')
        root = Path(directory)
        if not label or not root.is_dir():
            p.error(f'bad --site-dir {item!r}')
        tasks, stray = task_dirs(root, a.plan_name)
        problems += stray
        if not tasks:
            problems.append(f'{root}: no task directories')
        for task in tasks:
            got, issues = load_task(task)
            problems += [f'{task}: {x}' for x in issues]
            for r in got:
                r['site_label'] = label
                r['site'] = r['site'] or label      # receipts of the first Expanse version lack 'site'
            records += got
    reference = records[0]['schema'] if records else None
    for r in records:
        if r['schema'] != reference:
            problems.append(f"{r['path']}: record schema differs from {records[0]['path']}")
    comparisons, incompatibilities = [], []
    for i, ra in enumerate(records):
        for rb in records[i + 1:]:
            if (ra['order'], ra['lam']) != (rb['order'], rb['lam']):
                continue
            n = min(ra['N'], rb['N'])
            diff = max(abs(x - y) for x, y in zip(ra['xchain'][:n], rb['xchain'][:n]))
            kind, fields = classify(ra, rb)
            c = {'a': ra['path'], 'b': rb['path'], 'sites': [ra['site'], rb['site']],
                 'cross_site': ra['site'] != rb['site'], 'classification': kind, 'differing': fields,
                 'overlap_N': n, 'max_abs_raw_chain_difference': diff,
                 'interpretation': {'replica': 'Same configuration and sources: floating-point agreement expected.',
                                    'variant': 'Declared configuration difference: a consistency diagnostic, '
                                               'not an error bound.',
                                    'incompatible': 'Different scientific sources: not a like-for-like comparison.'}[kind]}
            comparisons.append(c)
            if kind == 'incompatible':
                incompatibilities.append(c)
    # Source compatibility over the whole collection, whatever the (order, lambda) overlap (R2-003).
    source_sets: dict[str, list[str]] = {}
    for r in records:
        source_sets.setdefault(r['sources_sha256'], []).append(r['path'])
    if len(source_sets) > 1 and not a.allow_mixed_sources:
        problems.append(f'{len(source_sets)} different scientific source sets in one collection '
                        f'(pass --allow-mixed-sources to merge them deliberately): '
                        + '; '.join(f'{k[:12]}: {len(v)} records' for k, v in sorted(source_sets.items())))
    if incompatibilities and not a.allow_mixed_sources:
        problems += [f"incompatible sources: {c['a']} vs {c['b']}" for c in incompatibilities]
    index = [{k: v for k, v in r.items() if k not in ('xchain', 'schema')} for r in records]
    out = {'plan': a.plan_name, 'site_dirs': a.site_dir, 'records': index, 'overlap_comparisons': comparisons,
           'source_sets': {k: len(v) for k, v in source_sets.items()},
           'incompatibilities': incompatibilities, 'record_schema': reference, 'problems': problems,
           'all_verified_and_compatible': not problems,
           'scope': 'Merged index of verified fixed-regulator records from several sites. Overlap differences are '
                    'grid/roundoff consistency diagnostics, not continuum error bounds. No fit, no C2.'}
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(out, indent=2, allow_nan=False) + '\n')
    cross = [c for c in comparisons if c['cross_site']]
    print(f'MERGED {len(records)} verified records from {len(a.site_dir)} site dirs; {len(comparisons)} comparisons '
          f'({len(cross)} cross-site); incompatibilities: {len(incompatibilities)}; problems: {len(problems)} -> {a.output}')
    for c in cross:
        print(f"  {c['classification']:12s} {c['sites']}: overlap N={c['overlap_N']} "
              f"max |diff| = {c['max_abs_raw_chain_difference']:.3e} {c['differing'] or ''}")
    for x in problems[:20]:
        print('  PROBLEM', x)
    if problems:
        sys.exit(1)


if __name__ == '__main__':
    main()
