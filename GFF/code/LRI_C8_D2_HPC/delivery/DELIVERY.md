# Completed C7(2) HPC delivery

## Revision 2026-10-02 (review fixes; local commits on top of fb64c47)

This revision acts on the review of 2026-09-30 (findings M1-M4, L1-L21) under the
Codex-approved plan `LRI_C7_D2_HPC_loop/PLAN.md`. It is software and provenance
work, not a new physics calculation: no physical C7(2) value is produced or
claimed, and `numerical_change` stays false for the native kernel.
- **Native code.** One `src/` hunk (A-L18: explicit `T(...)` at `kernel.hpp:144`).
  With default flags the compile commands are unchanged, and on symmetry (job
  567518) both Boost 1.77 builds are byte-identical to the `fb64c47` builds and to
  the 2026 production binaries. `--describe` and the native schema are unchanged.
  Correction (host finding H1): the compile failure the review attributed to
  Boost 1.86 came from the system Boost 1.66 (Expanse's `boost/1.86.0` module sets
  only `BOOST_ROOT`). Real Boost 1.86 compiles both `fb64c47` and this revision;
  Boost 1.66 fails for `fb64c47` and compiles this revision (Expanse jobs
  54583692/54583699). A-L18's acceptance text ("the original fails with 1.86 under
  GCC 11.4") rested on that misattribution; the table in `docs/NUMERICS.md` is what
  was demonstrated instead.
- **Job handling** ported from the C6(3) package: job-private runtime with
  digests and node fingerprints in every checkpoint; input verification at plan
  time; pos-ordered blocks; cost-proportional shards and calibrated estimates;
  resumable fail-closed merge; status, recovery and one guarded submission path
  with a campaign lock, queue checks and wall-time policies; Slurm templates
  with offsets for arrays above 1000.
- **Opt-in allocation options** (`--power-divisor`, `--primitive-allocation
  neyman`): allocation only; the defaults give exactly the delivered counts.
- **Reporting:** lower-order pulls with both SEs and the C6(2) reference,
  power-difference null tests, test-only results under `test_partial`.
- **Package:** schemas `c7-d2-production-2`, `c7-d2-group-2`,
  `c7-d2-hpc-result-2` (version-1 plans are refused; use `fb64c47` for them);
  `tools/verify_delivery.py --write`; records written only via `--output`.

Checks run on the packaging Mac (pure Python; no native build is possible there):
`tests/unit_orchestration.py`, `tests/check_inputs.py`,
`tools/reassemble_reference.py`, `tests/test_delivery_verifier.py`,
`tests/compat_2026.py` against the 2026 production, and
`tools/verify_delivery.py --strict`; `reference/SHA256SUMS` verifies. On the
clusters (commit 572a956; `benchmarks/symmetry_2026-10/README.md` lists every
job): D1 byte identity, `make test`, `make test-full` (3,511 kernels, both
backends, exact gate), `--strict`, the Boost version checks, real-Slurm drills
1-4, the decimal calibration (now in `tools/calibration.json`) and the block
throughput (0.909-0.947 busy cores). Fix round 1 (host review) changed tests,
tools, docs and the Makefile's non-compile lines; see `CHANGELOG.md`. The
sections below describe the delivery of 2026-09-30 and are kept unchanged; the
verification records `delivery/optimized_source_preservation.json` and
`delivery/verifier_tests.json` belong to that delivery (the manifest lists them
as historical).

## Scope

This is the final all-in-one packaging of the previously delivered optimized
full C7(2) program. It is not a new physics calculation or a new precision claim.
The power-free and power-containing sectors are both included. The complete
original numerical archive was restored under `reference/`, stripping only its
outer `LRI_C7_d2_complete/` directory. All 4,329 file contents match the source
ZIP byte-for-byte. No original raw data or mathematical derivation was edited.

The packed kernel inputs were regenerated from those reference files using the
unchanged `tools/prepare_inputs.py`. There are 3,511 required kernels at loops
three through seven, stored in ten sector/loop packs. The final source package
contains no machine-specific executable; build on the target cluster.

## What was added or repaired in this packaging pass

- `tools/verify_delivery.py`: standard-library inventory/hash verification,
  with optional strict checking for extra files.
- `tests/test_delivery_verifier.py`: valid, corrupt, missing, checksum-index,
  extra-file and unsafe-path failure tests (see the actual recorded test names).
- `tools/prepare_benchmarks.py` and fixtures: reproducible top-cost graph
  selections, Sobol direction matrices and task tables.
- Three benchmark/profile entry points now use these fixtures rather than
  referring to unavailable historical task files. No integration kernel or
  scientific production/assembly source was changed.
- `DELIVERY_MANIFEST.json`, `SHA256SUMS`, provenance and fresh validation logs.

## Evidence and provenance

The historical optimized benchmark aggregate JSON files and reports are retained
unchanged. Their original per-run task/net files and detailed timing logs were
not separately available after the interrupted delivery. The NEW benchmark
fixtures are explicitly marked as new; they do not claim to reconstruct those
historical timing streams. Profile and benchmark commands now generate fresh
matched old/new comparisons on the shipped fixed workload. No historical
performance number has been re-labelled as a fresh measurement.

`delivery/fresh_checks.json` records the checks actually rerun for this delivery,
with commands, return codes and logs. `delivery/reassembly.json` recomputes the
accepted full, power-free and power-correction means and covariance from the
unchanged original production data. This is not a new production integration.
`delivery/reference_preservation.json` lists every reference file's original
hash; `delivery/optimized_source_preservation.json` distinguishes the unchanged
scientific code from small packaging/benchmark repairs.

## Verification

From the unpacked source directory:

```bash
python3 tools/verify_delivery.py --strict
python3 -m pip install -r requirements.txt
make -j4
make test
make -j4 gmp                   # Optional: GMP development headers/library needed
make test-full
python3 tools/reassemble_reference.py
```

Verify before generating build/test artifacts. Afterwards the default verifier
allows unlisted local build files while still requiring all delivered payloads
to match. `sha256sum -c SHA256SUMS` is an alternative content check on systems
with GNU coreutils. Internal checks detect corruption but are not a cryptographic
signature; compare the separately supplied ZIP hash as well.

The numerical algorithm, default decimal300 fallback and opt-in GMP350 backend
are unchanged. No high-statistics physics production or multi-node performance
test was performed during packaging. Earlier empirical uncertainty allowances
remain empirical, not rigorous enclosures.
