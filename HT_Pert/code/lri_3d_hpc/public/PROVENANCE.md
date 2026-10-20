# Provenance of lri_3d_hpc and of the d = 3 perturbative records

## The package

| What | Who | When | Commit |
|---|---|---|---|
| The original 3D finite-cutoff calculation (`reference/perturbative.py`, `reference/taylor_vertices.py`, `vendor/ht3d/`) and the optimized solver (`code/`, `tests/`, `hpc/`, `docs/`, `benchmarks/`, `results/`, `fixtures/`) | OpenAI GPT-6 astra (via ChatGPT), for the author; supplied by the author as one archive, `lri_3d_hpc_optimized.zip` | received 2026-10-08 | `14b10e2` (the archive as received) |
| Port to SDSC Expanse and the symmetry cluster: precision and residual gates, no-clobber publishing, cluster-wide output lock, rank-local MPI sortedness, the two-site `cluster/` layer (staged releases, validation receipts, stage runner, submit wrapper) | Claude Code session HT3dPert (Claude Opus 5.5), for the author | 2026-10-08 | `e85d3b7`, `feb13d4`, `ccd1eab` |
| Fix rounds 1 to 10 after Codex inspections (OpenAI GPT-6 astra, effort xhigh) | the same Claude Code session; findings by Codex | 2026-10-08 | `59a4d22`, `b4a1c11`, `f6069aa`, `22b9885`, `3fe8a52`, `5f0eeeb`, `be6060d`, `cd4832a`, `ba88b4f`, `8fa8339`, `7c8a67e` |
| Codex inspection round 11: APPROVED | Codex | 2026-10-08 | `7c8a67e` |
| This public overlay (`public.mk`, `public/`), the records manifest, the replay and these documents | Claude Code session HT3dPert (Claude Opus 5.5) | 2026-10-14 | not in the package's history |

The numerical code of the supplied archive (`code/*.py`, `code/native_kernels.cpp`, `reference/`, `vendor/`) was not
changed by the port except where the commit messages say so (gates, publishing and locking around the solver; the
solver arithmetic is unchanged). Every production result and gate record carries the sha256 of the eight files of
`code/` it ran with (`request.source_sha256`); `make replay` (check REC-SRC) compares them with the shipped files.

The package ships at `7c8a67e`, the release of the production campaign (`campaign.json`: `release.git_sha`
`7c8a67e1fe5bfc47c00d0130d0a12e657d55e49d`). No later commit exists. Before publication, the authors' cluster paths in
`cluster/RUNBOOK.md` were replaced by placeholders (`public/SCRUBBED.txt`).

## Validation receipts of the release (not shipped; quoted here)

The production campaign is frozen to a release and to the environment a validation receipt passed on
(`cluster/receipt.py`: the package's checks, the L4 fixture at 1e-16, an L14 store built by the stage runner and its
cutoff-14 gates, the 32-case L14 grid, MPI tests and failure drills):

| Site | Job | Node class | Result |
|---|---|---|---|
| symmetry | 571711 (amddebugq) | AMD EPYC 7532 | passed, 30 stages, 334 s |
| SDSC Expanse | 54770924 (debug) | AMD EPYC 7742 | passed (the receipt the campaign is frozen to) |
| SDSC Expanse | 54771372 | AMD EPYC 7742, 2 nodes | MPI receipt, passed |

Environment of the campaign (identical stack on both sites, from the hash-pinned `cluster/requirements.lock`): CPython
3.12.9, numpy 2.5.3, scipy 1.17.0, numba 0.68.0, llvmlite 0.50.0, mpi4py 4.1.2 (built from source); g++ 13.3.0 on
Expanse. The L14 stores built on Expanse and on symmetry are value-identical (padding-free fingerprint), and their
cutoff-14 gates differ by exactly zero; both differ from the supplier's reference results by at most about 1.2e-14
(float64 SO(3) projector, BLAS/libm).

## The production campaign `pert3d` (SDSC Expanse, 2026-10-08/09)

The author chose Expanse for production on 2026-10-08. One campaign, frozen to release `7c8a67e` and environment
fingerprint `782c2c7a...`:

| Job | Partition, request | Stages | Wall | Charge |
|---|---|---|---|---|
| 54772054 | shared, 16 cores, 32 GB | L16: prepare, images, matrix, finalize, verify, gate, solve, crosscheck | 18.5 min | about 10 SU |
| 54772079 | shared, 64 cores, 200 GB | L18: prepare .. solve | 36 min | about 60 SU |
| 54773175 | shared, 64 cores, 200 GB | L20: prepare, images | 10 h 12 min | about 1020 SU |
| 54779357 | large-shared, 64 cores, 1700 GB | L20: matrix, finalize, verify, gate, solve (L = 16, 18, 20 from the L20 store) | 3 h 26 min | about 1460 SU |

In total about 2550 SU. All gates passed; the records are in `HT_Pert/data/HT_3d/pert3d` and the table in
`HT_Pert/results/HT_3d/SUMMARY.md` (written 2026-10-09 by the same session from the result records; `make replay`
rebuilds it). The intermediate pipeline files (363 GiB) and the vertex stores (L16 2.6 GiB, L18 22 GiB, L20 177 GiB)
are not published (`HT_Pert/data/HT_3d/DATA.md`).

## Later use

- 2026-10-10: the ratios C_n(20)/C_n were formed against the diagrammatic values (paper Table 1) and quoted in the
  paper (`\HTpRatio<n>Three`); no extrapolation was made (three cutoffs, no complete window).
- 2026-10-14: the paper replaced these ratios by the extrapolated C2..C4(3) of the exact sums (`lri_3d_c4_exact`),
  which agree with this package's results at every even L <= 20 to about 1e-13.
- 2026-10-19: the final paper (`a6772872`) prints no number of this package; `\HTpThreeLmax`, the ratios and the
  L = 14 gate stay defined, unprinted, in its `numbers.tex`. The HT_Pert note quotes the cutoffs and the gate.
- The finite-coupling package `HT/code/lri_3d_window_hpc` reads C4(20) of the consistent scheme from
  `HT_Pert/results/HT_3d/SUMMARY.md` (60.26 % of C4(3), quoted there as 60 %).
