#!/usr/bin/env python3
"""Driver for the direct finite-cutoff campaign (runs inside a Slurm allocation).

  python3 run_campaign.py gauss main  results/gauss_main.jsonl
  python3 run_campaign.py gauss n8    results/gauss_n8.jsonl
  python3 run_campaign.py qmc   -     results/qmc.jsonl  [--workers 64] [--log2 22 --reps 16]

Resumable: tasks whose key is already in the output file are skipped.
"""
import argparse
import concurrent.futures as cf
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import plan  # noqa: E402


def done_keys(path):
    keys = set()
    if os.path.exists(path):
        with open(path) as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        keys.add(json.loads(line)['key'])
                    except Exception:
                        pass
    return keys


def run_gauss(group, out, binary, kind=None):
    tasks = plan.gauss_tasks(group)
    if kind:
        tasks = [t for t in tasks if t['kind'] == kind]
    # cheap first: estimated cost N^(n-1) (x N0/N for form 1)
    def cost(t):
        c = float(t['N']) ** (t['n'] - 1)
        if t['form'] == 1:
            c *= t['N0'] / t['N']
        return c * (1 + t['ord'])
    tasks.sort(key=cost)
    have = done_keys(out)
    print('gauss group %s: %d tasks, %d already done' % (group, len(tasks), len(have & {plan.task_key(t) for t in tasks})), flush=True)
    for t in tasks:
        key = plan.task_key(t)
        if key in have:
            continue
        cmd = [binary, '-n', str(t['n']), '-k', t['kind'], '-e', repr(t['eps']), '-f', str(t['form']),
               '-o', str(t['ord']), '-N', str(t['N']), '-N0', str(t['N0'])]
        if t['E']:
            cmd.append('-E')
        t0 = time.time()
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            print('FAILED', key, res.stderr, flush=True)
            continue
        d = json.loads(res.stdout)
        d['key'] = key
        d['cmd'] = ' '.join(cmd)
        with open(out, 'a') as fh:
            fh.write(json.dumps(d) + '\n')
        print('%s  %.1fs' % (key, time.time() - t0), flush=True)


def one_qmc(t, log2, reps):
    cmd = [sys.executable, os.path.join(HERE, 'qmc_check.py'), '-n', str(t['n']), '-k', t['kind'],
           '-e', repr(t['eps']), '-o', str(t['ord']), '--log2', str(log2), '--reps', str(reps), '--map', t['map']]
    if t['E']:
        cmd.append('-E')
    env = dict(os.environ, OMP_NUM_THREADS='1', MKL_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1')
    res = subprocess.run(cmd, capture_output=True, text=True, env=env)
    return t, cmd, res


def run_qmc(out, workers, log2, reps):
    tasks = plan.qmc_tasks()
    have = done_keys(out)
    todo = [t for t in tasks if plan.qmc_key(t) not in have]
    todo.sort(key=lambda t: -t['n'])  # longest first
    print('qmc: %d tasks, %d to do' % (len(tasks), len(todo)), flush=True)
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(one_qmc, t, log2, reps) for t in todo]
        for f in cf.as_completed(futs):
            t, cmd, res = f.result()
            if res.returncode != 0:
                print('FAILED', plan.qmc_key(t), res.stderr[-2000:], flush=True)
                continue
            d = json.loads(res.stdout)
            d['key'] = plan.qmc_key(t)
            d['cmd'] = ' '.join(cmd)
            with open(out, 'a') as fh:
                fh.write(json.dumps(d) + '\n')
            print('%s  %.1fs' % (d['key'], d['seconds']), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', choices=['gauss', 'qmc'])
    ap.add_argument('group')
    ap.add_argument('out')
    ap.add_argument('--binary', default=os.path.join(HERE, 'direct_moments'))
    ap.add_argument('--workers', type=int, default=os.cpu_count())
    ap.add_argument('--log2', type=int, default=22)
    ap.add_argument('--reps', type=int, default=16)
    ap.add_argument('--kind', default=None, help='restrict gauss tasks to one kind (A, Z or Q)')
    a = ap.parse_args()
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    if a.mode == 'gauss':
        run_gauss(a.group, a.out, a.binary, a.kind)
    else:
        run_qmc(a.out, a.workers, a.log2, a.reps)


if __name__ == '__main__':
    main()
