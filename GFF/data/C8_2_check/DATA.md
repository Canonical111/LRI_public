# Data of the independent C8(2) check (GFF/data/C8_2_check, GFF/results/C8_2_check)

## In git

| Path | Size | Contents | Bound by |
|---|---:|---|---|
| `data/C8_2_check/prod1/manifest.json` | 59 KiB | the production's frozen plan: seed, 342 work indices, 24 groups, pinned tools, inputs, executable | `results/C8_2_check/prod1/C8_result.json` (`source_manifest_sha256` 13ea54c0…) |
| `data/C8_2_check/prod1/allocation.json` | 9.4 MiB | the frozen Neyman allocation (points per replicate for every graph; forecast SE 14.97) | the manifest |
| `data/C8_2_check/prod1/cost_model.json` | 1.0 MiB | the pilot's per-graph cost model used to cut shards | the manifest |
| `data/C8_2_check/prod1/groups/<group>/config.json` | 24 files, 0.9 MiB | group configuration (sector, campaign, loop, seed, rate, net, shards, task hashes) | the manifest |
| `data/C8_2_check/prod1/groups/<group>/merged.json` | 24 files, 0.3 MiB | the merged replicate jets of each group (64 replicates) | `C8_result.json` (`merged_sha256`) |
| `data/C8_2_check/prod1/attempts/<index>.jsonl` | 342 files | start, end, node, outcome of every run of a work index (cost numbers) | not bound |
| `data/C8_2_check/pilot1/...` | 1.1 MiB | the pilot's manifest, configs and merged records (32 replicates) | `results/C8_2_check/pilot1/C8_result.json` |
| `results/C8_2_check/prod1/C8_result.json` | 20 KiB | the production result (sha256 856595ff97fa925c9fefbcdc5de4bf4b6f5b437337b429cbad73afccc2e2abc5) | — |
| `results/C8_2_check/pilot1/C8_result.json` | 20 KiB | the pilot result | — |
| `results/C8_2_check/prod1_analysis/` | 1.1 MiB | `inspect.json`/`.txt` (per-graph variance ranking), `cost_model.json` (measured), `compare.txt`, `kernel_util.txt` | — |

The manifests and configs contain the production's absolute paths (home directory, compiler); they are hash-bound and
ship unchanged. Everything `test`, `fixtures` and `replay` need is in git.

## (a) Hosted, needed for a named target

Both files are in the paper's Zenodo data record (https://doi.org/10.5281/zenodo.23466766), at `https://zenodo.org/records/23466766/files/<name>`. `make -f public.mk fetch-data` (public/fetch.py,
public/hosted.json) downloads the first, checks its size and sha256, and unpacks it; `fetch-data ALL=1` adds the second.

| Archive | Size | Target | Contents |
|---|---:|---|---|
| `GFF__data__C8_2_check__c8d2_check_prod1.tar.gz` (933,181,042 B, sha256 ff5df33bc46f961593056cb698bae935fe8df428a2b6058e8d5bfd7408d87084; unpacks to `data/C8_2_check/hosted/prod1/`) | 4.33 GB unpacked, 3,210 files | `remerge` | the production campaign directory: per-group checkpoints, `tasks.sqlite`, `sobol.bin`, `graph_replicates.csv`, and the manifest, allocation, cost model, configs, merged records and `C8_result.json` as in git; `attempts/` as in git (host and log scrubbed). Left out, as in git: `done/`, `claims/`, `runner_logs/`, `slurm_logs/`, `site_identity.json`, `site_submissions.jsonl`, `seed_receipt.json` (operational; node and account names). `remerge` re-merges all 24 groups and compares with the shipped merged records byte for byte, then recomputes the kernel time (verified on Expanse on the campaign directory, 2026-10-13, and on this unpacked file, 2026-10-19: 24/24 identical, 25,585.3 kernel core-hours). |
| `GFF__data__C8_2_check__LRI_C8_D2_HPC.zip` as delivered (483,599,705 B, sha256 14b0a4a6df74bade4f5842ee04d7879706f7b82d8bd76a6a440e036d3a8e0494; `fetch-data ALL=1` puts it at `data/C8_2_check/LRI_C8_D2_HPC.zip`) | 484 MB (8.3 GB unpacked) | a production rerun (REPRODUCE.md) | the original package of the delivering model; its `inputs/packs/` holds the twelve graph packs (L3-L7 byte-identical to those of the main calculation; free_L8 6.1 GB and power_L8 1.4 GB its own), attached with `tools/attach_inputs.py <unpacked>/inputs`. Never unpack it next to `GFF/code/LRI_C8_D2_HPC`: its top folder has the same name. |

## (b) Archive only

Nothing else. The pilot's campaign directory (on Expanse) is not archived; its merged records in git reproduce the pilot
result.

The complete production campaign directory, with the operational files left out above, is kept by the authors and is
available on request.
