# Before the Stage-6 inspection (2026-10-05): F11 fixed, route (b) implemented, the cost table on symmetry's own factors

Mac only (arm64, anaconda Python 3.10.11, numpy 1.23.5); no cluster job, 0 core-hours. The code change is 23540b2
(`tools/design.py`, `tools/production.py`, `tools/sweep.py`, `tests/test_pipeline.py`); its Mac suite is
`../../../mac_2026-10-c8/pre6/README.md`. This folder recomputes, from committed Stage-5 records, what the change does
to J-DES-5's designs and to the refined cost table (`docs/PERFORMANCE.md`, "Stage 5: the refined cost table").

## F11: r from the smallest multiplier

The Stage-5 `split()` gave each (sector, L) the replicates r of its LARGEST stratum multiplier; the fixed one takes the
largest power of two in [32, 128] not above its SMALLEST positive multiplier (`docs/DESIGN.md`, rule 4 and "F11", for
the variance-cost argument). `pre6_tables.py` runs `tools/design.py`'s `optimize()` on each J-DES-5 freeze's own strata
(V1, C1) at its own target, (a) with the Stage-5 rule re-implemented in the script, which reproduces all four frozen
designs exactly (r, s and cost to 1e-9), and (b) with the package's fixed rule:

| Target | What changes | Predicted SE (target) | Lane core-hours on symmetry | Over the continuous bound |
|---|---|---:|---:|---:|
| 1e-3 | free L8 r 128 → 32; s: free L8 primitives 1 → 8, free L5 16 → 32, free L7 2 → 4, power L3 1 → 2, power L4 2 → 4, power L5 2 → 4 | 44.21 (46.00), was 32.63 | **1,738**, was 3,963 | ×1.31, was ×2.98 |
| 5e-4 | nothing | 22.61 (23.00) | 5,856 | ×1.10 |
| 2.5e-4 | nothing | 11.31 (11.50) | 23,423 | ×1.10 |
| 1.35e-4 | nothing | 6.08 (6.21) | 76,623 | ×1.05 |

At 1e-3 the remaining ×1.31 is the r ≥ 32 floor of strata whose multiplier is below 32 (power L8's is 7.3) and the
power-of-two rounding. On these freezes the costliest stratum of free L8 is also the one with the smallest multiplier,
so "costliest" and "smallest" give the same design here.

## The cost table with symmetry's own `dd+mp256` factors

`pre6_tables.md` (from `pre6_tables.json`). The `dd+mp256` factors on symmetry come from the gate of the exact
`dd+mp256` build there (job 570210, `../close/clflag.570210.0/jflag_dd+mp256/numerics_flags.json`, sha256
`99e42907…`) by `aflag7_table.py`'s `speedups()` (F4 per sector at L8: free ×2.485, power ×2.644; F2's pooled task
seconds at L ≤ 7); on Expanse, as before, Stage 4c's `dd+mp256+exp1` gate. Each stratum's core-hours are divided by
its factor and the allocation is kept. (This README said route (b) re-costs the allocation and "can only do better";
**measured afterwards, the 23540b2 `design.py` did worse**: finding F13 in `../../pre6/README.md`, where the profile
cost model confirms these fixed-allocation rows to 1.5%: 669 / 2,309 / 9,236 / 30,067. F13 is fixed for the Stage-6
inspection: a route-(b) freeze now keeps the cheaper of its re-optimized design and the exact design re-costed,
`docs/DESIGN.md`, "Route (b)".)

| Design | Row | 1e-3 | 5e-4 | 2.5e-4 | 1.35e-4 |
|---|---|---:|---:|---:|---:|
| J-DES-5 freeze (Stage-5 rule) | default, symmetry | 3,963 | 5,856 | 23,423 | 76,623 |
| J-DES-5 freeze (Stage-5 rule) | `dd+mp256`, symmetry (own k) | 1,581 (×0.399) | 2,298 (×0.392) | 9,193 (×0.392) | 30,503 (×0.398) |
| J-DES-5 freeze (Stage-5 rule) | `dd+mp256`, Expanse (Expanse k) | 1,751 (×0.467) | 2,503 (×0.456) | 10,011 (×0.456) | 33,435 (×0.464) |
| F11 fixed | default, symmetry | 1,738 | 5,856 | 23,423 | 76,623 |
| F11 fixed | default, Expanse SU | 1,640 | 5,487 | 21,949 | 72,125 |
| F11 fixed | `dd+mp256`, symmetry (own k) | **678** (×0.390) | **2,298** (×0.392) | **9,193** (×0.392) | **30,503** (×0.398) |
| F11 fixed | `dd+mp256`, Expanse (Expanse k) | 742 (×0.452) | 2,503 (×0.456) | 10,011 (×0.456) | 33,435 (×0.464) |

The Stage-5 row of `dd+mp256` on symmetry with Expanse's factors was 1,851 / 2,669 / 10,675 / 35,505: symmetry's own
factors are about 15% lower, as the G5 re-check found (×0.392-0.399). The A-PERF-5 column of `dd+mp256` on symmetry is
recomputed the same way (`pre6_tables.md`, second table; `docs/PERFORMANCE.md`).

As in Stage 5, σ² is the J-SWEEP-2 sweep's projection (2 replicates × 512 points per graph) with the margin 1.5; the
pilot replaces it, and every row scales with it.

## Route (b)

Implemented in 23540b2 and described in `docs/DESIGN.md`, "Route (b)": `design.py freeze --numerics dd+mp256
--approved-numerics-change "<ref>" --cost-model <model measured under dd+mp256> --numerics-gate <gate record>` from the
EXACT pilot; `plan --design` of that bundle with `--numerics dd+mp256 --approved-numerics-change "<ref>"`, the profile
cost model and a gated build. Nothing ran on a cluster for this folder. The sweep under `dd+mp256` that route (b)
needs for its cost model (`tools/sweep.py --numerics dd+mp256`, J-SWEEP-2's shape; its exact-path run took 18.6
core-hours of one amdq node) has since run on symmetry: job 570240, 7.7 core-hours,
`cost_models/gmp_symmetry_amd_c8_dd+mp256.json` (`../../pre6/`). With it and the gate record above, route (b) needs
nothing more on symmetry. A build of another site or compiler (Expanse, GCC 13.3) needs its own sweep and gate before
a non-test plan accepts it. Since Stage 6 this holds for every non-test plan whose numerics are not exact, not only
route (b): a route-(a) bundle or an approved profile pilot is planned only with `--numerics-gate` naming a passed
full-scale gate record of the plan's own build, a non-test profile pilot also needs the user's go in
`production.APPROVED_PROFILE_PILOTS` (empty), and `design.py freeze --numerics` refuses a profile cost model measured
with a build that none of its gate records passed (here both are `d5df32ac…`).

## Files

`pre6_tables.py` (the script; its docstring lists the inputs), `pre6_tables.json` (every number above, the factors,
the design.py sha256 and the gate record's sha256), `pre6_tables.md` (the tables as printed).

```bash
python3 -B benchmarks/symmetry_2026-10-c8/stage5/pre6/pre6_tables.py --package . \
  --out benchmarks/symmetry_2026-10-c8/stage5/pre6/pre6_tables.json --markdown benchmarks/symmetry_2026-10-c8/stage5/pre6/pre6_tables.md
```
