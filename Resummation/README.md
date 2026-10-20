# Resummation and comparison

Resummation of the epsilon expansion of the long-range Ising model in d = 1, 2, 3 with the short-range end imposed, the
large-order (instanton) analysis, and the comparison of all descriptions (perturbation theory, Hamiltonian truncation,
NRG, Monte Carlo, published values). It reproduces every number of the paper's sections "Resummation" and "Comparison" (\RS* and \CMP*
macros; also those of the ninth-order paragraph "Higher orders" in Sec. "Around the generalized free field" and those the Discussion
and Appendix "Numerical results" repeat; `results/quoted_numbers.json` names where each is printed), the resummed column of the results tables tab:num1-3 (with their d = 2, 3 HT and d = 2 MC columns, which come from records frozen here) and the data of the figures fig:cmp1d and fig:cmp2d3d.

- `note/`: the self-contained note (TeX, PDF; Appendix "Reproduction").
- `code/resum_d1/`: the d = 1 resummation (short-range series through C^SR_8, final C8(1)); `code/resum_d23/`: d = 2, 3;
  `code/instanton/`: the critical bubble and the amplitude K_I with its benchmarks; `code/comparison/`: the comparison numbers.
  Production code ships verbatim (dated snapshots with sha256 lists); `public.mk` and `public/` are added.
- `data/inputs/`: frozen copies of the HT, NRG, MC records used and of the literature extraction; `INPUTS.json` lists every
  external input (also the coefficients and short-range data embedded in the code) with its source.
- `results/`: `quoted_numbers.json` (the macro texts of the paper), `comparison/*.csv`, `figures/` (the two PDFs and the CSV
  behind every plotted curve and point).
- `verify/`: shared replay helpers, the figure-data check, the check of the inputs against the sibling folders.
- `results_map.md`: every quoted number (\RS*, \CMP*) and every cell of tab:num1-3 taken from this folder with the record it is recomputed from, the command that
  reproduces it and the tolerance; per package in `code/<package>/public/results_map.md`.

Start with `make test` and `make replay` (about 1 min each); `REPRODUCE.md` gives the order and the cost.
The resummed curves are sensitivity ranges over prescriptions, not error bars; no HT, NRG or MC value enters a curve or
serves as a criterion for choosing a prescription (in d = 1 the number K of imposed short-range coefficients was fixed
after the data were seen; no comparison favours K = 8 over K = 4).
