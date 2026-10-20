# Provenance: c2_cylinder_d2

`SRI/code/c2_cylinder_d2/` is the git repository `LRI_C2_expanse` at commit **98e1935** (2026-10-14; its tracked
files, a subset, see `DATA_c2_cylinder_d2.md`). Its cluster records under `outputs/` are git-ignored in that repository,
so they ship as a dated snapshot (2026-10-15, unchanged since 2026-10-14; sha256 list `public/SNAPSHOT.sha256`).
`public.mk` and `public/` are new.

## Who wrote what

| Part | Author | Source, date | Later changes |
|---|---|---|---|
| The cylinder-Hamiltonian study: solver `code/hamiltonian/` (29 modules), `scripts/run.py`, archived records `data/hamiltonian/` (raw sequences, auxiliary leading-tail inputs, reference analysis), note `note/lri_c2_progress.tex` and `.pdf` (not shipped since 16 October 2026; its method is the SRI note, Appendix F), `README.md`, `requirements*.txt`, `provenance/PACKAGING_NOTES.md`, the first cluster helpers (`cluster/run_task.py`, `collect_records.py`, `resource_estimate.py`, `slurm_array.sh`, `extension_plan.json`, `smoke_plan.json`, `test_cluster.py`, `cluster/README.md`) | OpenAI GPT-6 astra via ChatGPT, supplied by the author (stated by the author on 2026-10-14 and 2026-10-15; recorded in `provenance/original_study_source_map.json`, key `authorship`). All four archives consolidated in the zip are GPT-6 astra's: the final-method study `LRI_C2_final_method(1).zip`, the independent formula/elliptic/local checks `C2_independent_checks.zip`, and the two Hamiltonian packages `LRI_C2_hamiltonian_partial_checks.zip` and `LRI_C2_Hamiltonian_result.zip` (the source of the solver) | `LRI_C2_complete.zip`, imported unchanged as commit 474487c ("pristine", 2026-10-12) | Claude Code (below): `analyze_extended.py`, `exact_leading_tail.py`, `reproduce.py`, `tail_transseries_fit.py` (configurable leading-tail cutoff, default 2048 as before; outputs byte-identical with defaults); `scripts/run.py` (the `continuum` subcommand); the four cluster helpers above and `README.md` (documentation and validation). `data/` and the note are unchanged since 474487c. |
| Launch layer for SDSC Expanse and symmetry: `cluster/sitekit/`, `cluster/expanse/`, `cluster/symmetry/`, `cluster/production_plan.json`, `smoke2_plan.json`, `analysis_checks_plan.json`, `analysis_checks_plan_rev6.json` and their tests | Claude Code sessions (a builder subagent under a coordinating session) | commits 3d1353e..fa3858a, 2026-10-12..13; later 86539b6..3097d55 (extraction-check plans) | inspected twice by Codex (see `REVIEWS.md`); fix-round-2 edits uninspected |
| Arbitrary-N continuum analysis: `code/continuum/` (driver, analysis, records, report, legacy mode, auxiliary-input job, tests), `results/continuum_2026-10/` | Claude Code sessions | commits 86539b6..98e1935, 2026-10-13..14 | plan reviewed by Codex in 7 rounds (approved at rev 7); code inspected twice; fix-round-2 edits uninspected |
| Production and extraction-check records `outputs/` | computed by the shipped code on the clusters, submitted by Claude Code sessions | 2026-10-13..14 (jobs below) | none |
| `public.mk`, `public/` | Claude Code (SRI export session) | 2026-10-15 | new files |

The closed form of c_2 that the replay compares with was derived by GPT-6 astra (the sibling package `c2_closed_d2`);
`public/c2cyl_common.py` re-evaluates the formula of the paper's appendix with mpmath. No file of this package uses it
as an input (`meta.proposed_closed_form_used = false`; test_continuum checks the code for its digits).

## Records and the jobs that produced them

Science sources of every cluster record: sha256 digest `eebafa82d841...` of the 29 modules of `code/hamiltonian/`
(the set at 98e1935; checked by `test_continuum` and by the analysis on every receipt).

| Records | Pool | Site, jobs | Notes |
|---|---|---|---|
| `outputs/expanse/production_plan_20261013/`: PILOT (N = 512, order 1, lambda 0.1), P2 (N = 1024, orders 1, 2) | PRIMARY | SDSC Expanse (account <ACCOUNT>), large-shared: pilot row 54886939, P2 grid 54894364, P2 rows 54894365_4 and _5 | about 220 SU for P2 |
| `outputs/symmetry/production_plan_20261013/`: PILOT replica, P1 (N = 768, orders 1, 2, 3) | PRIMARY | symmetry: pilot row 574038 (amdq), P1 grid 574141 (defq), rows 574142 and 574143 (amdq) | pilot replica agrees with Expanse to 2e-15 relative in the raw sums |
| `outputs/expanse/analysis_checks_plan_20261013/`: 5 extraction checks on N = 1024 grids (radius 4.5 and 4.0) | DIAGNOSTIC | Expanse large-shared: grid 54898601, rows 54898602_0-2, 54899013_3-4 (requeued once after a node failure) | 252 SU |
| `outputs/symmetry/analysis_checks_plan_rev6_final/`: 20 completion rows (plan rev 6/7) | DIAGNOSTIC | symmetry defq: N = 512 rows 574330, 574331; deviation D1: N = 1024 grids rebuilt 574363, 574364, rows 574425_3, 574428_4, 574434_0, 574436_1, 574438_2 | no SU |
| `outputs/symmetry/c2aux_574247/`: aligned auxiliary inputs (mixed 16384, collapsed 400000/800000, tail 2048/8192) | input | symmetry defq, job 574247 (6 min) | |
| `data/hamiltonian/raw/` (17 archived records, N = 128..384) | PRIMARY | computed by GPT-6 astra in its own environment, as part of the supplied study (author, 2026-10-15) | machine, dates and software versions not recorded |

The merged indexes `outputs/merged_*.json` were written by `cluster/sitekit/merge_records.py` on the authors' personal desktop
after the per-site collections, all records verified (0 problems, one source set).

## Not recorded

1. The machine, dates and software versions of GPT-6 astra's runs that produced the 17 archived raw records
   `data/hamiltonian/raw/*.json`: not recorded beyond the records themselves. The records are bound to
   `MANIFEST.sha256`. The new N = 512..1024 records reproduce them on the shared cutoffs: the N = 512 pilot agrees with
   the archived N = 384 record to 4.4e-7 absolute in the raw partial sums, about 1e-11 relative.
2. The ChatGPT sessions in which GPT-6 astra wrote the four archives: not recorded.

The approved analysis plan `PLAN_ANALYSIS.md` rev 7 is identified by its sha256 (f76af1bf...) in every output. It is
part of the plan and review history, which is not shipped (author decision). Its rules are copied into `meta.rules` of
every output, and `REVIEWS.md` summarises the reviews.
