# HT: Hamiltonian truncation at finite coupling

The thermal dimension of the long-range Ising model at finite coupling from Hamiltonian truncation: the dressed
zero-mode truncation in d = 1 and dressed-window truncations in d = 2 and 3, each with an independent solver. The
method, every quoted result with its status word, the checks and the caveats are in the note; this folder holds the
note, every code package that produced a quoted number, the records, and a replay for each number. The perturbative
coefficients obtained from truncation are in `HT_Pert/`.

- **The note:** `note/lri_ht_finite_coupling.pdf` (with its TeX sources); `note/README.md` explains how it is built and
  checked. Its Section 9 maps every number to a package, record, replay command and tolerance.

## Quick start

```
make list                 # the 7 packages
make test                 # fast tests of every package
make replay               # recompute every quoted number from the shipped records and compare (PASS/FAIL per package)
make replay PKG=lri_3d_window_hpc
make note                 # check the shipped note (tools/check_note.py --checksums)
```

`make test` and `make replay` need no download. Each package keeps its production code verbatim; the public targets
are in `code/<package>/public.mk`, with their scripts in `code/<package>/public/`; several packages also have `smoke`
(a small production run compared with the records). Python 3.11 or 3.12 with numpy, scipy, numba, mpmath, sympy and
pytest; each package lists its own requirements. Run on a Linux node; the solvers use many cores
(`NUMBA_NUM_THREADS` at most the job's cores).

## What is where

| File or folder | Contents |
|---|---|
| `note/` | the note (TeX, PDF, `Makefile`, `tools/check_note.py`, `MANIFEST.json`) |
| `code/<package>/` | one package per solver or analysis, at its production commit; `public.mk` and `public/` added |
| `data/HT_<d>d/` | the production records (self-hashed JSON; the replays verify each one) |
| `results/HT_<d>d/` | the quoted numbers, tables and comparison inputs |
| `PACKAGES.md`, `REPRODUCE.md`, `results_map.md`, `PROVENANCE.md`, `REVIEWS.md`, `data/DATA.md` | assembled from the package authors' texts, one section per package |

| d | Packages in `code/` |
|---|---|
| 1 | `lri_dressed_phi4_hpc` (solver), `lri_dressed_phi4_hpc_analysis` (extrapolations, tables), `lri_dressed_phi4_independent_check` (blind solver) |
| 2 | `lri_2d_window_hpc` (solver), `lri_2d_window_indep` (independent solver) |
| 3 | `lri_3d_window_hpc` (solver), `lri_3d_window_indep` (independent solver) |

## Conventions

The same as `GFF/README.md`: verbatim production code and hash-bound records; placeholders such as `<SCRATCH>`,
`<USER>`, `<ACCOUNT>`, `<NODE>` in files that are not hash-bound (`AGENTS.md`, rule 7); `public/SCRUBBED.txt` where a
package's own checksum list ships verbatim. Two HT-specific points:

- **Runtime-bound bases (d = 1).** A trained basis artifact loads only on the exact runtime that trained it (production:
  Python 3.11.4, numpy 2.3.5, scipy 1.17.0, numba 0.65.1). On any other runtime `make smoke` says so and retrains the
  basis with the production settings first (a few minutes).
- **Rebuilt, not hosted (d = 3).** The N = 20 static cache of the 3D production (193 GB) is not shipped; a rerun
  rebuilds it (about 9 h and 92 GiB on one node, see `REPRODUCE.md`). Every quoted number replays from the records.

## Tested

On the published tree, `make test`, `make replay` and every `smoke` pass on the symmetry cluster (Intel Xeon Gold 6148;
Python 3.12.9, numpy 2.3.5, scipy 1.17.1, numba 0.68); the d = 3 smoke also on AMD EPYC 8534P. The productions ran on
SDSC Expanse and the symmetry cluster.
