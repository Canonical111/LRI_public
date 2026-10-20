# GFF: the perturbative coefficients of the long-range Ising model

The epsilon expansion of the long-range Ising model around the generalized free field, coefficient by coefficient:
C0 to C5 in closed form (any d, and d = 1, 2, 3), and C6, C7, C8 in d = 1, 2 and 3. C8(2) and C8(3) also have
independent checks from separately written code. The derivations, the numbers and their uncertainty analysis are in the
note; this folder holds the note, every code package that produced a quoted number, the records, and a replay for each
number.

- **The note:** `note/long_range_ising_condensed.pdf` (203 pages, with its TeX source). `note/README.md` has the table of
  current values, the map from note sections to packages, and the corrections of this edition. Section 33 of the note
  is the reproduction guide.
- **Values:** see `note/README.md` ("Current numerical entries"). The allowances are empirical, not rigorous bounds;
  the note says how each was set.

## Quick start

```
make list                 # the 28 packages
make test                 # fast tests of every package (about 1 h on one node; C8(2) alone about 25 min)
make replay               # recompute every quoted number from the shipped records and compare (PASS/FAIL table per package)
make replay PKG=LRI_C8_HPC
make note                 # check the shipped note against note/MANIFEST.json
```

`make test` and `make replay` need no download. Each package keeps its own production `Makefile` verbatim; the public
targets are in `code/<package>/public.mk` (`make -C code/<package> -f public.mk help` where available), with their
scripts in `code/<package>/public/`. Run everything on a Linux cluster node, not a laptop: several packages build
C++ code (GCC >= 11, C++17 with OpenMP, GMP, Boost 1.77 headers, libquadmath) and some tests use many cores.

Python: 3.11 or 3.12 with numpy, scipy, mpmath 1.3 (gmpy2 optional), sympy, networkx and pytest; each package lists its
own requirements in `code/<package>/public/requirements.txt` or the package's `requirements.txt`.

## What is where

| File or folder | Contents |
|---|---|
| `note/` | the note (TeX, PDF, `Makefile`, `tools/check_note.py`, `MANIFEST.json`) |
| `code/<package>/` | one package per result, exported at the commit its production ran; `public.mk` and `public/` are added for the public targets |
| `results/C<n>_<d>/` | published outputs and production records per coefficient (`C8_2_check`, `C8_3_check`: the independent checks; `closed_forms_*`: the closed forms) |
| `data/` | merged records that are not results, and `DATA.md`: what is in git and what is hosted |
| `PACKAGES.md` | what each package contains and computes |
| `REPRODUCE.md` | per package: environment, test, replay, and the documented production rerun |
| `results_map.md` | every quoted number: its record, the command that recomputes it, the tolerance |
| `PROVENANCE.md` | per package: origin, author (the author, Claude Code sessions, OpenAI GPT-6 astra), commit, later changes |
| `REVIEWS.md` | summaries of the code and results reviews (raw review logs are not published) |

The map from results to packages (as in `note/README.md`):

| Result | Packages in `code/` |
|---|---|
| C0-C5 in closed form, d = 1 | `lri_numerical_resolution`, `lri_psi_complete_update`, `lri_fixed_hypergeometric_update` |
| C0-C5 in closed form, general d | `lri_general_special_functions_update`, `lri_general_closed_update`, `lri_general_periodization_update` |
| L2, K2 and C5(2) in closed form | `LRI_C5_d2_simplify`, `LRI_C5_d2_proof` |
| d = 3 specialization; generic-d reduction of L_d, Z_d, K_d | `lri_d3_reduction_update`, `lri_d3_matrix_update`, `LRI_C5_general_d`, `LRI_C5_d3` |
| C6(1) and its analytic representation | `LRI_C6_1D_HPC`, `C6_research_note`, `LRI_C6_closed_form_review` |
| finite kernels, power compensation, C6(2), C6(3) | `lri_C6_d2_complete_update`, `lri_C6_d3_complete_update`, `LRI_C6_D2_HPC`, `LRI_C6_D3_HPC` |
| full C7(1), C7(2), C7(3) | `LRI_C7_HPC`, `LRI_C7_D2_HPC`, `LRI_C7_D3_HPC` |
| full C8(1), C8(2), C8(3) and the independent checks | `LRI_C8_HPC`, `LRI_C8_D2_HPC`, `LRI_C8_shared`, `LRI_C8_D2_HPC_optimized` (check of C8(2)), `LRI_C8_D3_HPC`, `LRI_C8_D3_OPT` (check of C8(3)) |

## Conventions

- **Verbatim production code.** Code that produced a published number ships byte-identical at its production commit
  (`PROVENANCE.md` names it). Records bound by hash chains also ship byte-identical, even where they name the machines
  and paths of the original runs.
- **Placeholders.** In files that are not hash-bound, the authors' paths and machine names are replaced by tokens such as
  `<SCRATCH>`, `<HOME>`, `<USER>`, `<ACCOUNT>`, `<NODE>` (see `AGENTS.md` at the top of the repository).
- **`public/SCRUBBED.txt`.** Where a package's own checksum lists ship verbatim, the files whose placeholders changed their
  bytes are listed in `code/<package>/public/SCRUBBED.txt`; the package's verifiers treat those as scrubbed and fail on any
  other mismatch.
- **Run-time links.** Large reference trees shared by several packages are shipped once; `public.mk setup` links or copies
  them where another package expects them (e.g. `LRI_C6_D3_HPC/reference` -> `LRI_C6_D2_HPC/reference`).
- **Hosted data.** A few targets (`replay-full`, production reruns) need files too large for git. They are listed in
  `data/DATA.md` with sizes and sha256; hosting is planned on Zenodo, with no record yet, so `make fetch-data` in a package
  only prints what to fetch and where it goes.

## Tested

`make test` and `make replay` of every package have been run on the published tree:
results of the acceptance run are added here when it completes.
