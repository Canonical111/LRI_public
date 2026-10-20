#!/usr/bin/env python3
"""Run only the selected tasks used by the final-method note.

The underlying stage code is unchanged. Work takes place in disposable
copies, while actual execution records are collected under outputs/rerun/.
"""
from __future__ import annotations
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXACT = [
    'wheel_exact', 'seventh_central_exact', 'cubic_exact', 'even_exact',
    'standard_primitive_exact', 'sixth_exact', 'eighth_exact', 'lower_exact',
    'compact_primitive_exact', 'single_wheel_exact',
    'seventh_barnes_exact', 'unit_slope_exact',
]

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--timeout', type=int, default=180)
    parser.add_argument('--resume', action='store_true', help='Keep already-passed task records.')
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error('--timeout must be positive')
    commands = [
        ['--profile', 'core'],
        ['--profile', 'exact', '--only', *EXACT],
        ['--profile', 'numerical'],
    ]
    statuses = []
    for selection in commands:
        cmd = [sys.executable, str(ROOT/'code/reproduce.py'), *selection,
               '--timeout', str(args.timeout)]
        if args.resume:
            cmd.append('--resume')
        result = subprocess.run(cmd, cwd=ROOT, check=False)
        statuses.append({'arguments': selection, 'exit_status': result.returncode})
        if result.returncode:
            break
    report = {
        'scope': 'Selected supplied-code tasks for the final real-valued method; not a new graph/RG derivation.',
        'expected_tasks': 22,
        'exact_task_ids': EXACT,
        'resume_requested': args.resume,
        'profile_execution_status': statuses,
        'all_profiles_passed': len(statuses)==3 and all(s['exit_status']==0 for s in statuses),
    }
    out = ROOT/'outputs/final_method_run.json'
    out.write_text(json.dumps(report, indent=2)+'\n')
    return 0 if report['all_profiles_passed'] else 1

if __name__ == '__main__':
    raise SystemExit(main())
