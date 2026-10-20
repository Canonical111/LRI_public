# Reproduce c2_closed_d2

Environment: Python >= 3.10 with mpmath, sympy, numpy, scipy, matplotlib (`requirements_c2_closed_d2.txt`; the study
pins mpmath 1.3.0, sympy 1.14.0, numpy 2.3.5, scipy 1.17.0, matplotlib 3.10.8 in its own `requirements.txt`). For the
Monte Carlo rerun: a C compiler with libquadmath (gcc). Run everything from `SRI/code/c2_closed_d2/`.

1. `make -f public.mk test` (seconds): the snapshot sha256 list (`public/SNAPSHOT.sha256`); the study's own verifier
   `code/verify_package.py` (its `MANIFEST.json`; files listed in `public/SCRUBBED.txt`, whose private paths were replaced by
   placeholders at publication, count by presence: run alone, `verify_package.py` reports them as changed); the closed form of the appendix at 50 digits against
   `outputs/summary.json`; the verbatim three-4F3 evaluator rerun in a copy (byte-identical output); the Monte Carlo
   chunk inventory and the recombination to -4.075 +- 0.019.
2. `make -f public.mk replay` (about 1 min on one core): the study's eight-stage runner `code/reproduce.py` in a copy of
   `code/` and `inputs/` (about 30 s); every output compared with the shipped one; every constant of the appendix
   subsection cf:sec:cr2 at 50 digits (exact relations, R_Gamma, P, Q, T with an independent summation, c_2, and the
   note's b_0, I, B_31, z_41, J(0), Omega_4(0)); the verbatim `mc/summ.py` on the chunks of each configuration against
   the lines of the production logs; the recombination and the review's numbers; `\SRtwoCtwo`, `\SRtwoCtwoMC` and the
   d = 2 row of tab:sr. PASS/FAIL table in `.work/replay_c2_closed_d2.txt`; exit status non-zero on any FAIL.
3. Optional, the study's own steps: `python code/verify_package.py` (before any rerun), `python code/reproduce.py`
   (rewrites `outputs/` in place: run it in a copy), `python code/build_note.py` (rebuilds the study's own note,
   which is not shipped; it fails without `note/`). The derivation is in the SRI note, Appendix E.
4. Monte Carlo rerun (cluster).
   - `make -f public.mk rerun-mc-smoke` (under a minute): builds `mc/c2mc3.c` with `-DUSE_QUAD` in `.work/` and runs one
     chunk of 2e6 samples with the weights of run A. A build and run check, not a reproduction.
   - `make -f public.mk mc-batch-check` (about 3 min, gcc with libquadmath, an x86-64-v3 CPU): builds `mc/c2mc3.c` with
     the production flags and reruns the first batch (1.5e7 samples) of chunk 1 of configuration A; its three
     histogram lines must match `mc/run_A/out_1.txt` (equal to the printed 10 digits, or within 1e-8 of the line's
     largest entry). This ties the shipped code to the shipped chunks: bitwise identical on an AMD EPYC 7532 node (runs A, B
     ran on AMD EPYC nodes of symmetry), within 1.6e-11 of the largest entry on Intel Xeon 6148 (2026-10-15).
   - Production: `mc/prod.sbatch` (one node per configuration; usage line in the file; it compiles with
     `gcc -O2 -march=x86-64-v3 -DUSE_QUAD`, adapts the channel weights when no weight file is given, and starts one
     chunk per core). The three production configurations (from the chunk headers):
     A: `sbatch prod.sbatch A 0.05 0.35 300000000 1000 alpha_e0.05_L16_k35.txt` (64 chunks, seeds 1001..1064);
     B: `sbatch prod.sbatch B 0.1 0.35 300000000 5000` (64 chunks, seeds 5001..5064, weights adapted at start);
     C: `mc/prodC.sbatch` (14 chunks, eta 0.07, KAP 0.2, seeds 9001..9014, weights adapted at start).
     Edit the partition and the paths (placeholders) first. Measured cost: A 49 min, B 61 min on a 64-core AMD EPYC
     node of symmetry, C 74 min on 14 cores of a personal desktop: about 135 core-hours in all. Then
     `python3 summ.py run_X/out_*.txt` per configuration and the recombination of `public/c2lib.py`
     (`make -f public.mk replay` on the new chunks). A rerun gives a statistically equivalent, not identical, result
     unless the same binary, weights and seeds are used.

## Decisions you must not make

- The cut Lambda > -15 of the quoted Monte Carlo value and the inverse-variance combination of the three
  configurations (the review's rule; the replay shows the plateau over the other cuts as INFO).
- The map from the Monte Carlo integral to c_2 (z_41 = Omega_4/32 + b_0 B_31 with the Gaussian-source B_31) and the
  prescription of the closed form (critically tuned analytic minimal subtraction): both are part of the result.
- The tolerances of the replay: 1e-45 for the 50-digit evaluation, 1e-40 for decimal strings of the rerun, 1e-9
  relative for floats from numpy quadrature, the rounding of the macro text.
