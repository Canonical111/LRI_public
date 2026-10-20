#!/usr/bin/env python3
"""Re-execute the review's check scripts in a fresh copy (<work>/checks) and record exit status and runtime.

The review did not record its command lines; the list below is reconstructed from the names of its recorded
outputs (e.g. gvals_mb_50.out comes from `gvals_mb.py 50`). The shipped scripts are copied unchanged, except
that the two assemble.py scripts read the package reassembly from the environment variable C6_REASSEMBLY
instead of the absolute path of the review machine (a one-line rewrite in the copy only).
Afterwards run  public/verify_review.py replay --records <work>/checks  (public.mk target `rerun` does both).
Needs mpmath, sympy, numpy and scipy. Expected total: 10 to 25 min on one core (personal desktop), memory < 2 GB.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True   # never write __pycache__ into the shipped tree

COMMANDS = {
    'reduced_input': [
        ('test_tools.py', [], 'test_tools.log'),
        ('ordinary.py', [], 'ordinary.log'),
        ('wheel.py', [], 'wheel.log'),
        ('m7.py', [], 'm7.log'),
        ('polylog.py', [], 'polylog.log'),
        ('primitive.py', [], 'primitive.log'),
        ('primitive_dps95.py', [], 'primitive_dps95.log'),
        ('extras.py', [], 'extras.log'),
        ('meijer.py', [], 'meijer.log'),
        ('assemble.py', [], 'assemble.log'),
    ],
    'final_values': [
        ('sidechecks.py', [], 'sidechecks.out'),
        ('polylog.py', [], 'polylog.out'),
        ('kernelchecks.py', [], 'kernelchecks.out'),
        ('gvals_mb.py', ['25'], 'gvals_mb_25.out'),
        ('gvals_mb.py', ['50'], 'gvals_mb_50.out'),
        ('gvals_meijerg.py', ['20'], 'gvals_meijerg_20.out'),
        ('gvals_meijerg.py', ['12', 'G6,G8'], 'gvals_meijerg_12.out'),
        ('series.py', ['30'], 'series_30.out'),
        ('series.py', ['45'], 'series_45.out'),          # leaves series_out.json at 45 digits, as recorded
        ('reduced1d.py', ['25'], 'reduced1d_25.out'),
        ('reduced1d.py', ['40'], 'reduced1d_40.out'),
        ('primitive1d.py', ['30'], 'primitive1d_30.out'),
        ('primitive1d.py', ['40'], 'primitive1d_40.out'),
        ('h2d_trap.py', ['HW'], 'h2d_trap_HW.out'),
        ('h2d_trap.py', ['H7'], 'h2d_trap_H7.out'),
        ('h2d_trap.py', ['HP', '0.5:0.025:34', '0.08:0.02:34'], 'h2d_trap_HP_b.out'),
        ('h2d_trap.py', ['HP', '0.0:0.05:34', '0.0:0.025:34', '0.0:0.0125:34', '0.03:0.0125:34'], 'h2d_trap_HP_tau0.out'),
        ('h2d_nested.py', [], 'h2d_nested.out'),
        ('assemble.py', [], 'assemble.out'),
        ('hlists.py', [], 'hlists.out'),
        ('bounds.py', [], 'bounds.out'),
    ],
    'algebra': [(f, [], f.replace('.py', '.log')) for f in
                ['s1_basics.py', 's2_polylog_kernels.py', 's3_ordinary.py', 's4_wheel_exact.py', 's5_wheel_num.py',
                 's6_wheel2.py', 's7_seventh.py', 's7b.py', 's8_prim_exact.py', 's9_prim_num.py', 's9b.py', 's9c.py',
                 's10_wheelcert.py', 's11_euler_rec.py', 's12_assembly.py', 's13_inner2.py', 's13b.py']],
    '.': [('c6_repair.py', [], 'c6_repair.log')],
}
# Scripts of the review that end with a known error after printing all their checks. s7_seventh.py's last line calls
# cot(), which checks/algebra/common.py never imports, so it stops with this NameError in every environment (found by
# C71d on a personal desktop, 2026-10-13). Such a run counts as ok only if the last line of its output is this error (Python 3.10+
# appends ". Did you mean: 'cos'?").
KNOWN_FINAL_ERROR = {'s7_seventh.py': "NameError: name 'cot' is not defined"}
PATH_RE = re.compile(r"open\('[^']*C6_research_note/outputs/reassembly\.json'\)")


def main():
    work = Path(sys.argv[1] if len(sys.argv) > 1 else PKG / '.work').resolve()
    reas = os.environ.get('C6_REASSEMBLY') or str((PKG / '../C6_research_note/outputs/reassembly.json').resolve())
    if not Path(reas).is_file():
        sys.exit(f'package reassembly not found: {reas} (set C6_REASSEMBLY)')
    dst = work / 'checks'
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(PKG / 'checks', dst, ignore=shutil.ignore_patterns('__pycache__', '.DS_Store'))
    for p in dst.rglob('*'):            # every recorded .json/.out/.log is an output: start from none of them
        if p.suffix in ('.json', '.out', '.log'):
            p.unlink()
    for sub in ('reduced_input', 'final_values'):
        p = dst / sub / 'assemble.py'
        s, n = PATH_RE.subn("open(__import__('os').environ['C6_REASSEMBLY'])", p.read_text())
        if n != 1:
            sys.exit(f'{p}: expected one reassembly path, found {n}')
        p.write_text(s)
    env = dict(os.environ, C6_REASSEMBLY=reas, PYTHONDONTWRITEBYTECODE='1', MPLBACKEND='Agg')
    log, failed = [], 0
    for sub, cmds in COMMANDS.items():
        for script, args, out in cmds:
            t0 = time.monotonic()
            with open(dst / sub / out, 'w') as fh:
                rc = subprocess.run([sys.executable, script, *args], cwd=dst / sub, env=env, stdout=fh,
                                    stderr=subprocess.STDOUT).returncode
            dt = time.monotonic() - t0
            known = KNOWN_FINAL_ERROR.get(script); raw = rc
            if rc != 0 and known and (dst / sub / out).read_text().rstrip().splitlines()[-1].startswith(known):  # Python >= 3.10 appends a hint
                print(f'known final error of {script} (all checks printed before it): {known}', flush=True)
                rc = 0
            failed += rc != 0
            log.append(dict(folder=sub, command=[script, *args], output=out, returncode=raw, accepted_known_final_error=raw != rc,
                            seconds=round(dt, 1)))
            print(f'{"ok " if rc == 0 else "ERR"} {sub}/{script} {" ".join(args)} -> {out}  {dt:.1f} s', flush=True)
    (work / 'rerun_checks.json').write_text(json.dumps(dict(python=sys.version, reassembly=reas, runs=log,
                                                            failed=failed), indent=1) + '\n')
    print(f'{len(log)} commands, {failed} failed; outputs in {dst}')
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
