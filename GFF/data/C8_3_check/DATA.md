# Data: independent check of C8(3) (`GFF/results/C8_3_check`, `GFF/data/C8_3_check`)

This file is `GFF/data/C8_3_check/DATA.md`. The code is `GFF/code/LRI_C8_D3_OPT` (`public/README.md` there).

## In git

| path | size | what | bound by |
|---|---|---|---|
| `GFF/results/C8_3_check/runs/prod1/C8_result_54838171.json` | 195,059 B | the estimator, covariances, stored means and input covariances per loop and sector, campaigns, half streams, bootstrap, lower-order checks | sha256 `58de4f97...` (production README; replay R0) |
| `GFF/results/C8_3_check/runs/prod1/manifest.json` | 5,907,683 B | the frozen plan: seeds, per-graph points, graph hashes, input and tool hashes, executable, 1,994 jobs | the result's `manifest_sha256` (`9906a8da...`) |
| `GFF/results/C8_3_check/runs/prod1/graph_statistics_54838171.json` | 15,974,782 B | per graph and campaign: projected mean and replicate SD of the C8 contribution, points, CPU seconds, promotion counts (measured on Expanse; usable for a new allocation) | sha256 `537258cb...` (replay R0) |
| `GFF/results/C8_3_check/allocations/prod1_2000.json` | 508,251 B | the frozen per-graph allocation | the manifest's `allocation_source` (`fccf8969...`) |
| `GFF/results/C8_3_check/README.md` | 2,328 B | the production summary: jobs, dates, nodes, cost | none |
| `GFF/code/LRI_C8_D3_OPT/inputs/{free,power}/` | 179 files, 16,274,032 B | the graph payloads the tests read (`tests/optimization_graphs.json`, `verification/new_graphs.json`) | `inputs/inventory.json`, `SHA256SUMS` |

Total in git for this check: about 22.6 MB of records and 33.4 MB of code (with `inputs/inventory.json`, 11.95 MB,
and `SHA256SUMS`, 3.07 MB). No file exceeds 16 MB.

## Hosted (in the project's Zenodo data record, https://doi.org/10.5281/zenodo.23466766; `make -f public.mk fetch-data` in `GFF/code/LRI_C8_D3_OPT`)

Built on 2026-10-19 by `GFF/code/LRI_C8_D3_OPT/public/make_data_bundles.sh` (GNU tar 1.34, xz 5.2.5 on the symmetry
cluster) from the production tree of the package, after checking every bundled file against the package's `SHA256SUMS`;
their sha256 are in `public/data_bundles.sha256` of that folder. `fetch-data` downloads them from the Zenodo record
(default base URL `https://zenodo.org/records/23466766/files`; `ZENODO=<base URL>` selects a mirror) into `GFF/data/C8_3_check/`,
checks those sha256, unpacks them into `GFF/code/LRI_C8_D3_OPT/`, and runs `verify-data` (every unpacked file against the
package's `SHA256SUMS`). In the record a bundle is named `GFF__data__C8_3_check__<bundle>`.

| bundle | unpacks to | files | raw size | bundle size | needed by |
|---|---|---|---|---|---|
| `c8opt_inputs_free.tar.xz` | `inputs/free/L3..L8/G*.txt` | 18,997 | 7,402,139,146 B | 80,917,980 B | a production rerun (the planner hashes every payload; the workers read them); full `verify-data` |
| `c8opt_inputs_power.tar.xz` | `inputs/power/L3..L8/G*.txt` | 5,176 | 1,745,151,389 B | 17,252,520 B | same |
| `c8opt_pilot_20261008.tar.xz` | `results/pilot_20261008/` | 7,659 | 141,722,637 B | 24,099,184 B | `replay-full` (R7: the allocation from the pilot's `graph_statistics.json`, sha256 `41e3a0d7...`), `test-cluster` (the pilot's manifest), the lane bundling of a rerun, re-assembly of the delivered pilot (1514.6 +- 161.7) |
| `c8opt_regeneration.tar.xz` | `regeneration/`, `inputs/complete_inventory_L3..L8.json` | 20 | 40,828,336 B | 1,152,920 B | graph regeneration and the coverage audits only (`tools/generate_graphs.py`, `verify_graph_census.py`, `audit_graph_forests.py`; `docs/GRAPH_GENERATION.md`) |

The payloads compress very well: the four bundles total 123,422,604 B (0.12 GB) for 9.33 GB of files. Every payload is also bound by its sha256 in `inputs/inventory.json`
and in the production manifest's `graph_hashes`. The payloads can instead be regenerated with
`tools/generate_graphs.py` (needs the regeneration bundle and pynauty), which checks them against the same hashes.

## Not archived

The native outputs, job files and receipts of the 1,994 production jobs (the per-replicate, per-graph sums from which
the result was assembled) stay in the campaign directory on the production cluster's scratch filesystem and are not
archived. Without them the campaign standard errors, half streams and bootstrap cannot be recomputed; everything else
is replayed from the records above. The port's plan, review transcripts, logs, admission ledger, seed registry and
lane summaries are not published (summaries in `GFF/code/LRI_C8_D3_OPT/public/REVIEWS.md` and `PROVENANCE.md`).
