# Provenance: lri_3d_window_hpc and the d = 3 production records

## Code

| part | written by | when | commit |
|---|---|---|---|
| Numerical code 0.2.0rc1 (`code/`, `reference/`, `tests/` except the Expanse tests, `benchmarks/`, `validation/`, `cluster/` except `cluster/expanse/`, docs) | OpenAI GPT-6 astra (model stated by the author, 2026-10-14), via ChatGPT; supplied by the author as `lri_3d_window_hpc_performance_optimized.zip` | received 2026-10-07 | b5f6e1f (baseline, unmodified) |
| Expanse site layer (`cluster/expanse/`, `tests/test_expanse_lanes.py`, `EXPANSE.md`) | Claude Code (Claude Opus 5.5), under the claudex loop: plan reviewed by OpenAI GPT-6 astra (Codex CLI, effort xhigh) in 5 rounds; code inspected by fresh GPT-6 astra sessions in 2 rounds | 2026-10-07 | 77b37a6 … e895443 |
| L18/L20 projector repair 0.2.1rc1 (gesvd fallback after a failed gesdd null-space SVD, exact sizing, streamed hashing) | OpenAI GPT-6 astra (model stated by the author, 2026-10-14), via ChatGPT; supplied by the author as `lri_3d_L18_L20_fix.patch` and applied unmodified; manifest rebuilt and receipt stage added by Claude Code | 2026-10-08 | 33ef4f3 |
| Runbook caveat (inspection-3 finding L18-01) | Claude Code | 2026-10-08 | 7de47eb |
| large-shared partition in campaigns, partition-aware SU estimates | Claude Code (not inspected) | 2026-10-08 | ccd055a |
| `guard_cap_gib` opt-in (memory guard above the allocation, with a written reason) | Claude Code (not inspected) | 2026-10-09 | b330ee7 |
| Public tooling (`public.mk`, `public/*`) | Claude Code | 2026-10-13 | patches overlay |

The numerical source hash (`ht3d.hpc.source_hash()`: every `code/**/*.py` plus `inputs/prior_3d_points.json`) is
d27a3bc28838897de5f4fbee4c8d91e495161a1c9e0df17d20cd0e3478adaf8a. It is the same at 33ef4f3, 7de47eb, ccd055a and
b330ee7, and every shipped record carries it (replay check REC-SRC). Changes after 33ef4f3 touch only
`cluster/expanse/`, `tests/test_expanse_lanes.py` and docs.

`public/bp_x07.py` (the Borel–Padé value at Ds = 0.7) holds a script that Claude Code wrote and ran inline on
2026-10-08, during the independent check. The functions and coefficients are copied unchanged from the session
transcript; only the command-line wrapper is new. It reproduces the recorded output (1.4721437, spread
1.4721093–1.4721664, n = 29) exactly.

## Production

All on SDSC Expanse (AMD EPYC 7742; allocation `<ACCOUNT>`), Python 3.11.9, numpy 2.3.5, scipy 1.17.0, numba 0.65.1,
llvmlite 0.47.0 (venv built from `cluster/expanse/requirements-expanse.txt`).

| campaign | what | release (receipt) | Slurm | dates (PDT) | charge |
|---|---|---|---|---|---|
| grid18 | 14 lanes, teacher N = 6 → N = 8 … 18, Ds = 0.52 … 0.7499 | 33ef4f35ff4b (54745249) | array 54762491, shared 16c/64G | 2026-10-08 about 08:05–09:50 | 542.4 SU |
| grid18sri | the same at Ds = 0.518149 | 33ef4f35ff4b (54745249) | 54762505 | 2026-10-08 | 45.3 SU |
| l20x06 | N = 20 at Ds = 0.6, J = 1 diagnostics | ccd055a99531 (54762738) | 54776102, large-shared 32c/1000G | 2026-10-08 19:51–23:51 | 997.4 SU |
| grid20 | N = 20, 13 Ds, scalar only | b330ee7c25c2 (54779486) | array 54780394, shared 32c/240G | 2026-10-09 07:39–09:45 | 1548.9 SU |
| grid20sri | N = 20 at Ds = 0.518149, scalar only | b330ee7c25c2 (54779486) | 54780407 | 2026-10-09 | 208.1 SU |
| (static cache) | N = 20 graph and projectors (no record shipped) | 33ef4f35ff4b | 54762506, large-shared 4c/224G | 2026-10-08 08:04–19:45 | ended out of memory in the spin-1 vertices; spin-0 parts used |

Charges are measured from Slurm accounting (billing TRES), as reported by `campaign.py status`. The physics choices
(the Ds grid, adding 0.518149, the N = 20 point at 0.6 before the grid, scalar-only N = 20) were the author's
decisions, made on Claude Code's recommendations.

The records ship byte-identical: each carries `record_sha256` over its canonical JSON, including the production
paths of its inputs, and names its seed and basis by sha256.

## Independent check

`../lri_3d_window_indep`, written by Claude Code (Claude Opus 5.5) on 2026-10-08 from the method description
(`reference/baseline/docs/METHOD.md`) only, without reading or importing `code/ht3d`. It was run on Expanse
(campaign-free Slurm jobs, 2026-10-08). See that package's PROVENANCE.
