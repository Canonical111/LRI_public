# lri_3d_window_indep: a separately written solver for the d = 3 window HT

A clean-room re-implementation of the finite model that `../lri_3d_window_hpc` solves: the dressed zero-mode
truncation on S² × ℝ with the vacuum window. It was written from the method description only, without reading or
importing the production code. It checks that the production code computes the stated model (HT note, d = 3
checks: 2×10⁻¹¹ at N ≤ 12, macro `\HTnpDthreeIndep`). It does not test whether the model's limit is the CFT.

Deliberately different choices from the production code:
- a complex Condon–Shortley Y_lm Fock space with all magnetic sectors;
- the J = 0 bath space from the null space of the Casimir J₋J₊ (dense eigh per species block), not an SVD null space;
- scalar vertices ⟨:χᵏ:⟩ evaluated at a generic sphere point and checked at a second one;
- the zero mode in a plain number-state basis, truncated to its K lowest local eigenstates (no trained density basis);
- window fixed points by bracketed Brent root finding;
- tuning by `scipy.optimize.root`.

## Files (as they ran; verbatim)

| file | role |
|---|---|
| `indep_ht3d.py` | the solver: modes, Fock space, J = 0 projection, vertices, local basis, window, `Model.solve`, `Model.tune` |
| `indep_spin.py` | J = 1, 2 sectors (descendant diagnostics) |
| `run_compare.py` | one comparison: production (r, g) at K = 16 and 24, then independent tuning from a start displaced by 2% |
| `t_fixed.py`, `t_spin.py` | the session's quick checks at fixed couplings (scalar, J = 1, 2); a third, `t_basic.py`, is not shipped (it read a local file by an absolute path), and `public/test_indep.py` runs its checks |
| `indep_extract.json` | the production values (r, g, ΔE, gaps, window energies) of 181 records, extracted on 2026-10-08; replay checks every value it uses against the shipped records |
| `results/cmp_L*_*.json` | the 23 comparisons quoted (N = 8, 10, 12; window and raw) |
| `tasks.txt`, `*.sbatch` | the Expanse job list and job scripts that produced them |
| `public/` | `test_indep.py`, `replay_indep.py`, `INDEPENDENT_CHECK.md` (the full report), `slurm/` template |

## Targets

```
make -f public.mk test      # structural checks + one fixed-coupling production point (~1 min, 1 core)
make -f public.mk replay    # the quoted agreement from the 23 comparison records (~1 s)
make -f public.mk rerun L=10 X=0.6 MODE=window   # one comparison from scratch (minutes to hours, see public.mk)
```

Requirements: Python ≥ 3.10, numpy, scipy ≥ 1.15 (`public/requirements.txt`).
