#!/usr/bin/env python3
"""Replay of the C8(2) tail screen and the per-stratum variance analysis from the full group tables (make -f public.mk
replay-tails; needs `make -f public.mk fetch-data`, DATA.md part (a): the production's graph tables, 2.7 GB, its ledger and lane
logs, and the exact pilot's campaign records).

Steps, each with the package's own unmodified tools at the production commit:
  1. production.validate_merged on all 24 production groups and all 24 pilot groups: every graph_replicates.csv,
     graph_tails.csv and graph_costs.csv at the sha256 its merged.json pins (the check `replay` skips);
  2. tools/design.py report --pilot <production batch> with the caps raised as in job 571296 (at this commit the
     report's hypothetical-design table refuses a production batch under the default caps; fixed later in aafa8a4,
     which does not change the tails), run as --test-only with --eta-node set to the published efficiency
     (results/C8_2/production/accounting.json, eta_node 0.98256...): a production-mode report takes eta_node from the
     cluster's Slurm accounting (sacct over the campaign's ledger and every checkpoint), which only the cluster has;
     eta_node enters the report's cost columns, not the tail statistics (the production-mode report on the full
     campaign directory, with sacct, writes the same table). The tail table tails.csv must equal the published one
     (results/C8_2/production/tails.csv.gz, decompressed sha256 8039682a...) in every row and column, with xi_hat and
     largest_share to relative 1e-9: other numpy and BLAS builds change the last digit of xi_hat in about half the rows;
  3. benchmarks/symmetry_2026-10-c8/production/result/scripts/pr_result_analysis.py (the post-production analysis of
     job 571287) on the production batch and the pilot: its `tails` and `variance` blocks must equal
     results/C8_2/production/analysis.json (counts exactly; floats to relative 1e-9: the same numpy arithmetic on the
     same tables; only BLAS summation order differs), which gives the 27.6% share and the realized/predicted variances.
Outputs go to public/out/tails/ (the tools write there, never into the data). PASS/FAIL table on stdout,
public/out/replay_tails.json, exit 1 on any FAIL.
Data (fetch-data): the production's graph tables, its ledger and lane logs (submissions.jsonl, slurm_logs/lane-*.log, user
and node names scrubbed; the report reads the ledger, the analysis the lane logs), and the pilot's records.
Expected run time: about 10-15 min and 8 GB of memory on one node (job 571296: 5:05 for step 2 and the follow-up on
8 cores; job 571287: 9:18 including the combine).
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import subprocess
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG / 'tools'))
import production as prod  # noqa: E402

RUN_NAME = 'prod1-2.5e-4-ddmp256-20261006-ba68f401e46e'
PILOT_NAME = 'pilot1-20261006-ba68f401e46e'
CAPS = ['--max-checkpoints', '100000000', '--max-tasks', '2000000000']
ROWS = []
TAIL_FLOATS = ('xi_hat', 'largest_share')


def compare_tails(got: bytes, want: bytes):
    """(rows, rows outside the tolerance, largest relative difference) of two tail tables: same header and row order,
    every column equal as text except the floats TAIL_FLOATS, which must agree to relative 1e-9 (or be equal as text)."""
    g, w = got.decode().splitlines(), want.decode().splitlines()
    if not g or g[0] != w[0] or len(g) != len(w):
        return len(w) - 1, max(len(w) - 1, 1), float('inf')
    head = w[0].split(',')
    fl = {head.index(c) for c in TAIL_FLOATS}
    bad, worst = 0, 0.0
    for lg, lw in zip(g[1:], w[1:]):
        a, b = lg.split(','), lw.split(',')
        ok = len(a) == len(b)
        for i, (x, y) in enumerate(zip(a, b)):
            if x == y:
                continue
            if i not in fl:
                ok = False
                continue
            try:
                fx, fy = float(x), float(y)
            except ValueError:
                ok = False
                continue
            d = abs(fx - fy) / max(abs(fx), abs(fy))
            worst = max(worst, d)
            ok = ok and d <= 1e-9
        bad += not ok
    return len(w) - 1, bad, worst


def row(name, got, want, ok, note=''):
    ROWS.append(dict(check=name, got=got, expected=want, status='PASS' if ok else 'FAIL', note=note))


def sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def tables(run: Path) -> None:
    data = (run / 'manifest.json').read_bytes()
    m, mh = json.loads(data), sha_bytes(data)
    bad = []
    for g in m['groups']:
        try:
            p, cfg = prod.group_of(run, m, g['name'])
            prod.validate_merged(p, cfg, m, mh)
        except Exception as e:  # noqa: BLE001
            bad.append(f'{g["name"]}: {e}')
    row(f'{run.name}: production.validate_merged on {len(m["groups"])} groups (graph tables at their pinned sha256)',
        f'{len(bad)} bad', '0 bad', not bad, '; '.join(bad[:3]))


def close(a, b, path='', bad=None, rtol=1e-9):
    bad = [] if bad is None else bad
    if isinstance(b, dict):
        if not isinstance(a, dict) or set(a) != set(b):
            bad.append(f'{path}: keys differ')
            return bad
        for k in b:
            close(a[k], b[k], f'{path}.{k}', bad, rtol)
    elif isinstance(b, list):
        if not isinstance(a, list) or len(a) != len(b):
            bad.append(f'{path}: length differs')
            return bad
        for i, (x, y) in enumerate(zip(a, b)):
            close(x, y, f'{path}[{i}]', bad, rtol)
    elif isinstance(b, float) and isinstance(a, (int, float)) and not isinstance(a, bool):
        if abs(a - b) > rtol * max(abs(b), 1e-300) and abs(a - b) > 1e-15:
            bad.append(f'{path}: {a!r} vs {b!r}')
    elif a != b:
        bad.append(f'{path}: {a!r} vs {b!r}')
    return bad


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--data', type=Path, default=PKG / '../../data/C8_2')
    ap.add_argument('--results', type=Path, default=PKG / '../../results/C8_2')
    ap.add_argument('--out', type=Path, default=PKG / 'public/out')
    ap.add_argument('--python', default=sys.executable)
    a = ap.parse_args()
    run, pilot, res = (a.data / RUN_NAME).resolve(), (a.data / PILOT_NAME).resolve(), a.results.resolve()
    out = (a.out / 'tails').resolve()
    out.mkdir(parents=True, exist_ok=True)
    for d in (run, pilot):
        missing = [g for g in (d / 'groups').iterdir() if g.is_dir() and not (g / 'graph_replicates.csv').is_file()] if (d / 'groups').is_dir() else [d]
        if missing:
            print(f'{d}: graph tables missing (run make -f public.mk fetch-data; see ../../data/C8_2/DATA.md)', file=sys.stderr)
            return 2
    tables(run)
    tables(pilot)
    env = {'OPENBLAS_NUM_THREADS': '1', 'PATH': '/usr/bin:/bin', 'PYTHONDONTWRITEBYTECODE': '1'}
    # 2. the tail report
    for f in ('report.json', 'tails.csv'):
        (out / f).unlink(missing_ok=True)
    eta = json.loads((res / 'production/accounting.json').read_text())['eta_node']
    r = subprocess.run([a.python, '-B', 'tools/design.py', 'report', '--pilot', str(run), *CAPS, '--test-only', '--eta-node', repr(eta),
                        '--json', str(out / 'report.json'), '--tails-out', str(out / 'tails.csv')], cwd=PKG, capture_output=True, text=True, env=env)
    (out / 'report.txt').write_text(r.stdout + r.stderr)
    row(f'tools/design.py report --pilot <production batch> --test-only --eta-node {eta:.5f} (caps raised as in job 571296)',
        f'exit {r.returncode}', 'exit 0', r.returncode == 0)
    if r.returncode == 0:
        got = (out / 'tails.csv').read_bytes()
        want = gzip.open(res / 'production/tails.csv.gz').read()
        nrows, bad, worst = compare_tails(got, want)
        row('tails.csv = the published table: every row and column; xi_hat and largest_share to relative 1e-9',
            f'{bad} of {nrows} rows outside (max relative difference {worst:.1e})', f'0 of {nrows} rows outside', bad == 0,
            'byte for byte' if got == want else f'not byte for byte ({sha_bytes(got)[:16]} vs {sha_bytes(want)[:16]}): last-digit '
            'differences of xi_hat (numpy and BLAS builds differ from the production environment)')
    # 3. the post-production analysis
    ana = PKG / 'benchmarks/symmetry_2026-10-c8/production/result/scripts/pr_result_analysis.py'
    (out / 'analysis.json').unlink(missing_ok=True)
    r = subprocess.run([a.python, '-B', str(ana), '--package', str(PKG), '--run', str(run), '--pilot', str(pilot), '--accounting',
                        str(res / 'production/accounting.json'), '--out', str(out / 'analysis.json')], cwd=PKG, capture_output=True,
                       text=True, env=env)
    (out / 'analysis.txt').write_text(r.stdout + r.stderr)
    row('pr_result_analysis.py (job 571287\'s analysis) on the production batch and the pilot', f'exit {r.returncode}', 'exit 0', r.returncode == 0)
    if r.returncode == 0:
        got, want = json.loads((out / 'analysis.json').read_text()), json.loads((res / 'production/analysis.json').read_text())
        for block in ('tails', 'variance'):
            bad = close(got[block], want[block], block)
            row(f'analysis.json {block} block = published (counts exact, floats relative 1e-9)', f'{len(bad)} differences', '0 differences',
                not bad, '; '.join(bad[:3]))
        th = got['tails']['threat']
        share = 100 * (th['free_L8']['confirmed_share_of_C8_variance'] + th['power_L8']['confirmed_share_of_C8_variance'])
        row('confirmed graphs\' share of Var C8(2) (%; note prints 27.5, erratum)', f'{share:.1f}', '27.6', f'{share:.1f}' == '27.6')
        row('confirmed graphs (all, free, power)', (got['tails']['production_confirmed_total'], *got['tails']['production_confirmed_by_sector'].values()),
            (4832, 4631, 201), (got['tails']['production_confirmed_total'], got['tails']['production_confirmed_by_sector']['free'],
                                got['tails']['production_confirmed_by_sector']['power']) == (4832, 4631, 201))
    (a.out / 'replay_tails.json').write_text(json.dumps(dict(rows=ROWS), indent=1, default=str) + '\n')
    for x in ROWS:
        print(f"{x['status']:4}  {x['check']}  {x['got']}  (expected {x['expected']})" + (f"  {x['note']}" if x['note'] else ''))
    fails = sum(x['status'] == 'FAIL' for x in ROWS)
    print(f'\n{len(ROWS) - fails} PASS, {fails} FAIL')
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
