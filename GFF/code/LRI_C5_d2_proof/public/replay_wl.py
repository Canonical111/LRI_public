#!/usr/bin/env python3
"""Optional replay of the Mathematica checks of LRI_C5_d2_proof (needs wolframscript and Mathematica 14 or 15; the
originals ran with Mathematica 15.0). Run: make -f public.mk replay-wl.

Each script runs unchanged in a work copy, one kernel at a time, wrapped as
`wolframscript -code 'Get["<script>"]; Quiet@CloseKernels[]; Exit[0]'` so that no kernel outlives it. The lines that
carry its results must equal the same lines of the shipped output.

  K2_selberg/laurent_K2.wl           cited by note l.5391: Laurent extraction, K2 - (32 Catalan^2 - 28 Zeta[3] Log[2]) = 0
  K2_selberg/jgamma_series.wl        J^Gamma series (the proof of the closed form of K2, note Section 18)
  drafter/check_series.wl            exact series checks; generating functions, moments, the twelve-term form at
                                     tau = 3/10 and C5(2) end to end (note l.5146-5148, 5451-5454; minutes)
  L2_structural/checks_all.wl        checks of the second L2 proof (rim-spoke reflection, note Section 18; minutes)
  review_L2_singlesums_numerics_r0/s3_modes.wl   jets and chain to 1e-82 (note l.5145-5146; long, cluster node;
                                     run only when named on the command line)
"""
import re, shutil, subprocess, sys, time
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
JOBS = [  # script, shipped output, regex selecting the result lines to compare
    ('K2_selberg/laurent_K2.wl', 'K2_selberg/laurent_K2.out', r'^(  tau\^|K2 |N\[K2|\[t\^2\]|\[tau\^)'),
    ('K2_selberg/jgamma_series.wl', 'K2_selberg/jgamma_series.out', r'\S'),
    ('drafter/check_series.wl', 'drafter/check_series.out',
     r'^(rho_|C_j|lambda_j|\(1/2\)|T\(1/2\)|log Q|B2|J\^Gamma|4\*|U\(1/2\)|P4\(2\)|L2 closed|K2 closed|J_\{2tau\}|J_1 = 3 Q2 check|P5|C5\(2\)|C4\(2\))'),
    ('L2_structural/checks_all.wl', 'L2_structural/checks_all.log', r'\S'),
    ('review_L2_singlesums_numerics_r0/s3_modes.wl', 'review_L2_singlesums_numerics_r0/s3.log', r'^(Lemma|Prop|Equivalent|x=1/2|check d_x)'),
]


def main():
    if not shutil.which('wolframscript'):
        print('wolframscript not found: replay-wl is optional and needs Mathematica'); return 2
    only = sys.argv[1:]
    fails = 0
    for script, ref, pat in JOBS:
        if (only and script not in only) or (not only and script.startswith('review_')):
            continue  # the long reviewer script runs only when named: replay_wl.py review_L2_singlesums_numerics_r0/s3_modes.wl
        src = PKG / script
        wd = PKG / 'public/out/work_wl' / src.stem
        if wd.exists():
            shutil.rmtree(wd)
        shutil.copytree(src.parent, wd, ignore=shutil.ignore_patterns('logs', '*.log', '*.out'))
        t0 = time.time()
        # wrapped so that no kernel or subkernel can outlive the run, whatever the script's own ending
        p = subprocess.run(['wolframscript', '-code', f'Get["{src.name}"]; Quiet@CloseKernels[]; Exit[0]'], cwd=wd,
                           capture_output=True, text=True)
        out = p.stdout
        (wd / (src.stem + '.new')).write_text(out + p.stderr)
        sel = lambda t: [l.rstrip() for l in t.splitlines() if re.search(pat, l) and 'Failed to open' not in l]
        new, old = sel(out), sel((PKG / ref).read_text())
        ok = p.returncode == 0 and new == old and len(old) > 0
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {script}: {len(new)} result lines {'equal' if new == old else 'differ from'} {ref} "
              f"({time.time() - t0:.0f} s, exit {p.returncode})")
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
