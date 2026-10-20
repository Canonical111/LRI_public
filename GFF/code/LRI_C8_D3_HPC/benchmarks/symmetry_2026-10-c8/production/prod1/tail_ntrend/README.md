# Heavy-tail N-trend check with the production as the third sample length (2026-10-12)

**Question.** In the pilot, 441 L8 graphs were confirmed "possible infinite variance": 246 free and 195 power, with the
two-campaign mean of the fixed-k (16) Hill ξ̂ above 0.44 at 32,768 points per replicate. A true heavy tail keeps ξ̂
constant as the sample length N grows. Bounded, peaked weights make ξ̂ fall. C62d's discriminator: about N^−0.30 for
its certified-bounded d=2 weights. The pilot measured PF (N = 4,096) against PC (N = 32,768): exponent about −0.23
(free) and −0.18 (power), no rate signature (PLAN-REVIEW-LOG 2026-10-08). The production, with independent seeds and
its own per-replicate N, is the third point.

**Method.**
- `prod_tails.py` computes the production's replicate-mean Hill ξ̂ per L8 graph and campaign from the four L8
  `graph_tails.csv` files, exactly as `tools/assemble.py hill`/`tail_monitor` do.
  - Run on the Mac on verified copies (sha256 against symmetry), 81 s.
  - It reproduces the tail monitor's 10,034 listed rows to 2.2e−16.
- `ntrend.py` compares, per graph-campaign:
  - ξ̂_prod with the bounded-trend prediction ξ̂_4096 · (N_prod/4096)^β, where β is the PF→PC exponent of that
    graph-campaign;
  - ξ̂_prod with the constant (true-tail) value ξ̂_32768.
- Outputs: `prod_tails.csv`, `ntrend.json` (every row plus the summary) and `ntrend_summary.txt`.

## Results (revised 2026-10-12 after Codex results review r1: C8D3-R2, C8D3-R3)

**Sample lengths.** Production lengths equal to a pilot length (4,096 or 32,768) repeat that length with fresh seeds.
They are reproducibility checks, not trend tests: at 32,768 the trend and constant predictions coincide. Only
genuinely new lengths (8,192, 16,384, 65,536) test the trend. Medians carry 68% bootstrap bands over graphs.

**New sample lengths.** These are 8,192 and 16,384, which lie inside the pilot's range (interpolation), and 65,536,
beyond it (extrapolation). Medians with 68% bootstrap bands; "constant" is the pilot's ξ̂ at 32,768, which a true
heavy tail would keep:

| group | graph-campaigns | ξ̂_prod / trend prediction | ξ̂_prod / ξ̂_32768 | closer to trend / constant | β PF→prod (β PF→PC) |
|---|---|---|---|---|---|
| free a | 195 | 0.997 [0.993, 1.006] | 1.166 [1.160, 1.178] | 172 / 23 | −0.228 (−0.229) |
| free b | 202 | 0.998 [0.990, 1.002] | 1.187 [1.175, 1.194] | 176 / 26 | −0.260 (−0.258) |
| power a | 62 | 0.999 [0.991, 1.016] | 1.254 [1.205, 1.277] | 56 / 6 | −0.190 (−0.176) |
| power b | 53 | 1.004 [0.996, 1.009] | 1.256 [1.243, 1.294] | 49 / 4 | −0.203 (−0.194) |

The same rows by length (`summary.*.new_n.by_n`):

| length | role | graph-campaigns | ξ̂_prod / trend | ξ̂_prod / ξ̂_32768 | closer to trend |
|---|---|---|---|---|---|
| 8,192 (power) | interpolation | 77 | 0.996–1.000 | 1.30–1.38 | 74 |
| 16,384 (free) | interpolation | 385 | 0.997–0.999 | 1.17–1.19 | 338 |
| 16,384 (power) | interpolation | 37 | 1.006–1.031 | 1.13–1.14 | 30 |
| 65,536 (free) | extrapolation | 12 | 0.965–1.020 | 0.82–0.88 | 10 |
| 65,536 (power) | extrapolation | 1 | 0.936 | 0.871 | 1 |

**Reading** (corrected 2026-10-12 by the coordinator; rev 1 called the production a third point beyond the pilot and
said "below the constant").
- Most new-length rows (499 of 512) are **interpolations**. With independent seeds, they land on the falling PF→PC line
  to about 1% in the median, 13–38% *above* the pilot's 32,768 value. That confirms the pilot's N-dependence is not a
  seed fluctuation, but adds no lever arm.
- The **extrapolation** to 65,536 has only 13 graph-campaigns. There ξ̂ keeps falling: medians 0.82–0.88 of its
  32,768 value, and 0.94–1.02 of the trend prediction. 11 of 13 are closer to the trend.

**Repeated sample lengths (reproducibility).** The ratio ξ̂_prod / pilot ξ̂ at the same N has median:
- free 0.965 [0.958, 0.975] (a, 51 at 32,768) and 0.990 [0.974, 1.000] (b, 44);
- power 0.990 [0.982, 1.006] (a, 133, mostly 4,096) and 1.013 [0.997, 1.021] (b, 142).

**The 16 steady-ξ̂ power candidates.** They are 0.68–1.87 at production. Those at new lengths mostly follow the trend
(`ntrend.json`, `summary.candidates`). Margin probes 571479 and 571516 found no rate deficit in any of them.

**a/b shift of ξ̂ at matched sample length.** Only pairs with equal N are compared: production pairs with unequal N
(47 free, 51 power) are excluded. The face model of a rate-limited tail predicts ξ̂_b − ξ̂_a = −(1 − ξ̂_a)/7. Medians
with 68% bands:

| sector | sample | pairs | observed ξ̂_b − ξ̂_a | face model |
|---|---|---|---|---|
| free | pilot N = 4,096 | 246 | +0.108 [+0.099, +0.123] | −0.004 |
| free | pilot N = 32,768 | 246 | +0.029 [+0.024, +0.036] | −0.059 |
| free | production N = 16,384 | 173 | +0.049 [+0.047, +0.050] | −0.043 |
| free | production N = 32,768 | 24 | +0.034 [+0.033, +0.037] | −0.064 |
| power | pilot N = 4,096 | 195 | +0.151 [+0.127, +0.173] | +0.051 |
| power | pilot N = 32,768 | 195 | +0.073 [+0.057, +0.079] | −0.006 |
| power | production N = 4,096 | 118 | +0.208 [+0.194, +0.215] | +0.054 |
| power | production N = 8,192 | 15 | +0.045 [+0.009, +0.080] | +0.012 |
| power | production N = 16,384 | 9 | +0.074 [+0.067, +0.090] | +0.001 |

- **Free sector:** the shift is positive at every matched length, opposite in sign to the rate-limited prediction. So
  there is no rate signature.
- **Power sector:** the shift has the predicted sign at small N, but it is several times larger and falls with N. It
  identifies neither a rate-limited tail nor its absence: inconclusive. (Production N = 65,536 and 32,768 have 2 pairs
  each and are not tabulated.)

**Tail monitor.**
- 0 graphs flagged (above 3% of their group's variance); the largest single share is 1.65%.
- The listed graphs (ξ̂ > 0.44) carry 62% of the free and 99.5% of the power L8 group variance. So the power L8 error
  is dominated by graphs whose ξ̂ is high at their small N, and the trend above is the evidence that their variance is
  finite.

**Conclusion.**
- With independent seeds the production reproduces the pilot's falling ξ̂(N) at intermediate lengths. In the few
  graphs run beyond the pilot's range (65,536) ξ̂ keeps falling at the trend's rate (N^−0.23 free, N^−0.19 to −0.20
  power), not constant as a true heavy tail would. The extrapolation rests on 13 graph-campaigns.
- In the free sector the campaign shift shows no rate signature; in the power sector it is inconclusive.
- This is empirical evidence, not a certificate. The d=3 U^(3/2) kernel blocks C62d's exact tc_cert; see the margin
  probes for the analytic side.
- The four-SE allowance remains heuristic and conditional on finite variance.
