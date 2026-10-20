# Amendment P1 calibration (synthetic data)

Amendment sha256 2a18c0ae3ae7…; calibration script d94b59f200b3…; evaluators 2D 3c3e35fca8f5…, 3D d635c917dd31…; 2026-09-30_21:37:48 on canonical (python 3.8.8, numpy 1.20.1); seed entropy 20260930; 2000 sets × 500 draws per ensemble; 695.6 s.

Adoption: A1 per stratum with ≥ 200 eligible fits: profiled 1σ coverage ≥ 0.6 and 2σ ≥ 0.9; A2 per point with ≥ 200 sets with U4 and Y eligible: profiled false-failure rate ≤ 0.1; A3 pooled fixed-ω′ 1σ coverage < 0.6.

**A3: holds** — pooled fixed-ω′ 1σ coverage 0.287 over 45440 eligible synthetic fits (profiled: 1σ 0.784, 2σ 0.955).

## A1 strata (coverage of the true Δ_ε by eligible synthetic fits)

| dim | s | stratum | eligible / sets | profiled 1σ / 2σ | fixed 1σ / 2σ | median σ_prof/σ_fixed | ineligible (reason: sets) | status |
|---|---|---|---|---|---|---|---|---|
| 2D | 1.05 | U4 | 0 / 2000 | — / — | — / — | — | chi2/dof: 465, omega interval at the grid boundary: 1535 | UNCALIBRATED |
| 2D | 1.05 | U6 | 0 / 2000 | — / — | — / — | — | chi2/dof: 476, omega interval at the grid boundary: 1524 | UNCALIBRATED |
| 2D | 1.05 | U8 | 19 / 2000 | 1.000 / 1.000 | 0.158 / 0.526 | 8.55 | chi2/dof: 422, omega interval at the grid boundary: 1559 | UNCALIBRATED |
| 2D | 1.05 | Y | 1493 / 2000 | 0.833 / 0.946 | 0.118 / 0.238 | 10.20 | chi2/dof: 363, omega interval at the grid boundary: 144 | PASS |
| 2D | 1.05 | J | 1812 / 2000 | 0.683 / 0.948 | 0.589 / 0.906 | 1.17 | chi2/dof: 188 | PASS |
| 2D | 1.1 | U4 | 0 / 2000 | — / — | — / — | — | chi2/dof: 505, omega interval at the grid boundary: 1495 | UNCALIBRATED |
| 2D | 1.1 | U6 | 1 / 2000 | 1.000 / 1.000 | 0.000 / 0.000 | 6.65 | chi2/dof: 469, omega interval at the grid boundary: 1530 | UNCALIBRATED |
| 2D | 1.1 | U8 | 8 / 2000 | 1.000 / 1.000 | 0.000 / 0.000 | 7.82 | chi2/dof: 431, omega interval at the grid boundary: 1561 | UNCALIBRATED |
| 2D | 1.1 | Y | 1672 / 2000 | 0.834 / 0.953 | 0.153 / 0.300 | 6.88 | chi2/dof: 312, omega interval at the grid boundary: 16 | PASS |
| 2D | 1.1 | J | 1799 / 2000 | 0.686 / 0.960 | 0.629 / 0.934 | 1.11 | chi2/dof: 201 | PASS |
| 2D | 1.2 | U4 | 0 / 2000 | — / — | — / — | — | chi2/dof: 656, omega interval at the grid boundary: 1344 | UNCALIBRATED |
| 2D | 1.2 | U6 | 0 / 2000 | — / — | — / — | — | chi2/dof: 631, omega interval at the grid boundary: 1369 | UNCALIBRATED |
| 2D | 1.2 | U8 | 0 / 2000 | — / — | — / — | — | chi2/dof: 566, omega interval at the grid boundary: 1434 | UNCALIBRATED |
| 2D | 1.2 | Y | 490 / 2000 | 0.335 / 0.818 | 0.000 / 0.000 | 11.02 | chi2/dof: 377, omega interval at the grid boundary: 1133 | FAIL |
| 2D | 1.2 | J | 1805 / 2000 | 0.667 / 0.950 | 0.617 / 0.920 | 1.11 | chi2/dof: 195 | PASS |
| 2D | 1.3 | U4 | 0 / 2000 | — / — | — / — | — | chi2/dof: 683, omega interval at the grid boundary: 1317 | UNCALIBRATED |
| 2D | 1.3 | U6 | 0 / 2000 | — / — | — / — | — | chi2/dof: 653, omega interval at the grid boundary: 1347 | UNCALIBRATED |
| 2D | 1.3 | U8 | 0 / 2000 | — / — | — / — | — | chi2/dof: 600, omega interval at the grid boundary: 1400 | UNCALIBRATED |
| 2D | 1.3 | Y | 196 / 2000 | 1.000 / 1.000 | 0.005 / 0.087 | 8.24 | chi2/dof: 541, omega interval at the grid boundary: 1263 | UNCALIBRATED |
| 2D | 1.3 | J | 194 / 2000 | 0.103 / 0.443 | 0.010 / 0.119 | 1.70 | chi2/dof: 265, omega interval at the grid boundary: 1541 | UNCALIBRATED |
| 2D | 1.4 | U4 | 0 / 2000 | — / — | — / — | — | chi2/dof: 628, omega interval at the grid boundary: 1372 | UNCALIBRATED |
| 2D | 1.4 | U6 | 0 / 2000 | — / — | — / — | — | chi2/dof: 608, omega interval at the grid boundary: 1392 | UNCALIBRATED |
| 2D | 1.4 | U8 | 0 / 2000 | — / — | — / — | — | chi2/dof: 566, omega interval at the grid boundary: 1434 | UNCALIBRATED |
| 2D | 1.4 | Y | 0 / 2000 | — / — | — / — | — | chi2/dof: 556, omega interval at the grid boundary: 1444 | UNCALIBRATED |
| 2D | 1.4 | J | 15 / 2000 | 0.867 / 1.000 | 0.867 / 1.000 | 1.02 | chi2/dof: 217, omega interval at the grid boundary: 1768 | UNCALIBRATED |
| 2D | 1.5 | U4 | 1 / 2000 | 0.000 / 1.000 | 0.000 / 0.000 | 6.84 | chi2/dof: 565, omega interval at the grid boundary: 1434 | UNCALIBRATED |
| 2D | 1.5 | U6 | 0 / 2000 | — / — | — / — | — | chi2/dof: 559, omega interval at the grid boundary: 1441 | UNCALIBRATED |
| 2D | 1.5 | U8 | 3 / 2000 | 0.000 / 1.000 | 0.000 / 0.000 | 7.87 | chi2/dof: 536, omega interval at the grid boundary: 1461 | UNCALIBRATED |
| 2D | 1.5 | Y | 234 / 2000 | 0.000 / 0.021 | 0.000 / 0.000 | 10.00 | chi2/dof: 533, omega interval at the grid boundary: 1233 | FAIL |
| 2D | 1.5 | J | 0 / 2000 | — / — | — / — | — | chi2/dof: 270, omega interval at the grid boundary: 1730 | UNCALIBRATED |
| 2D | 1.6 | U4 | 0 / 2000 | — / — | — / — | — | chi2/dof: 552, omega interval at the grid boundary: 1448 | UNCALIBRATED |
| 2D | 1.6 | U6 | 0 / 2000 | — / — | — / — | — | chi2/dof: 528, omega interval at the grid boundary: 1472 | UNCALIBRATED |
| 2D | 1.6 | U8 | 2 / 2000 | 1.000 / 1.000 | 0.000 / 0.000 | 7.21 | chi2/dof: 536, omega interval at the grid boundary: 1462 | UNCALIBRATED |
| 2D | 1.6 | Y | 222 / 2000 | 0.000 / 0.032 | 0.000 / 0.000 | 11.07 | chi2/dof: 552, omega interval at the grid boundary: 1226 | FAIL |
| 2D | 1.6 | J | 0 / 2000 | — / — | — / — | — | chi2/dof: 258, omega interval at the grid boundary: 1742 | UNCALIBRATED |
| 2D | 1.7 | U4 | 62 / 2000 | 0.000 / 0.129 | 0.000 / 0.000 | 8.59 | chi2/dof: 520, omega interval at the grid boundary: 1418 | UNCALIBRATED |
| 2D | 1.7 | U6 | 69 / 2000 | 0.000 / 0.101 | 0.000 / 0.000 | 8.59 | chi2/dof: 525, omega interval at the grid boundary: 1406 | UNCALIBRATED |
| 2D | 1.7 | U8 | 144 / 2000 | 0.403 / 1.000 | 0.000 / 0.000 | 8.58 | chi2/dof: 448, omega interval at the grid boundary: 1408 | UNCALIBRATED |
| 2D | 1.7 | Y | 214 / 2000 | 0.000 / 0.037 | 0.000 / 0.000 | 11.81 | chi2/dof: 526, omega interval at the grid boundary: 1260 | FAIL |
| 2D | 1.7 | J | 0 / 2000 | — / — | — / — | — | chi2/dof: 294, omega interval at the grid boundary: 1706 | UNCALIBRATED |
| 3D | 1.55 | U4 | 1225 / 2000 | 0.864 / 0.980 | 0.185 / 0.353 | 8.87 | chi2/dof: 358, omega interval at the grid boundary: 417 | PASS |
| 3D | 1.55 | U6 | 1396 / 2000 | 0.873 / 0.973 | 0.173 / 0.340 | 8.45 | chi2/dof: 320, omega interval at the grid boundary: 284 | PASS |
| 3D | 1.55 | U8 | 1666 / 2000 | 0.828 / 0.963 | 0.168 / 0.330 | 5.98 | chi2/dof: 317, omega interval at the grid boundary: 17 | PASS |
| 3D | 1.55 | Y | 1663 / 2000 | 0.690 / 0.946 | 0.195 / 0.362 | 4.21 | chi2/dof: 337 | PASS |
| 3D | 1.55 | J | 1771 / 2000 | 0.676 / 0.951 | 0.634 / 0.933 | 1.09 | chi2/dof: 229 | PASS |
| 3D | 1.6 | U4 | 1122 / 2000 | 0.992 / 1.000 | 0.311 / 0.521 | 5.80 | chi2/dof: 335, omega interval at the grid boundary: 543 | PASS |
| 3D | 1.6 | U6 | 1165 / 2000 | 0.983 / 1.000 | 0.310 / 0.551 | 4.69 | chi2/dof: 325, omega interval at the grid boundary: 510 | PASS |
| 3D | 1.6 | U8 | 1378 / 2000 | 0.877 / 1.000 | 0.290 / 0.550 | 3.74 | chi2/dof: 307, omega interval at the grid boundary: 315 | PASS |
| 3D | 1.6 | Y | 1668 / 2000 | 0.685 / 0.953 | 0.210 / 0.429 | 3.62 | chi2/dof: 332 | PASS |
| 3D | 1.6 | J | 1786 / 2000 | 0.702 / 0.947 | 0.672 / 0.933 | 1.06 | chi2/dof: 214 | PASS |
| 3D | 1.7 | U4 | 825 / 2000 | 0.916 / 1.000 | 0.200 / 0.359 | 9.40 | chi2/dof: 328, omega interval at the grid boundary: 847 | PASS |
| 3D | 1.7 | U6 | 1107 / 2000 | 0.903 / 0.996 | 0.191 / 0.380 | 9.32 | chi2/dof: 313, omega interval at the grid boundary: 580 | PASS |
| 3D | 1.7 | U8 | 1603 / 2000 | 0.886 / 0.971 | 0.159 / 0.321 | 7.30 | chi2/dof: 321, omega interval at the grid boundary: 76 | PASS |
| 3D | 1.7 | Y | 1671 / 2000 | 0.695 / 0.961 | 0.184 / 0.357 | 4.23 | chi2/dof: 329 | PASS |
| 3D | 1.7 | J | 218 / 2000 | 0.289 / 0.890 | 0.060 / 0.326 | 1.89 | chi2/dof: 283, omega interval at the grid boundary: 1499 | FAIL |
| 3D | 1.75 | U4 | 428 / 2000 | 0.998 / 1.000 | 0.014 / 0.124 | 8.10 | chi2/dof: 413, omega interval at the grid boundary: 1159 | PASS |
| 3D | 1.75 | U6 | 420 / 2000 | 0.983 / 1.000 | 0.021 / 0.148 | 6.74 | chi2/dof: 410, omega interval at the grid boundary: 1170 | PASS |
| 3D | 1.75 | U8 | 684 / 2000 | 0.813 / 1.000 | 0.155 / 0.364 | 3.99 | chi2/dof: 370, omega interval at the grid boundary: 946 | PASS |
| 3D | 1.75 | Y | 1710 / 2000 | 0.689 / 0.953 | 0.233 / 0.446 | 3.51 | chi2/dof: 290 | PASS |
| 3D | 1.75 | J | 47 / 2000 | 0.000 / 0.085 | 0.000 / 0.000 | 3.37 | chi2/dof: 241, omega interval at the grid boundary: 1712 | UNCALIBRATED |
| 3D | 1.8 | U4 | 228 / 2000 | 0.987 / 1.000 | 0.000 / 0.066 | 7.53 | chi2/dof: 542, omega interval at the grid boundary: 1230 | PASS |
| 3D | 1.8 | U6 | 246 / 2000 | 0.951 / 1.000 | 0.008 / 0.053 | 6.03 | chi2/dof: 526, omega interval at the grid boundary: 1228 | PASS |
| 3D | 1.8 | U8 | 229 / 2000 | 0.410 / 1.000 | 0.017 / 0.109 | 3.36 | chi2/dof: 520, omega interval at the grid boundary: 1251 | FAIL |
| 3D | 1.8 | Y | 1645 / 2000 | 0.699 / 0.960 | 0.258 / 0.497 | 3.09 | chi2/dof: 347, omega interval at the grid boundary: 8 | PASS |
| 3D | 1.8 | J | 1 / 2000 | 0.000 / 0.000 | 0.000 / 0.000 | 2.02 | chi2/dof: 255, omega interval at the grid boundary: 1744 | UNCALIBRATED |
| 3D | 1.85 | U4 | 717 / 2000 | 1.000 / 1.000 | 0.318 / 0.537 | 9.00 | chi2/dof: 367, omega interval at the grid boundary: 916 | PASS |
| 3D | 1.85 | U6 | 996 / 2000 | 1.000 / 1.000 | 0.265 / 0.516 | 8.14 | chi2/dof: 343, omega interval at the grid boundary: 661 | PASS |
| 3D | 1.85 | U8 | 1483 / 2000 | 0.927 / 1.000 | 0.226 / 0.446 | 4.89 | chi2/dof: 325, omega interval at the grid boundary: 192 | PASS |
| 3D | 1.85 | Y | 1695 / 2000 | 0.698 / 0.959 | 0.218 / 0.441 | 3.42 | chi2/dof: 305 | PASS |
| 3D | 1.85 | J | 0 / 2000 | — / — | — / — | — | chi2/dof: 273, omega interval at the grid boundary: 1727 | UNCALIBRATED |
| 3D | 1.9 | U4 | 531 / 2000 | 1.000 / 1.000 | 0.380 / 0.646 | 8.17 | chi2/dof: 352, omega interval at the grid boundary: 1117 | PASS |
| 3D | 1.9 | U6 | 764 / 2000 | 1.000 / 1.000 | 0.321 / 0.567 | 7.81 | chi2/dof: 355, omega interval at the grid boundary: 881 | PASS |
| 3D | 1.9 | U8 | 1289 / 2000 | 0.984 / 1.000 | 0.317 / 0.571 | 4.38 | chi2/dof: 319, omega interval at the grid boundary: 392 | PASS |
| 3D | 1.9 | Y | 1663 / 2000 | 0.711 / 0.974 | 0.291 / 0.546 | 2.87 | chi2/dof: 290, omega interval at the grid boundary: 47 | PASS |
| 3D | 1.9 | J | 0 / 2000 | — / — | — / — | — | chi2/dof: 267, omega interval at the grid boundary: 1733 | UNCALIBRATED |
| 3D | 1.95 | U4 | 216 / 2000 | 1.000 / 1.000 | 0.000 / 0.042 | 8.86 | chi2/dof: 522, omega interval at the grid boundary: 1262 | PASS |
| 3D | 1.95 | U6 | 237 / 2000 | 0.992 / 1.000 | 0.008 / 0.038 | 7.50 | chi2/dof: 517, omega interval at the grid boundary: 1246 | PASS |
| 3D | 1.95 | U8 | 254 / 2000 | 0.469 / 1.000 | 0.000 / 0.043 | 3.88 | chi2/dof: 529, omega interval at the grid boundary: 1217 | FAIL |
| 3D | 1.95 | Y | 182 / 2000 | 0.154 / 0.841 | 0.005 / 0.038 | 2.72 | chi2/dof: 529, omega interval at the grid boundary: 1289 | UNCALIBRATED |
| 3D | 1.95 | J | 0 / 2000 | — / — | — / — | — | chi2/dof: 305, omega interval at the grid boundary: 1695 | UNCALIBRATED |

## A2 cross-check (joint ensemble, common true Δ_ε)

| dim | s | sets with U4 and Y eligible | false failures profiled | fixed | status |
|---|---|---|---|---|---|
| 2D | 1.05 | 0 / 2000 | — | — | UNCALIBRATED |
| 2D | 1.1 | 0 / 2000 | — | — | UNCALIBRATED |
| 2D | 1.2 | 0 / 2000 | — | — | UNCALIBRATED |
| 2D | 1.3 | 0 / 2000 | — | — | UNCALIBRATED |
| 2D | 1.4 | 0 / 2000 | — | — | UNCALIBRATED |
| 2D | 1.5 | 0 / 2000 | — | — | UNCALIBRATED |
| 2D | 1.6 | 0 / 2000 | — | — | UNCALIBRATED |
| 2D | 1.7 | 0 / 2000 | — | — | UNCALIBRATED |
| 3D | 1.55 | 1062 / 2000 | 0.007 | 0.687 | PASS |
| 3D | 1.6 | 1076 / 2000 | 0.007 | 0.610 | PASS |
| 3D | 1.7 | 108 / 2000 | 0.000 | 0.426 | UNCALIBRATED |
| 3D | 1.75 | 108 / 2000 | 0.000 | 0.759 | UNCALIBRATED |
| 3D | 1.8 | 79 / 2000 | 0.000 | 0.873 | UNCALIBRATED |
| 3D | 1.85 | 93 / 2000 | 0.108 | 1.000 | UNCALIBRATED |
| 3D | 1.9 | 92 / 2000 | 0.326 | 1.000 | UNCALIBRATED |
| 3D | 1.95 | 39 / 2000 | 0.641 | 1.000 | UNCALIBRATED |

## Production points: strata they use (E from the baseline evaluation; the evaluator decides P1-CALIBRATED)

| dim | s | baseline decision | E | strata used → P1-CALIBRATED? |
|---|---|---|---|---|
| 2D | 1.05 | CONDITIONAL | Y | A1 Y PASS → yes |
| 2D | 1.1 | CONDITIONAL | Y | A1 Y PASS → yes |
| 2D | 1.2 | CONDITIONAL | J | A1 J PASS → yes |
| 2D | 1.3 | MODEL-LIMITED, EXTRAPOLATION UNAVAILABLE | — | — → no |
| 2D | 1.4 | MODEL-LIMITED, EXTRAPOLATION UNAVAILABLE | — | — → no |
| 2D | 1.5 | MODEL-LIMITED, EXTRAPOLATION UNAVAILABLE | — | — → no |
| 2D | 1.6 | MODEL-LIMITED, EXTRAPOLATION UNAVAILABLE | — | — → no |
| 2D | 1.7 | MODEL-LIMITED, EXTRAPOLATION UNAVAILABLE | — | — → no |
| 3D | 1.55 | CROSS-CHECK FAILED [sigma_stat above target] | U4,U6,U8,Y | A1 U4 PASS, A1 U6 PASS, A1 U8 PASS, A1 Y PASS, A2 PASS → yes |
| 3D | 1.6 | CROSS-CHECK FAILED [sigma_stat above target] | U4,U6,U8,Y,J | A1 U4 PASS, A1 U6 PASS, A1 U8 PASS, A1 Y PASS, A1 J PASS, A2 PASS → yes |
| 3D | 1.7 | CROSS-CHECK FAILED | U4,U6,U8,Y | A1 U4 PASS, A1 U6 PASS, A1 U8 PASS, A1 Y PASS, A2 UNCALIBRATED → no |
| 3D | 1.75 | MODEL-LIMITED, EXTRAPOLATION UNAVAILABLE | — | — → no |
| 3D | 1.8 | MODEL-LIMITED, EXTRAPOLATION UNAVAILABLE | — | — → no |
| 3D | 1.85 | CROSS-CHECK FAILED | U4,U6,U8,Y | A1 U4 PASS, A1 U6 PASS, A1 U8 PASS, A1 Y PASS, A2 UNCALIBRATED → no |
| 3D | 1.9 | CROSS-CHECK UNAVAILABLE | U4,U6,U8 | A1 U4 PASS, A1 U6 PASS, A1 U8 PASS → yes |
| 3D | 1.95 | MODEL-LIMITED, EXTRAPOLATION UNAVAILABLE | — | — → no |

## Misspecified family (reported, not an adoption rule): J truth + a·L^(−2ω′_J) in U4 (else Y), achieved U4 − Y within 2 % of the recorded one

| dim | s | series: a (achieved U4−Y / target) | U4 / Y / J ineligible | cross-check fails profiled / fixed | flagged (gates or cross-check) profiled / fixed | J bias, J profiled 1σ coverage |
|---|---|---|---|---|---|---|
| 2D | 1.05 | no amplitude in U4 or Y reproduces the recorded difference within 2% (target +0.0542; reachable U4 [-0.0082, +0.0024], Y [-0.0165, +0.0560]) | | | | |
| 2D | 1.1 | Y: -95.16 (+0.0390 / +0.0385) | 1.00 / 0.63 / 1.00 | 0.00 / 0.00 | 1.00 / 1.00 | —, — |
| 2D | 1.2 | Y: 1.924 (-0.0151 / -0.0151) | 1.00 / 0.98 / 0.21 | 0.00 / 0.00 | 1.00 / 1.00 | 0.0009, 0.70 |
| 2D | 1.3 | U4: 0.08839 (-0.0117 / -0.0119) | 1.00 / 1.00 / 0.12 | 0.00 / 0.00 | 1.00 / 1.00 | -0.0115, 0.00 |
| 2D | 1.4 | no amplitude in U4 or Y reproduces the recorded difference within 2% (target -0.0244; reachable U4 [-0.0065, +0.0002], Y [-0.0136, +0.0003]) | | | | |
| 2D | 1.5 | U4: 0.03902 (-0.0051 / -0.0051) | 1.00 / 0.88 / 1.00 | 0.00 / 0.00 | 1.00 / 1.00 | —, — |
| 2D | 1.6 | U4: -4 (-0.0120 / -0.0120) | 0.17 / 0.89 / 1.00 | 0.03 / 0.10 | 0.94 / 1.00 | —, — |
| 2D | 1.7 | Y: -0.25 (-0.0324 / -0.0327) | 0.89 / 0.98 / 1.00 | 0.00 / 0.00 | 1.00 / 1.00 | —, — |
| 3D | 1.55 | Y: 4.242 (+0.0326 / +0.0326) | 0.41 / 1.00 / 1.00 | 0.00 / 0.00 | 1.00 / 1.00 | —, — |
| 3D | 1.6 | U4: 4.784 (-0.0025 / -0.0025) | 1.00 / 0.15 / 0.54 | 0.00 / 0.00 | 1.00 / 1.00 | -0.0062, 0.00 |
| 3D | 1.7 | U4: 2514 (-0.0676 / -0.0676) | 1.00 / 0.89 / 1.00 | 0.00 / 0.00 | 1.00 / 1.00 | —, — |
| 3D | 1.75 | no amplitude in U4 or Y reproduces the recorded difference within 2% (target -0.1066; reachable U4 [-0.0968, +0.0024], Y [-0.0020, +0.0792]) | | | | |
| 3D | 1.8 | no amplitude in U4 or Y reproduces the recorded difference within 2% (target -0.1365; reachable U4 [-0.1142, +0.0029], Y [-0.0017, +0.0763]) | | | | |
| 3D | 1.85 | no amplitude in U4 or Y reproduces the recorded difference within 2% (target -0.1723; reachable U4 [-0.1053, +0.0041], Y [-0.0012, +0.0507]) | | | | |
| 3D | 1.9 | no amplitude in U4 or Y reproduces the recorded difference within 2% (target -0.2018; reachable U4 [-0.1148, +0.0029], Y [-0.0010, +0.0411]) | | | | |
| 3D | 1.95 | no amplitude in U4 or Y reproduces the recorded difference within 2% (target -0.2327; reachable U4 [-0.1131, +0.0029], Y [-0.0005, +0.0208]) | | | | |
