# HT_Pert d = 2 data: what is where

Everything needed by `test`, `smoke` and `replay` of `HT_Pert/code/lri_d2_coeff_hpc` and
`HT_Pert/code/lri_2d_coeff_independent_check` is in git; nothing is hosted (`make -f public.mk fetch-data` says so).

| Folder | Contents | Files | Bound | Used by |
|---|---|---|---|---|
| `HT_Pert/data/HT_2d/prod/check_small_symmetry` | 21 records, L = 2..14, raw/consistent/literal, degree 8; campaign.json | 22 | records and campaign.json self-hashed | replay (p2.prod.*, p2.impl_agree), smoke |
| `HT_Pert/data/HT_2d/prod/prod1_symmetry` | 16 records, L = 16..30, raw/consistent; coefficients.csv; campaign.json; validation receipt 571623 | 20 | records and campaign.json self-hashed; coefficients.csv cited by sha256 (d86743c1…) in `HT/data/HT_2d/pert_crosscheck` | replay |
| `HT_Pert/data/HT_2d/prod/prod2_expanse` | 4 records, L = 32, 34, raw/consistent; coefficients.csv; campaign.json; Expanse validation receipt 54765932 | 8 | records and campaign.json self-hashed | replay |
| `HT_Pert/code/lri_2d_coeff_independent_check/**/results`, `*.csv`, `*.txt` | the exact and large-L outputs of the independent check (see that package's README) | ≈ 600 | not bound (listed in public/SNAPSHOT.sha256) | replay (p2.*), replay-full, test |
| `HT_Pert/results/HT_2d` | where each quoted output lives; the replay outputs of the release check | 3 | no | reading |

Binding: each lri-coeff-v1 record and each campaign.json carries `sha256` = sha256 of the canonical JSON of its `payload` (sorted keys, compact
separators) and the solver's `source_digest` (550e9266…, recomputed from `code/lri_d2_coeff_hpc/src/lri_coeff`). They
ship byte-identical (the validation receipts are not bound), with the original cluster paths, node names and the Expanse user inside: these are history, not
paths to use. The two coefficient tables cited by HT (`prod/prod1_symmetry/coefficients.csv`,
`code/lri_d2_coeff_hpc/reference/lri_d2_perturbative_C8/results/coefficients_C0_C8.csv`) are also byte-identical.

Archive only (not published): the per-task pickled caches of the C5 production (10012 tasks at L = 300) and of the
C4 L = 2000 run, the raw modular residues of the exact solvers, all Slurm logs, superseded and diagnostic runs, the
internal research logs.
