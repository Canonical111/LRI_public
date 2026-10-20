# C8(3): full-coefficient HPC package (in development; generalizes LRI_C7_D3_HPC@a6ce987)

This package is being generalized from the C7(3) package (C0 through C7 in dimension THREE, ε = 2s−3, both the
power-free and the power-containing sectors) to C8(3), on symmetry and on Expanse. Amendment A1 (2026-10-05) puts
symmetry first and keeps Expanse for its template checks. See `CHANGELOG.md` for the stages done so far and
`LRI_C8_D3_HPC_loop/PLAN.md` for the plan.

**Status (2026-10-07): Stage 6 complete (G6 closed on the user's acceptance of the listed residuals).** The code is final at
K₆ a914db2 (`CHANGELOG.md`). Fix round 2 followed the second and final Codex inspection round; the user chose a
targeted fix round with no third round, so fix round 2 is not Codex-reviewed. Its cluster chain passed (`docs/HPC.md`
"Stage 6 results"). **G5 holds except:**
- **A-PERF-3 / A-SMK-4: per-block SHORTFALL.** Three of J-SMK-4's 789 blocks are below 0.95 (0.916, 0.929, 0.936;
  walls of 5.5–63 ms, 1.4e-6 of the integration core-seconds). Its cause is reported: per-launch overhead and
  end-of-block imbalance are possible explanations, not measured
  (`benchmarks/symmetry_2026-10-c8/stage5_59d4922/smk4/thru_report_s6b.json`).
- **A-ORC-4 (i): fixed by F8-d3, and passed in J-DRL-5 (re-merge 570796) and J-DRL-8 (re-merge 570815) on real Slurm**
  (Stage 6).
- **A-ORC-13: PASS on re-derivation** from J-SMK-4's 82 hook records (`smk4/thru_report_s6b.json`).

Details: `docs/HPC.md` "Stage 6 results", with "Stage 5 results" kept as the historical record, and `docs/PERFORMANCE.md`
"C8(3) Stage 5". The G5 table is `LRI_C8_D3_HPC_loop/artifacts/G5_TABLE.md` (its "Stage 6 update").
- **Stage 5 (complete).** Its verdicts are kept as recorded and labelled historical where Stage 6 replaced them:
  A-ORC-4 (i) FAIL and A-ORC-13 FAIL, now pass as above; A-PERF-3 PASS on the time-weighted mean, now a SHORTFALL per
  block (`docs/HPC.md` "Stage 5 results", whose table links the replacements).
  - **Final validations.** J-VAL-1..4 and J-RUN1 passed on the final Stage-5 code: 2241d64, with val1 on its
    test-only successor e3b9252 and val4 on Expanse. J-VAL-1-G passed on the tests/tools commit c4b9502, and so did
    J-E0-final on Expanse.
  - **Cost models.** Stage 5: symmetry `0fc934e7…` (J-SWEEP-2 570403), Expanse `56df9d61…` (54694976), both J-BLDs
    passed. Stage 6 refreshed symmetry's on the fix-round-1 binary `e9b6f6c3…`: `gmp_symmetry_epyc7543_c8.json` is now
    `554bb1d6…` (sweep2 570664, data-only commit D′₁ 3e2480a, J-BLD 570738). Expanse's refresh is pending.
  - **Smoke, drills and the design chain.** The smoke and its twins, the drills J-DRL-0..9, J-DES-5 and the J-EXP
    template checks on Expanse passed, except the re-merges after recovery in J-DRL-5 and J-DRL-8 (F8-d3; historical:
    both passed in Stage 6). J-SMK-3 passed (A-SMK-3): fallback freeze, both batches and the partial and final
    combines (label partial, final false). J-DRL-10 passed (A-ORC-17 real), closed by the user's decision
    (PLAN-REVIEW-LOG.md:667).
  - **Throughput.** Stage 5's R-SMK4 recorded A-PERF-3 PASS (busy 0.937, OpenMP time-weighted 0.990) and A-ORC-13
    FAIL (F13-d3). Both are historical; the current verdicts are those above.
  - **Pilot readiness.** J-PIL-0 published the PA plan and its `lanes 2/3 --dry-run` passed. `docs/PILOT_RUNBOOK.md`
    is the pilot runbook on symmetry.
- **Stage 6, fix round 1** (F8-d3, F13-d3, S4-007, the CPU pin <NODE>/<NODE>, and groups A–C of the first inspection
  round). Revalidated on symmetry (`docs/HPC.md` "Stage 6 results"):
  - the bitwise rows proof 570658; val1 570736 on K₃ (PASS; 19 SITE_REFUSED, three of them disclosed as lost
    real-cluster coverage); sweep2 570664 and J-BLD 570738;
  - the re-plans DL, DA, PA and DL2;
  - the drills S2-001 (vendor pin), F7 (scancel), J-DRL-5 and J-DRL-8;
  - the rename probe: BeeGFS, like Expanse's Lustre, takes the `recheck_rename` fallback.
  - PA was re-planned (2,737 graphs, 30.7 busy core-h). Its `lanes 2/3 --dry-run` refused 65 while C62d's 9/3 production
    window was open, because `amd_total ≤ 8` could not express it. Fix round 2 lets a dated re-split reach 12 (docs/HPC.md, H11).
- **Fix round 2** (the round-2 findings the user chose, and the H11 re-split up to 12). Revalidated on the final code:
  val1, val2 and val3 on symmetry; sweep2, J-BLD and J-PIL-0 (PA2); the F7 drill on the new stop path. On
  Expanse: the bitwise proof, val1 and sweep2.
- **Next: Stage 7 (the pilot).** It needs the user's pilot line, its site and an H11 window.
- **Accepted by the user** (after the second inspection round, 2026-10-06: a targeted fix round, no third Codex
  round), as residuals:
  - S2-R2-002, S2-R2-003, S2-R2-004 = S3-R2-008 and S2-R2-006: concurrency races outside the operating procedure;
  - S2-R2-001 and S1-R2-04: defense in depth behind working guards;
  - S1-R2-03 beyond its duplicate-ID refusal.

Since Stage 3a:

- **Native worker.** One worker, two orders (`bin/c8d3_{gmp,decimal}`, `src/c8d3_integrate.cpp`): order 7 replays
  C7(3) bit for bit against the unchanged original worker (`make c7ref`, `reference/src`), order 8 is production
  (`docs/NUMERICS.md` "Order modes"). The default backend is GMP350.
- **Tooling.** It plans, runs, checks and merges restartable campaigns (24 groups: 2 campaigns × 2 sectors × L3–L8)
  through the guarded submitter (Expanse and symmetry), and assembles results with the vendored order-8 assembly
  (`docs/HPC.md`).
- **Results so far** (C7(3), inherited).
  - The archived C7(3) is −227.61810947469945 with sampling SE 3.8273968756607397.
  - The C7(3) run1 campaign (symmetry, M=4096, 2026-09-30) gives −220.35448047392794 with sampling SE
    0.031818800575016494. `tests/compat_run1.py` reassembles it with the order-8 assembly at order 7.

## Verify, build, test

The integrity check comes first, before any local build output exists:

```bash
python3 tools/verify_delivery.py --strict   # DELIVERY_MANIFEST.json is regenerated at delivery (until then: C7(3)'s)
python3 -m venv .venv && source .venv/bin/activate && python3 -m pip install -r requirements.txt   # Python >= 3.10
make -j4 && make -j4 decimal          # bin/c8d3_gmp (default) and bin/c8d3_decimal; make c7ref: bin/ref/c7d3_*
make test-python                      # every pure-Python test (fake worker, fake Slurm); C8_ALLOW_NO_L8=1 on the Mac
make test                             # + the native gates on a subset (validate, class_b), workflow and staging
make test-full                        # + every L <= 7 kernel, the inspector and the point checks of all tiers
make test-replay                      # replays the 168,528 archived production rows (C8 worker, order 7), rebuilds C7(3)
```

- **Requirements.** GNU C++17 with OpenMP, Boost 1.77 headers, libquadmath and GMP.
  - `make` requires Boost 1.77 (107700) unless `BOOST_ACCEPT=<version>` is given, and refuses Boost < 1.70.
  - On Expanse, `~/c8d3/env.sh` (from `slurm/sites/expanse/env.sh.example`) loads GCC 13.3.0 and the Spack Boost
    1.77 and GMP 6.2.1 with an RPATH. On symmetry (Amendment A1), `slurm/sites/symmetry/env.sh.example`: system GCC
    11.4, the `boost/1.77.0` module and system GMP 6.2.1 (`docs/HPC.md`, "Symmetry").
- **Build flags.** `make` keeps the delivered command line exactly: `-O3`, then `-std=c++17 -fopenmp
  -ffp-contract=off -fno-fast-math`.
  - `OPTFLAGS`, `CPPFLAGS`, `CXXFLAGS`, `LDFLAGS` and `LDLIBS` add to it. The strict flags cannot be dropped, and
    tokens that would override them are refused before compiling: the fast-math family, `-Ofast`, other
    `-ffp-contract` or `-std` values, `-mfpmath`.
  - Each build writes `bin/<binary>.buildinfo.json`.
  - Results are not bit-reproducible across CPU types (`docs/NUMERICS.md`).
- **Backends.** `make decimal` builds the lower-precision decimal300 backend. Select it deliberately.

## Run a campaign

On Expanse and on symmetry every job goes through `tools/slurm_submit.py` (`raw` for direct jobs; `lanes N`, `submit`, `window`,
`resubmit`, `release` for campaigns), which applies the admission rules and the SU gate under the session lock;
`docs/HPC.md` is the runbook ("Campaigns"; the L8 smoke commands are in PLAN.md "Verification", the pilot's on
symmetry in `docs/PILOT_RUNBOOK.md`). Since
Stage 2b the inputs are complete; the L8 packs are not in git: a package export gets them from the store with
`make link-l8 STORE=$C8_STORE` (`docs/HPC.md` "Stage 2b"). Plans of role `campaign` use the measured cost model of their binary and site (HD11): `cost_models/gmp_<site>_<cpu>_c8.json` (`$C8_SITE_MODEL` of `slurm/site.sh`; since Stage 3b `gmp_expanse_epyc7742_c8.json`, J-SWEEP-1, for `bin/c8d3_gmp` 24adff54…; Stage 5's J-SWEEP-2 refreshes it on the final binary and adds symmetry's `gmp_symmetry_epyc7543_c8.json`, which J-BLD checks on each data-only export), and `make baseline STORE=$C8_STORE` installs the `c8-stage3` baseline binaries into `bin/baseline/`. On symmetry every AMD job is pinned to EPYC 7543, the model's CPU (`slurm_submit.py` excludes the other AMD nodes; `slurm/site.sh c8_cpu_guard` stops a job elsewhere with 68; `docs/HPC.md` "CPU pin"). The C7(3) symmetry runbook is kept at the end of
`docs/HPC.md` as a record; its wrappers (`c7_legacy/`) were removed in Stage 3a.

## Contents

- `src/`: the native worker (`c8d3_integrate.cpp`, `kernel.hpp`, `stream.hpp`, `identity.hpp`, `diagnostics.hpp`)
  and the inspector `c8d3_inspect.cpp`.
- `tools/`:
  - `production.py`: plan, run, merge, status, recover;
  - `slurm_submit.py`: guarded submission;
  - `lanes.py`: lane mode;
  - `assemble.py`: assembly and gates;
  - `report.py`: re-verification;
  - `thru_report.py`: J-SMK-4's throughput report (A-PERF-3, A-ORC-13 real Slurm, A-ORC-5);
  - `drill_select.py`: J-DRL-9's hand-made selections;
  - packs, benchmarks and delivery tools.
- `slurm/`: job scripts and wrappers.
- `tests/`: numerical and workflow regressions, and fixtures.
- `inputs/`: the C8(3) inputs (C8(3) Stages 2a and 2b; `docs/HPC.md` "Inputs"). They hold the order-8 low-loop files
  (from the vendored `inputs_d3/`), C7(3)'s order-7 files in `inputs/order7/`, the L3–L7 packs (L7 complete: 2,441 +
  709), the L8 packs' pins (16,064 + 4,336 kernels; the packs themselves live in `$C8_STORE/packs/` and are hard-linked
  by `make link-l8`), H1's `selection.json` and the chains of `h1/` and `d3/` to the two external pins, the inventory
  of 24,173 kernels with the inspect fields (`make inputs-inspect` on Expanse, `inspect/inspect.json`) and the
  manifest. `make inputs` regenerates them byte for byte (`make inputs-l8` once, from the d=3 payload), and
  `tests/check_inputs.py` checks them. `tests/fixtures/inputs_mini/` holds the 8 smallest real L8 kernels per sector
  for tests.
- `references/`: lower-order references for the gates.
- `cost_models/`: the site-named measured models `gmp_<site>_<cpu>_c8.json` of the site's pinned CPU: the first,
  `gmp_expanse_epyc7742_c8.json` (J-SWEEP-1, Stage 3b; EPYC 7742), and symmetry's `gmp_symmetry_epyc7543_c8.json`
  after J-SWEEP-2's data-only commit (Stage 5); and the inherited symmetry model of C7(3).
- `reference/`: the complete original numerical package, byte-for-byte preserved.
- `gen3/`: the d=3 payload pipeline and C63d's gates on H1 (C8(3) Stage 1; `docs/HPC.md` "d=3 payloads"):
  `regenerate_rates.cpp` (`make gen3`, `make gen3-sanitize`), `run_d3.sh`, `gates_d3.py`, the gate tools and
  `test_gen3.py`; `gen3/pins/` pins C7(2)'s frozen d=2 payloads and the C7(3) payload set. Its Expanse jobs are
  `slurm/gen_d3_0.sh` (J-GEN-D3-0), `slurm/h1_copy.sh` (J-H1-COPY) and `slurm/gen_d3.sh` (J-GEN-D3).
- `vendor/c8_assembly/`: C63d's order-8 assembly (C8(3) Stage V). It holds byte copies of the 13 files
  `HANDOFF_assembly.json` (sha256 `f5ff6a35…`) lists, plus the HANDOFF. It is never an input (PLAN E.1 "One read
  rule").
- `vendor/c8_assembly_fixtures/`: the `LRI_ROOT` tree of the vendored tests, as pinned byte copies.
- `tools/VENDORED.json`: the pins, the fixture provenance, the review record and the interface. It is written by
  `tools/vendor_assembly.py`, and checked by `tests/check_vendored.py --standalone` and `tests/vendored_isolated.py`
  (A-ASM-1).
- `docs/`:
  - `HPC.md`: runbook;
  - `PILOT_RUNBOOK.md`: the Stage-7 pilot on symmetry (A-SMK-5);
  - `NUMERICS.md`: numerical contract;
  - `PERFORMANCE.md`: measurements.
- `benchmarks/`: evidence: C8(3)'s in `expanse_2026-10-c8/` and `symmetry_2026-10-c8/` (Stage 5: `stage5_*/`, each
  with a README of its jobs and verdicts), and C7(3)'s in `symmetry_2026-10/`.
- `DELIVERY_MANIFEST.json` and `SHA256SUMS`: the integrity inventory (`tools/write_delivery.py` regenerates them).

Work identities are campaign, sector, loop, graph, replicate and point interval, never node, lane or thread IDs.
Complete power-of-two Sobol nets are kept, and chunks are never independent replicates.
