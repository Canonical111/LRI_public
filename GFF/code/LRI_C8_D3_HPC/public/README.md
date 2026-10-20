# C8(3): the eighth-order coefficient in three dimensions (code/LRI_C8_D3_HPC)

**C8(3) = 1602.6 ± 3.9** (ε = 2s − 3), from the estimator 1602.6052229663408 with sampling standard error
0.9516489064069612. The allowance is four sampling SEs rounded up to a multiple of 0.1; it was fixed after the result and
confirmed by the author. It is empirical, conditional on finite variance (note Sec 32.5 gives evidence, not a bound), and
does not cover errors shared by the graph and renormalization framework. Note: condensed note Section 32 (`app:C8d3`).
The paper rounds the same allowance (4 SE = 3.807) by the PDG rule and quotes **C8(3) = 1603 ± 4**; the condensed note
keeps one more digit. `replay` checks both (rows S1.1, S1.2 and S1.8).

## What is computed

Both sectors of the eight-loop calculation are integrated explicitly: 24,173 kernels in 24 groups (campaigns a and b ×
power-free and power-containing × loops 3–8), with randomized digital nets, importance rates ×0.8 and ×0.7, and the
precision policy of the seventh-order worker (long double, binary128 at 1e-9, 350-digit GMP at 1e-23). The renormalization
functions are assembled through eight loops by the shared order-8 assembly (`vendor/c8_assembly/`), with three hard gates.

| part | value | sampling SE |
|---|---|---|
| power-free C8^pf(3) | 1601.9999290 | 0.7279030 |
| power correction Δp C8(3) | 0.6052940 | 0.6129303 |
| C8(3) | 1602.6052230 | 0.9516489 |

Checks: lower orders C3–C7 within 0.74 SE of their references; campaigns a/b 1604.684 ± 1.239 and 1600.527 ± 1.445
(pull 2.18, spread over loops and graphs); bootstrap SE 0.940; tail monitor: 10,034 L8 graphs listed, none above 3% of its
group's variance; pilot 1619 ± 16. Cost: 15,102 core-hours on AMD EPYC 7543 (symmetry), 2026-10-09 to 10-12.

## Use

```sh
cd GFF/code/LRI_C8_D3_HPC
make -f public.mk replay        # recompute every quoted number from results/C8_3 (~20 s, no hosted data)
make -f public.mk test          # pure-Python regression tests (~7-20 min, 1 core)
make -f public.mk fetch-data TIER=rerun && make -f public.mk test-native   # native build and gates (toolchain, 8.8 GB)
```

REPRODUCE.md (C8(3) part) has the tiers, the production rerun and the regeneration of the inputs. The package's own
`README.md`, `Makefile` and `docs/` ship verbatim from the production commit.

## Layout

```
code/LRI_C8_D3_HPC/            the package at git commit 4fbd1bae (the production export), verbatim, pruned
  src/ tools/ tests/ slurm/    worker, campaign tools, tests, job scripts
  gen3/ inputs/ vendor/        d=3 payload pipeline, the inputs (L3-L6 packs in git; L7/L8 hosted), vendored assembly
  reference/                   the original C7(3) package (L7 member files and archived production hosted; its copy of
                               the d=2 method note, reference/C7_d2_complete.tex, not shipped: public/dropped_paths.txt,
                               condensed note Section 28) + baselines
  benchmarks/symmetry_2026-10-c8/
    production/prod1/          the production report, campaign split (ab_split/), tail N-trend (tail_ntrend/),
                               status/verify/budget outputs, job list, frozen design (production/design_prod/)  [6dd4a75a]
    production/margin_*/       the rate re-derivation probes (48 graphs)                                       [6dd4a75a]
    production/price/          the three priced designs
    pilot/                     pilot report, sigma table, campaign manifests and summaries
  public.mk, public/           public targets; replay_c8_3.py, fetch_data.py, SHA256SUMS.evidence_6dd4a75a, REVIEWS.md
results/C8_3/                  C8_result.json, manifest.json, cost model, CPU vendor, SHA256SUMS.symmetry,
                               groups/<group>/{merged.json, config.json}  (byte-identical production records)
data/C8_3/                     DATA.md, HOSTED.json; hosted in the Zenodo record: L7/L8 packs, C7(3) reference tars,
                               graph_replicates.csv and the L8 graph_tails.csv (two bundles)
```

## Limitations

- The ±3.9 is a heuristic allowance, not a confidence interval. The d=3 kernel's U^(3/2) blocks the exact tail bound used
  at d = 2; finite variance rests on empirical evidence (rate probes on 48 graphs; ξ̂ falling with N).
- The campaigns differ by 2.18 combined SEs; no concentrated cause was found, but a diffuse rate effect is not excluded.
- Production-support tools added after the second code inspection (budget line, conservative tail rule, margin probe)
  were not Codex-inspected (public/REVIEWS.md).
- Off the production CPU class, `tools/verify_result.py` can stop at a rounding-level gate diagnostic; the replay
  compares every other field and reports this row as KNOWN.
- Two printed numbers of the note edition fa71533 disagree with the records in the last digit (Sec 32.4 error table,
  power-free L = 4: 0.011 vs 0.010; Sec 32.5: 0.88 vs 0.87); the replay reports them as ERRATUM.
- The independent check (1600.98 ± 3.97) is a separate package (`C8_3_check`).
