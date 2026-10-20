# LRI_C7_D3_HPC: the seventh-order coefficient C7(3)

Published as `GFF/code/LRI_C7_D3_HPC/public/README.md`. The package's own `README.md` next to it is the delivered one,
unchanged.

## What it computes

The coefficient C7 of Δ_E(3, ε) = Σ C_n(3) εⁿ, ε = 2s − 3, for the thermal operator of the long-range Ising model in
d = 3, from the finite-scheme forest kernels of loops 3 to 7 in both the power-free and the power-containing sector, by
randomized quasi-Monte Carlo. The method is condensed in Section 29 of the note (`GFF/note/`).

**Result** (production run1, symmetry cluster, 30 Sep to 1 Oct 2026):

| | value |
|---|---|
| C7(3), reported | **−220.35 ± 0.13** (allowance = 4 sampling SE rounded up to 0.01; empirical, sampling only) |
| estimator, sampling SE | −220.35448047392794, 0.0318188006 |
| power-free part, power correction | −220.3723574 ± 0.0277073, +0.0178769 ± 0.0156478 |
| previous calculation (the delivered `reference/`) | −228 ± 16 (estimator −227.6181095, SE 3.8273969); the new estimator is 1.90 of its SE away |

The by-products C3 to C6 agree with the special-function values and the C6(3) production (pulls +2.30, +1.08, +0.04,
−0.79); the two campaigns agree to 1.02 combined SE; no gate was flagged. Limits: the allowance covers sampling only;
the result shares the graph and renormalization framework with the rest of the note and does not validate it; a
quadrature-truncation effect, as found in C7(1), would lie outside it.

## Two commits, one folder

- **The production code**: this folder is the export of git commit **4de9412** (the package as delivered on
  2026-09-30, unchanged). The run1 manifest pins `tools/{production,assemble,common,prepare_inputs}.py` by sha256, and
  `make replay` checks that the shipped files are those bytes. The production binary was built from `src/` (identical
  to `reference/src/`) with GCC 11.4 and Boost 1.77: `bin/c7d3_gmp`, sha256 635428f9….
- **The re-verification tool**: `reverify_a6ce987/` holds `tools/report.py`, `tools/assemble.py`, `tools/common.py`,
  `references/lower_order_d3.json` and run1's cost model from commit **a6ce987**, the symmetry-ready successor built and
  inspected in a Codex fix loop (approved at c71cc56; a6ce987 adds the results review's gate fix). It is a separate
  folder, not an overlay, because its `assemble.py` and `common.py` differ from the production files of the same names.
  It needs its own copy of `inputs/{manifest,two_loop,primitive_reference}.json` (byte-identical to `inputs/`). The rest
  of a6ce987 (lane mode, Slurm wrappers, its tests) is not published.
- **The public layer**: `public.mk` and `public/` (new files, Claude, 2026-10-13).

## What is where

| path | content | in git? |
|---|---|---|
| `src/`, `tools/`, `tests/`, `slurm/`, `docs/`, `Makefile`, `requirements*.txt`, `README.md` | the delivered code and docs | yes, verbatim |
| `inputs/manifest.json`, `inventory.json`, `two_loop.json`, `gamma_d3_7.txt`, `primitive_reference.json` | the d=3 inputs; the run1 manifest pins `inputs/manifest.json` (5048b336…) | yes |
| `inputs/packs/*.pack` (10 files, 321.8 MB) | the 3,511 kernels in packed form | as `public/kernels/inputs_packs.tar.gz` (14.8 MB); `make -f public.mk setup` unpacks and verifies them |
| `reference/` | the previous calculation, byte-for-byte: its code, sources, README, verification records (result, assembly, dimension, two-loop and Gamma checks) | yes, except the three items below |
| `reference/inputs/{free,power}/L3..L7/G*.txt` | the same 3,511 kernels as single files | restored by `setup` from the packs (each checked against `inputs/inventory.json` and `SHA256SUMS`) |
| `reference/records/` (784 files, 51.6 MB) | raw streams of the previous production, pilot and control | hosted: `data/C7_3/reference_records.tar.gz` (`make -f public.mk records`) |
| `reference/reference/C7_d2_complete.tex` | a copy of the method note of the earlier d = 2 seventh-order calculation; its substance is in the condensed note, Section 28 (`GFF/note/`) | no (author rule 2026-10-16: one TeX note per direction); named in `public/dropped_paths.txt`, read by no code |
| `benchmarks/` | the 8 delivered validation records that `docs/NUMERICS.md` cites | yes; the timing, memory and profile benchmarks are not published |
| `SHA256SUMS`, `DELIVERY_MANIFEST.json` | the delivery's checksum lists, verbatim (not pruned or regenerated) | yes; `make -f public.mk checksums` verifies every present file and classifies the absent ones |
| `reverify_a6ce987/` | the re-verification tool (above) | yes |
| `public.mk`, `public/` | public targets and scripts | yes |

The production records are in `GFF/results/C7_3/` (see its `REVIEWS.md` and `results_map.md`); the complete run
directory is hosted as `GFF/data/C7_3/run1-20260930-m4096_full.tgz`.

## Targets (`make -f public.mk <target>`, from this folder)

| target | what | needs | time |
|---|---|---|---|
| `replay` | recomputes every quoted C7(3) number from `results/C7_3` with the production assembly and the a6ce987 gates; PASS/FAIL table | Python ≥ 3.10, numpy | ~10 s, any machine |
| `test` | `setup`, then the production commit's own `make test`: builds `bin/c7d3_gmp`, `tests/validate.py` (up to 16 graphs per loop and sector against the original d=3 worker built from `reference/src`; thread and chunk independence; assembly identical to the original), `tests/workflow.py` (tiny campaigns through plan, run, restart, corruption refusal, merge, assembly) | x86-64 Linux, GCC with OpenMP and libquadmath, GMP, Boost 1.77 headers, SciPy | < 10 min on a 64-core node (validate 18 s, workflow 12 s after the builds, on AMD EPYC 7532) |
| `checksums` | verifies the tree against the delivery's checksum lists | — | seconds |
| `test-full` | the production commit's `make test-full`: every graph, 450-digit point checks, reassembly of the previous result | as `test`, plus `records` | ~3 min more (96 s, 43 s, 2 s on the same node) |
| `archived-replay` | the cited check: rerun the worker on the 168,528 archived rows | as `test`, plus `records` | 95 s at 64 threads |
| `indep-rows` | the independent mpmath re-implementation on chosen archived rows | `records`, mpmath | seconds per row |
| `reverify` | runs `reverify_a6ce987/tools/report.py` on the hosted run directory and compares with `results/C7_3/run1_report_bb9d2ca.json` | the hosted run tarball | ~1 min, 0.6 GB |
| `smoke` | re-plans run1 with its seed, flags and cost model and reruns job indices 0, 320, 192; compares with run1's checkpoints | as `test`, plus the hosted run tarball, SciPy 1.17.1 | ~3 min on 64 cores |

`fetch-data` downloads the two hosted files from the project's Zenodo data record (https://doi.org/10.5281/zenodo.23466766) and checks them. `clean` removes `.work/`, `bin/` and test output;
`distclean` also removes what `setup` and `records` restored.

## Caveats

- Results are bit-reproducible only on the same CPU type: the worker differs across CPU types by up to 2.0e-11
  normalized, and the float64 assembly by a few ulp. The replay's tolerances allow for this.
- `src/kernel.hpp` does not compile with Boost ≥ 1.86; `public.mk` refuses such versions.
- The tests write `bin/` and `benchmarks/validation.json` (git-ignored; the shipped records in `benchmarks/` are only printed, not rewritten). Run1's nets were made with SciPy 1.17.1; a rerun with the
  same seed needs that version to reproduce the same Sobol nets.
- The delivered `tools/verify_delivery.py --strict` fails on the public tree because the bulk is restored or hosted; use
  `make -f public.mk checksums`.
