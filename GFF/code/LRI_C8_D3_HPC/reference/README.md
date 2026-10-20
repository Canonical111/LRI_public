# Full numerical C7(3) calculation

Convention: epsilon = 2s - 3.

C7(3) = -227.6181094747
Sampling standard error = 3.82739688
Suggested reporting: -228 +/- 16 (empirical allowance, not a rigorous bound).

Both the power-free and power-containing sectors are included. The power
correction was measured, not assumed zero. The pilot is excluded; both complete
production campaigns use all required graph strata, including all primitive
strata. Previous lower-order values are checks, not fitting constraints.

## Reassemble the saved production
Install numpy, scipy and mpmath, then run from this directory:
    python3 code/analyze.py production_a production_b --bootstrap 4096

The driver verifies raw-record checksums and full graph/replicate coverage.
This reassembles data; it does not rerun the integrations.

## Rebuild and run new integrations
Requires GNU C++17, OpenMP, Boost headers, libquadmath, and GMP development files:
    mkdir -p bin
    g++ -O3 -std=c++17 -fopenmp -ffp-contract=off -fno-fast-math \
        -DC7_USE_GMP src/c7d3_integrate.cpp -lquadmath -lgmp -o bin/c7d3_gmp
    python3 code/run_campaign.py new_a --seed 3074017111 --replicates 24 \
        --allocation inputs/allocation.json --rate 0.8 --threads 8
    python3 code/run_campaign.py new_b --seed 3079017331 --replicates 24 \
        --allocation inputs/allocation.json --rate 0.7 --threads 8

Use new campaign names, preserving the archived results. The two independent
production campaigns each contain 39,264,768 kernel evaluations. The pilot and
independent two-loop control are not included in the estimate. Complete Sobol
nets and whole randomized-replicate covariance must be retained.

## Contents and scope
- inputs/: dimension-three kernels, endpoint rates, analytic low-loop jets,
  and frozen pilot-derived allocation.
- records/: complete production outputs, tasks, net matrices, pilot and controls.
- verification/: final result, covariance, exact assembly and numerical checks.
- src/ and code/: integration and statistical-analysis sources.
- reference/: inherited graph-map hashes and diagnostic reference data.

The graph combinatorics and local-subtraction framework are inherited from the
project; this is not an independent seven-loop field-theory validation.
The worker uses long double, binary128 fallback and explicitly selected
350-decimal GMP arithmetic. No precision reduction is introduced.

The offset/length/hash/points metadata in inputs/inventory.json originates in
the D2 source inventory. The driver uses its graph selection; actual D3 payload
hashes are in DELIVERY_MANIFEST.json.

This archive deliberately excludes the unfinished draft TeX note and generated
executables. It contains the completed numerical calculation and its raw data.
