### Table 1. Independent per-spin code (perspin_topmode.py, Lmax = 200, dps 40)

| case | kernel | per-factor balance sigma+alpha_i+beta_i+g_i-d'/2 | max_l abs(d_l c_-top^(l)), abs(d_l c_+top^(l)) | spin-summed abs(c_-top), abs(c_+top) | ratio to max abs(c_k), abs(k)<top |
|---|---|---|---|---|---|
| R1 | R kernel d=1.7 tau=0.55+0.3j | 0, 0, 0 | 4.31, 1.54 | 7.164e-16, 3.032e-16 | 2.07e-17, 8.77e-18 |
| R2 | R kernel d=3.3 tau=1.6-0.4j | 0, 0, 0 | 3.22, 9.43 | 7.502e-17, 2.592e-16 | 6.12e-19, 2.12e-18 |
| R3 | R kernel d=0.5 tau=0.9+0.2j | 0, 0, 0 | 0.466, 0.417 | 2.453e-20, 3.99e-21 | 4.16e-20, 6.77e-21 |
| R4 | R kernel d=2.6 tau=2.0+0.5j | 0, 0, 0 | 7.59, 2.95 | 7.708e-19, 9.426e-20 | 9.42e-21, 1.15e-21 |
| R5 | R kernel d=1.25 tau=0.7 | 0, 0, 0 | 1.54, 1.54 | 2.404e-18, 2.404e-18 | 2.96e-19, 2.96e-19 |
| G1 | G1: random mixed balanced r=3, d=2.2 | 0, 0, 0 | 3.87, 1.74 | 3.647e-14, 1.895e-14 | 6.54e-16, 3.4e-16 |
| G2 | G2: random mixed balanced r=4, d=1.3 | 0, 0, 0, 0 | 0.607, 0.347 | 2.415e-18, 1.474e-18 | 2.37e-19, 1.45e-19 |
| C1 | control C1: right shifts (+0.15,-0.15,q-tau): total balance kept, per-factor balance broken | 0.15, -0.15, 0 | 4.1, 1.5 | 0.4233, 0.0899 | 0.0135, 0.00287 |
| C2 | control C2: R kernel at d=1.7 with multiplicities of d'=1.9 | -0.1, -0.1, (-0.1 + 0.0j) | 4.31, 1.54 | 2.087, 0.7113 | 0.0597, 0.0203 |
| C3 | control C3: third right shift q-tau+0.1 | 0, 0, (0.1 + 0.0j) | 4.53, 1.53 | 0.5316, 0.2868 | 0.0138, 0.00747 |

Fit spreads of the spin-summed top modes (six extrapolation variants): R1 2.93e-14/9.82e-15; R2 3.19e-15/1.43e-14; R3 7.49e-19/6.72e-19; R4 2.48e-17/1.44e-17; R5 1.68e-16/1.68e-16; G1 1.11e-12/5.12e-13; G2 1.29e-16/7.4e-17; C1 2.41e-14/7.87e-15; C2 1.93e-13/6.49e-14; C3 3.96e-14/1.42e-14.
Per-spin validation: tail consistency (recurrence vs reflected Gamma form) <= 1.18e-36; per-spin finite-mode reconstruction <= 4.48e-36.

### Table 2. Horn-block code (K_general/R_part/rblocks.py unchanged), five nodes t0 + j/5, dps 40

| d | tau | region | ratio abs(c_-2), abs(c_+2) to max abs(c_k) at (K,M)=(14,160) | same at (20,240) | change of c_0 between settings | 3-node vs 5-node rel. diff (20,240) |
|---|---|---|---|---|---|---|
| 0.3 | 1.0+0.1i | convergence region | 3.33e-25, 3.27e-25 | 2.55e-28, 2.02e-28 | 1.0e-24 | 2.83e-27 |
| 0.5 | 0.9+0.2i | convergence region | 1.27e-25, 1.15e-25 | 8.21e-31, 1.04e-30 | 3.5e-25 | 2.17e-30 |
| 1.25 | 0+0.08i | continued | 1.49e-23, 1.49e-23 | 5.91e-33, 5.9e-33 | 3.8e-23 | 3.43e-32 |
| 1.25 | 0.7 | convergence region | 3.8e-25, 3.8e-25 | 1.07e-30, 1.07e-30 | 0.0 | 6.98e-31 |
| 1.7 | 0.55+0.3i | convergence region, residue strip | 9.39e-24, 9.1e-24 | 1.23e-31, 1.22e-31 | 1.0e-23 | 2.56e-31 |
| 2.2 | -0.12+0.05i | continued | 1.26e-21, 1.21e-21 | 2.4e-30, 2.44e-30 | 1.5e-21 | 2.69e-29 |
| 2.6 | 2.0+0.5i | convergence region | 2.38e-22, 2.2e-22 | 7.98e-29, 7.98e-29 | 6.0e-22 | 1.06e-27 |
| 3.3 | 1.1-0.4i | convergence region, residue strip | 6.42e-21, 1.0e-20 | 2.69e-29, 1.2e-28 | 3.6e-20 | 3.82e-27 |
| 3.3 | 1.6-0.4i | convergence region | 3.24e-21, 4.28e-21 | 4.86e-29, 3.63e-28 | 1.9e-20 | 6.62e-27 |
| 3.7 | 0.95+0.15i | convergence region, residue strip | 6.0e-20, 5.27e-20 | 1.61e-27, 9.33e-28 | 1.7e-19 | 8.17e-24 |
| 3.9 | 1.2+0.3i | convergence region, residue strip | 1.46e-19, 1.07e-19 | 3.16e-27, 1.23e-27 | 2.7e-19 | 1.47e-21 |

### Table 3. Cross-check of the two codes: lower modes, per-spin extrapolation vs Horn blocks (20,240) / Gamma(2q)^2

| case | d | tau | rel. diff c_-1 | rel. diff c_0 | rel. diff c_1 |
|---|---|---|---|---|---|
| R1 | 1.7 | 0.55+0.3i | 1.9e-15 | 1.2e-15 | 6.5e-16 |
| R2 | 3.3 | 1.6-0.4i | 6.8e-16 | 3.7e-15 | 1.4e-16 |
| R3 | 0.5 | 0.9+0.2i | 1.1e-15 | 4.7e-16 | 2.2e-16 |
| R4 | 2.6 | 2.0+0.5i | 5.6e-16 | 4.7e-16 | 1.6e-15 |
| R5 | 1.25 | 0.7 | 2.3e-16 | 3.8e-16 | 2.3e-16 |

### Table 4. K_d from the three-node rule vs the 100-digit MB values and the five-node production run (same settings)

| d | settings (r, N, K, M, dps) | K_d, three nodes (first 40 digits) | rel. dev. from MB, 3 nodes | rel. dev. from MB, 5 nodes | rel. diff 3 vs 5 | [tau^0]F | [tau^1]F - (3/2)psi_2(q) |
|---|---|---|---|---|---|---|---|
| 0.8 | 0.04, 48, 30, 400, 72 | 92.37277023992277163264539189903637646055 | -8.1e-47 | -8.0e-47 | -3.0e-49 | -4.5506e-45 | -1.1614e-44 |
| 1.25 | 0.08, 48, 30, 400, 72 | 17.20334572992168832708572010654874727422 | -1.0e-41 | -1.0e-41 | -3.5e-47 | -2.613e-40 | -4.2668e-40 |
| 2.75 | 0.08, 48, 30, 400, 72 | 1.429249188660312000099175536883865557291 | -3.5e-44 | 6.0e-44 | -9.5e-44 | 5.6687e-45 | 1.3989e-43 |

