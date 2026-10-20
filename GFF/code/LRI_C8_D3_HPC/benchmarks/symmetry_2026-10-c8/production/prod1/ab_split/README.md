# Campaign a/b split of the production C8 (2026-10-12)

Campaigns a and b integrate the same graphs with importance rates 0.8 and 0.7. The production reads a 1604.684 ±
1.239 and b 1600.527 ± 1.445, pull +2.18. The independent c8opt production uses the same two rates and reads a 1603.53
± 4.91 and b 1598.42 ± 6.24, pull +0.64.

`ab_split.py` (run from the package root with numpy, on the local copy
`LRI_C8_D3_HPC_production/results_prod1-20261008/`) works as follows:
- It recomputes the per-campaign C8 with the package's own assembly, `tools/assemble.py combine`. C8 is reproduced
  exactly: 1602.6052229663.
- It splits a − b, linearized with the order-8 row of the Jacobian, over sectors and loops. The linearization
  reproduces +4.1573 exactly.
- Within L8 it splits a − b over graphs (`graph_replicates.csv`; the graph sums reproduce the batches to 6e−15), and by
  the production tail index (`../tail_ntrend/prod_tails.csv`).

Output: `report.txt`.

## Results

- **By sector and loop: the difference is spread out.** Most terms are positive:
  - free L5 +0.19 ± 0.10 (the largest pull, +2.0);
  - free L7 +0.90 ± 0.72;
  - free L8 +1.36 ± 1.22;
  - power L8 +1.39 ± 1.13.

  No single term dominates.
- **By graph:** the per-graph a − b pulls have χ²/dof 0.994 (16,064 free L8 graphs) and 1.010 (4,336 power L8
  graphs). The 10 largest |a − b| graphs sum to +0.19 (free) and −0.07 (power).
- **By tail index:** the free L8 bins (ξ̂ ≤ 0.3, 0.3–0.44, 0.44–0.6, 0.6–0.8, > 0.8) have pulls +0.53, −0.31, +0.52,
  +0.62 and +1.39. The power bins have −1.68, +0.30, +2.09 and +0.94.

**Reading** (narrowed 2026-10-12 after Codex results review r1, C8D3-R1).
- No concentrated discrepancy was detected: the +2.18 a/b pull is spread over loops, graphs and tail-index bins, and
  no single graph, loop or bin carries it.
- This does **not** establish that the per-graph SEs are calibrated, nor that the difference is a pure fluctuation:
  - each per-graph pull's denominator is estimated from the same replicates as its numerator, so rare-event-dominated
    graphs can show a squared pull near 1 whatever their size;
  - a small coherent bias spread over many graphs (a diffuse rate effect) would leave χ²/dof near 1 while shifting the
    sum.
- The diffuse +2.18 pull is therefore compatible with a 2σ fluctuation and with a diffuse rate effect.
- c8opt's a − b (+5.1 ± 7.9, the same rates) is uninformative at its precision. The independent production as a whole
  agrees with this one (−0.40σ).
- The four-SE allowance is heuristic and conditional on the sampling assumptions (finite variance, unbiased campaign
  means).
