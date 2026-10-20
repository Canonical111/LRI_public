# Expected values: C0..C5 at general dimension

`expected.json` lists what the note (Sections 1, 12-15) and the paper (Table tab:pt at f496d39a) quote, and the values
the paper printed in earlier versions (kept as checks of the records), from the three bundle packages
`GFF/code/lri_general_special_functions_update`, `GFF/code/lri_general_closed_update` and
`GFF/code/lri_general_periodization_update`:

- `formulas`: C0..C3(d), b3, c3, the general C4(d) and C5(d) and the fourth- and fifth-order RG combinations b4, c4, D4,
  D5, transcribed from the note (equation labels and line numbers at git fa71533) in SymPy syntax;
- `values`: the numbers quoted from these packages (C2..C5 at d = 2 and 3 to the digits of the Section 1 table, Q2 to
  50 digits, P4(2) to 50 digits, P5(2) to 25 digits, the Horn counts of L_d, Z_d, K_d, the vector B7 at q = 1/2), each
  with its record and field;
- `cross_checks`: values owned by other units that these packages can be compared with (the d=2 closed forms of
  `GFF/results/closed_forms_2`, the d=3 values of the C63d unit, the d=1 values of the C71d unit), with their sources.

The packages' delivered records stay inside the code folders (`verification/...`), where the delivered scripts read and
write them. Each package's `make -f public.mk replay` reruns its scripts in a copy, compares with those records and with
the rows of this file that name the package, and prints a PASS/FAIL table (also written to `public/out/replay.json`).

Scope: the formulas for C4(d) and C5(d) come from a single graph-by-graph minimal-subtraction calculation that has not
been rederived independently at generic d. They are checked exactly at d = 1 (against the analytic C4(1), C5(1)) and, at
d = 2 and 3, only through the six masters (closed forms at d = 2, 50-digit evaluations at d = 3). The finite Horn arrays
are a function-class statement: their sums must be continued as complete combinations outside 1/6 < d/4 < 1/2, and they
are not a reduction to ordinary hypergeometric values.
