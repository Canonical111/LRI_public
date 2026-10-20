# Reproduce c1_d3

Environment: Python >= 3.10 with numpy, scipy (HiGHS LP), mpmath, threadpoolctl and matplotlib
(`requirements_c1_d3.txt`; the authors' exact versions are in `requirements-pinned.txt`). One core; no network, no
SDPB, no TeX (TeX only for `make pdf` of the authors' Makefile). Run from `SRI/code/c1_d3/`:

1. `make -f public.mk test` (about 1 min): the dated snapshot (`public/SNAPSHOT.sha256`) and the authors' delivery
   list (`SHA256SUMS`, subset mode: `public/NOT_SHIPPED.txt` lists the files left out of the export); the smoke
   profile in a copy (a0, b0, C1 against `outputs/reference/`, 5e-10; block closed-form checks below 1e-12); the
   revision guards under `python -O`.
2. `make -f public.mk replay` (about 8 min): in a copy under `.work/replay/run`, `code/workflow/reproduce.py full
   --from-scratch` (20 stages, every number regenerated from `data/inputs/`), `code/workflow/verify.py results` (23
   checks), every JSON and NPZ output against the shipped full run `outputs/reproduced/` (atol 2e-8 + rtol 1e-8),
   `make_assets.py` on the rerun (`current_summary.json` and 11 CSV tables against the shipped ones), and the quoted
   numbers `\SRthreeCone`, `\SRthreeConeRange`, `\SRthreeConeBRRZ` (cited), the d = 3 row of tab:sr, the inputs
   S, E_SR, and the note-only `\SRthreeConeImplDev`, "two independent implementations agree to 10^{-12}" (a
   bound; INFO row; each implementation within 1e-12 of the package is a PASS/FAIL row): the review's two
   re-implementations in `review_indep/` rerun on the shipped spectrum (about 1 min), |delta c_1| <= 1e-12 against
   the package and between the two. PASS/FAIL table in `.work/replay/replay_c1_d3.txt`.
3. `make -f public.mk replay-full` (about 25 min): the review-revision diagnostics (central inputs infeasible in the
   nominal LP, 68 rows; 11 gap/padding and 8 input-box scenarios; the three sensitivity tables) against
   `outputs/review_validation/` and `outputs/tables/review_*.csv`.

The authors' own entry points work in place too (`python code/workflow/reproduce.py full --from-scratch --output
<dir>`, `python code/workflow/verify.py results --results <dir>`; see `README.md`). Do not run `verify.py integrity`
on the public tree: it fails by design on the files left out of the export (`public/NOT_SHIPPED.txt`) and on the
added `public/` files; `make test` performs the same check in subset mode. Give side runs their own `--output`, so
the shipped `outputs/reproduced/` is not overwritten.

## Decisions you must not make

- The gap hypotheses (no unlisted Z2-even primary below 8, no unlisted Z2-odd primary below 7), the box of twice the quoted
  input errors, the epsilon-prime window [1.5349, 1.5375], the chosen allowances (5e-5 objective, denominator box
  rounded outward to 1e-6, crossing padding 1.5 times the sampled nonlinearity, external-dimension factor 1.001) and
  the update counts (10 nominal, 8 doubled padding and weaker gaps).
- The estimated range [0.269, 0.276]: the authors' outward rounding of the nominal and doubled-padding envelopes. It is
  CONDITIONAL and scenario-specific; do not widen, narrow or average it with the sensitivity scenarios, and do not
  present it as a confidence interval or a certified bound.
- The retained value 0.27315242 is reported separately from the range; the midpoint 0.2725 is not a best fit.
