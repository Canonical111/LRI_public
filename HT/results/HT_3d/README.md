# HT_3d: d = 3 finite-coupling Hamiltonian truncation, published outputs

`finite_L_table.csv` lists ΔE (the thermal dimension) of the dressed window truncation at bath cutoffs N = 8, 10, …,
20 (column `L`), for 15 values 0.518149 ≤ Ds ≤ 0.7499. For each point it also gives:
- the tuned couplings r and g and the tuning residual;
- the wall time and peak RSS of the production step;
- the record it comes from (`data/HT_3d/campaigns/...`) and that record's `record_sha256`.

These are finite-cutoff values, not continuum limits. The paper prints the N = 20 row (main.tex, Appendix "Numerical
results", Table tab:num3, column "HT, N = 20") and plots it (Fig. cmp2d3d, green squares); the HT note discusses their
behaviour in N.

The table is written by `make -C ../../code/lri_3d_window_hpc -f public.mk replay`, which rebuilds it from the records
and requires it to equal this file byte for byte (row TABLE). Every other quoted d = 3 number is listed, with its
check, in `../../code/lri_3d_window_hpc/public/results_map.md`.
