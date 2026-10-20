# HT_Pert: perturbative Hamiltonian truncation

The epsilon-expansion coefficients C2..C8 of the long-range Ising model computed from the truncated Hamiltonian,
without Feynman graphs, in d = 1, 2, 3: the coefficients at finite cutoff, the window corrections, the extrapolations
to infinite cutoff where they are made, the exact finite-cutoff sums, and the independent checks. The method, every
quoted result with its status word, the checks and the caveats are in the note; this folder holds the note, every
code package that produced a quoted number, the records, and a replay for each number. The finite-coupling
truncation is in `HT/`; the diagrammatic coefficients that these are compared with are in `GFF/`.

- **The note:** `note/lri_ht_perturbative.pdf` (with its TeX sources); `note/README.md` explains how it is built and checked.
  Its reproduction section maps every number to a package, record, replay command and tolerance.

## Quick start

```
make list                 # the packages
make test                 # fast tests of every package
make replay               # recompute every quoted number from the shipped records and compare (PASS/FAIL per package)
make replay PKG=lri_3d_hpc
make note                 # check the shipped note (read-only: generated files, d = 1 numbers, MANIFEST.json)
```

`make test` and `make replay` need no download. Each package keeps its production code verbatim; the public targets
are in `code/<package>/public.mk`, with their scripts in `code/<package>/public/`; several packages also have `smoke`
(a small production run compared with the records) or `replay-full` (the shipped fit scripts rerun on a scratch
copy). Python 3.11 or 3.12 with numpy, scipy, numba, mpmath and pytest; each package lists its own requirements. The
d = 2 and d = 3 solvers compute in x87 80-bit long double, so their `test` and `smoke` need Linux x86-64 and a C++17
compiler with OpenMP; `lri_2d_coeff_independent_check` needs python-flint for its `test`. Every `replay` runs on any
OS.

## What is where

| File or folder | Contents |
|---|---|
| `note/` | the note (TeX, PDF, `Makefile`, `MANIFEST.json`) |
| `code/<package>/` | one package per solver or analysis, at its production commit or as a dated snapshot; `public.mk` and `public/` added |
| `data/HT_<d>d/` | the production records (self-hashed JSON or checksum-listed; the replays verify them) and `data/MANIFEST.sha256` |
| `results/HT_<d>d/` | the quoted numbers and tables |
| `PACKAGES.md`, `REPRODUCE.md`, `results_map.md`, `PROVENANCE.md`, `REVIEWS.md`, `data/DATA.md` | assembled from the package authors' texts, one section per package |

| d | Packages in `code/` |
|---|---|
| 1 | `lri_1d_c4_exact`, `lri_1d_c5_exact` (exact sums: C2..C4(Λ) to Λ = 2000 and C5(Λ) to Λ = 500; the paper's d = 1 values of C2..C5), `lri_hpc_Hamitonian` (solver and analysis: C2..C7 at Λ ≤ 118, Expanse records), `lri_eh_hpc` (the g²D vacuum-window add-on), `lri_c8_hpc` (C0..C8 at Λ = 52..92), `lri_d1_full_coefficient_flow` (complete-window C0..C8 to Λ = 72), `lri_1d_dconn_refit` (large-Λ limits of C4..C8 with the complete window), `lri_d1_fullblock_tail_response` (cited check of the cutoff tail) |
| 2 | `lri_d2_coeff_hpc` (solver: C2..C8 at L = 2..34, raw, consistent and literal windows), `lri_2d_coeff_independent_check` (two clean-room solvers, exact C2..C5(L) to large L, the derived windows, the C4 and C5 extrapolations) |
| 3 | `lri_3d_c4_exact` (exact sums: C2..C4(L) to L = 600 and C5(L) to L = 40; the paper's d = 3 values of C2..C4 and the C5 estimate), `lri_3d_hpc` (solver: C2..C8 at L = 16, 18, 20; the validation partner of the exact sums) |

## Conventions

The same as `GFF/README.md`: verbatim production code and hash-bound records; placeholders such as `<SCRATCH>`,
`<USER>`, `<ACCOUNT>`, `<NODE>` in files that are not hash-bound (`AGENTS.md`, rule 7); `public/SCRUBBED.txt` where a
package's own checksum list ships verbatim. Three HT_Pert-specific points:

- **Rebuilt, not hosted.** The vertex stores and intermediate files of the d = 3 production (L = 20 store 177 GiB, 363
  GiB of pipeline files) are not shipped; a rerun rebuilds them (cost in `REPRODUCE.md`). Every quoted number replays
  from the shipped records.
- **Hosted on Zenodo, not needed for the replay (d = 1).** The joint scans of the d = 1 refits (97.5 MB), the
  model-independent outputs that git leaves out (34 grids with their companion files: one archive of 319 MB, 1.77 GB
  unpacked) and the blind constrained-fit results of `lri_1d_c5_exact` (28 MB archive, 71 MB unpacked) are in the
  Zenodo data record (DOI 10.5281/zenodo.23466766). `make -f public.mk fetch-data` in `code/lri_1d_dconn_refit` and
  `code/lri_1d_c5_exact` downloads them and checks every sha256; the documented reruns also regenerate them. Every
  quoted number replays from the shipped records.
- **Fixed protocols.** The windows contain no fitted parameter, and the extrapolation protocols (tower families, fit
  ranges, the rule for the quoted value and its uncertainty) are fixed; they are listed under "Decisions you must not
  make" in `REPRODUCE.md`.

## Tested

On the published tree, `make test`, `make replay` and every `smoke` and `replay-full` of all 12 packages, and
`make note`, pass on the symmetry cluster on Intel Xeon Gold 6148 and AMD EPYC 7543 nodes (the d = 2, 3 packages also
on AMD EPYC 7532), with Python 3.12.9, numpy 2.3.5, scipy 1.17.1, numba 0.68 and python-flint 0.9.0. The whole folder
takes about 1.5 h on one node, most of it the d = 1 `replay-full` targets. No shipped file changes during the runs.
The productions ran on SDSC Expanse and the symmetry cluster.
