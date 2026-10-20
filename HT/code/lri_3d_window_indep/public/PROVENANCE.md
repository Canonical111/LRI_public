# Provenance: lri_3d_window_indep

- **Written by:** Claude Code (Claude Opus 5.5), the session that also ran the d = 3 production. Written on
  2026-10-08 at the author's request: "do a fully independent check of the solver, to make sure it is correctly
  calculating what we want".
- **Inputs:**
  - the method description of the supplied package (`lri_3d_window_hpc/reference/baseline/docs/METHOD.md`), with the
    formulas re-derived;
  - the production records, read only through `indep_extract.json`, for the couplings to compare at.
  - The production code (`code/ht3d`) was neither read nor imported.
- **Run:** on SDSC Expanse, `shared` partition, in the production venv (Python 3.11.9, numpy 2.3.5, scipy 1.17.0),
  2026-10-08.
  - Array 54766121 (`indep.sbatch`, `tasks.txt`) and the single jobs in `l8.sbatch`, `retune*.sbatch` and
    `spin.sbatch`.
  - Three N = 12 tunings were rerun from a 2% start (54771132, 54771237, 54772616).
  - The scripts and `.sbatch` files ship as they ran. The `.sbatch` files contain the production paths; the template
    with placeholders is `public/slurm/compare.slurm`.
- **Report:** `public/INDEPENDENT_CHECK.md`, written by Claude Code on 2026-10-08 and last updated the same day with
  the N = 12 tunings; one dated wording correction on 2026-10-18 (the zero-mode basis, under question A). Its part B
  (physics against the continuum, at N ≤ 18) is the source of the HT note's statement that the d = 3 values are not
  yet close to the continuum at Ds = 0.7.
  - Its Borel–Padé numbers come from the script that ships as `lri_3d_window_hpc/public/bp_x07.py`.
  - Its perturbative cross-check (Sec. A2) compares against `lri_3d_hpc` coefficients at L ≤ 14 (HT_Pert); it is
    not quoted in the paper.
- **Not reviewed by Codex.**
- **Public tooling** (`public.mk`, `public/test_indep.py`, `public/replay_indep.py`): Claude Code, 2026-10-13.
