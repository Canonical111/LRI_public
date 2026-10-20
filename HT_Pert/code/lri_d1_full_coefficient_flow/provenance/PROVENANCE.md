# Input provenance and boundaries of the new result

`ENVIRONMENT.json` records the exact supplied archive hashes and unchanged
vendor/input hashes. The prior coefficient, gap, and asymptotic input files are
copied without alteration. The two independent coefficient helpers and the
previous fitter are retained under `vendor/`; they are not new code.

The new source in `code/ragged_quotient.py` is an ordinary stationary-quotient
implementation of the same finite Dconn model with ragged subcutoff vacuum
storage. It is not a new physical counterterm or a proof of the model's continuum
limit. `tests/exact_stationarity.py` verifies the quotient order by exact Fraction
matrix arithmetic; `tests/independent_coefficients.py` compares the physical
coefficient recursion to the ordinary and rational reference implementations.

The frozen forecast uses only the previously available corrected finite data.
The numerical model choices and old cutoff endpoints are in
`inputs/PROTOCOL.json`. Its JSON and checksum were written before generating the
new high-order records. The model predictions themselves are never rewritten by
the evaluation scripts. Lower-order corrected data through Lambda118 were
already available, so the new test withholds newly calculated HIGH-ORDER
coefficients, not every datum of each new cutoff. Prior thermal continuum values
were historically visible; this is not claimed prospectively blind research.

The subsequent unconstrained leading-polynomial probes use the new data and
are retrospective exploratory attempts. They are not analytic determinations,
physical confidence intervals, or an accepted fit ensemble. Both successful and
rank/sample-count rejected designs remain in the records.

No physical C4..C8 benchmark enters the solver or forecasts. C2,C3 and independent
gap exponents are declared controls of the linked forecasts only. The direct
coefficient calculation does not use those controls. Original HPC data are used
as independent raw-coefficient checks, not relabelled as new corrected outputs.

All tables distinguish computed finite values from extrapolated quantities.
No claim that all full C6,C7,C8 tail amplitudes have been derived is made.
The theoretical formulas supporting stationary elimination are elementary
finite-matrix identities derived in `docs/METHOD.md`; no external paper supplies
the new finite-cutoff numerical values.
