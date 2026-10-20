# lri_C6_d3_complete_update: d = 3 power-sector compensation of C6(3) (audit subset)

This folder is a subset of package 22 of the research bundle `LRI_complete_research_bundle.zip`: 37 of its 165 files
(7.7 of 55.1 MB), all byte-identical. Only `public.mk` and `public/` were added for the public release. The bundle's own
documentation is `README.md`; it also describes files that are not shipped (see below).

## What it gives

The six-loop coefficient C6(3) is computed in a finite (zero-momentum) scheme for the power-free graphs, plus an
analytically evaluated correction Δp for the graphs that contain a proper power-divergent subgraph. This package holds
that analytic correction and the d = 3 inputs of the finite-scheme assembly. The production value
C6(3) = 33.5754 ± 0.0005 (`GFF/code/LRI_C6_D3_HPC`, results in `GFF/results/C6_3/`) uses this compensation and does not
redo it.

The condensed note quotes, in the section "Analytic power-sector compensation at d = 2, 3":
- the sunset factor M_3 = −16π/15 (d3six:sunset);
- the counts of power classes: 1, 5, 31 at loops 3–5; at six loops 121 with nonzero weight and 52 with zero weight;
- the exact cancellation of the two unknown four-loop core coefficients (d3six:coreResidues,
  d3six:unknownCancellation). Two trial assignments change the residues as predicted, to better than 4 × 10⁻⁷³;
- the lower-order power pieces (d3six:lowerPower) and the assembly polynomial δR (d3six:deltaR);
- Δp,higher = −Δp,lower = 0.0736516970441648694692229455611… at 90 digits (d3six:powerNumbers). Their sum is
  −1.02 × 10⁻⁸⁹. A 75-digit run with other core assignments gives −1.94 × 10⁻⁷⁵. A stress test with arbitrary masters
  gives 1.52 × 10⁻⁶⁵.

It quotes, in the section "Finite-scheme sixth-order assembly", subsection "The changes required by dimension three":
- 660 sixth-order classes (487 power-free, 173 with a power subgraph) and 1, 5, 16, 76, 395 kernels at L = 2–6;
- the 20 Gamma logarithmic jets and 5 normalizations, checked to 2.27 × 10⁻⁵⁹ (d3six:GammaJets);
- the two-loop beta jets b_{2,0…4} (d3six:twoLoopValues);
- 256 exact fixed-point/Lagrange checks (d3six:lagrange).

These are high-precision consistency checks plus an exact proof of the core cancellation. They are not an all-orders
theorem and not interval bounds.

## Run

From this folder (Python 3 with `pip install -r public/requirements.txt`; no compiler):

```sh
make -f public.mk test     # about 10 s: checksums, the seven light audit scripts, the shipped records against the note
make -f public.mk replay   # about 2 min on one core: also the three graph-recursion audits and analyze_power.py
```

Each target copies the package to `.work/pkg/` (git-ignored) and runs the commands of `README.md` ("Reproduce the
analytic power-target audit", "Independent numerical and algebraic checks") unchanged there:
- the three `power_ms_d3.py` runs (75 digits with core (0, 0), 90 digits with core (101, −37), and 65 digits with
  arbitrary masters Q = 7, P = 11, K = 5, Z = 13 and core (−17, 29));
- `analyze_power.py` on each;
- `check_core_propagation.py`, `check_coverage.py`, `check_unknown_core.py`, `power_assembly_polynomial.py`,
  `check_mom_d3.py`, `check_gamma_d3.py` and `two_loop_d3.py`.

In `replay` the three audits overwrite the copy's power records, so that the later scripts read the reruns. Everything is
compared with the shipped `records/` and with `../../results/C6_3/power_compensation_quoted.json`. The table goes to
`.work/REPLAY.md`, and any FAIL exits non-zero. Locally (macOS, Python 3.10.12, mpmath 1.3.0) the replay gave 68 PASS,
0 FAIL. All 931 per-graph numbers of each audit were bitwise equal to the delivered records.

## What is shipped and what is not

Shipped:
- the nine audit scripts in `code/`;
- `vendor/` (the position-space engine and graph parser of the preceding d = 2 calculation, vendored by the package);
- `inputs/classified_inventory.json` and `inputs/forest_L2..6.txt`;
- the audit records in `records/`;
- `verification/file_checksums.json` (the package's own list, verified with ignore-missing) and `environment.json`.

Not shipped (47.4 MB):
- the first full C6(3) Monte Carlo run of this package: estimate 33.50 ± 0.6, sampling SE 0.13. It is superseded and not
  quoted by the note. Its C++ sampler, rates, allocations, batch vectors, pilots and endpoint valuations are left out;
- the run and TeX logs;
- the TeX notes (author rule 2026-10-16: one TeX note per direction): `C6_d3_complete.tex`/`.pdf` and
  `C6_d3_appendix.tex`, the d = 3 power-compensation chapter, now the condensed note's Sections 24 and 25 (d = 3 parts),
  and the snapshots `long_range_ising_complete.tex`/`.pdf` and `provenance/previous_note.tex` of the earlier full
  research note;
- the copies in `verification/` of files that are in `records/`.

`public/BUNDLE_SHA256SUMS` lists all 165 files of the bundle package. `make test` checks that every shipped file is on it
and byte-identical, and counts the 128 that are not shipped. The full tree is also tracked, byte-identical, as
`reference_d3/` in `LRI_C6_D3_HPC` at commit 1c6dfb3 (not shipped there either). Shipping the full tree here instead
needs only the removal of the entry's `keep_only` (55.1 MB, largest file 16.3 MB; the notes would then need excludes),
and the replay runs unchanged.

## Caveats

- The two unknown core coefficients are not evaluated. They cancel exactly from the physical target. The individual MS
  sums in the audit records were obtained with trial values for them and are not physical.
- The audit uses Q_3 and P_4(3) to 38 to 39 decimals as common inputs (`code/power_ms_d3.py`); they agree with
  `GFF/code/lri_d3_reduction_update`.
