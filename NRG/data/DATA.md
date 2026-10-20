# NRG data

Everything needed to reproduce the results is in git. There is nothing to fetch. The production scratch data are not
released: per-item checkpoints, trial flows of the bisection and lane stdout. They are not needed, because every record
holds the complete final flow, the derivative and the window audit.

## `data/records/<campaign>/<item id>.json`: 197 result records (47 MB)

| campaign | records | content |
|---|---:|---|
| `example_K64_B10` | 3 | the package's example items (s = 0.8, 0.9, 0.98 at K = 64, n_b = 10, Λ = 3) |
| `ds13` | 146 | the thirteen points with scans in K, n_b and Λ |
| `lambda_pilot` | 18 | Λ = 1.5, 2, 2.5 at Δσ = 0.2, 0.1, 0.05 |
| `lambda_followup` | 30 | Λ = 2.5 at all other points; Λ = 2 at K = 192, 256 |

Each record is JSON with three keys:
- `sha256`: SHA-256 of the canonical JSON (sorted keys, no spaces) of `{"identity": …, "payload": …}`.
- `identity`:
  - the configuration (s, Λ, n_b, K, N, Δ, threads);
  - the kind, bracket, fraction, tolerance, iteration limit and derivative flag;
  - `source_sha256`, the solver source hash `3a40deb333e1…`;
  - `runtime`, the Python, NumPy and SciPy versions and the BLAS libraries.
- `payload`:
  - `critical_flow`: the flow at α_c, with per-site records and the bisection summary;
  - `tuning`: the bisection history and final bracket;
  - `tangent`: the derivative flow, per site ∂_α g_n and ln|∂_α g_n|;
  - `analysis`: every window with its Δ_E, fit residual and variation, the quality range and the selected window
    (the settled window of note §3.7);
  - `scope`.

Per-site records hold:
- the parity gap `odd_gap`;
- the lowest levels of each sector;
- the boson occupation and top-level probability of the newest site;
- spin and scale correlations.

The eigen-residual and orthogonality checks are stored once per flow, as the maxima over the checked sites
(`validation.max_checked_eigen_residual`, `validation.max_checked_orthogonality`), not per site.

`INDEX.json` in each campaign folder lists the generation of every record. Generation 2 means the item was interrupted
by the cluster outage of 3 October 2026 and resumed from its checkpoint.

The records are **byte-identical to production**. `code/analysis/summarize.py` recomputes each checksum. It checks the
identity against the item in `inputs/manifests/<campaign>.json` and the runtime against
`inputs/validation_receipt/receipt.json`, and it re-applies the numerical gates. A single changed byte stops `make
replay`.

## `data/lane_logs/<job id>/events.jsonl`: one file per production lane job

One JSON line per item start and end: item id, threads, wall seconds, peak RSS (KiB) and exit code. `summarize.py`
reads them for the cost table (`resources.json`) and the thread-hour total. For the release the host names in the events
were replaced by the anonymous node names `amd-1` … (consistent with `job_accounting.txt`), and the per-lane `node.json`
was dropped.

## `data/job_accounting.txt`

The Slurm accounting (`sacct`) of every job of the study: validation, smoke, drills and production. It gives the job id,
name, partition, state, start, elapsed time, exit code and node. Node names were replaced by `amd-1` … `amd-8`
consistently. `build_tables.py` turns it into the note's resources table.

## Related inputs (`inputs/`)

- `items/*.json`: the item lists. `code/campaigns/make_*_items.py` regenerate the ds13, pilot and follow-up lists byte for
  byte (run them in an empty directory). `example_items.json` (the package's example list) and `smoke_items.json` (the
  small list of the pre-production smoke lane) were written by hand.
- `manifests/*.json`: the frozen manifests that were submitted. Each holds the items plus the solver source hash.
- `validation_receipt/`:
  - `receipt.json`: the receipt of validation job 569161, itself a checksummed record;
  - `GIT_SHA`: the code commit;
  - `lscpu.txt`: the node CPU.
- `environment/ENV.json`: versions and `pip freeze` of the production venv. For the release the host name was replaced by
  `<NODE>` and the venv path by `<SCRATCH>`; the cluster's module paths were kept. Its `threadpool_info` was recorded on
  the login node; the compute-node runtime that binds the records is the one in `receipt.json`.
- Dropped for the release, as not needed to reproduce: `validation_receipt/host.txt`, `validation_receipt/threadpool_info.json`
  and `environment/wheels/`.

## Outputs of the checks

- `independent_check/out/c1.json` … `c8.json`: the second implementation's outputs, in the format described in
  `independent_check/NOTES.md`. These hold the chain, α_c, critical flow, finite-difference derivatives, window audit
  and timing, plus a block describing the run environment, in which only the node name (`hostname`, `SLURM_JOB_NODELIST`,
  `SLURMD_NODENAME`) was replaced by `amd-9` for the release.
- `independent_check_compare/{compare,trusted_windows}.{json,md}` and `method_comparison/comparison.{json,md}`: written
  by `make replay` and compared byte for byte (`comparison.json` to 1e-9 + 1e-9 relative, `.md` to the last printed digit).
- `results/ds13_final.json`, `ds13_final_table.md`, `lambda_study.json`: the final table and the Λ study, computed from the
  records by `code/analysis/build_tables.py` with the estimator of `code/analysis/estimator.py`. Field names: `Delta_E`
  (the value), `depth`, `keep_nb`, `Lambda`, `total` (the error components of note §4; `null` for the points not
  converged in chain depth), `settled`, `plateau_drift`, `extrapolated`, `extrapolation_fits`, `extrapolation_status`
  (`null` values where the extrapolation is not determined, Δσ = 0.001), `crosschecks` (the late and crossover fits of
  `code/analysis/crosscheck.py`, not adopted), and `midpoint` (the superseded estimator, note App. E). Replay compares
  these files with tolerances, because the fits differ in their last bits between library builds (REPRODUCE.md §6). Record field names map to symbols as `keep` = K, `nb` = n_b, `nsites` = N,
  `Lambda` = Λ, `tunneling` = Ω (the tunneling amplitude), `odd_gap` = g_n.
- `../MC/data/1d/scan_data/FIT_V3_SCAN.json`: the Monte Carlo table used by `method_comparison/`. It is part of the MC
  folder (SHA-256 `fb6ebb16…`).
