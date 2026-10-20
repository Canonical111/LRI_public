# 2026-09-26 direct primitive sector (PLAN2)

- `tools/assemble.py`: the primitive sector is defined as `primitive && !power` (44 L7 classes; the
  `primitive_guard.primitive_classes` metadata changes from the raw-flag count of 64 to 44). It is counted exactly
  once:
  - either by the retained input, where no source may support a guarded class, including power sources;
  - or by one direct unit-weight primitive source that supports exactly those classes.

  Source metadata is bound to the verified campaign manifest. Authenticated archived power records without counts
  are accepted as power-only streams. There are new result keys `primitive_source` and
  `retained_primitive_crosscheck`.
- `tools/combine.py --primitive DIR`: uses a verified `--selection primitive` campaign instead of the retained
  input. The inter-batch χ² is centred so it is invariant under the replacement.
- Inspection fixes:
  - Primitive-class support is taken from the verified manifest counts. The merged files must match them, and
    `campaign.py verify` checks every merged header (L, N, replicates, seed, counts, manifest hash) against the
    manifest.
  - All new-style sources at one loop order must share the inventory, index and Gamma input hashes. The inventory
    and Gamma files must also equal the authenticated archive inputs (reference/SHA256SUMS), including in mixed
    archived/direct assemblies. `combine.py --primitive` compares the primitive campaign's inputs with the
    batches'.
  - The `--original` baseline is the committed fixture `tests/fixtures/assemble_original_0227dc5.json`;
    `tests/regenerate_original_baseline.py` rebuilds it from git history.
- `combine.py --jobs N`: re-verifies campaigns in parallel processes (identical output; the test requires byte equality).
- Tests: the direct-primitive combine and χ² invariance; rejection of incomplete, doubled, mislabelled,
  cancelling, complementary, kind-contradicting and wrong-inventory configurations; `--original` equal to the
  commit-0227dc5 output apart from the two new keys and the corrected class count.

# 2026-09-25 review fixes

Kernels are unchanged: `tests/compare_binaries.py` requires bitwise-identical rows against the delivered source
(baseline commit `c21b9e8`); only the added `build` output key may differ.

- Slurm launch: `srun` now gets `--cpus-per-task="$SLURM_CPUS_PER_TASK"`. On Slurm 22.05–23.02 the step did not inherit the
  job's CPUs per task, got one CPU, and every OpenMP thread was pinned to it (effective parallelism 0.99 of 8 threads, measured on SDSC Expanse,
  Slurm 23.02.7). `campaign.py run` refuses fewer allowed CPUs than threads unless `--allow-oversubscribe` is given,
  and drops `OMP_PLACES`/`OMP_PROC_BIND` on unconfined nodes (more allowed CPUs than threads).
- Templates: optional `C7_ENV_SETUP` sourced before strict mode, `C7_PYTHON` with a Python ≥ 3.8 preflight (exit 64),
  `C7_INDEX_OFFSET` for plans larger than `MaxArraySize`, empty-array expansion safe on bash < 4.4.
- Build portability: `CXXFLAGS ?= -O3 -g` with the required flags always appended, `CPPFLAGS` for include paths,
  automatic `-lstdc++fs` for GCC 8, optional `RPATH=1`; `tools/toolchain.py` gives every helper that compiles C++ the
  same command builder instead of a literal `g++`.
- C++ (no numerical change): temporary output created with mode 0666 so the umask applies; output metadata
  `"build":{"compiler","boost"}`.
- Campaign integrity (`tools/campaign.py`, manifest schema `c7-campaign-2`):
  - `payload_sha256` of the canonical scientific content, published atomically inside each checkpoint; recomputed on
    reuse, at merge and by the new `campaign.py verify DIR`; corrupt checkpoints fail loudly and are set aside only by
    the explicit `campaign.py quarantine DIR IDENTITY`;
  - executable, planned inputs and net re-hashed before every C++ invocation; the digest actually checked and the
    resolved runtime libraries (`ldd` path and SHA-256) recorded in provenance;
  - no silent default index; SIGTERM unwinds and removes the temporary block directory; file modes follow the umask;
  - transactional plan (`sobol.net` and `manifest.json` published only after every validation); `inputs` stored
    relative to the campaign inside a production directory; `run --executable` override that must match the hash;
  - merge coverage checked exactly against the manifest (replicates × active graphs at their totals), statistics
    computed before publishing, idempotent reruns (byte-identical reuse or an error), `audit.json` last; legacy
    `c7-campaign-1` campaigns still merge.
- Production (`tools/production.py`, schema `c7-production-2`): per-campaign `--design` with validation (positive
  integers, power-of-two QMC multipliers, equal A/B pair multipliers); `--refine7` degree-6/7 check campaigns;
  `--inputs`/`--extra-inputs` copied into a self-contained `<production>/inputs/` snapshot; relative paths and a copied
  affine map, so a production directory can move; `--label`; lazy NumPy import, so `run` needs only the standard
  library; `run` forwards `--executable`/`--scratch`/`--threads`; audited campaigns are re-verified on merge; the final
  `C7_result.json` is published atomically and verified on rerun.
- Assembler (`tools/assemble.py`):
  - reproduces the full `final_analysis.py` diagnostic set (power levels, resolution sequence, C3–C6 checks,
    spurious-pole z-scores, half-splits, uncontrolled C7, applied control) to 2e-15 relative, bootstrap SE within 5%;
  - uncontrolled estimator with its SE and per-L zero-pole control terms with SEs;
  - pre-registered allowance: headline to 2 significant figures including the degree-7 check, plus the archived
    `ceil_to_1000` literal, with every component; "systematic tension" flag for |z| > 3 at C5 or C6;
  - `role: "check"` sources reported as a level but never added to the estimate;
  - legacy archive records accepted only via `--original` or `legacy_archive: true` and authenticated against
    `reference/SHA256SUMS`;
  - pairing guard (lower subtracted degree, complete, verified, same manifest/rate/seed/replicates/counts),
    stream-overlap guard over primaries and subtractions (path and content hash), retained-primitive guard;
  - unique source names with campaign/level aggregates; reconciliation of components with the total mean and
    covariance to 1e-9; location-independent result files; atomic, idempotent output.
- New tools: `tools/combine.py` (verified combination of independent batches with a byte-identical canonical
  scientific configuration, distinct seeds, batch-qualified sources, inter-batch χ²) and `tools/design.py`
  (pre-registered per-campaign Neyman allocation from the archive and a pilot).
- Tests: `tests/test_pipeline.py` (pure Python, in `make test`); `tests/validate.py` with the QMC tolerance tightened to
  1e-18, power degrees 1 and 5, verify/remerge/mode checks and the diagnostic reproduction; `tests/compare_binaries.py`;
  `tests/check_quad.py` with executable hashes, `--inputs`/`--counts`/`--reference-ld` and degree 7;
  `tests/make_validation_inputs.py`, `tests/check_weights.py` and `tests/check_degree.py` for the degree-7 weight
  checks.
- New `inputs_extra/`: degree-7 weights `cw_L{5,6,7}_N7.txt` (100 digits) with provenance and check reports. On x86-64:
  - 100 vs 150 digits agree to 3.3e-95;
  - moment errors are at most 3.3e-89;
  - regenerated degree 6 equals the shipped weights exactly;
  - original vs optimized at degree 7 agree to ≤1.2e-14 of slot scale.

  They are used only by the `--refine7` check campaigns.
- Documentation corrections: the srun statement; the MP100 difference comes from precomputed v2/v3 powers, not the
  prefix trie; the projected-C7 replay difference is 1.65e-13 (exact Decimal), not 1.34e-14; the replay records
  predate the delivered binary; the Sobol self-check covers direction columns 0–3 only; the benchmark mix is much
  heavier than production (production-weighted continuous speedup about 3×); real production cost (about 3 core-hours
  at multiplier 1); durable shared paths instead of `/scratch/$USER`; absolute `--output` logs; the `afterany` merge
  recipe; new variables, minimum versions and file permissions; an Expanse recipe.

# Optimization release

- Profiled continuous precision fallbacks and tensor geometry/weight/contraction phases before rewriting.
- Added ordered-prefix continuous kernels at unchanged long-double/binary128/MP100 precision.
- Replaced unbounded full-grid power geometry storage with bounded tiling and compensated sums.
- Added global-index deterministic work units, OpenMP load balancing and independent-node job dispatch.
- Added immutable plans, no-clobber atomic checkpoints and complete-coverage deterministic merging.
- Added the full 21-campaign C7 production design and exact archived-data reassembly.
- Included reproducible regression tests, binary128 replays, profiles, timing/memory benchmarks and Slurm templates.
- Preserved every original C7 reference file; no research result or TeX derivation was changed.

Measured scope and known tradeoffs are documented in docs/PERFORMANCE.md.
No new full C7 integration, GPU port, or actual multi-node scaling test is claimed.
