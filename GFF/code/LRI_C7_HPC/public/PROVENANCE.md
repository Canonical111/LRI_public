# Provenance: LRI_C7_HPC and the C7(1) result

## Who wrote what

| Part | Author | When |
|---|---|---|
| `reference/`: the seven-loop calculation (graph inventory, coordinate forests, binary-cluster sampler, meromorphic radial quadrature, controls, affine assembly, archived streams, TeX derivation) | the September 2026 research bundle's package `lri_C7_complete_update`, delivered by GPT-6 astra (OpenAI; attribution by the author, the files name no system) | September 2026 (files dated 2026-09-23) |
| Optimized HPC implementation (`src/`, first versions of `tools/`, `tests/`, `cluster/`, `docs/`, `benchmarks/`) | GPT-6 astra, delivered as `LRI_C7_HPC_optimized.zip` (30,877,961 bytes, sha256 fc818c0258823237c6be0f3f35255a4ba449d050e6810b050fae2e8127dd6f4c, 479 files dated 2026-09-23); its benchmark records carry the delivering sandbox's `/mnt/data/c7_optimization_work` paths | 2026-09-23 |
| Review fixes, degree-7 check, production tooling (`tools/campaign.py` integrity layer, `production.py`, `assemble.py` diagnostics and allowance, `combine.py`, `design.py`, `toolchain.py`, new tests, Slurm fixes, `inputs_extra/` degree-7 weights, documentation) | Claude Code (Claude Opus 5.5, coordinator plus Claude helper agents), reviewed by Codex gpt-6-astra | 2026-09-25 to 2026-09-26 |
| Direct primitive sector and parallel combine (PLAN2) | Claude Code, reviewed by Codex gpt-6-astra | 2026-09-26 |
| Expanse production, results and report | Claude Code (session C71d), on SDSC Expanse | 2026-09-25 to 2026-10-01 |
| Public replay layer (`public.mk`, `public/`) | Claude Code (helper of C71d) | 2026-10-13 |

## Repository history (`LRI_C7_HPC`, git, branch main; local only)

| Commit | Date (EDT) | Content |
|---|---|---|
| c21b9e8 | 2026-09-25 22:15 | baseline: the delivered package, byte-identical to the zip (479 files) |
| 3213ce0 | 2026-09-25 23:53 | review fixes, degree-7 check, production tooling; **frozen copy on Expanse: the workers, the batch planning and the batch merges of all 399 batches and of P1 ran this code** (executable sha256 33bab738..., GCC 13.3, Boost 1.86, AMD EPYC 7742) |
| 3129a97 | 2026-09-26 09:16 | inspection fix rounds 2–5 (verify rebuilds coverage, design-input validation, per-element replay accuracy); final combine of v1 |
| 0227dc5 | 2026-09-26 11:39 | v1 result: 46 batches, retained primitive, −322554 ± 160 |
| b0d2cd3 | 2026-09-26 16:35 | direct primitive sector (PLAN2) |
| 7320afc | 2026-09-26 16:57 | `combine.py --jobs`; **code of the final combination** (2026-09-28) |
| f923ad8 | 2026-09-28 08:01 | final result: 399 batches plus the direct primitive, −322550 ± 41 |
| e480fdc, acc3ec6, 14e6655, 68dc6be | 2026-09-28 to 2026-10-01 | REPORT corrections, the C6(1) addendum and the results-review revision (RR-003) |

**Shipped:** commit 68dc6be. Its code files are byte-identical to 7320afc (7320afc..68dc6be changes only `results/` and
`SHA256SUMS`). Against 3213ce0 the shipped code differs in `tools/campaign.py` (plan_counts and check_coverage
refactors, coverage rebuild and merged-header checks in `verify_campaign`), `tools/assemble.py` (primitive-sector guard,
input binding), `tools/combine.py` (`--primitive`, `--jobs`), `tools/design.py` (pilot validation) and tests;
`src/`, `cluster/`, `Makefile`, `tools/production.py`, `inputs_extra/` and `reference/` are identical. The worker path
(`campaign.py run` and the C++ integrator) is therefore unchanged, and the merge code differs only by a refactor that
keeps its output. `public/diff_3213ce0_to_shipped.patch` reverses to the 3213ce0 tools and tests exactly (checked).

## Production facts (from `results/C7_1/production_run.json`, REPORT.md and the review log)

- Machine: SDSC Expanse, `shared` partition, Slurm 23.02.7; 16 CPUs and 16 GB per array element, 3 h limit.
- Design: `design_v1.json` (sha256 fd356a15...), frozen on 2026-09-25 from a multiplier-1 pilot (seed 2026092501) and the
  archived components by `tools/design.py` (estimator-only Neyman allocation; predicted SE 203 per batch).
- Seeds: batch k uses the first 8 bytes (little endian) of sha256("C7-expanse-2026-09:batch:k"); each campaign seed is
  derived from it by `production.py`; P1 uses sha256("C7-expanse-2026-09:primitive"), matrix seed XOR 0x17219317.
- Batches: 46 in the first wave (2026-09-25 20:59 to 2026-09-26 06:58 PDT, 29,725 core-hours), then extension batches
  under a pre-registered stop (2026-09-29 06:00 PDT, 400 batches, or 300,000 SU); the 400-batch cap was reached on
  2026-09-28 01:15 PDT. b215 was never submitted (its planning read a truncated Lustre copy of an input and failed
  closed), so 399 batches are included. 17 transient `srun` step failures were resubmitted once each.
- Cost: about 250,000 core-hours for the batches (55 elements × 16 CPUs per batch, about 640 core-hours each), about 20
  for P1, about 60 for the combinations; project accounting gives 255,952 SU on Expanse plus 12.5 core-hours of tests
  on a personal desktop.
- Final combination: 2026-09-28 02:56–04:45 PDT, `combine.py --jobs 16`, every campaign re-verified with its
  checkpoints.

## Changes made for the public export

None to shipped files. New: `public.mk`, `public/` (replay, data and Slurm helpers). Not shipped: `benchmarks/`,
`results/` (moved to `GFF/results/C7_1/`), git history.
