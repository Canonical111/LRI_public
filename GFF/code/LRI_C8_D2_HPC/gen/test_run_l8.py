#!/usr/bin/env python3
"""A-INV-1: an injected failing gate stops the J-GEN-2 pipeline (gen/run_l8.sh, run by slurm/gen/build_l8.slurm)
before publication. Pure logic, seconds.

The three steps of gen/run_l8.sh are replaced through its test hooks (C8_GEN_TEST_HOOKS=1): the build creates a
stage marker, the gate step fails (an injected failing gate: `exit 1`, or gen/gates.py's own refusal of an unknown
injection), and the publication would create the target. Checks: the script exits nonzero, the target does not
exist, and the publication step never started. Positive control: with a passing gate step the target is
published. Also: a builder that fails stops the script before the gates; an existing target or stage is refused.
Usage: python3 -B gen/test_run_l8.py [--output FILE]"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(td: Path, name: str, build: str, gates: str, publish: str, pre_target: bool = False, extra: dict | None = None) -> dict:
    stage, target = td / f'{name}_stage', td / f'{name}_inventory8_d2'
    if pre_target:
        target.mkdir()
    env = dict(os.environ, C8_PACKAGE=str(ROOT), C8_GEN_COMMIT='0' * 40, C8_GEN_BIN=str(td / 'bin'),
               C8_GEN_STAGE=str(stage), C8_GEN_TARGET=str(target), C8_GEN_THREADS='1', C8_GEN_TEST_HOOKS='1',
               C8_GEN_BUILD_CMD=build, C8_GEN_GATES_CMD=gates, C8_GEN_PUBLISH_CMD=publish, **(extra or {}))
    r = subprocess.run(['bash', str(ROOT / 'gen/run_l8.sh')], env=env, capture_output=True, text=True)
    return dict(rc=r.returncode, target_exists=target.exists(), log=r.stdout + r.stderr,
                published_marker=(td / f'{name}.published').exists())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--output', type=Path)
    a = ap.parse_args()
    results, failed = [], []

    def check(name: str, ok: bool, detail: str = '') -> None:
        results.append(dict(check=name, passed=bool(ok), detail=detail[-600:]))
        if not ok:
            failed.append(name)
        print(('PASS ' if ok else 'FAIL ') + name + (f': {detail[-300:]}' if detail and not ok else ''), flush=True)

    with tempfile.TemporaryDirectory(prefix='c8d2_run_l8_') as tdn:
        td = Path(tdn)

        def publish(name: str) -> str:
            return f'touch {td}/{name}.published && mkdir "$C8_GEN_TARGET"'

        r = run(td, 'inject', 'mkdir -p "$C8_GEN_STAGE/L8_free"', 'echo "gate k_forests: FAIL (injected)"; exit 1',
                publish('inject'))
        check('an injected failing gate stops the pipeline before publication',
              r['rc'] != 0 and not r['target_exists'] and not r['published_marker'] and 'step publish' not in r['log'],
              r['log'])
        r = run(td, 'gatespy', 'mkdir -p "$C8_GEN_STAGE"',
                f'{sys.executable} -B {ROOT}/gen/gates.py --stage "$C8_GEN_STAGE" --bin "$C8_GEN_BIN" '
                '--inject-fail no_such_gate', publish('gatespy'))
        check('a gates.py run that exits nonzero stops the pipeline before publication',
              r['rc'] != 0 and not r['target_exists'] and not r['published_marker'], r['log'])
        r = run(td, 'control', 'mkdir -p "$C8_GEN_STAGE/L8_free"', 'true', publish('control'))
        check('control: a passing gate step reaches publication', r['rc'] == 0 and r['target_exists']
              and r['published_marker'], r['log'])
        r = run(td, 'buildfail', 'exit 3', 'true', publish('buildfail'))
        check('a failing build stops the pipeline before the gates', r['rc'] == 3 and 'step gates' not in r['log']
              and not r['target_exists'], r['log'])
        # Stage-6 fix round 2 (Y2's defect class): no inherited OpenMP control reaches the steps (builders, gates)
        omp = td / 'omp.env'
        r = run(td, 'ompenv', f'env | grep -E "^(OMP|GOMP|KMP)_" | sort > {omp}; mkdir -p "$C8_GEN_STAGE"', 'true', publish('ompenv'),
                extra=dict(OMP_THREAD_LIMIT='1', OMP_DYNAMIC='true', GOMP_SPINCOUNT='0', KMP_AFFINITY='none'))
        seen = omp.read_text().split() if omp.exists() else None
        check('an inherited OMP_THREAD_LIMIT, OMP_DYNAMIC=true, GOMP_* or KMP_* never reaches a pipeline step',
              r['rc'] == 0 and seen == ['OMP_DYNAMIC=FALSE'], f'{seen} {r["log"]}')
        r = run(td, 'exists', 'true', 'true', publish('exists'), pre_target=True)
        check('an existing target is refused before any step', r['rc'] == 64 and 'step build' not in r['log'],
              r['log'])
    rec = dict(schema='c8-d2-gate-1', gate='A-INV-1 injected failing gate (gen/run_l8.sh)', passed=not failed,
               failed=failed, checks=results)
    if a.output:
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(json.dumps(rec, indent=1) + '\n')
    print(f'test_run_l8: {len(results) - len(failed)}/{len(results)} checks passed')
    return 0 if not failed else 1


if __name__ == '__main__':
    sys.exit(main())
