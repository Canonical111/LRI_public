# Independent d = 2 solver against the production records

`out_sym/<task>.json` holds the 155 outputs of `HT/code/lri_2d_window_indep/run_check.py`, from two symmetry jobs:
- 571680: 143 tasks, all Δσ, at N = 8 … 18, and N = 20 at Δσ = 0.125, 0.25;
- 571811: 12 follow-up tasks at strong coupling, N = 18 … 22.

There are two kinds of task:
- **fixed:** the spectrum at the production couplings θ of the record;
- **tune:** an independent root search from θ + (0.05, −0.05).

`K` is the independent zero-mode truncation (states per parity) and `M` the oscillator basis.

Each output holds:
- `indep`: the independent levels, the vacuum table E_v(M) and the window D;
- `records`: the production values it was compared with (θ, Δ_E, gaps, E_v, the J = 1, 2 spectra where computed, and the
  production `record_sha256` for nz = 12, 16, 20).

The replay (`make -f public.mk replay` in `HT/code/lri_2d_window_indep`) checks every embedded value against the
shipped record and recomputes the agreement. Results:
- 1.4e-12 at N = 12, 16 (K ≥ 32);
- 4.4e-10 and 4.0e-10 at N = 22 (K = 32);
- K = 24 is not converged at strong coupling.

The `host` field is the symmetry node, scrubbed to a placeholder.
