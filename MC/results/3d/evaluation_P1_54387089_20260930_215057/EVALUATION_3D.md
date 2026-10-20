# FIT_MODEL_3D evaluation — amendment P1 (--sigma-rule profiled)

| Δσ | s | decision | Δε | σ_stat | σ_sys | E (ref) | ω′ [Δχ²≤1] | cross-check | reblock 1000/4000 | largest pair U4(σ) / Y |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.725 | 1.55 | CROSS-CHECK FAILED [sigma_stat above target] | 1.48118 | 0.01632 | 0.02716 | U4,U6,U8,Y (U4) | 0.75 [0.44,1.11] | CROSS-CHECK FAILED (|difference| > 2 sigma_D) | 1.00/0.99 | 64->128: 1.4729(0.0030) / 1.4269 |
| 0.7 | 1.6 | ACCEPTED [sigma_stat above target] | 1.47314 | 0.00118 | 0.00230 | U4,U6,U8,Y,J (J) | 1.24 [1.23,1.25] | pass | 1.02/0.97 | 64->128: 1.4715(0.0031) / 1.4628 |
| 0.65 | 1.7 | CROSS-CHECK FAILED | 1.47375 | 0.00174 | 0.05237 | U4,U6,U8,Y (U4) | 0.66 [0.28,1.09] | CROSS-CHECK FAILED (|difference| > 2 sigma_D) | 1.02/1.00 | 64->128: 1.4650(0.0029) / 1.5263 |
| 0.625 | 1.75 | MODEL-LIMITED, EXTRAPOLATION UNAVAILABLE | — | — | — | — (—) | — | unavailable | 1.07/1.06 | 64->128: 1.4615(0.0027) / 1.5596 |
| 0.6 | 1.8 | MODEL-LIMITED, EXTRAPOLATION UNAVAILABLE | — | — | — | — (—) | — | unavailable | 0.93/1.00 | 64->128: 1.4515(0.0027) / 1.5818 |
| 0.575 | 1.85 | CROSS-CHECK FAILED | 1.45830 | 0.00103 | 0.09064 | U4,U6,U8,Y (U4) | 1.2 [0.71,1.85] | CROSS-CHECK FAILED (|difference| > 2 sigma_D) | 1.02/1.10 | 64->128: 1.4569(0.0027) / 1.6221 |
| 0.55 | 1.9 | CROSS-CHECK UNAVAILABLE | 1.45449 | 0.00720 | 0.00452 | U4,U6,U8 (U4) | 1.15 [0.63,1.87] | unavailable | 1.16/0.96 | 64->128: 1.4511(0.0026) / 1.6488 |
| 0.525 | 1.95 | MODEL-LIMITED, EXTRAPOLATION UNAVAILABLE | — | — | — | — (—) | — | unavailable | 0.93/0.97 | 64->128: 1.4493(0.0028) / 1.6790 |

## Deviations

- --index-remap /expanse/lustre/scratch/zzheng8/temp_project/lri3d/prod3d/=LRI_3d_MC/prod/: histogram indices read from restored copies (operational deviation; each must still hash to the index_sha256 of its record)

## Amendment P1: σ rule per point

Amendment sha256 2a18c0ae3ae7…; calibration `LRI_2d3d_reanalysis/calibration/run_20260930_213748/CALIBRATION.json` (sha256 897142c1685b…): binding VALID; A3 holds (pooled fixed-ω′ 1σ coverage 0.28704). labels of P1-CALIBRATED points are decided by the profiled quantities of amendment §3; every other point keeps the complete frozen fixed-rule evaluation and carries the note "P1 not applied: ..." (§3.6).


| s | rule applied | label | fixed-rule label | σ_stat fixed / profiled | σ_D fixed / profiled | reblock ratio fixed / profiled | strata / note |
|---|---|---|---|---|---|---|---|
| 1.55 | profiled (P1-CALIBRATED) | CROSS-CHECK FAILED [sigma_stat above target] | CROSS-CHECK FAILED [sigma_stat above target] | 0.00165 / 0.01632 | 0.00111 / 0.01310 | 1.06/1.00 ; 1.00/0.99 | A1 U4 PASS, A1 U6 PASS, A1 U8 PASS, A1 Y PASS, A2 cross-check PASS |
| 1.6 | profiled (P1-CALIBRATED) | ACCEPTED [sigma_stat above target] | CROSS-CHECK FAILED [sigma_stat above target] | 0.00112 / 0.00118 | 0.00086 / 0.00552 | 0.99/0.93 ; 1.02/0.97 | A1 U4 PASS, A1 U6 PASS, A1 U8 PASS, A1 Y PASS, A1 J PASS, A2 cross-check PASS |
| 1.7 | fixed | CROSS-CHECK FAILED | CROSS-CHECK FAILED | 0.00174 / 0.01680 | 0.00120 / 0.01380 | 1.02/1.00 ; 1.03/0.91 | A1 U4 PASS, A1 U6 PASS, A1 U8 PASS, A1 Y PASS, A2 cross-check UNCALIBRATED; P1 not applied: A2 cross-check: UNCALIBRATED |
| 1.75 | fixed | MODEL-LIMITED, EXTRAPOLATION UNAVAILABLE | MODEL-LIMITED, EXTRAPOLATION UNAVAILABLE | — / — | — / — | 1.07/1.06 ; 1.07/1.06 | P1 not applied: no eligible series (no calibrated quantity enters the label) |
| 1.8 | fixed | MODEL-LIMITED, EXTRAPOLATION UNAVAILABLE | MODEL-LIMITED, EXTRAPOLATION UNAVAILABLE | — / — | — / — | 0.93/1.00 ; 0.93/1.00 | P1 not applied: no eligible series (no calibrated quantity enters the label) |
| 1.85 | fixed | CROSS-CHECK FAILED | CROSS-CHECK FAILED | 0.00103 / 0.00750 | 0.00074 / 0.00614 | 1.02/1.10 ; 1.02/1.13 | A1 U4 PASS, A1 U6 PASS, A1 U8 PASS, A1 Y PASS, A2 cross-check UNCALIBRATED; P1 not applied: A2 cross-check: UNCALIBRATED |
| 1.9 | profiled (P1-CALIBRATED) | CROSS-CHECK UNAVAILABLE | CROSS-CHECK UNAVAILABLE | 0.00113 / 0.00720 | — / — | 1.00/0.95 ; 1.16/0.96 | A1 U4 PASS, A1 U6 PASS, A1 U8 PASS |
| 1.95 | fixed | MODEL-LIMITED, EXTRAPOLATION UNAVAILABLE | MODEL-LIMITED, EXTRAPOLATION UNAVAILABLE | — / — | — / — | 0.93/0.97 ; 0.93/0.97 | P1 not applied: no eligible series (no calibrated quantity enters the label) |

s = 1.6 (label changed by P1): drop-smallest check (§6 R4; information) at each series' own ω′*, pairs ['16->32', '32->64', '64->128']: U4 1.4724(0.0023) at ω′ 1.29, χ² 0.27/1; Y 1.4746(0.0026) at ω′ 1.21, χ² 1.47/1 (all four pairs: Δε 1.47314 from J)
