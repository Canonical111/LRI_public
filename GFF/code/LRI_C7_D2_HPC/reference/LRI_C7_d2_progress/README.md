# Two-dimensional seventh-order LRI calculation: computed sectors

## Read this first

**The full physical coefficient C_7(2) has not been determined.** This package is
an actual numerical extension of the earlier two-dimensional finite-forest
calculation to seven loops, not an extrapolation from C_0,...,C_6.

In the convention epsilon = 2s - 2, the new computed quantities are:

| Quantity | Estimate | Sampling standard error |
|---|---:|---:|
| Complete primitive seven-loop contribution | -8657.426219598536 | 1.2165092149844356 |
| Power-free fixed-point coefficient, including that primitive contribution | -3955.3837529230477 | 76.54167996471733 |
| Power-containing correction to the physical coefficient | **not evaluated** | **not bounded** |
| Full C_7(2) | **unset** | **unset** |

The second row includes logarithmically subdivergent graphs and the required
lower-loop regulator coefficients. It is **not** the first row, and is **not**
the complete physical coefficient. The exact bookkeeping relation is

    C_7(2) = C_7^power-free(2) + Delta_power C_7(2).

No assumption Delta_power C_7(2)=0 is made. Its observed cancellation at sixth
order does not establish seventh-order cancellation. The errors above are
replicate-based sampling standard errors, not rigorous intervals and not bounds
on the missing correction or shared field-theory implementation errors.

## Logic of the calculation

1. Read the retained canonical seven-loop inventory (3,986 classes). Reconstruct
   exact rational coupling and mass weights. Identify proper logarithmic and
   power-containing two-point subgraphs.
2. For power-free graphs construct the complete local logarithmic-forest kernel
   in Schwinger parameters. Form numerator cancellations before integration.
   The same construction reproduces all 492 retained L=3,...,6 kernels exactly
   after vertex/edge relabelling; new L=7 kernels are independently checked by
   rational Kirchhoff determinants.
3. Retain the regulator dependence through epsilon^(7-L) at loop order L.
   The new fifth Taylor coefficient at two loops is evaluated independently on
   two Cauchy contours from the exact hypergeometric master.
4. Integrate the finite kernels using per-graph randomized Sobol nets with
   forest-aware importance rates. Use full power-of-two nets per graph and
   estimate errors between randomizations, never between points of one net.
   A separate pilot freezes graph allocations; it is excluded from production.
5. Integrate the 44 primitive classes independently. Their conformal completions
   form 14 periods; three are exact products of known lower periods. Use those
   products as replacements, after checking their directly sampled values.
6. Combine the two production campaigns with fixed equal weights on the RG
   Taylor data, not inverse-error fitted weights on C_7. Add the common primitive
   estimate once. Retain coupling/mass and Taylor-order covariance, solve the
   regulator-dependent fixed point, and propagate uncertainty.
7. Audit the power-containing sector separately. Among 845 nonzero seven-loop
   target classes, 740 have a conservative structural Gamma/kite MS route and
   105 do not. **These are routing counts, not 740 completed integrations.**
   No complete numerical power correction is supplied by this package.

See `notes/C7_d2_progress.tex` / `.pdf` for the equations, normalization,
intermediate steps, numerical comparisons, and precise remaining target.

## Contents

- `code/`: strict extended-precision native kernel, graph generator, sampling
  driver, exact checks, primitive normalization, final assembly, reproduction.
- `inputs/`: frozen per-graph kernels and rate tables, Sobol matrices, allocation,
  Gamma prefactors, and exact two-loop Taylor data. These are ready to use.
- `records/productionA`, `productionB`: fresh nonprimitive production. Each has
  16 randomized replicates and 9,169,152 kernel evaluations.
- `records/primitiveA`, `primitiveB`: independent primitive production, each
  16 replicates and 2,883,584 evaluations.
- `records/pilot3`: completed allocation pilot, excluded from final estimates.
- `verification/C7_d2_progress_result.json`: final computed-sector statistics,
  covariance, lower-order checks, bootstrap, coverage and provenance.
- `verification/power_unresolved.csv`: all 845 nonzero power-sector classes,
  including their exact weights and whether the structural reduction closes.
- `reference/`: retained canonical classes, primitive completion dictionary,
  and minimal unmodified dependencies for reproducing the structural audit.
- `verification/source_provenance.json`: hashes of the three input archives.

There are **24,105,472 fresh production kernel evaluations** across the four
campaigns. Pilot and numerical tests are not included in that count. The
previous one-dimensional C_7 result, and the two-dimensional C_6 result, were
not inputs to the new C_7 estimator. C_3 through C_6 are checked afterward.

## Reassemble without rerunning integrals

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 code/reproduce.py
```

The script verifies frozen input/data hashes, requires complete nonoverlapping
row coverage, checks task metadata, and reconstructs the reported means and
covariance. It also verifies that the full C_7 field remains unset. Exact
saved-data reassembly was tested in the delivered directory; platform/library
changes can affect the final floating-point rounding. Tested versions are in
`verification/environment.json`.

## Build and run numerical checks

Requires GCC with OpenMP, libquadmath, and Boost multiprecision headers.

```bash
make -j4
make test
```

The integration uses long double with at least 64 significant binary bits,
GNU binary128 fallback, and a 300-decimal fallback. Cancellation thresholds
remain 1e-9 and 1e-23. Do not use fast-math. The fallback now shares monomial
products instead of exponentiating every monomial. That changes rounding order,
not arithmetic precision; 69 high-precision comparisons and a matched-stream
replay are supplied. Final coefficient and covariance analysis use NumPy
float64, as did the retained pipeline.

## Rerun the delivered production design

The frozen input files are sufficient; no original /mnt/data working folder is
required. Use **new output tags** for a rerun. These commands perform expensive
integrations (they are not planning-only commands):

```bash
python3 code/run_campaign.py rerunA --loops 3 4 5 6 7 \
  --replicates 16 --allocation inputs/allocation.json \
  --net a --seed 6749215 --threads 8 --rate .8
python3 code/run_campaign.py rerunB --loops 3 4 5 6 7 \
  --replicates 16 --allocation inputs/allocation.json \
  --net b --seed 85037479 --threads 8 --rate .9
python3 code/run_campaign.py rerunPrimitiveA --loops 7 \
  --primitive --points 4096 --replicates 16 \
  --net a --seed 294092991 --threads 8 --rate .8
python3 code/run_campaign.py rerunPrimitiveB --loops 7 \
  --primitive --points 4096 --replicates 16 \
  --net b --seed 684028257 --threads 8 --rate .9
```

These are exact stream replays, not independent new campaigns. New production
must use independently generated nets/seeds. The supplied nets contain 16
replicates. The driver is a research driver, not a newly validated distributed
HPC orchestration package. The numerical worker accepts sample intervals and
is threaded; full cluster scheduling and merging should be adapted from the
previous C6(2) HPC package with seventh-order schema and coverage checks.

`code/finalize.py` reconstructs the specifically delivered four campaigns.
For different campaigns, update the explicit campaign list and primitive
reference accounting rather than adding graph totals as physical coefficients.
Never interpret primitive records alone as C_7.

## Regeneration boundaries

`code/build_schwinger.cpp` rebuilds kernels from `reference/classesL.txt`. Its
initial generic importance rates differ from the frozen rates: lower-loop
rates were copied from the proven prior implementation after exact edge
relabelling, and seven-loop rates were subsequently strengthened by the
integer/half-integer face-power bound. These rate transformations are recorded
in `legacy_mapping.json` and `parity_rate_update.json`. The ready-to-use frozen
rates, not the generator's initial rates, reproduce production.

`python3 code/prepare.py` reevaluates two-loop inputs and regenerates the supplied
Sobol matrices; keep a backup before intentionally replacing frozen inputs.
`python3 code/primitive_checks.py` freshly evaluates the scalar hypergeometric
references. `python3 code/audit_power_routes.py` reruns the **structural** power
routing audit. Its old reference routines are NOT a completed seven-loop
numerical MS evaluation; this command never invokes their numerical master
jets. The old six-loop Laurent truncation would require a separate seven-loop
extension before such an evaluation.

## Evidence limits

The exact tests establish graph/kernel and coefficient-assembly identities.
The numerical controls support the reported computed-sector sampling errors.
They are not an independent seven-loop field-theory determination or a rigorous
error enclosure. The parent research notes and accepted C_0,...,C_6 entries have
not been overwritten, and no numerical full C_7(2) has been inserted there.
