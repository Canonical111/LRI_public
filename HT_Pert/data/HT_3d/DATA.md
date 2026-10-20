# HT_Pert/data/HT_3d: records of the d = 3 perturbative HT campaign

Everything `make replay` reads is in git; nothing is hosted.

## `pert3d/` (194 files, 1.5 MB, largest 0.06 MB)

The production records of the SDSC Expanse campaign `pert3d` (release `7c8a67e`, 2026-10-08/09). `MANIFEST.sha256`
holds the sha256 of every file as produced; `make replay` checks it (row REC-MANIFEST).

- **Byte-identical (20 files):** `results/`, `gates/`, `crosscheck/`. Each carries a self-hash of its request
  (`request_sha256`), the sha256 of the code it ran (`source_sha256`) and of its vertex store's manifest; the
  crosscheck comparison records bind the four L = 16 result files by sha256. They keep the cluster paths, user and node
  names of the run, and the replay recomputes the gate and crosscheck numbers from them.
- **Scrubbed (the files listed in `SCRUBBED.txt`):** `campaign.json` and the per-stage records `records/`. No other
  file binds their bytes; before publication the authors' cluster paths, user and account names in them were replaced
  by placeholders (AGENTS.md rule 7). The values the replay reads from them (store manifest sha256, release
  fingerprint, exit codes, cutoffs) are unchanged; REC-MANIFEST counts the listed files as scrubbed and fails on any
  other difference.

| Path | Contents |
|---|---|
| `campaign.json` | the frozen campaign: release (git sha, tarball sha256, fingerprint), order 8, long double, CPU class, validation receipt, environment fingerprint and identity |
| `results/L16/c16_{raw,consistent}.json`, `results/L18/c18_*.json`, `results/L20/c20_*.json` | the coefficients C_0..C_8, r, g, the four seed energy series and every subcutoff vacuum energy, at each store's own cutoff, with the request (incl. `source_sha256`, `store_manifest_sha256`), the execution record and the residual gate |
| `results/L20/c{16,18}_*.json` | the same at L = 16, 18, solved from the L20 store (cross-store check) |
| `gates/L{16,18,20}/{raw,consistent}_c14.json` | each store solved at L = 14 and validated against `code/lri_3d_hpc/results/reference_coefficients_L14.json` (the original code) |
| `crosscheck/L16/` | L = 16 solved with the recurrence strategy, and the comparison records with the stationary results |
| `records/L{16,18,20}/<stage>/` | one record per stage task (prepare, images, matrix, finalize, verify, gate, solve, crosscheck): job, node, seconds, peak memory, store manifest sha256, release fingerprint |

Not shipped: the job logs, the submission ledger and the validation receipts (operational; their results are quoted
in `code/lri_3d_hpc/public/PROVENANCE.md`).

## Not hosted

| What | Size | Why |
|---|---|---|
| vertex stores L16, L18, L20 (`stores/L<L>`, Taylor-vertex CSR arrays in x87 long double) | 2.6 GiB, 22 GiB, 177 GiB | rebuildable by a production rerun (`public/REPRODUCE.md`); not read by test or replay; the long-double `.npy` files are not byte-reproducible (6 uninitialised padding bytes per value), their content is pinned by the padding-free value fingerprint in the records |
| L20 intermediate pipeline files (projector, particle images, matrix tasks) | 363 GiB | same; the L20 projector alone took 9.9 h |
