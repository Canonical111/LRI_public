# lri_dressed_phi4_independent_check: blind re-implementation of the d = 1 finite-coupling HT

This is a separately written solver for the same model as `../lri_dressed_phi4_hpc`. A Claude Code subagent wrote it
on 2026-10-08 from the definition of the model. It was not allowed to read the production code, results or analysis:
it read only the "Definition" section of the window documentation and the "Hamiltonian" section of the algorithm
notes, and derived H itself from the GFF radial quantization (`DERIVATION.md`). The Supplementary Material
names it among the independent recomputations (opening section "AI agents and reproducibility"); its numbers are in
the HT note, Section "Independent checks".

**Own method.**

- The zero mode is on a sinc-DVR grid instead of an oscillator basis.
- It builds its own bath Fock space.
- It implements literal and consistent windows.
- It runs Newton tuning continued from weak coupling.
- Every point is verified on 1.5× finer and 1.5× wider grids.

**Result.**

- **Production comparison.** 38 points: raw and consistent at Ds = 0.249, 0.2, 0.1, 0.05, 0.025 and 0.01 with
  N = 12, 16, 20, plus literal at Ds = 0.2 and 0.1 with N = 12. Delta_eps agrees with production to ≤ 1.3e-9 where
  production used nz 48 (or Ds ≥ 0.2), and to ≤ 4.8e-9 where it used nz 24/32. The latter gap is production's
  zero-mode truncation.
- **Weak coupling.** Delta_eps = 1/2 − eps/6 + C2(N) eps^2 is reproduced, with C2(N) equal to the exact rational
  formula to ≤ 3e-7 for N = 0..16.

The check verifies that production solves the stated model. It says nothing about the model's continuum limit.

## Targets (run from `HT/code/lri_dressed_phi4_independent_check`)

| Command | What | Time |
|---|---|---|
| `make -f public.mk test` | `tests/test_indep_ht.py`, 64 unit checks | a few minutes, one core |
| `make -f public.mk replay` | `public/replay_indep.py`, four steps below | about 10 s |
| `make -f public.mk smoke` | Reruns one point (Ds = 0.2, N = 12, raw) and compares it to 1e-10 | 1–2 min |

What `replay` does:

1. Rebuilds `results/indep_results.json` from `results/raw_runs/` with the shipped `analyze.py`.
2. Rebuilds the production reference from `../../data/HT_1d`.
3. Recomputes the agreement: 1.3e-9 and 4.8e-9, giving the 5e-9 quoted in the paper.
4. Recomputes the C2(N) check: ≤ 3e-7.

**Files.**

- `indep_ht.py`: the solver.
- `analyze.py`: merges the per-task outputs and runs the C2 fits.
- `make_tasks.py`, `tasks/`: the run inputs.
- `slurm/`: job scripts (site values replaced by placeholders).
- `retune_check.py`: full retuning on altered grids.
- `REPORT.md`: the subagent's report, with the host's comparison.
- `results/`.

Production cost: about 3 h on one symmetry node (jobs 571688 and 571710).
