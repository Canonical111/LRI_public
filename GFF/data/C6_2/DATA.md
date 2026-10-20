# Data of C6(2) (GFF/data/C6_2, GFF/results/C6_2)

The production of 28 September 2026 (SDSC Expanse, run directory `run-20260928-m8192`). Every record is bound to the
others by SHA-256: `C6_result.json` names the plan and the 8 merged records; the plan names the 8 configs, the 5 tools and
the inputs manifest of the code; each config names its task table and Sobol net; each merged record names its per-graph
table and carries its own payload hash; each checkpoint carries the plan hash, the config hash and its payload hash.

## In git

| Path | Size | Contents | Bound by |
|---|---:|---|---|
| `data/C6_2/run-20260928-m8192/manifest.json` | 35,172 B | the frozen plan: seed, 428 jobs, 8 groups, pinned tools and inputs, executable hash, primitive allocation, estimates | `C6_result.json` (`source_manifest_sha256` a3212ac3...), the merged records and the checkpoints |
| `data/C6_2/run-20260928-m8192/groups/<g>/config.json` | 8 files, 26 KB | group configuration (campaign, loop, seeds, net, per-kernel counts, shards, task-table hash) | the plan |
| `data/C6_2/run-20260928-m8192/groups/<g>/merged.json` | 8 files, 78 KB | 64 replicate jet vectors per group, fallback counts, integration seconds | `C6_result.json` (`merged_sha256`) |
| `data/C6_2/run-20260928-m8192/groups/<g>/graph_replicates.csv` | 8 files, 3.45 MiB | per-graph sums of every replicate (decimal, 21 digits) | the merged records |
| `data/C6_2/hosted_run-20260928-m8192.sha256` | 134 KB | SHA-256 of the 1,038 hosted files | — |
| `results/C6_2/C6_result.json` | 9,085 B | the result (sha256 59c9029aca61fb336c290ad2765e96a481d24746cfa5eef0a3a895fbeb9a461f) | — |
| `results/C6_2/CAMPAIGN.md`, `README.md` | 14 KB | production record (public rewrite), file guide | — |
| `results/C6_2/preflight/threadcheck-54508994.out` | 0.8 KB | thread-identity check (64 vs 16 threads) | — |

The plan contains the absolute path of the package on the cluster (`/home/<user>/...`). It is hash-bound and ships
unchanged. `replay` needs only the files in git (and `../../results/C7_2/C7_result.json`).

## Hosted (not in git; `make -f public.mk fetch-data`)

The hosted file is in the paper's Zenodo data record (https://doi.org/10.5281/zenodo.23466766), at `https://zenodo.org/records/23466766/files/<name>`. `fetch-data` (public/fetch.py, public/hosted.json)
downloads it, checks its size and sha256, and unpacks it.

### (a) Needed for a target

| Archive | Size | Needed for | Contents |
|---|---:|---|---|
| `GFF__data__C6_2__c6_2_run-20260928-m8192.tar.gz` (79,253,339 B, sha256 14cf392bf17de9ffada0b2a541bb47c362cc7598a7c2addcfe8048351097703e; unpacks to `data/C6_2/hosted/run-20260928-m8192/`) | 1,038 files, 411,336,487 B = 392.3 MiB unpacked | `make -f public.mk remerge`; re-running archived blocks (REPRODUCE.md) | the complete run directory without its Slurm logs: `manifest.json`, `C6_result.json`, and per group `config.json`, `merged.json`, `graph_replicates.csv` (as in git), `tasks.sqlite` (8 files, 63.9 MiB; the a and b tables are identical), `sobol.bin` (8 files, 3.7 MiB) and `checkpoints/` (996 files, 321.1 MiB: the per-task jets of all 865,664 tasks) |

Verify after unpacking: `data/C6_2/hosted_run-20260928-m8192.sha256` (per file, paths relative to `data/C6_2/hosted/`);
`remerge` does this first. Source: `LRI_C6_D2_HPC_production/run-20260928-m8192/` in the project folder (a verified copy
of the cluster run directory).

### (b) Archive only

| Item | Size | Why kept |
|---|---:|---|
| `LRI_C6_D2_HPC_optimized.zip` as delivered (sha256 55ec6457fdf7b69cc934abd6d6b4b3ea368b011756b38edd4e56c66fe2d0361b) | 54 MB (174 MB unpacked, 1,391 files) | the delivered package: the 1,390 files of the package's git baseline 3e643c8 plus the delivering model's prebuilt executable. Between 3e643c8 and the released 6aaf656, `reference/` and `src/c6_integrate.cpp` are unchanged, `src/kernel.hpp` gains only a test-only hook (`C6_FORCE_LEVEL`, not defined in production builds; the production binary is byte-identical), and `inputs/` gains source digests and the primitive allocation table |

The Slurm logs of the 428 elements and the merge (429 files, 62 KB; node names) are not released; what they record is in
`results/C6_2/CAMPAIGN.md`.
