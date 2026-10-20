# lri_numerical_resolution: public targets

This folder and `../public.mk` were added for the public edition (2026-10-13). Everything else in
`GFF/code/lri_numerical_resolution/` is the package as delivered in the September 2026 research bundle,
byte for byte (checked against `sha256_manifest.json`). The package's own `README.md` is its final report;
it mentions files that are not exported here (the note copies `long_range_ising_complete.*`, `previous/`,
`additions/`, `source_diff.patch`, `build_note.py`, `make_readme.py`, `conversation_progress.md`, the run logs
`verification/records/logs/` and three note-build records). They are not needed to reproduce anything; the
note is `GFF/note/`.

## What the package establishes

The full-graph numerical control of the one-dimensional five-loop coefficient (note Section 14): raw Laurent
amplitudes of all 59,145 ordered six-vertex graphs, integrated without any analytic period as input, reassembled
at 80 digits through minimal subtraction and the fixed point, give C5(1) within 6.4e-13 (span) and 3.0e-12
(largest gap) of the closed form -731.13947662453982585... . It also holds the exact residue certificate of the
26 four-loop and 92 five-loop rows (note Appendix A) and its symbolic check against the RG assembly.

## Targets (run from `GFF/`)

    make -C code/lri_numerical_resolution -f public.mk test     # ~1 s
    make -C code/lri_numerical_resolution -f public.mk replay   # ~25 s

One core, Python >= 3.10 with `public/requirements.txt`; no compiler. The original scripts run unchanged in a
fresh copy under `.work/pkg/`, because they write their records in place. `public/replay.py` compares each
regenerated record with the shipped one and every quoted number with `GFF/results/closed_forms_1/C5_1_quoted.json`,
prints a PASS/FAIL table and writes it to `.work/VERIFY_<target>.md`.

| Step | Original script | What is checked |
|---|---|---|
| test | `verification/symbolic_audit.py` | b4, c4, D5 remainder from the certificate and the RG assembly equal the closed C5 exactly (SymPy) |
| test | `verification/exact_decimal_audit.py` | rational reassembly of the historical degree-22 records; dC5/dH = 5/729 exactly |
| test | `verification/audit.py` | forward reassembly of all raw amplitudes with the saved reference; Section 14 table, budget, README values |
| replay | `verification/lower_controls.py` | lower-loop degree-32 data against the analytic C0..C4, b3, c3, b4, c4 |
| replay | `verification/audit.py --refresh-reference` | fresh 80-digit K, L, P4 (mpmath 4F3(1)), P5 (Gamma quadrature), closed-form C5(1) |
| replay | `verification/regenerate_graph_audit.py` | 59,145 graphs and 49,605 combined graphs regenerated; SHA-256 of the executed inputs |
| replay | `verification/enumeration_audit.py` | 60 sectors, 342 and 335 exponent groups, no a = -2 derivative sector |
| replay | `public/graph_classes.py` (new) | 129 = 92 + 6 + 3 + 28 unlabelled classes; certificate words and RG weights; Section 12 table |

Tolerances: integers, hashes, flags and exact rationals must agree exactly; decimal records written at 80 working
digits must agree to 1e-55 relative (observed: identical on macOS/arm64 with mpmath 1.3.0 and 1.2.1); quoted
decimals must agree to one unit in their last quoted digit.

## Production rerun (not part of `replay`)

The raw five-loop integrals (`verification/records/combined5_*.json`, `amplitude5_*.json`) and the lower-loop
inputs (`lower_*_32.json`) were produced by the commands of the package README, section "Full integral
regeneration". They need a C++17 compiler with OpenMP, Linux, and for `--method combined-simd` an x86-64 CPU with
AVX-512F (the driver checks `/proc/cpuinfo`); `--method scalar` needs a 64-bit long-double significand (x86-64,
not arm64). From the production logs (Intel Xeon Platinum 8573C, 4 threads): lower loops 8 min, scalar degree 18
21 min, combined degree 18/22/24 10/8/12 min, about 1 h wall and 4 core-hours in total. The weight array alone
is about 2.3 GB at degree 24 (the log label "W MB" counts 8-byte scalars; the package README says to double it);
request 16 GB. A Slurm template is in the GFF REPRODUCE guide. Thread reductions and libm can change the
last bits, so a rerun is compared with tolerances, not bitwise.

`public/lattice_comparison.py` (run by `make -f public.mk replay`) recomputes the external lattice comparison of
Section 14 of the GFF note: the six Borel-Pade-Leroy ranges of y_t = 1 - Delta_E at s = 0.6, 0.7, 0.8 from the
closed-form C0..C5, the absence of positive Borel poles, the s = 0.8 tension with the Monte Carlo value of Uzelac,
Glumac and Anicic (Phys. Rev. E 63 (2001) 037101), and the C5 +-20% statement. mpmath only; seconds.
