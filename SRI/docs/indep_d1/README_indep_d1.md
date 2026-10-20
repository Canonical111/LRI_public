# indep_d1: independent re-derivation of the inputs of C^SR_5..C^SR_8 (d = 1)

The coefficients C^SR_n of the dual series of the chain (package `dual_d1`) are assembled from about forty "beta
inputs": Laurent coefficients of hard-core ordered moments of up to nine kinks, combined by a renormalization-group map.
The compendium computed them with its own code. This package recomputes every input of C^SR_5..C^SR_8 with code
written from the definitions alone and compares with the compendium only at the end.

Paper: since paper e89a94a0 (2026-10-18) the paper quotes the magnetization-scheme value \SRCeightMag (package
integ_d1; Sec. 3.2 "Checks") instead of \SRCeightIndep; since c9adefbf the text no longer prints the pulls. So
\SRCeightIndep, \SRindepPullMax, \SRCeightPull and \SRCeightPullMax are all "note only" (INFO rows of the replay),
and the SRI note keeps them (Sec. 2.6). The paper's Sec. 3.2 says only that every input of C^SR_5..C^SR_7 was
recomputed from scratch. Note: SRI/note, the section on the independent re-derivation.

Results (quoted error = the largest of three estimators: linear propagation, the spread of six per-replicate
assemblies, and a sector-pooled estimate):

| quantity | this package | claim (eq:sr-closed, eq:sr-C8) | pull |
|---|---|---|---|
| C5 | 29.237811563 +- 1.35e-7 | 29.2378115810 | -0.13 |
| C6 | -58.66569861 +- 1.45e-6 | -58.6656974742 | -0.78 |
| C7 | 51.0689860 +- 3.14e-5 | 51.0689886129 | -0.08 |
| C8 | 242.83 +- 2.37 | 247.381204805 | -1.92 |

* The 25 inputs of C5..C7 agree with the compendium's 100-digit values with rms pull 0.34 (largest 0.91, Omega).
* C8 - J9/4 (everything except the nine-kink input J9) agrees at -0.20 sigma (315.81130 +- 0.0051). J9 = -291.9 +- 9.5
  against -273.72; inside J9 only the integral A9[eps^0 l^1] deviates (ours - archive = -20.4 +- 9.3, -2.19 sigma,
  3.3e-5 relative). The magnetization-scheme value of the SRI note (Sec. 2.7, Appendix I; package integ_d1),
  247.38118 +- 0.13, shares no input with this package, agrees with the record to 2.5e-5, which indicates that the low C8
  here is the one in error, located by the comparison above in A9[eps^0 l^1]; an independent A9 run (about 9k core-hours) would show whether it is a fluctuation with an
  underestimated error or a systematic error.
* This tests the compendium's numbers, not the zeta-value form of C8 (a 1 % measurement cannot identify it).

| part | what |
|---|---|
| `spec/` | definitions of the inputs from the compendium's note alone (`spec.md`, `spec.json`), archive-free validation targets (`out/`), and the sealed archive values used only for the final comparison (`comparison/`, `comparison_C8/`, with SHA256SUMS) |
| `framework/` | the response-to-beta map J0 beta = R1 and the C8 assembly, rederived with sympy (`derive_rg.py`, `derive_invariants.py`, `derive_C8.py`), the module `lri_framework.py` (strict, per-replicate assembly), tests and outputs |
| `engine/` | the Mellin-Hepp sector engine (`src/lri_engine.cpp`: Mellin transform in the cutoff, Hepp sectors, analytic subtraction, rank-1 lattice QMC with six random shifts, double-double arithmetic), campaign tools (`py/`), specs, validation and plan records, and per production run its manifest, job definitions (`*.cfg`), collected results, framework inputs and sha256 records |
| `direct/` | code of the finite-cutoff direct integration used as a gross-error screen (tables not shipped) |
| `assembly/` | the assembly scripts: `run_assembly.py` (phase 2: C5..C7), `run_assembly_C8.py` (C8), `compare_archive*.py`, `make_report*.py`, `pooled_errors.py` |
| `RESULTS*.md`, `RESULTS*.json` | the reports and machine-readable results: phase 2 (`RESULTS*`), C8 tier A (`*_tierA*`), C8 tiers A+B+C (`RESULTS_C8*`); the archive-free json files were written and hashed before the comparison files |
| `public/` | `make` targets (public.mk), the replay and test tools, `pooled_sector_record.json`, `REPLAY_FULL.md`, sha256 lists |
| `RE-PINNED.json`, `RE-PINNED.md` | the 22 files published in a scrubbed form (the personal desktop's name removed; no number changed), with their original and published sha256 |

`make -f public.mk test` (5 min) and `make -f public.mk replay` (about 4 min) need no cluster. The raw per-sector
engine outputs (131 MB) are not shipped; `public/pooled_sector_record.json` holds their exact sufficient statistics,
and `make -f public.mk replay-raw RAW=<dir>` reruns everything on the raw outputs once they are hosted. Engine runs
went to the symmetry cluster, except C8 tier A and the cheaper tier-B/C groups (run directories with the suffix `_can`),
which ran on a personal desktop.

Independence: no code of the compendium was imported, called or copied, and no archived raw data was used as input;
archived numbers were read only by `compare_archive*.py`, after the archive-free results had been written and hashed
(PROVENANCE_indep_d1.md, RESULTS.md and RESULTS_C8.md list every exception in which an archive number was visible).
The whole programme assumes the compendium's matched two-coupling prescription; it checks the numbers within it.
