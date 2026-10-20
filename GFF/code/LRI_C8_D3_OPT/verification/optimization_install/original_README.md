# C8 in the three-dimensional long-range Ising model

This package extends the supplied `LRI_C7_D3_HPC` calculation to the coefficient
of **epsilon^8 in the thermal scaling dimension**, with **epsilon = 2s - 3**:

\[
\Delta_{\mathcal E}(3,\epsilon)
=\frac32-\frac{\epsilon}{2}+\gamma_r(g_*(\epsilon),\epsilon)
=\sum_{n=0}^{8} C_n(3)\epsilon^n+O(\epsilon^9).
\]

It supplies the complete regenerated graph inputs, the three-dimensional
mixed-forest integrator, analytic low-loop data, fixed-point assembly,
replicate covariance, and restartable local/Slurm-array campaign tools.
The scientific scheme and local subtractions are inherited from the supplied
study; the new independent checks are described in `docs/DERIVATION.tex`,
`inputs/coverage.json`, and `verification/`.

## Scope and current numerical status

The complete input contains **24,173 active kernels** at loops three through
eight, including **20,400 eight-loop kernels and all 248 eight-loop primitives**.
Every required loop keeps its regulator Taylor polynomial through `z^(8-L)`.
The two-loop jets are analytic; every retained loop-three through loop-eight
kernel is integrated in both independent campaigns.

The delivered numerical run is a **full-coverage pilot**, with its design frozen
before integration. It is not a precision production campaign. Its raw
checkpoints, complete-net coverage, estimator, covariance, bootstrap controls,
and lower-order comparisons are retained under `results/pilot_20261008/`.
The pilot gives **C8(3) = 1514.6302**, with **sampling standard error 161.6820**.
The separate power-free coefficient is 1553.7029 (SE 153.8475), and the
power correction is -39.0727 (SE 49.7806). Their covariance is retained.
These are exploratory estimates: the eight-loop nets contain only 16 points
per graph and replicate, so the quoted sampling error is not a demonstrated
production reporting allowance.

`docs/C8_3D_calculation.pdf` and its LaTeX source give the result, derivation,
and limits. `results/pilot_20261008/C8_result.json` retains the complete
machine-readable diagnostics. All 21,342,208 planned evaluations finished;
the C3–C7 reference comparisons have absolute pulls below two.
A new production design must use fresh seeds and exclude any pilot used to
choose the allocation.

## Changes that are essential for C8

1. Integrate the complete eight-loop inventory, rather than extrapolating C7.
2. Keep one additional regulator coefficient at **every** lower loop.
   The required maximum powers at loops 2–8 are **6, 5, 4, 3, 2, 1, 0**.
3. Restore the **143 power-free and 119 power-containing nonzero L7 kernels**
   removed by the C7 top-channel cancellation. Their separate beta/mass jets
   affect C8. The same cancellation is used only at L8.
4. Use `U_F^(-3/2)` for each forest denominator and `x_e^(-1/4+z/4)` for
   each edge. Local power subtractions do not remove edges from the logarithmic
   root numerator.
5. Assemble the power correction as `F8(free+power)-F8(free)`, including the
   nonlinear changes involving lower loops. No power correction is set to zero.

The new top-loop combination is

\[
C_8(3)\supset\frac{3\widehat c_{8,0}-\widehat b_{8,0}}{19683}.
\]

The newly evaluated analytic coefficient is
`b[2,6] = -29.25812448091680655867122722198915804534567924810911619984...`,
with `c[2,6] = b[2,6]/6`.

## Build and quick verification

Requirements: Python 3.10 or newer, GNU C++17 with OpenMP and libquadmath,
compatible Boost multiprecision headers, and GMP development headers/libraries.
The tested native environment used GCC 13.3, Boost 1.77 and GMP 6.3.
The long-double arithmetic contract requires at least 64 significand bits and
the extended exponent range; x86-64 GNU/Linux meets the tested contract.

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements-tested.txt
make -j4
OPENBLAS_NUM_THREADS=1 python3 -B tests/test_rg.py
OPENBLAS_NUM_THREADS=1 python3 -B tests/test_campaign.py
make -j4 reference points
make test-native
make test-points
```

Provide site-specific include/library flags through `CPPFLAGS` and `LDFLAGS`
when needed. For example, a Boost installation can be selected with
`make CPPFLAGS=-I/path/to/boost_1_77_0`. Strict arithmetic compiler flags
cannot be overridden by fast-math or contraction options.

`reference_c7/` contains a small, untouched subset of the uploaded C7 source
and graph payloads, so the native regression is self-contained. The tests
do not require the original 100 MB ZIP. Source and input hashes are retained.

To regenerate the analytic jets:

```bash
python3 -B tools/prepare_low.py
```

This overwrites the generated low inputs and verification reports; finish it
before freezing any campaign. Graph regeneration and the full independent
graph audits are described in `docs/GRAPH_GENERATION.md`. The generated graph payloads
are already included, so regeneration is optional for running integrations.

## Run a new full-coverage pilot

Each point count is a power of two. Every randomized replicate sums every
active graph; individual Sobol points and checkpoint chunks are not
independent error samples.

```bash
python3 -B tools/campaign.py plan results/new_pilot \
  --seed 6129871430538291 --purpose pilot \
  --replicates 8 --points 16 --threads 2 --graph-block 32 \
  --allocation inputs/pilot_allocation.json
OPENBLAS_NUM_THREADS=1 python3 -B tools/campaign.py run results/new_pilot \
  --workers 4 --threads 2
python3 -B tools/campaign.py status results/new_pilot
OPENBLAS_NUM_THREADS=1 python3 -B tools/assemble.py results/new_pilot --bootstrap 1024
```

The example seed is a separate example stream. Use a new integer seed for each
independent campaign. `inputs/pilot_design.json` contains the delivered pilot's
seed for exact stream reconstruction, together with its allocation.
Re-running `run` resumes from verified completed checkpoints. It refuses
changed scientific inputs or work descriptions. A crashed job lock must be
inspected before removing it; it is never silently stolen.

To reconstruct the delivered result from its saved native checkpoints,
preserving the archived result, use new output paths:

```bash
OPENBLAS_NUM_THREADS=1 python3 -B tools/assemble.py results/pilot_20261008 \
  --bootstrap 1024 --output results/reassembled_C8.json \
  --graph-statistics results/reassembled_graph_statistics.json
```

Reassembly reads the completed checkpoints and does not require a matching
executable. Resuming native work requires the build pinned in the saved
plan; start a new plan after rebuilding on another host. Verify the supplied
files before modifications with `python3 -B tools/delivery.py verify --strict`.

## Production and cluster use

`tools/allocate.py` freezes a per-graph Neyman allocation from completed pilot
statistics, using measured graph costs. The pilot is excluded from production.
Its cost/variance extrapolation is a planning approximation, not a precision
guarantee. Production requires at least 4,096 points per active graph and
16 replicates per campaign. These are conservative software entry conditions,
not proof of convergence.

See `docs/HPC.md` for the local/Slurm workflow, array splitting, checkpoints,
fresh production seeds, and assembly. The package submits no jobs automatically.

## Contents

| Path | Purpose |
|---|---|
| `src/` | C8 native integration kernel and worker |
| `src/enumerate_graphs.cpp`, `src/build_forests.cpp` | Exact graph enumeration, mixed forests and importance rates |
| `regeneration/` | Canonical censuses, preserved lower-loop graph identities and expected payload hashes |
| `inputs/` | Analytic jets, all active graph payloads, complete graph inventories and bound coverage certificate |
| `tools/rg.py` | Fixed-point extraction, exact checks, Jacobians, affine high-loop map |
| `tools/campaign.py` | Frozen plans, local workers, Slurm job elements, checkpoint verification |
| `tools/assemble.py` | Complete coverage, both sectors, full covariance, bootstrap and lower-order checks |
| `tools/allocate.py` | Pilot-derived production allocation and projected cost |
| `tools/generate_graphs.py`, `tools/audit_graph_forests.py`, `tools/verify_graph_census.py` | Reproducible graph generation and independent full-coverage audits |
| `tests/` | Algebraic, coverage, covariance and native arithmetic checks |
| `reference_c7/` | Untouched small C7 regression fixture set |
| `reference_study/` | Untouched LaTeX study supplied with the original request |
| `verification/` | Graph, analytic, arithmetic and performance evidence |
| `results/pilot_20261008/` | Frozen pilot, every raw checkpoint, estimator and allocation diagnostics |
| `docs/` | Mathematical derivation, numerical contract and HPC runbook |

No known physical coefficient is used as a fitting constraint. Sampling error
estimates do not cover a common error in the inherited graph/renormalization
framework and do not bound truncation of the epsilon expansion.
