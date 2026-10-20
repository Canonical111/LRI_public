# C8(3) data: what is in git and what is hosted

Sizes from the local simulation of `export_entries.json` (2026-10-13). The hosted files of `data/C8_3` are in the project's
Zenodo data record (https://doi.org/10.5281/zenodo.23466766). `make -C code/LRI_C8_D3_HPC -f public.mk fetch-data TIER=<tier> [ZENODO=<base URL of its files>]`
downloads, checks and places them; the default base URL is `https://zenodo.org/records/23466766/files`. `data/C8_3/HOSTED.json` lists
every file with its size, its sha256, the git-tracked file that pins it and its name in the record (its repository path
with `/` replaced by `__`). The 24 replay tables and the 4 tail tables come as one `.tar.gz` bundle each; every member is
checked against its own pinned sha256 after unpacking.

## In git

| path | size | what |
|---|---|---|
| `code/LRI_C8_D3_HPC/` | 123.5 MB, 1,416 files | the package at 4fbd1bae (115.9 MB, 1,292 files), the production evidence of 6dd4a75a (7.5 MB, 118 files), `public.mk` and `public/` (0.1 MB, 6 files) |
| of which `inputs/` | 29 MB | inventory, H1 and d=3 chain files, low-loop inputs, the L3–L6 packs (14 MB) |
| of which `reference/` | 22 MB | the original C7(3) package without its L7 member files, archived production records and verification outputs |
| of which `benchmarks/` | 50 MB | the kept evidence; the largest file is the pilot report `pilot/evidence/pilot_report.json` (33.7 MB) |
| `results/C8_3/` | 11.7 MB, 54 files | `C8_result.json`, `manifest.json`, `cost_model.json`, `cpu_vendor.json`, `SHA256SUMS.symmetry`, `README.md`, and per group (24) `merged.json` + `config.json` |
| `data/C8_3/` | < 20 KB | `DATA.md` (this text) and `HOSTED.json` |

No file in git is larger than 50 MB.

## Hosted (`data/C8_3/`, by tier; tiers are cumulative)

| tier | file(s) | bytes | sha256 pinned by | in the Zenodo record as | needed by |
|---|---|---|---|---|---|
| replay | `results/groups/<group>/graph_replicates.csv` (24) | 332,089,533 (L8 alone: 241,679,146) | `results/C8_3/SHA256SUMS.symmetry`; `merged.json` `graph_replicates_sha256` | bundle `GFF__data__C8_3__replay_graph_replicates.tar.gz` (154,828,288 bytes) | replay steps H: the per-graph campaign split (note Sec 32.4) and the tail monitor's variance shares (Sec 32.5). Without them these rows are NOT RUN; the quoted numbers are still checked against the committed `ab_split/report.txt`. |
| test | `packs/free_L7.pack`, `packs/power_L7.pack` | 268,190,810 + 67,974,745 | `inputs/manifest.json` (b5bd6c12…, 0e5c6eab…) | `GFF__data__C8_3__packs__free_L7.pack`, `GFF__data__C8_3__packs__power_L7.pack` | `make inputs`, the native gates, `check_inputs`, `members_test`, `test_opt`, a production rerun |
| test | `c7d3_reference_L7_inputs.tar` | 311,080,960 (members 252,190,551 + 56,655,776; sha256 d507cbd3… in `HOSTED.json`) | members: `reference/DELIVERY_MANIFEST.json` | `GFF__data__C8_3__c7d3_reference_L7_inputs.tar` | `make inputs` / `check_inputs` (byte-for-byte rebuild of the L7 packs), `test-replay` |
| test | `c7d3_reference_production_records.tar` | 43,980,800 (500 members, 43,557,506; sha256 e4d7030b… in `HOSTED.json`) | members: `reference/DELIVERY_MANIFEST.json` | `GFF__data__C8_3__c7d3_reference_production_records.tar` | `test-replay` (cited in Sec 32.2), `tests/archived_replay.py` |
| rerun | `store/packs/d60ccb8c….pack` (free L8) | 7,121,248,655 (> 2^32) | `inputs/manifest.json` | `GFF__data__C8_3__store__packs__d60ccb8c….pack` (full sha256 in the name) | a production rerun; `class_b`, `workflow`, `staging`, `check_inputs` with L8 |
| rerun | `store/packs/92b70b36….pack` (power L8) | 1,674,690,805 | `inputs/manifest.json` | `GFF__data__C8_3__store__packs__92b70b36….pack` | as above |
| optional | `results/groups/{a,b}_{free,power}_L8/graph_tails.csv` (4) | 2,152,213,923 (848,154,529 + 227,941,843 + 848,180,895 + 227,936,656) | L8 `merged.json` `graph_tails_sha256` | bundle `GFF__data__C8_3__optional_graph_tails.tar.gz` (1,049,867,032 bytes) | only `prod1/tail_ntrend/prod_tails.py` (the production's per-graph Hill index); the replay instead checks the committed `prod_tails.csv` against the result's tail monitor |

Totals (unpacked): replay 0.33 GB; test +0.69 GB; rerun +8.80 GB; optional +2.15 GB. Downloads: replay 0.15 GB, optional 1.05 GB; the others as unpacked.

The L7 member files and the archived production records are byte-identical to `LRI_C7_D3_HPC/reference/` (C7_3 group);
the 500 production records are also in C7(3)'s hosted `reference_records.tar.gz`. This package keeps its own two tars so
that its fetch does not depend on another package's (about 44 MB of the record is duplicated).

## Not hosted

- **The d=3 payload** `d3_payload/46341a3c0f11` (9.2 GB): the intermediate the L7/L8 packs were built from. Regenerate it
  (REPRODUCE, "Regenerating the inputs") from H1 (`code/LRI_C8_shared`, hosted payload) and the frozen C7(2) d=2 inputs
  (`code/LRI_C7_D2_HPC/reference/`).
- **The production run tree** (13 GB, 33,776 files: checkpoints, task databases, the per-graph tail, promotion and cost
  tables, lane logs): on the symmetry cluster and in the authors' archive (two copies, catalog id `c8d3`). Only a
  directory-mode re-verification (`tools/verify_result.py RUN`) needs it.
- **The pilot campaigns** (groups, lanes and logs): their manifests, subset summaries and the pilot report are in git.

## Record identity

`C8_result.json` sha256 `b077625830dd4dcffd78052f06620914f27c3378e0c1e2271fac3656f3012e16`; `manifest.json`
`ac2ec093c11470613cb4dd37bddba411d8f7e5548f60d059111f40cb573704a0`. The records name the cluster paths, user and nodes
on which they were written; they are hash-bound and released byte-identical.
