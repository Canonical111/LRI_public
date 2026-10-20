# Full numerical seventh order in one-dimensional long-range Ising

Convention: epsilon = 2s - 1. This archive assembles the **complete** C7(1),
including the explicitly evaluated power-subgraph contribution.

## Result

- Full estimator: **-323405.3107891946**.
- Propagated sampling standard error: **5861.760221129077**.
- Reported numerical result: **(-3.23 +/- 0.24) × 10^5**.
- The +/-24000 allowance is empirical, not a rigorous interval, probability
  guarantee, or truncation error for the physical epsilon expansion.
- No missing graph contribution is set to zero or replaced by a Padé prediction.
- The earlier primitive estimate -696147.4459362661 (sampling error 25.3678)
  is retained once as an independent input. It is not the full answer.

`verification/C7_assembled_result.json` contains the unrounded mean, joint
covariance, all resolution levels, controls, independent-run comparisons,
bootstrap, lower-order checks and full-minus-power-free correction.

## Read the calculation

- `C7_1d_full_calculation.pdf`: eight-page standalone derivation and evidence.
- `long_range_ising_complete.pdf`: complete 212-page project note; Appendix Y
  is pages 203–210. Earlier formulas are retained; the title and abstract are updated.
- Corresponding TeX sources and the extracted appendix are supplied.
- `verification/source_preservation.json`: exact preservation of all 950 earlier
  displays and the entire previous main body.

## Fast reproduction — no integration

Run from the extracted archive directory:

```bash
python -m pip install numpy
OPENBLAS_NUM_THREADS=1 python code/reproduce.py
```

This verifies the SHA-256 hashes of every accepted production stream, then
reassembles the mean, covariance, telescoping quadrature refinement and bootstrap.
It does **not** rerun expensive seven-loop integrals. The result is deterministic
in the recorded software environment; floating-point libraries on other platforms
may change the last few digits, but not the stated precision.

The final three scalar fields are `C7_full`, `sampling_se`, and
`empirical_allowance`. `joint_sampling_se` is the full coefficient vector.

## What was actually computed

The inventory is 3986 graph classes (125894580 labelled graphs). An exact disjoint
partition of the seventh-order target is:

| Category | Classes |
| --- | ---: |
| Exactly zero channel weight | 459 |
| Additional exactly zero forest polynomial | 535 |
| Primitive, independently retained and re-matched | 44 |
| New power-free nonprimitive integration | 2254 |
| New meromorphic power-sector integration | 694 |

All required five- and six-loop regulator jets are included. The coordinate
prescription and full bare-series certificate cover power-containing graphs
as well as logarithmic forests. No seventh-order power-cancellation identity
is assumed.

The high-loop calculation uses:

1. Two independently randomized, graph-stratified Sobol campaigns for continuous
   power-free cluster-ratio integration. Counts are powers of two per graph.
2. Ordinary independently seeded sampling of discrete binary cluster trees for
   the power sector, combined with analytically continued radial quadrature.
3. Paired degrees 1/3, 3/5 and 5/6. Both resolutions share the same sampled tree.
4. Independently trained fixed zero-pole controls. No physical C5/C6 value is
   imposed as a constraint.

The first L7 degree-1/3 run (`power_refine3_L7_*`) trained the graph allocation
and is **excluded** from the accepted refinement mean. The fresh independent
`power_refine3B_L7_*` run supplies that mean. Pilot records are retained so this
separation can be checked.

`verification/production_audit.json` lists all 30 accepted production files,
random seeds, actual recorded times, SHA-256 hashes, and work counts. The
223824896 continuous points and 7043120 sampled-tree evaluations are not all
independent observations. Errors are estimated from independent replicate totals.
The nominal tensor-node count is 1714336280, with substantial geometry reuse.

## Rebuild the integration programs

The source is C++17, tested with GCC on x86-64 Linux. It uses OpenMP, GNU
quadmath and Boost multiprecision headers. Install the usual compiler and Boost
headers, then:

```bash
make -j2
python -m pip install numpy scipy mpmath networkx sympy
```

Use at most two memory-heavy tensor-quadrature processes concurrently on a
4-GB machine. The delivered safe implementation bounds its caches and uses two
threads per such process. Two earlier memory-interrupted attempts wrote no
accepted output; both were restarted at identical seeds. See the restart audit.

The stored `.bin` integration weights are native extended-precision arrays
(x86-64: 80-bit extended-precision format in 16-byte storage; see runtime metadata). They
must be regenerated on a platform with a different `numpy.longdouble` format.
Move those files out of `inputs/` first, then use, for example:

```bash
python code/prepare_coord.py 5,6,7 1,3,5,6
```

The new weights are generated with 100-digit arithmetic. The fixed input
`cgamma_L*.txt` is regenerated by the same script. The Sobol matrices can be
regenerated using the provided `sobol_net.make_net`; exported Gray-code values
are checked against SciPy's public `random_base2` output. Recorded SciPy: 1.17.0.

### Rerun production

The drivers use paths relative to their own extracted archive. **Use a separate
copy/output tree**, not the delivery copy, to avoid overwriting accepted data.
The continuous drivers deliberately refuse to overwrite output files. The
quadrature drivers skip already completed outputs.

```bash
python code/run_tree_production.py A
python code/run_tree_production.py B
python code/run_power_production.py coarseA
python code/run_power_production.py coarseB
python code/run_power_production.py refine3
python code/run_power_production.py refine5
python code/run_power_production.py refine6
python code/run_power_refine3B.py
```

Use the supplied frozen counts rather than recomputing allocations from the new
production data. The exact per-run commands are also retained in record manifests.
`run_power_refine3B.py` waits for the degree-five completion file to limit memory.

### Regenerate exact certificates

The class enumerator's argument is vertex count, not loop count:

```bash
./code/enumerate_classes 8 inputs/classes7.txt
./code/build_coordinate_forests inputs/classes7.txt inputs/L7
./code/forest_audit inputs verification/forest_polynomials.json
python code/check_forest_exact.py
python code/verify_affine_and_trees.py
python code/check_primitive_coverage.py
```

Class order matters for raw graph-indexed records. Do not mix regenerated or
modified inventories with a different numbering scheme. Keep the delivered input
SHA-256 hashes for exact replication. The reported coverage audit validates the
common class order.

## Rebuild the note

```bash
python code/build_note.py retained/previous_note.tex .
pdflatex -interaction=nonstopmode -halt-on-error long_range_ising_complete.tex
pdflatex -interaction=nonstopmode -halt-on-error long_range_ising_complete.tex
pdflatex -interaction=nonstopmode -halt-on-error C7_1d_full_calculation.tex
pdflatex -interaction=nonstopmode -halt-on-error C7_1d_full_calculation.tex
```

## Scope of the archive

This is a self-contained **C7 numerical reassembly and implementation package**.
The earlier primitive calculation is an explicitly retained measured input; its
summary, error and exact graph/period mapping are supplied. Its older raw period
integrations and the code behind all pre-existing appendices are not re-run or
repackaged here. Previous project archives provide that history.

The accepted numerical allowance does not certify the common graph/renormalization
framework independently. The calculation supplies exact algebraic checks,
independent integrand tests, lower-loop recovery and empirical numerical convergence,
not a rigorous interval enclosure of the physical coefficient.
