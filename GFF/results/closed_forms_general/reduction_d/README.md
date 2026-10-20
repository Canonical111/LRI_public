# Generic-dimensional reduction of L_d and Z_d: expected values (GFF/results/closed_forms_general/reduction_d)

`expected.json` lists every number that note Section 20 quotes for `GFF/code/LRI_C5_general_d`:

- the end-to-end values C5(1), C5(2) and C5(3) through the generic route, with their agreements;
- the checks of the printed formulas at eight dimensions;
- the d = 1, 2, 3 specializations and the 𝔇_L identity at d = 3;
- the pole-node check;
- the independent top-mode probes;
- the numbers from the review's own codes;
- the negative PSLQ results.

It also holds the three-node K_d column of the Section 21 table, which this package's joint review computed. The C5(1..3),
L₃, d_H and d_a values printed elsewhere in the note and in earlier versions of the paper appear as cross-checks; their owners are other
packages.

Each row of `expected.json` gives:

- the quoted text and its line in the note at commit fa71533;
- the comparison rule;
- the record and field it comes from.

The file also binds, by SHA-256, every record that the replay reads. To check them all, run
`make -C GFF/code/LRI_C5_general_d -f public.mk replay`.

The records themselves stay in the code package, at the paths its scripts read and write. The main ones are:

- `review/joint/numerics-end-to-end/e2e_report.json`;
- `specialize/results/*`;
- `L/results/*`;
- `Z/results/*`;
- `review/lemmaG-numeric/results/*`;
- `review/topmode-numeric/results/*`.

One quoted bound differs from its record. The note at fa71533 prints 3·10⁻²¹ for the pole-node check, but the record
reaches 4.76·10⁻²¹. `expected.json` uses the corrected text 5·10⁻²¹ (note change N9) and keeps the printed value in
`quoted_fa71533`.
