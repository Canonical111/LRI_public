# Reproduce integ_d1

Environment: Python >= 3.10 with mpmath, sympy, numpy (`requirements_integ_d1.txt`); `make test` also builds the C++
engine and the sector checker (g++ with OpenMP, `-march=x86-64-v3`) and needs bash. Run from `SRI/code/integ_d1/` (or
`make -C code/integ_d1 -f public.mk <target>` from `SRI/`). Nothing needs a cluster except the production rerun.
The shipped files are never modified: the verbatim tools run in a copy, `.work/<target>/run`, in their read-only modes.
Apart from `.work/`, only the temporary directories of `test_cluster.py` and `test_gates.py` are written (Python's
`tempfile`, i.e. `$TMPDIR`).

1. `make -f public.mk test` (about 4 min on 8 cores: 249 s on Intel Xeon 6148 and on AMD EPYC 7532; `THREADS=N` sets
   the engine threads):
   * `public/SNAPSHOT.sha256`: every exported project file against its sha256 at commit 8bd5a22 (files listed in
     `public/SCRUBBED.txt` by the public repository's scrub: presence only);
   * `public/git_blobs.json`: each blob id the git stand-in answers equals the git blob id of the shipped file it serves;
   * the sha256 of every registered record and of the six records of the note's App. I.8;
   * the engine built three ways and the checker once, with the verbatim `code/build_engine.sh` and `build_checker.sh`:
     the double (b0da6f7bc003c829) and double-double (06c88f4c378ed21d) builds of the f_301 runs must reproduce their
     production ids, and the delta^2 build of the f_202 runs, compiled from `public/historic/b2ab7c6/cluster_engine.cpp`,
     its id 5345fdf1bcec7a5a (an id is the sha256 of the sources and the compile command, so equal ids mean equal
     sources and flags, not equal compilers);
   * `code/test_cluster.py` (engine regression tests), `code/test_gates.py` (every gate's negative and positive tests,
     through the git stand-in), `code/test_two_bubble.py` (the two-bubble integrator of M2 against the exact Bethe
     ansatz at K = 0.3, below 1e-9);
   * a few sectors of four production chunks (fine and radius levels, complex K, f_202) rerun from the arguments in
     their headers, with the n = 4 input regenerated and checked against its manifest hash; every coefficient is
     compared with the shipped output at 40 digits: |rerun - shipped| <= 4 eps B (B the engine's first-order magnitude
     bound of that coefficient, |value| for the f_202 runs, which carry no bounds); the number of bitwise-identical
     values is printed (all of them for the double build). The double-double production outputs are heavy sectors
     (minutes each even on 40 cores) and are not rerun; the double-double build is tested by `test_cluster.py`, and
     `replay` checks every shipped override against the double output within the double roundoff bound (the gate).
     PASS/FAIL table in `.work/selftest_integ_table.txt`.
2. `make -f public.mk replay` (about 1.5 min on one core: 78 s Intel, 85 s AMD): in `.work/replay/run`, with `public/gitstub.py` as `git`,
   * `builds.py`; `m1_gate.py`; `m2_gate.py --stage2` and `m3_gate.py --stage2` (records regenerated from their engine
     outputs, byte-identical, sidecars, then C3..C7 against their closed forms at 1e-20); `m4a_gate.py --dry`;
     `m4b_gate.py --verify` (the three runs, the overrides and both validation samples; record and sidecar);
     `m4b_cx_check.py --amended --verify` and, without `--amended`, the original criterion (fails on K_B, as recorded);
     `m3_sector_check.py --verify-record` (3); `cluster_check.py 3` (three bubbles against the exact cluster);
     `c8_assemble.py --verify` and `--compare` (text equal to `results/C8_comparison.txt`);
   * every number of the note's App. I (`results_map.md`), with the note's TeX checked for each printed string;
   * \SRCeightMag, \SRintegClosedDev and \SRCeightMagDiff against `../../results/quoted_numbers.json`.
   PASS/FAIL table in `.work/replay_integ_table.txt`.
3. `make -f public.mk replay-full` prints the production rerun (`public/REPLAY_FULL.md`): about 1.6e4 core-hours of
   engine time on symmetry-class nodes, then the gates of step 2 without their read-only flags.
4. `make -f public.mk fetch-data`: nothing is hosted elsewhere.

Tolerances. Records: byte identity (sha256). Printed numbers: half-up rounding to the printed precision; 25-digit table
entries: decimal equality with the record; "to 10^-n": the value in [10^(-n-1/2), 10^(-n+1)). Engine reruns: 4 eps B
per coefficient. The verbatim gates apply their own thresholds (1e-20 for C3..C7 in M2/M3, 1e-6 for delta^0 of f_301,
1e-7 relative for its relations, 0.37 for its total error, sigma(C8) <= 0.3) and must pass.

## Decisions you must not make
* The uncertainty 0.131 is the linear sum fixed in the plan (3/4 x sigma(f_301) + 2 x sigma(f_202) + the rest), with
  sigma(f_301) = |fine - coarse| + |fine - radius| + validated roundoff. Do not combine in quadrature or call it a
  standard deviation; the comparison is stated as differences and ratios to stated uncertainties.
* The amendments A and B were decided by the author after seeing the data and are disclosed (REVIEWS.md). Do not
  present the second records as if the original criteria had passed; the first records ship and stay frozen.
* The session that ran the computation was exposed to the comparison before the error bar was evaluated
  (REVIEWS.md, Disclosures). The central value was frozen before.
* The calculation supports the compendium's C8 record within 0.13 and the prescription's closed forms C3..C7; it does
  not prove them, and at 5e-4 relative it cannot identify the zeta-value form of C8.
