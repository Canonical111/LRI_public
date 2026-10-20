# C7(1): full seventh order of the one-dimensional long-range Ising model

This folder is the public layer of `GFF/code/LRI_C7_HPC`, the package that computed

> **C7(1) = −322550 ± 41** (estimator −322549.8888129889, sampling standard error 10.08791295; the ±41 is the output
> of a pre-registered empirical policy, not a rigorous bound). A post hoc truncation-aware assessment gives
> −322524 ± 38.
>
> The paper quotes −322550 ± 40: it rounds the allowance candidate 40.35 (four sampling standard errors) by the PDG rule. The condensed note and this package keep the pre-registered rule, which rounds it up to two significant figures, ±41.

in the convention ε = 2s − 1, Δ_ε = ½ − ε/6 + Σ C_n(1) εⁿ (condensed note, Section "Full seventh order in one
dimension"). The estimator combines 399 independent fresh-seed batches of one frozen design (SDSC Expanse, September
2026, about 2.6×10^5 core-hours) with a direct integration of the 44 seven-loop primitive classes. The records are in
`GFF/results/C7_1/` (final) and `GFF/results/C7_1/v1_46batches/` (the earlier 46-batch combination).

The package's own documentation is `../README.md` (build, campaign tools, cluster recipe), `../docs/NUMERICS.md`,
`../docs/HPC.md`, `../docs/ARCHITECTURE.md`, `../CHANGELOG.md`. `../reference/` is the inherited September 2026
calculation (graph inventory, forest arrays, the archived streams, the retained primitive input and the TeX
derivation), authenticated by `../reference/SHA256SUMS`. The delivery benchmarks cited in `../README.md` and
`../docs/PERFORMANCE.md` (`benchmarks/`) are not part of this public copy.

## Targets (run from `GFF/code/LRI_C7_HPC`)

| Command | What it does | Needs | Time |
|---|---|---|---|
| `make -f public.mk test` | the package's own `make test`: builds `bin/c7_integrate`, then oracle, multithread/shard, malformed-input, pipeline and inventory tests | x86-64 Linux, GCC ≥ 9 with `__float128`/quadmath, OpenMP, Boost multiprecision headers (`CPPFLAGS=-I...`), Python ≥ 3.8 with numpy, scipy, mpmath | about 10–20 min on 16 cores |
| `make -f public.mk replay` | Tier 1: recomputes every quoted number from `GFF/results/C7_1` and `reference/` (214 checks; table in `.work/replay7_tier1.txt`) | Python ≥ 3.8, numpy | about 5 s, one core |
| `make -f public.mk fetch-data` | downloads the merged records (`C7_1_merged_records.tar.gz`, 338 MB) from the project's Zenodo data record ([doi:10.5281/zenodo.23466766](https://doi.org/10.5281/zenodo.23466766)), checks the sha256 in `public/data_C7_1.json` and unpacks them into `GFF/data/C7_1/`; a copy already placed there is used if its sha256 matches | network | |
| `make -f public.mk replay-full` | Tier 2: reruns the production `tools/combine.py` on the hosted records and compares with `GFF/results/C7_1` byte for byte (to 1e-12 where the platform differs in the last bits; see REPRODUCE.md) | the hosted records (0.97 GB unpacked) | about 7 min, one core, < 2 GB (Expanse, 2026-10-13: 409 s, peak 1.7 GB) |

The production rerun is documented in `REPRODUCE.md` (Slurm, placeholders, node sizes, core-hours).

### What Tier 1 recomputes

`C7_final.json` stores, for each of its 9577 sources (24 campaigns × 399 batches, plus the primitive campaign), the
mean and covariance of the replicate values projected through the frozen affine map. From these and the map's
constant K (`reference/verification/full_affine_assembly.json`, whose SHA-256 the result records), the replay rebuilds
in the production order the estimator, its covariance and standard error (bitwise), every quadrature level and the
degree 6→7 check, the telescoped resolution sequence, the lower-order checks, the allowance candidates and the
allowance, the flag, the 399 per-batch values and the inter-batch χ², the primitive cross-check and the post hoc
truncation-aware estimate. It reruns the archived reassembly (`tools/assemble.py --original`, 1 s), checks the
inventory counts of the note from `reference/inputs`, the inherited exact checks in `reference/verification`, both
checksum lists, the batch seeds and the campaign structure. Five quantities need the raw replicate streams and are
checked only as recorded (RECORDED rows): the replicate bootstrap standard error, the half-split estimates, the
spurious-pole means, the zero-pole control terms and the uncontrolled estimator; Tier 2 recomputes them.

### What Tier 2 substitutes

`public/replay7_full.py` imports the shipped `tools/combine.py`, `assemble.py` and `campaign.py` unchanged. Two things
are substituted in memory: the campaign verifier skips the re-reading of checkpoint and task files, which are not
hosted, but keeps every other check and requires the audit's checkpoint list to match the manifest's plan; and
`inputs/L7_coord.txt`, the only input file the combination reads, is rebuilt from `reference/inputs` after a SHA-256
check against every L7 campaign manifest. Every hosted merged stream is checked against the SHA-256 recorded in the
published `C7_final.json`.

## Files of this folder

- `replay7.py`, `replay7_full.py`: the two replay tiers.
- `fetch_data.py`, `data_C7_1.json`: hosted-data pointer.
- `make_data_archive.py`: builds the hosted archive from a production tree (maintainer tool).
- `slurm/archive_and_replay.sbatch`: archive build plus Tier 2 on one node; `slurm/rerun_production.sh`: full rerun.
- `diff_3213ce0_to_shipped.patch`: the production workers ran commit 3213ce0; this diff (tools and tests only) is the
  whole difference to the shipped code (`patch -R -p1` from the package root restores the 3213ce0 files).
- `REPRODUCE.md`, `PROVENANCE.md`, `REVIEWS.md`, `results_map.md`, `requirements.txt`.

## Checksums

`../SHA256SUMS` (515 lines) ships unchanged. The replay verifies it with the `results/` lines mapped to
`GFF/results/C7_1/`; 155 lines name files that are not shipped (`benchmarks/`, two v1 files). A mismatch in code,
`reference/`, the degree-7 weights or the bound result records fails; a mismatch in a documentation or provenance file
is reported as a warning. `../reference/SHA256SUMS` (286 lines) must verify completely, since `tools/assemble.py`
authenticates the archive against it.

## Scope

The allowance is empirical. Plan criterion A5 (optimized radial quadrature no less accurate than the original,
element by element) is reported as not met: 9 of 112 replay elements are less accurate, worst 18× at 4.2e-14 relative,
about 1e-10 of the sampling noise. The degree-6 truncation, not sampling, now limits the precision; the lower orders
agree with their references only after the measured degree 6→7 step and a geometric tail (see `REVIEWS.md`).
