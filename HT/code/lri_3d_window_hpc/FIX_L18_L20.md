# L18/L20 projector repair — 0.2.1rc1

## What this release changes

The supplied Expanse report identifies a `scipy.linalg.null_space` / LAPACK `gesdd`
nonconvergence during L18 angular setup, before any Hamiltonian eigensolve. L20
was not attempted on Expanse. This repair implements the report's minimal-first
strategy and adds the missing sizing, logging, and regression tools.

* The default `null_space(jp, rcond=5e-13)` call is unchanged. Only a
  `numpy.linalg.LinAlgError` triggers a second SVD using `lapack_driver='gesvd'`.
  The fallback requests **full** right singular vectors and uses the same rank
  cutoff. An economy SVD of a wide matrix would omit the very null vectors needed.
* Both ranked and legacy highest-weight builders use the repair; this includes
  scalar and spin-1/spin-2 diagnostics. Existing column signs and ordering remain.
* Every returned kernel must have the exact representation-theoretic nullity,
  finite entries, `max(abs(Jplus @ Q)) <= 1e-10`, and
  `max(abs(Q.T @ Q - I)) <= 1e-10`. No state, tolerance, or amplitude is dropped.
* Nonfinite input, impossible dimensions, a bad nullity, and a failed residual
  remain errors. A second SVD failure remains a failure, with block context and an
  optional exact matrix dump; the code never returns an empty substitute.
* Projector COO assembly uses numerical chunks instead of Python scalar lists.
  This changes storage, not coefficients, ordering, or the SVD policy.
* Exact graph/edge counts check the graph-array budget **before** allocations.
  The old estimate could allocate substantial initial arrays before discovering
  the edge arrays would exceed the requested budget.
* Sparse-projector hashing is streamed rather than copying the entire projector
  into one `bytes` object. Its digest is byte-for-byte the previous digest.

There is no Hamiltonian, normal-ordering, regulator, window, local-basis, ARPACK,
precision, or fitting change. Results identify the numerical release as 0.2.1rc1.
The principal numerical arrays remain float64 and graph pointers remain int64.

## Expanse integration boundary

The available source is the original performance ZIP (baseline `b5f6e1f` in the
report). The report says `e895443` changed only added site-layer files, leaving the
original numerical files and 615-entry manifest unchanged. The later 21-file
Expanse site layer itself was **not supplied**. This patch therefore does not
modify or replace `cluster/expanse/`, `EXPANSE.md`, or the site lane tests.

Apply the surgical patch to a NEW working branch of e895443. Do not unpack this
baseline distribution over the site checkout or overwrite a running installation.
The standalone ZIP is a reference/test distribution, not a merged Expanse release.

```bash
# In a fresh e895443 working branch; substitute the actual patch path.
git apply --check /path/to/lri_3d_L18_L20_fix.patch
git apply /path/to/lri_3d_L18_L20_fix.patch
python scripts/rebuild_fix_manifest.py
python tests/verify_manifest.py
```

The manifest rebuilding script checks every old baseline file against its pinned
original hash or its explicitly declared patched hash. It does not ignore changed
files, and it does not bless arbitrary local edits. A new distribution manifest is
written; the original is retained in `provenance/MANIFEST_0_2_0.sha256`. The site
release builder must separately regenerate its `RELEASE.sha256` and validation
receipt. The patch does not claim to edit an unseen `receipt.py` contract.

The complete ZIP already has its new manifest; do **not** run the patch-only
manifest builder on the ZIP after tests have rewritten validation evidence.

### Historical benchmarks are not silently rebound

The 83 shipped timing records remain unchanged. They are verified against the
pinned `reference/performance_0_2_0/code` snapshot that produced them. The revised
`tests/validate_benchmarks.py` then runs **fresh current-source spectrum and
forced-fallback checks** and verifies their source identity before passing.
There is no `expected-stale`, skipped-stage, or collect-only substitute. These
records establish historical performance provenance, not new timings for this fix.

All changed numerical code invalidates the old source/release identity and static
cache implementation key. Old caches are left intact but are not reused as this
release's caches. Old campaigns/checkpoints must not be relabelled or resumed as
new-source runs. Reuse old couplings only as explicitly recorded initial guesses
in a newly frozen campaign, with the site's predecessor/basis validation policy.
The former Expanse receipt 54742071 does not certify this release.

## Tests run locally and their scope

See `validation/l18_fix/` and `REPORT_L18_L20.md` for actual records. The main
suite includes all 62 inherited package cases and 34 additional cases. The site
receipt must still require collected = executed, zero failures and zero skips;
its old 122-case count should not be hard-coded for an expanded suite.

```bash
export OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 OMP_NUM_THREADS=1
export NUMBA_NUM_THREADS=4
python -m pytest -q
python tests/validate_physics.py
python tests/validate_numerics.py
python tests/validate_large.py
python tests/validate_benchmarks.py
```

Tests compare fallback **subspaces** and rotated operators, not individual SVD
columns. Different successful SVD drivers can choose different orthonormal bases
for a degenerate kernel. The normal successful `gesdd` branch is left unchanged.

On this local runtime the original code itself fails at L16. The repaired code
completes that projector by retrying the failed blocks. Consequently a claim of
full original-versus-new L16 bit equality is not possible on this runtime. At
successful smaller cases, including the complete L14 graph/projector, the arrays
are compared exactly. Fresh raw/window L8 spectra at x=.6,.5182 are also compared.
Examine the actual L8–L16 Expanse records again on the new release; they are not
available here beyond the status report's rounded table.

## L18 and L20: start with exact counts, not guessed dimensions

The following commands allocate only small character/counting arrays. They do not
construct the full Fock graph, call SVD, or calculate a spectrum:

```bash
python scripts/probe_large_setup.py --L 18 --spins 0 1 2 \
  --output runs/preflight_L18.json
python scripts/probe_large_setup.py --L 20 --spins 0 1 2 \
  --output runs/preflight_L20.json
```

Each reports exact full-state and edge counts, natural-inversion spin dimensions,
block-size histograms, largest block signatures, and graph-array bytes. Vertex
nonzero counts, peak process memory, solve time, and SU are NOT inferred from this
census. In particular, graph-array bytes are only a lower-level storage component.

### Actual staged setup (inside an adequately sized allocation)

The L18 numbers below are the *provisional settings from the supplied report*,
not a new calibrated resource guarantee. Use its reviewed staging/receipt layer
before invoking the probe in a compute job. Run one cutoff/spin per job initially.

```bash
python scripts/probe_large_setup.py --L 18 --x .6 --spins 0 --nz 16 \
  --execute --stop-after vertices \
  --max-bath-states 50000000 --memory-limit-gib 40 --threads 8 \
  --dump-dir runs/L18_failed_blocks --output runs/setup_L18_J0.json
```

`--stop-after graph` or `projector` isolates the earlier stages. Omitting
`--execute` is always counting-only. The output is checkpointed at every stage,
with status `started` before the expensive operation, and includes current RSS,
process high-water RSS, dtypes, vertex nnz, block maxima, and retry counts. A
sibling `.projector.jsonl` records large block allocation/start/end and fallbacks.
A crash leaves the last completed stage; it does not manufacture a completion.
No mid-SVD resume is claimed.

For ordinary production invocations, a unique per-process
`HT3D_PROJECTOR_LOG=/absolute/job-specific/path.jsonl` enables the same logging.
The log's parent directory must already exist. `HT3D_PROJECTOR_DUMP_DIR` opts into
exact `.npy` matrices and JSON context when both SVD drivers fail. Logs are not a
shared multiwriter database. The scalar final result also includes
`scalar_projector_checks`; diagnostic sector checks include their projector data.

For L20, first run a graph/projector probe with `--max-bath-states 200000000` and a
budget appropriate to the measured allocation. The graph alone occupies about
17.41 GiB of numerical arrays, BEFORE projectors, vertices, LAPACK workspaces,
Krylov vectors, or Python/transient storage. No full L20 setup or eigenvalue run
was completed in the local 4-GiB environment. The report's 150–250 GiB full-run
estimate remains unmeasured, not confirmed by this patch. Do not reuse the scalar
budget for `--diagnostics all`; the spin-2 space is substantially larger.

### Isolated physical-block replay

A largest-species block can be generated independently without allocating all
40,968,710 L18 states or all 182,727,113 L20 states:

```bash
# Real L18 scalar block, with an explicitly INJECTED initial-driver failure.
python scripts/probe_species_block.py --L 18 --spin 0 --force-fallback \
  --memory-limit-gib 2 --output runs/L18_block_retry.json

# Largest L20 block: sparse assembly and exact character-moment checks only.
python scripts/probe_species_block.py --L 20 --spin 0 --assemble-only \
  --output runs/L20_block_sparse.json
```

For dense L20 block testing, remove `--assemble-only` and choose a sufficiently
large memory limit/allocation. `--force-fallback` is strictly a testing injection;
it is not a production setting, and its timings do not imply that `gesdd`
naturally failed. The precise block that failed in Expanse job 54739261 remains
unknown because that job did not save its block context.

## Recommended deployment order

1. Review/apply this patch in the site repository and issue a new immutable release.
2. Obtain a new on-node receipt without weakening any test gate. Verify raw/window
   L8–L16 regressions against the existing calibration outputs on that runtime.
3. Complete L18 graph/projector/vertex probes, including separate J1/J2 probes.
   Test the new static cache's concurrent publication/read behavior on Lustre.
4. Calibrate one L18 continuation at x=.6 and the separate near-endpoint lane only
   after its exact-x teacher has been generated/validated. Measure the new costs.
5. Probe L20 stages before committing to a full point or a 15-point budget.

The existing L<=16 production campaign can remain on its already validated release;
this patch does not require invalidating its scientific results. Keep the new-source
and old-source campaigns separate. There is no physical continuum improvement or
new curve point claimed in this repair.
