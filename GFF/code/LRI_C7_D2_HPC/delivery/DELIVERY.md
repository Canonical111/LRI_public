# Completed C7(2) HPC delivery

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
