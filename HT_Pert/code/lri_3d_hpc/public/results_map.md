# d = 3 perturbative HT: every quoted number -> record, command, tolerance

Package `HT_Pert/code/lri_3d_hpc` (git ref `7c8a67e`); records `R = HT_Pert/data/HT_3d/pert3d` (Expanse campaign
`pert3d`; sha256 in `HT_Pert/data/HT_3d/MANIFEST.sha256`; results, gates and crosscheck byte-identical, campaign.json
and the stage records scrubbed, `HT_Pert/data/HT_3d/SCRUBBED.txt`); table `HT_Pert/results/HT_3d/SUMMARY.md`.
Every row is a check of `make -f public.mk replay` (run from `code/lri_3d_hpc`; `public/replay_pert3d.py`), which
prints the table and exits 1 on any FAIL. Check ids match the note's reproduction table.

Status (2026-10-19, paper final at `a6772872`): the paper prints none of these numbers. Its d = 3 values (Table 2,
`tab:htpert`, Sec. 3.1) come from `code/lri_3d_c4_exact` (its own `public/results_map.md`). The ratios, the cutoffs
and the L = 14 gate below were printed in earlier drafts; their macros are still defined, unprinted, in the paper's
`numbers.tex`, and they are kept as checks of the records. The HT_Pert note (d = 3 section) quotes the cutoffs and
the L = 14 gate. C4-RATIO is still read by `HT/` (the finite-coupling note's 60 %).

Continuum values C_n(3) (the denominators of the ratios) are those of the paper's Table 1 (`tab:pt`) and `GFF/note/README.md`:
C2..C5 exact, C6..C8 the reported estimators (33.57542664131543, -220.35448047392794, 1602.6052229663408).

| Check | Quoted (macro) | Value | Records | Rule / tolerance |
|---|---|---|---|---|
| CUTOFFS | `\HTpThreeLmax` = 20; "L = 16, 18, 20" (HT_Pert note; not printed in the paper) | 16, 18, 20 | `R/results/L{16,18,20}/c{L}_{raw,consistent}.json` | the cutoffs of the shipped results |
| RATIO-2 | `\HTpRatioTwoThree` = 0.995 | 0.99495 | `R/results/L20/c20_consistent.json` (`result.C[2]`) | C2(20)/C2(3), consistent scheme, rounded to 3 decimals |
| RATIO-3 | `\HTpRatioThreeThree` = 0.933 | 0.93286 | same (`C[3]`) | same |
| RATIO-4 | `\HTpRatioFourThree` = 0.603 | 0.60258 | same (`C[4]`) | same |
| RATIO-5 | `\HTpRatioFiveThree` = 0.577 | 0.57711 | same (`C[5]`) | same |
| RATIO-6 | `\HTpRatioSixThree` = 0.507 | 0.50745 (allowance of C6(3): 0.5074-0.5075) | same (`C[6]`) | same, with the central C6(3) |
| RATIO-7 | `\HTpRatioSevenThree` = 0.414 | 0.41362 (0.4134-0.4139) | same (`C[7]`) | same, with the central C7(3) |
| RATIO-8 | `\HTpRatioEightThree` = 0.378 | 0.37804 (0.3771-0.3790) | same (`C[8]`) | same, with the central C8(3) |
| C4-RATIO | `\HTnpDthreeCfourRatio` = 60 % (HT folder; read from SUMMARY.md by `HT/code/lri_3d_window_hpc`) | 60.26 % | same (`C[4]` = 0.7400078407092003721) | C4(20)/C4(3) in percent to 2 decimals = 60.26 |
| GATE-L14 | `\HTpThreeGateL` = 14, `\HTpThreeGate` = about 1e-14 (HT_Pert note, d = 3 checks; not printed in the paper) | max 1.25e-14 (raw 2.3e-15) | `R/gates/L{16,18,20}/{raw,consistent}_c14.json`; reference `code/lri_3d_hpc/results/reference_coefficients_L14.json` | each production store solved at L = 14 against the original code's results: reference bound by sha256; scaled error over C, r, g, all seed energies and subcutoff vacua recomputed (equal to the stored value within 1e-17), <= 5e-13 (tolerance of the run); maximum rounds to 1e-14 |
| TABLE | `HT_Pert/results/HT_3d/SUMMARY.md` (C2..C8, L = 16, 18, 20, raw and consistent) | 6/6 rows | `R/results/L*/c*_*.json` | every row equals the stored strings of `result.C[2..8]` exactly |
| RESIDUAL | SUMMARY.md: recursion residuals <= 4e-19 | max 5.1e-19 | the 6 results | `execution.residual_gate.value` <= 1e-16 (the run's limit) |
| CROSSCHECK-L16 | (SUMMARY.md, campaign gate) recurrence vs stationary | 1.1e-17 raw, 4.1e-16 consistent | `R/crosscheck/L16/*` | comparison records passed, bound by sha256 to both results; recomputed scaled difference <= 1e-15 |
| CROSS-STORE | SUMMARY.md: reproducibility ~1e-14 | max 9.8e-15 | `R/results/L20/c{16,18}_*.json` vs `R/results/L{16,18}/` | the L20 store re-solved at L = 16, 18 against the L16, L18 stores: scaled difference <= 5e-13 |
| REC-MANIFEST | records as produced | 194 files | `HT_Pert/data/HT_3d/MANIFEST.sha256`, `SCRUBBED.txt` | every record's sha256, files listed in SCRUBBED.txt excepted (never a result, gate or crosscheck record); nothing missing or extra |
| REC-SRC | code at `7c8a67e` | 12 records | results and gates | `request.source_sha256` equals the sha256 of the 8 shipped `code/` files |
| REC-CHAIN | store -> gate -> solve -> result | 6/6 | `R/records/L*/{verify,gate,solve}`, `R/campaign.json` | store manifest sha256 equal across verify, gate, solve records and the result and gate requests; release fingerprint of the campaign; cutoff, order 8, scheme |

`make -f public.mk test` additionally rebuilds an L = 14 vertex store from scratch and solves cutoffs 0..14 (both
schemes, both strategies, 32 cases) against the same reference within 5e-13: the note's L = 14 check rerun on the
reader's machine (`public/REPRODUCE.md`).

Not quoted and not replayed: `\HTpThreeStates` (182,727,113 bath states at L = 20, marked "not used" in the paper's
numbers.tex; it is `execution.vertex_metadata.full_bath_states` of `R/results/L20/c20_consistent.json`).
