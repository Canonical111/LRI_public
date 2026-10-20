# HT_2d data and results: what is where (d = 2 finite-coupling HT)

Everything needed by `test`, `smoke` and `replay` of `HT/code/lri_2d_window_hpc` and `HT/code/lri_2d_window_indep` is in
git; nothing is hosted (`make -f public.mk fetch-data` says so). Per-file SHA-256: `SHA256SUMS_HT_2d.txt` (paths from the
repository root; the last column below is the SHA-256 of that folder's lines).

| Folder | Contents | Files | Size | Largest | Used by | SHA-256 of list |
|---|---|---|---|---|---|---|
| `HT/data/HT_2d/prod1` | prod1 records (348 self-hashed JSON), frozen spec, inputs (bases, seeds) | 375 | 38.36 MiB | 0.18 MiB | replay, smoke, rerun | `e48edb4ee9f6d785…` |
| `HT/data/HT_2d/pert_crosscheck` | consistent-scheme C0..C8(N), N = 8..24 (extract) | 2 | 0.00 MiB | 0.00 MiB | replay (d2.pert_consistent) | `995137c96cda2809…` |
| `HT/results/HT_2d/prod1` | collected tables (collect.py) and largest_N.csv | 6 | 0.55 MiB | 0.23 MiB | replay | `62b12c579dd45f6b…` |
| `HT/results/HT_2d/valley_N24` | 12 valley-scan outputs | 13 | 0.02 MiB | 0.00 MiB | replay (d2.valley.*, d2.no_root, d2.fold) | `a6ca8dd2bd64ab25…` |
| `HT/results/HT_2d/independent_check` | 155 independent-solver outputs | 156 | 0.77 MiB | 0.01 MiB | replay (i2.*), smoke | `683f1653a252b95d…` |

Binding: the prod1 records carry `record_sha256` (SHA-256 of their canonical JSON without that key) and bind the code
(`configuration.source_sha256`, = `source_hash()` of `HT/code/lri_2d_window_hpc` at 889a968), their basis and their
seed. They ship byte-identical, with the original cluster paths inside: these are history, not paths to use. The
independent-check outputs embed the `record_sha256` of the records they were compared with. The valley outputs and the
independent-check outputs are not self-hashed; their machine identifiers are replaced by placeholders.

Archive only (not published): the Slurm logs, Newton checkpoints and claims of prod1, the stalled N = 24 restarts at
Δσ = 0.125, 0.126, the drill campaigns, and the review transcripts.
