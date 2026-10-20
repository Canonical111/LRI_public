# FIT_MODEL_2D evaluation — amendment P1 (--sigma-rule profiled)

| Δσ | s | decision | Δε | σ_stat | σ_sys | E (ref) | ω′ [Δχ²≤1] | cross-check | reblock 1000/4000 | largest pair U4(σ) / Y |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.475 | 1.05 | CONDITIONAL | 0.92078 | 0.01773 | — | Y (Y) | 0.6 [0.43,0.76] | unavailable | 1.08/1.04 | 512->1024: 0.9702(0.0025) / 0.8964 |
| 0.45 | 1.1 | CONDITIONAL | 0.92846 | 0.01012 | — | Y (Y) | 0.8 [0.61,1.0] | unavailable | 0.90/1.09 | 512->1024: 0.9659(0.0023) / 0.9172 |
| 0.4 | 1.2 | CONDITIONAL | 0.96202 | 0.00182 | — | J (J) | 0.55 [0.53,0.57] | unavailable | 1.02/1.07 | 512->1024: 0.9631(0.0022) / 0.9478 |
| 0.35 | 1.3 | MODEL-LIMITED, EXTRAPOLATION UNAVAILABLE | — | — | — | — (—) | — | unavailable | 1.05/1.03 | 512->1024: 0.9584(0.0020) / 0.9698 |
| 0.3 | 1.4 | MODEL-LIMITED, EXTRAPOLATION UNAVAILABLE | — | — | — | — (—) | — | unavailable | 1.00/1.06 | 512->1024: 0.9627(0.0020) / 0.9977 |
| 0.25 | 1.5 | MODEL-LIMITED, EXTRAPOLATION UNAVAILABLE | — | — | — | — (—) | — | unavailable | 0.99/1.08 | 512->1024: 0.9661(0.0018) / 1.0245 |
| 0.2 | 1.6 | MODEL-LIMITED, EXTRAPOLATION UNAVAILABLE | — | — | — | — (—) | — | unavailable | 0.93/1.00 | 512->1024: 0.9698(0.0018) / 1.0620 |
| 0.15 | 1.7 | MODEL-LIMITED, EXTRAPOLATION UNAVAILABLE | — | — | — | — (—) | — | unavailable | 0.98/1.01 | 512->1024: 0.9773(0.0017) / 1.1088 |

## Deviations

- --index-remap /expanse/lustre/scratch/zzheng8/temp_project/lri2d/prod2d/=LRI_2d_MC/prod/: histogram indices read from restored copies (operational deviation; each must still hash to the index_sha256 of its record)

## Amendment P1: σ rule per point

Amendment sha256 2a18c0ae3ae7…; calibration `LRI_2d3d_reanalysis/calibration/run_20260930_213748/CALIBRATION.json` (sha256 897142c1685b…): binding VALID; A3 holds (pooled fixed-ω′ 1σ coverage 0.28704). labels of P1-CALIBRATED points are decided by the profiled quantities of amendment §3; every other point keeps the complete frozen fixed-rule evaluation and carries the note "P1 not applied: ..." (§3.6).


| s | rule applied | label | fixed-rule label | σ_stat fixed / profiled | σ_D fixed / profiled | reblock ratio fixed / profiled | strata / note |
|---|---|---|---|---|---|---|---|
| 1.05 | profiled (P1-CALIBRATED) | CONDITIONAL | CONDITIONAL | 0.00181 / 0.01773 | — / — | 1.05/1.05 ; 1.08/1.04 | A1 Y PASS |
| 1.1 | profiled (P1-CALIBRATED) | CONDITIONAL | CONDITIONAL | 0.00145 / 0.01012 | — / — | 0.98/0.99 ; 0.90/1.09 | A1 Y PASS |
| 1.2 | profiled (P1-CALIBRATED) | CONDITIONAL | CONDITIONAL | 0.00162 / 0.00182 | — / — | 1.07/1.06 ; 1.02/1.07 | A1 J PASS |
| 1.3 | fixed | MODEL-LIMITED, EXTRAPOLATION UNAVAILABLE | MODEL-LIMITED, EXTRAPOLATION UNAVAILABLE | — / — | — / — | 1.05/1.03 ; 1.05/1.03 | P1 not applied: no eligible series (no calibrated quantity enters the label) |
| 1.4 | fixed | MODEL-LIMITED, EXTRAPOLATION UNAVAILABLE | MODEL-LIMITED, EXTRAPOLATION UNAVAILABLE | — / — | — / — | 1.00/1.06 ; 1.00/1.06 | P1 not applied: no eligible series (no calibrated quantity enters the label) |
| 1.5 | fixed | MODEL-LIMITED, EXTRAPOLATION UNAVAILABLE | MODEL-LIMITED, EXTRAPOLATION UNAVAILABLE | — / — | — / — | 0.99/1.08 ; 0.99/1.08 | P1 not applied: no eligible series (no calibrated quantity enters the label) |
| 1.6 | fixed | MODEL-LIMITED, EXTRAPOLATION UNAVAILABLE | MODEL-LIMITED, EXTRAPOLATION UNAVAILABLE | — / — | — / — | 0.93/1.00 ; 0.93/1.00 | P1 not applied: no eligible series (no calibrated quantity enters the label) |
| 1.7 | fixed | MODEL-LIMITED, EXTRAPOLATION UNAVAILABLE | MODEL-LIMITED, EXTRAPOLATION UNAVAILABLE | — / — | — / — | 0.98/1.01 ; 0.98/1.01 | P1 not applied: no eligible series (no calibrated quantity enters the label) |
