# Data of C8(2) (GFF/data/C8_2, GFF/results/C8_2, and the payloads of GFF/code/LRI_C8_shared)

C8(2) = 45990 +- 33 (note Section 31) was computed in one production batch on the symmetry cluster on 6 and 7 October
2026: campaign directory `prod1-2.5e-4-ddmp256-20261006-ba68f401e46e` (about 9.8 GB: plan, 24 merged groups, 24,848
checkpoint blocks, tasks, logs). The exact-path pilot that fixed its design is `pilot1-20261006-ba68f401e46e`.
`make -f public.mk replay` (in GFF/code/LRI_C8_D2_HPC) needs only what is in git.

## In git

| Path | Size | Contents | Bound by |
|---|---:|---|---|
| `data/C8_2/prod1-.../manifest.json` | 560 KiB | the frozen plan of the batch: seed, 1,129 work indices, 24 groups, pinned tools, inputs manifest, executable, design bundle, cost model | `C8_result.json` `source_manifest_sha256` (be215e0e…); every merged.json `manifest_sha256` |
| `data/C8_2/prod1-.../cost_model.json` | 5.2 MiB | the dd+mp256 cost model the plan used (sha256 18e50440…; equal to `code/LRI_C8_D2_HPC/cost_models/gmp_symmetry_amd_c8_dd+mp256.json`) | the manifest |
| `data/C8_2/prod1-.../design_bundle/` | 0.6 MiB | the frozen Neyman design (route (b), K = 1): `design_meta.json` (6afb6dd6…), `design.json`, 24 counts files | the manifest; `C8_final.json` `design` |
| `data/C8_2/prod1-.../groups/<g>/config.json` | 24 files, 3.9 MiB | group configuration (sector, campaign, loop, seed, rate, net, points per graph, task hashes) | the manifest (`groups[].sha256`) |
| `data/C8_2/prod1-.../groups/<g>/merged.json` | 24 files, 0.6 MiB | the merged replicate jets (128 replicates) and the table hashes of each group | `C8_result.json` (`merged_sha256`) |
| `data/C8_2/prod1-.../C8_result.json` | 20 KiB | the batch's assembled result (sha256 9383ab81…) | — |
| `data/C8_2/prod1-.../cpu_vendor.json`, `runtime_identity.json` | 2 KiB | the batch's CPU-vendor pin (AMD EPYC 7543) and runtime-identity pin (04f1e51d…) | — |
| `results/C8_2/C8_final.json` | 17 KiB | **the published C8(2) record** (combination of the one planned batch; sha256 b14da47c…) | — |
| `results/C8_2/pilot/C8_result.json` | 19 KiB | the exact pilot's result (45620 +- 214) | — |
| `results/C8_2/production/` | 1.1 MiB | `analysis.json` (variance per stratum, tail classes and their share of the variance), `accounting.json` (13,453.83 core-hours), `tails.csv.gz` (the tail table of all 48,346 graph-campaigns; decompressed sha256 8039682a…), `report_summary.txt` | — |
| `results/C8_2/tailcheck/` | 0.3 MiB | the weight-boundedness verification (`cert_summary.json`, `cert_check.json`), the nine controls (`negctl_check.json`), the nested-sampling and double-lift tests (`nested_joint.json`, `nested_split.json`, `dl_targeted.json`), the Hill tables (`ab_hill.json`) | — |

The results files are byte copies of files in `code/LRI_C8_D2_HPC/benchmarks/symmetry_2026-10-c8/` at git commit 9df5b1c
(`results/C8_2/SOURCES.txt`). The plan, the design bundle and the configs name the cluster paths and user name of the
production; they are hash-bound and ship unchanged.

## Hosted (not in git; in the paper's Zenodo data record (https://doi.org/10.5281/zenodo.23466766), files at `https://zenodo.org/records/23466766/files/<name>`)

`make -f public.mk fetch-data` in `code/LRI_C8_D2_HPC` downloads the three C8(2) files, checks their sizes and sha256
(public/fetch.py, public/hosted.json) and unpacks them; `make -f public.mk fetch-data` in `code/LRI_C8_shared` does the same
for the four payload tars, which it places in `inventory/inventory8_d2/payload/` as they are.

### (a) Needed for a named target

| File in the record | Size | Needed for | Contents, where it unpacks | sha256 |
|---|---:|---|---|---|
| `GFF__data__C8_2__c8d2_prod1_tables.tar.gz` | 1,400,534,652 B (2.7 GB unpacked) | `replay-tails` | `groups/<g>/graph_replicates.csv`, `graph_tails.csv`, `graph_costs.csv` of the 24 production groups; unpacks over `data/C8_2/prod1-2.5e-4-ddmp256-20261006-ba68f401e46e/` | 32276b1cebbd45eb948f2146288118d19ad30cf490ab870c2af3585f81ef5322; every table's sha256 is pinned in its `merged.json` (`graph_*_sha256`) |
| `GFF__data__C8_2__c8d2_prod1_lane_records.tar.gz` | 24,396 B | `replay-tails` | the production's ledger `submissions.jsonl` (read by `tools/design.py report`) and its lane logs `slurm_logs/lane-*.log` (read by the post-production analysis), user and node names scrubbed; unpacks over the same folder | b53899d32a80cbe16ba50194728df2285babaef60d382785e62c5bb0c2a7241b (not hash-bound) |
| `GFF__data__C8_2__c8d2_pilot1_records.tar.gz` | 89,627,696 B (173 MB unpacked) | `replay-tails` | the pilot campaign's `manifest.json` (828fb586…), `cost_model.json`, `C8_result.json`, `cpu_vendor.json`, `runtime_identity.json`, `groups/<g>/{config.json, merged.json, graph_*.csv}`; unpacks to `data/C8_2/pilot1-20261006-ba68f401e46e/` | 7feac081c2525ec7673bcac59eaab7a7a9a0a7f95642a4d4cfdfd3c419ab152b; the manifest pins the configs, merged.json pins the tables (the host field of `cpu_vendor.json` and `runtime_identity.json`, not bound, scrubbed as in the production's copies in git) |
| `GFF__code__LRI_C8_shared__inventory__inventory8_d2__payload__L7_free.tar` (placed as `L7_free.tar`) | 233,338,880 B | `setup-l8` / `jval1` (via `make inputs-l8`), production rerun, C8(3) | `code/LRI_C8_shared/inventory/inventory8_d2/payload/` (2,441 G-files) | 74ecb589e1b7cf893ec0ee9659c052404ddceac39056433fe69e4ba660e4cecb |
| `GFF__code__LRI_C8_shared__inventory__inventory8_d2__payload__L7_power.tar` (placed as `L7_power.tar`) | 57,630,720 B | as above | same folder (709 G-files) | f9a2688fdc56a98faa74d9e27483de2da8465a9bbdc5e7f55ee4f09f0c7c4c7b |
| `GFF__code__LRI_C8_shared__inventory__inventory8_d2__payload__L8_free.tar` (placed as `L8_free.tar`) | 6,431,672,320 B | as above | same folder (16,798 G-files) | 25e2fc1d2f60b523428b6baa99b537dccbcccbb679d1b30e5f1fb83b2bb01d8c |
| `GFF__code__LRI_C8_shared__inventory__inventory8_d2__payload__L8_power.tar` (placed as `L8_power.tar`) | 1,615,616,000 B | as above | same folder (4,891 G-files) | 4bc418cf45333ac9b56bb5e6e63cdd5e2a9f05d2c99a0aaa566942624f37420e |

The four payload tars are shipped as they are (their sha256, md5, size and member count are in
`inventory8_d2/MANIFEST.json`, whose sha256 is the pin C8_H1_PIN 46341a3c…; `make -f public.mk verify` in
`code/LRI_C8_shared` checks all four levels). The L7 tars hold the same G-files as the C7(2) reference trees, from which
`setup` rebuilds the L7 packs; only the L8 tars are needed in practice, but the pinned tree needs all four.

### (b) Archive only

| What | Size | Where today |
|---|---:|---|
| the full production and pilot campaign directories (checkpoints, tasks, lane and Slurm logs, the uncompressed tail report) and the tail-check runs | 10.6 GiB, 31,281 files | symmetry cluster file system and two Google Drive copies of the project archive (catalog entry `c8d2`) |
| the gated dd+mp256 executable and the build tree of the production export | — | not archived; rebuilt by `make gmp NUMERICS=dd,mp256` (its sha256 a46f3060… reproduces only with the production toolchain, GCC 11.4 on Ubuntu 22.04) |
