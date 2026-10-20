# Specification (definitions only): independent re-derivation of the C6/C7 inputs (d=1 LRI, short-range end)

Generated 2026-10-02 by `scripts/make_spec_md.py` from `spec_definitions.json` (version 3). The compendium `/Users/zheng/Documents/Agent_LRI/LRI_SRI_research_compendium` was only read.

**This file contains no archive-derived number.** Every value below is a note statement, an exact derivation, a value implied by a note closed form, or a project-internal computation; each validation target carries a provenance tag. Archive numbers are sealed in `comparison/archive_comparison.json`, which production code never reads and which is consulted only in the final comparison step. `spec.json` is a deprecated copy in the old key layout.

## 0. Claims under test

* **C6** = 26 - 38 z2 + 104 z3 - 80 z4 - 272 z5 + 112 z2 z3 = -58.665697474225308949717146128630...
* **T3** = C6/4 = -14.666424368556327237429286532157...
* **D4** = 13 - 179/8 z2 + 47/2 z3 - 493/8 z4 + 289 z5 - 130 z2 z3 + 499/4 z6 - 76 z3^2 = -2.5346297995382501152606064124323...
* **C7** = 4 D4 - T3 - T2^2 + C3 C5/2 = 1798583/32768 - 90637/1024 z2 + 453/4 z3 - 16835/64 z4 + 1224 z5 - 540 z2 z3 + 4335/8 z6 - 320 z3^2 = 51.0689886129281088311839359798866...

Established lower orders (must be reproduced by the old inputs): D2 = 5/2 + 2 z2; T2 = 2 - 2 z2 - 4 z3; C3 = 39/16 + 2 z2; C4 = 4 - 4 z2 - 8 z3; D3 = 21/4 - 13 z2 + 11 z3 + 11 z4; C5 = 11249/1024 - 361/16 z2 + 24 z3 + 49/2 z4.

## 1. Conventions

* **thermal**: delta = 1-s, x = Delta_sigma = delta/2, t = sqrt(x), Delta_eps = 1 + sum_n C_n t^n
* **invariants**: T(delta) = delta/2 + T2 delta^2 + T3 delta^3 + ..., D(delta) = -2 delta + D2 delta^2 + D3 delta^3 + D4 delta^4 + ...; Delta_pm = 1 + T/2 pm sqrt(T^2/4 - D), Delta_eps = Delta_-
* **conversion**: {'C3': 'D2-1/16', 'C4': '2*T2', 'C5': '2*D3-T2/2+(D2-1/16)^2/4', 'C6': '4*T3', 'C7': '4*D4-T3-T2^2+C3*C5/2', 'checked_by_direct_eigenvalue_expansion': True}
* **cutoff**: eps = dimensionless hard core on CONSECUTIVE kink gaps only; l = log(eps); unit interval; kappa = 1
* **zeta_symbols**: z2..z6 = zeta(2)..zeta(6); L2 = log 2; L3 = log 3; Li2h = Li2(-1/2); Li4h = Li4(1/2)

## 2. Integrals (raw moments)

* **f_delta**: `f_delta(r) = (r^delta - 1)/delta  (kappa=1), f_0 = log r;  d^j f/d delta^j at 0 = log^(j+1)(r)/(j+1)`
* **charges**: `q_i = (-1)^(i+1), i = 1..n (alternating, first kink +1); q_i q_j = (-1)^(i+j)`
* **domain**: `Omega_n(eps) = {0 < X_1 < ... < X_n < 1 : X_{i+1} - X_i >= eps}; NO wall-endpoint core`
* **kernel**: `W_n(v,delta;X) = exp[ 2 v sum_{i<j} q_i q_j f_delta(X_j - X_i) ];  at (1,0): W_n = prod_{i<j} (X_j-X_i)^(2 q_i q_j)`
* **dipole**: `D_{2m} = sum_{j=1}^m (X_{2j} - X_{2j-1})`

* **A_{2m+1}**: int_{Omega_{2m+1}} W
* **Z_{2m}**: int_{Omega_{2m}} W
* **Q_{2m}**: int_{Omega_{2m}} D_{2m} W
* **A_1**: 1 (external normalization), its source derivative E A_1 = j_1 = int_0^1 [f(X)+f(1-X)] dX = -2/(1+delta) (v-independent)
* **E M_n**: first endpoint-source derivative at eta=0: integrand multiplied by e(delta) = sum_i q_i [f_delta(X_i) +/- f_delta(1-X_i)] (+ for odd n = U^odd, - for even n = U^even); after integration identical to the reflected form e(delta) = 2 sum_i q_i f_delta(X_i) (reflection X -> 1-X maps Omega_n to itself, preserves W_n and D_{2m}, and q_{n+1-i} = -q_i (n even) / +q_i (n odd)). Reflection is NOT valid for second source derivatives (note l.283); none are needed for C6/C7.
* **E derivative pieces (reflected)**: e0 = 2 sum q_i log X_i ; e1 = d_delta e = sum q_i log^2 X_i ; e2 = d_delta^2 e = (2/3) sum q_i log^3 X_i  (at delta=0). Unreflected: e0 = sum q_i[log X_i +/- log(1-X_i)], e1 = (1/2) sum q_i[log^2 X_i +/- log^2(1-X_i)], e2 = (1/3) sum q_i[log^3 X_i +/- log^3(1-X_i)]
* **S_j**: S_j = sum_{i<k} q_i q_k log^j(X_k - X_i)
* **derivative_naming**: atom M_<der>: der in base,v,vv,vvv,d,vd,vvd,dd,vdd = full partial derivative d_v^a d_delta^b (NOT Taylor coefficient) at (v,delta)=(1,0), taken on the integrand (also acting on the endpoint factor e(delta) for E moments) BEFORE the eps expansion
* **eps_expansion**: each raw atom is a finite-cutoff function M(eps) = sum_{p>=pmin} sum_{k>=0} c_{p,k} eps^p l^k; positive powers p>0 are genuine and must be kept
* **coordinate_reductions (optional, value-preserving)**: non-E moments: integrate the first position -> translation factor (1 - span), X_j = j*eps + T_j, 0<T_1<..<T_{n-1}<1-(n-1)eps; E moments keep all n absolute positions X_j = (j-1) eps + T_j

Derivative insertions (full derivatives, multiply W_n at (v,delta)=(1,0)):

| atom suffix | d_v^a d_delta^b | insertion |
|---|---|---|
| `base` | (0,0) | `1` |
| `v` | (1,0) | `2*S1` |
| `vv` | (2,0) | `4*S1^2` |
| `vvv` | (3,0) | `8*S1^3` |
| `d` | (0,1) | `S2` |
| `vd` | (1,1) | `S2 + 2*S1*S2` |
| `vvd` | (2,1) | `4*S1*S2 + 4*S1^2*S2` |
| `dd` | (0,2) | `S2^2 + (2/3)*S3` |
| `vdd` | (1,2) | `(2/3)*S3 + 2*S2^2 + (4/3)*S1*S3 + 2*S1*S2^2` |

For an endpoint-source atom `EM_<der>` with (a,b): integrand = sum_j binom(b,j) e_j * [insertion (a,b-j)] * W_n (times D_n for EQ). Example: `EQ2_dd` = int D_2 (e0 [S2^2+(2/3)S3] + 2 e1 S2 + e2) W_2. The two-kink insertions are re-derived from the exponent in `scripts/two_kink_exact.py` and agree with this table.

## 3. Normalized responses, coefficient extraction, recurrence

* `C3 = A3 - Z2`
* `C5 = A5 - A3 Z2 + Z2^2 - Z4`
* `C7 = A7 - A5 Z2 + A3 (Z2^2 - Z4) - Z2^3 + 2 Z2 Z4 - Z6`
* `K2 (=Q2) = Q2`
* `K4 = Q4 - Q2 Z2`
* `K6 = Q6 - Q4 Z2 + Q2 (Z2^2 - Z4)`
* `K8 = Q8 - Q6 Z2 + Q4 (Z2^2 - Z4) + Q2 (-Z2^3 + 2 Z2 Z4 - Z6)`
* `EC3 = EA3 - EA1 Z2 - EZ2`
* `EC5 = EA5 - EA3 Z2 - A3 EZ2 + EA1 (Z2^2 - Z4) + 2 Z2 EZ2 - EZ4`
* `EK2 (=EQ2) = EQ2`
* `EK4 = EQ4 - EQ2 Z2 - Q2 EZ2`
* `EK6 = EQ6 - EQ4 Z2 - Q4 EZ2 + EQ2 (Z2^2 - Z4) + Q2 (2 Z2 EZ2 - EZ4)`
* origin: coefficients of (A1 + A3 g^2 + ...)/(1 + Z2 g^2 + ...) and (Q2 g^2 + ...)/(1 + Z2 g^2 + ...); E differentiates EVERY factor incl. A1 (EA1 = -2/(1+delta)); checked symbolically in derive_requirements.py (note eq:normalization, eq:K8norm)

**Extraction.** I_m := [eps^0 l^m] I for m = 0,1; products in the normalized responses are formed with the FULL eps/log expansions of the factors BEFORE extraction (Z2 ~ 1/eps multiplies eps^1 terms).

**Derivatives.** d_v^a d_delta^b I_m := [eps^0 l^m] (d_v^a d_delta^b I)|_(1,0), with d_v^a d_delta^b acting on the normalized product by Leibniz and on each raw moment at integrand level (atom names C3_1[v1d0] etc.).

**Finite-response recurrence** (note eq:subtraction l.427-444 and l.1150-1151):

```
j1       = -2/(1+delta)
j3       = -2 d_v C3_0 + EC3_0
j5       = -2 d_v C5_0 + EC5_0
lambda2  = -2 Q2_0 - 4 v d_v Q2_0 + 2 v EQ2_0
lambda4  = -2 K4_0 - 4 v d_v K4_0 + 2 v EK4_0
lambda6  = -2 K6_0 - 4 v d_v K6_0 + 2 v EK6_0   [EXTRAPOLATION: not defined in the note; see EXTRAPOLATIONS]
b3       = C3_1 + 2 v j1
h4       = K4_1 - 2 Q2_0 b3 + lambda2
b5       = C5_1 - 3 C3_0 b3 - 2 v j1 h4 + 2 v j3
h6       = K6_1 - 2 Q2_0 b5 - 4 K4_0 b3 - lambda2 h4 + lambda4
b7       = C7_1 - 3 C3_0 b5 - 5 C5_0 b3 - 2 v j1 h6 - 2 v j3 h4 + 2 v j5
h8       = K8_1 - 2 Q2_0 b7 - 4 K4_0 b5 - 6 K6_0 b3 - lambda2 h6 - lambda4 h4 + lambda6
```
note eq:subtraction (l.427-444) for j1..lambda4 and b3..b7; h8 from note l.1150-1151; lambda6 extrapolated. all quantities are functions of (v,delta); v = b0^2 (explicit factors come from d_h = sqrt2 b0 (-2 d_v + E) and b_dim = b0 - sqrt2 h); derivatives act on the FULL recurrence (explicit v, j1(delta), lambda_n) before setting (v,delta)=(1,0). Derived from the response-Jacobian equation J beta = R1 (note l.448-464), checked by review/recurrence_from_jacobian.py. h4,h6 are called eta4,eta6 in some archived notes.

**Beta jets.** F = `u**3*(J + Omega*z) + u**2*(G*z + Phi*z**2 + Psi*delta*z + R*delta + b) + u*(A*z**2 + E*delta*z + V*delta**2 + a*z + alpha*z**3 + beta*delta*z**2 + delta**2*gamma*z + delta*p + 1) + z`

H = `K*u**4 - delta + u**3*(N*z + P*delta + k) + u**2*(L*z**2 + M*delta*z + Q*delta**2 + c + delta*q + f*z) + 4*u`

beta_u = 2 u F, beta_z = (1+z) H, u = g^2, z = v - 1; F = z + sum_k b_{2k+1}(v,delta) u^k, H = -delta - 4 sum_k h_{2k}(v,delta) u^k with h2 = -1; Taylor-expand b, h around (v,delta) = (1,0).

## 4. Extrapolations beyond the note

* **lambda6**: `lambda6 := -2 K6_0 - 4 v d_v K6_0 + 2 v EK6_0  (K6_0 = [eps^0 l^0] of the normalized K6, EK6 its first source derivative).`  
  *Status:* EXTRAPOLATION, not written in the note. The note writes h8 with +lambda6 (l.1150-1151) but defines only lambda2 and lambda4 (l.430-431). lambda6 is the pattern extension lambda_n = -2 K_n,0 - 4 v d_v K_n,0 + 2 v E K_n,0.
  *Jacobian extension:* Equivalently the note's finite-response Jacobian (l.448-462) is extended by one order: J21 += sqrt2 b0 * 6 K6_0 g^5, J22 += lambda6 g^6, R1_2 += sqrt2 b0 K8_1 g^8. Solving J beta = R1 with this extension gives exactly the h8 line of the note (review/recurrence_from_jacobian.py).
  *Affects:* only h8, hence only the input K = -4 h8 (enters D4 with coefficient -3/128, C7 with -3/32). It requires the raw atoms EQ6_base, EQ4_*, EZ4_*, Q6_v and lower, through EK6_0 and d_v K6_0. C6 and every other input are unaffected.
  *How to test:* derive the h8 line (and lambda6) from first principles, e.g. by the framework team's independent RG map; an archive cross-check exists only in the sealed comparison file.
* **h8-is-in-the-note**: `h8 = K8_1 - 2 Q2_0 b7 - 4 K4_0 b5 - 6 K6_0 b3 - lambda2 h6 - lambda4 h4 + lambda6`  
  *Status:* written in the note (l.1150-1151, Sec. sec:C8setup); only lambda6 inside it is undefined there.

## 5. The 25 inputs (definition chains)

Atom notation: `C3_1[v1d0]` = [eps^0 l^1] d_v C3 at (1,0); `K2` = Q2, `EK2` = EQ2. The full expansions (up to 101 terms, Omega) and each normalized atom's Leibniz expansion and windows are in `spec_definitions.json` (`DEFINITIONS.inputs`, `DEFINITIONS.normalized_atoms`).

| input | group | definition | #terms | max kinks | expansion (if short) |
|---|---|---|---|---|---|
| a | old | d_v b3 | 2 | 3 | `C3_1[v1d0] - 4` |
| p | old | d_delta b3 | 2 | 3 | `C3_1[v0d1] + 4` |
| A | old | d_v^2 b3 / 2 | 1 | 3 | `C3_1[v2d0]/2` |
| E | old | d_v d_delta b3 | 2 | 3 | `C3_1[v1d1] + 4` |
| c | old | -4 h4 | 5 | 4 | `8*C3_1[v0d0]*K2_0[v0d0] - 8*EK2_0[v0d0] - 24*K2_0[v0d0] + 16*K2_0[v1d0] - 4*K4_1[v0d0]` |
| f | old | -4 d_v h4 | 8 | 4 | `8*C3_1[v0d0]*K2_0[v1d0] + 8*C3_1[v1d0]*K2_0[v0d0] - 8*EK2_0[v0d0] - 8*EK2_0[v1d0] - 32*K2_0[v0d0] - 8*K2_0[v1d0] + 16*K2_0[v2d0] - 4*K4_1[v1d0]` |
| b | old | b5 | 10 | 5 | (see spec_definitions.json) |
| G | C5/D3 | d_v b5 | 18 | 5 | (see spec_definitions.json) |
| q | C5/D3 | -4 d_delta h4 | 7 | 4 | `8*C3_1[v0d0]*K2_0[v0d1] + 8*C3_1[v0d1]*K2_0[v0d0] - 8*EK2_0[v0d1] + 32*K2_0[v0d0] - 24*K2_0[v0d1] + 16*K2_0[v1d1] - 4*K4_1[v0d1]` |
| k | C5/D3 | -4 h6 | 22 | 6 | (see spec_definitions.json) |
| V | C6 | d_delta^2 b3 / 2 | 2 | 3 | `C3_1[v0d2]/2 - 4` |
| R | C6 | d_delta b5 | 18 | 5 | (see spec_definitions.json) |
| J | C6 | b7 | 43 | 7 | (see spec_definitions.json) |
| L | C6 | -2 d_v^2 h4 | 9 | 4 | (see spec_definitions.json) |
| M | C6 | -4 d_v d_delta h4 | 12 | 4 | (see spec_definitions.json) |
| N | C6 | -4 d_v h6 | 51 | 6 | (see spec_definitions.json) |
| alpha | C7 | d_v^3 b3 / 6 | 1 | 3 | `C3_1[v3d0]/6` |
| beta | C7 | d_v^2 d_delta b3 / 2 | 1 | 3 | `C3_1[v2d1]/2` |
| gamma | C7 | d_v d_delta^2 b3 / 2 | 2 | 3 | `C3_1[v1d2]/2 - 4` |
| Phi | C7 | d_v^2 b5 / 2 | 23 | 5 | (see spec_definitions.json) |
| Psi | C7 | d_v d_delta b5 | 35 | 5 | (see spec_definitions.json) |
| Omega | C7 | d_v b7 | 101 | 7 | (see spec_definitions.json) |
| Q | C7 | -2 d_delta^2 h4 | 9 | 4 | (see spec_definitions.json) |
| P | C7 | -4 d_delta h6 | 47 | 6 | (see spec_definitions.json) |
| K | C7 | -4 h8 (uses lambda6) | 82 | 8 | (see spec_definitions.json) |

**Matching and canonical terms.**

* **B**: B = (b0 - sqrt2 h) eps^(delta/2) -> v = B^2 = b0^2 e^(delta l): produces the tree term -delta in H (beta_v = -delta v); no extra single-log contribution.
* **Y**: Y = g_aux exp[l + b0^2 (1 - e^(delta l))/delta] = g_aux [1 - delta l^2/2 + delta^2 (l^4/8 - l^3/6) + ...] at b0=1; at delta=0, Y = g_aux e^{-(b0^2-1) l}: produces the tree term z in F; modifies only higher logarithms (appendix: aux -1/3 l^4 + 5/3 l^3 + 2 z2 l^2 - p l  ->  physical -4/3 l^4 + 13/6 l^3 + 2 z2 l^2 - p l : the single log is unchanged).
* **in_the_inputs**: Every input is computed from eq:subtraction (+h8) alone; finite-delta and charge dependence enter ONLY through (i) the moments, (ii) j1 = -2/(1+delta) [constants: a:-4, p:+4, E:+4, V:-4, gamma:-4 and products], (iii) j3, j5, lambda2,4,6 built from E and d_v of finite parts, (iv) explicit v factors. No additional fugmatch term is added to any input. Confirmed for the three-kink sector against the note closed forms (AMBIGUITIES: matching-wording).
* **in_validation_targets**: Higher-log predictions use the nonautonomous auxiliary flow with v_a = v0 e^(delta l), u_a = g^2 (1 - delta l^2 + delta^2 (l^4/2 - l^3/3)), eta = sqrt2 b0 h - 2 h^2, A1(eta) = B(1+eta,1+eta).

**Assemblies** (independently derived in `scripts/derive_invariants.py`; equal to the note's printed formulas):

```
D2 = -a/2 - c/8 + 1/2
T2 = -a/8 + b/4 - c/32 + f/16 + p/2
D3 = A/4 - E/2 - G/8 + b/8 + c**2/64 + f/16 - k/16 + p/2 - q/8
T3 = A/32 - E/8 - G/16 + 3*J/32 - L/32 + M/16 + N/64 + R/4 + V/2 + a**2/32 - a*b/32 + a*c/64 - a*p/8 - b*c/32 + c**2/256 - c*f/128 - c*p/32 - f/128 - k/128 - q/32
D4 = -A*a/16 + A*b/16 - A*c/64 + A*p/4 - A/32 + G*c/128 + J/32 - 3*K/128 - 3*L/128 + M/16 + 3*N/128 - Omega/32 - P/16 + Phi/16 - Psi/8 - Q/8 + R/8 + V/2 + a*c**2/512 - a*f/64 - a*k/128 - 3*alpha/32 - b*c/128 + 3*b*f/128 + beta/4 - 5*c**3/2048 - c**2/512 - c*f/64 + c*k/64 + c*q/32 + f*p/16 - f/128 - gamma/2 + k/128
C6 = 4 T3 = A/8 - E/2 - G/4 + 3*J/8 - L/8 + M/4 + N/16 + R + 2*V + a**2/8 - a*b/8 + a*c/16 - a*p/2 - b*c/8 + c**2/64 - c*f/32 - c*p/8 - f/32 - k/32 - q/8
B_old (C6) = A/8 - E/2 - G/4 + a**2/8 - a*b/8 + a*c/16 - a*p/2 - b*c/8 + c**2/64 - c*f/32 - c*p/8 - f/32 - k/32 - q/8
C6 new part = 2V + R + 3J/8 - L/8 + M/4 + N/16
B_old^{D4} = -A*a/16 + A*b/16 - A*c/64 + A*p/4 - A/32 + G*c/128 + J/32 - 3*L/128 + M/16 + 3*N/128 + R/8 + V/2 + a*c**2/512 - a*f/64 - a*k/128 - b*c/128 + 3*b*f/128 - 5*c**3/2048 - c**2/512 - c*f/64 + c*k/64 + c*q/32 + f*p/16 - f/128 + k/128
D4 new part = -3 alpha/32 + beta/4 - gamma/2 + Phi/16 - Psi/8 - Omega/32 - Q/8 - P/16 - 3K/128
C7 = 4 D4 - T3 - T2^2 + C3 C5/2 ; C7 - 4 D4 = -20*z2*z3 + 1011*z2/1024 - 16*z3**2 + 77*z3/4 - 1059*z4/64 + 68*z5 + 343*z6/8 + 94647/32768
conversion: C3 = D2-1/16, C4 = 2*T2, C5 = 2*D3-T2/2+(D2-1/16)^2/4, C6 = 4*T3, C7 = 4*D4-T3-T2^2+C3*C5/2
fixed point: u1=1/4, u2=-c/64, u3=c**2/512 + f/256 - k/256 - q/64, u4=-K/1024 - L/1024 + M/256 + N/1024 - P/256 - Q/64 - a*f/1024 + b*f/1024 - 5*c**3/16384 - 5*c*f/4096 + 5*c*k/4096 + c*q/256 + f*p/256, z1=-1/4, z2=a/16 - b/16 + c/64 - p/4, z3=-A/64 + E/16 + G/64 - J/64 - R/16 - V/4 - a**2/64 + a*b/64 - a*c/128 + a*p/16 + b*c/128 - c**2/512 + c*p/64 - f/256 + k/256 + q/64
```

## 6. Raw-moment requirements (tight and safe windows)

Tight (minimal) set: 75 raw atoms (2..8 kinks), 195 scalars [eps^p l^k] with p in {-2..2}, k in {0,1}. Safe set: 204 scalars (+9: 6 below the tight bound, which must vanish, and 3 genuine positive-power coefficients that multiply them). Only l^0 and l^1 of a raw coefficient can reach [eps^0 l^0], [eps^0 l^1] of a product; a raw moment entering linearly needs only l^m. 56 of the tight scalars belong to Z2_*/Q2_* and are known exactly (out/two_kink_exact.json). For the higher-log validation targets the same eps windows are needed with the full log polynomial.

* **tight bounds:** pmin: A_{2m+1},Z_{2m},EA_{2m+1}: -m; Q_{2m},EZ_{2m}: -(m-1); EQ2: 0, EQ_{2m>=4}: -(m-1); same Z2/Q2 supports
* **argument:** Power counting of the hard-core collapse (eps -> 0). The leading eps^-j comes from j pairs collapsed to gaps O(eps), each pair contributing O(1/eps) through its r^-2 kernel. A_{2m+1}, Z_{2m}: all m pairs collapse -> eps^-m (the lone charge of A, the endpoint factor of EA are O(1)). Q_{2m}: the dipole D_{2m} is O(eps) when all pairs collapse, O(1) when one pair is open -> eps^-(m-1). EZ_{2m}: the reflected endpoint factor 2 sum q_i log X_i is O(eps/X) per collapsed pair -> eps^-(m-1). EQ_{2m}: dipole and endpoint factors each cost one power when all pairs collapse, both are O(1) with one pair open -> eps^-(m-1) for m >= 2 and eps^0 for EQ2. The safe bound -floor(n/2) (Q2: 0) does not use this; the assembler checks the difference.
* **safe bounds:** pmin=-floor(n/2) for every raw moment except Q2 (0); Z2 support {-1,0}, Q2 support {0,1}
* **safe extras that must vanish:** EQ2_base [eps^-1 l^0], EZ2_base [eps^-1 l^0], EZ2_d [eps^-1 l^0], EZ2_v [eps^-1 l^0], Q4_base [eps^-2 l^0], Q4_base [eps^-2 l^1]
* **genuine positive-power safe extras:** EZ2_base [eps^2 l^0], Z4_base [eps^2 l^0], Z4_base [eps^2 l^1]
* **policy:** Integration teams supply every TIGHT scalar plus the below-bound scalars (they must come out zero within precision). scripts/assemble_from_raw.py --windows both (the default) refuses missing scalars, asserts the below-bound ones vanish (--zero-tol) and requires the tight and safe assemblies to agree (--agree-tol). The genuine positive-power extras are looked up only if their partner is non-zero (a convention error), in which case a missing one is an error.

Each entry `p:[k..]` means the coefficient [eps^p l^k] is needed. dim = integration dimension after the translation reduction. `exact` = known exactly in `out/two_kink_exact.json`.

| raw atom | kinks | E? | dim | tight pmin | needed (tight) [eps^p : l^k] | safe additions | used by |
|---|---|---|---|---|---|---|---|
| `EQ2_base` | 2 | E | 2 | 0 | 0:0; 1:0; 2:0 | -1:0 | c,f,b,G,k,R,J,N,Phi,Psi,Omega,P,K |
| `EQ2_d` | 2 | E | 2 | 0 | 0:0; 1:0 |  | q,R,M,Psi,P |
| `EQ2_dd` | 2 | E | 2 | 0 | 0:0 |  | Q |
| `EQ2_v` | 2 | E | 2 | 0 | 0:0; 1:0 |  | f,G,L,N,Phi,Psi,Omega |
| `EQ2_vd` | 2 | E | 2 | 0 | 0:0 |  | M,Psi |
| `EQ2_vv` | 2 | E | 2 | 0 | 0:0 |  | L,Phi |
| `EZ2_base` | 2 | E | 2 | 0 | 0:0; 1:0 | -1:0; 2:0 | b,G,k,J,N,Omega,P,K |
| `EZ2_d` | 2 | E | 2 | 0 | 0:0 | -1:0 | R,Psi,P |
| `EZ2_v` | 2 | E | 2 | 0 | 0:0; 1:0 | -1:0 | G,N,Phi,Omega |
| `EZ2_vd` | 2 | E | 2 | 0 | 0:0 |  | Psi |
| `EZ2_vv` | 2 | E | 2 | 0 | 0:0 |  | Phi |
| `Q2_base` | 2 |  | 1 | 0 | 0:0,1; 1:0,1 |  | c,f,b,G,q,k,R,J,L,M,N,Phi,Psi,Omega,Q,P,K (exact) |
| `Q2_d` | 2 |  | 1 | 0 | 0:0,1; 1:0,1 |  | q,R,M,Psi,Q,P (exact) |
| `Q2_dd` | 2 |  | 1 | 0 | 0:0,1; 1:0,1 |  | Q (exact) |
| `Q2_v` | 2 |  | 1 | 0 | 0:0,1; 1:0,1 |  | c,f,b,G,k,R,J,L,M,N,Phi,Psi,Omega,P,K (exact) |
| `Q2_vd` | 2 |  | 1 | 0 | 0:0,1; 1:0,1 |  | q,R,M,Psi,P (exact) |
| `Q2_vdd` | 2 |  | 1 | 0 | 0:0 |  | Q (exact) |
| `Q2_vv` | 2 |  | 1 | 0 | 0:0,1; 1:0,1 |  | f,G,L,N,Phi,Psi,Omega (exact) |
| `Q2_vvd` | 2 |  | 1 | 0 | 0:0 |  | M,Psi (exact) |
| `Q2_vvv` | 2 |  | 1 | 0 | 0:0 |  | L,Phi (exact) |
| `Z2_base` | 2 |  | 1 | -1 | -1:0,1; 0:0,1 |  | c,f,b,G,q,k,R,J,L,M,N,Phi,Psi,Omega,Q,P,K (exact) |
| `Z2_d` | 2 |  | 1 | -1 | -1:0,1; 0:0,1 |  | p,q,R,M,Psi,Q,P (exact) |
| `Z2_dd` | 2 |  | 1 | -1 | -1:0,1; 0:0,1 |  | V,Q (exact) |
| `Z2_v` | 2 |  | 1 | -1 | -1:0,1; 0:0,1 |  | a,f,b,G,k,J,L,M,N,Phi,Psi,Omega,P,K (exact) |
| `Z2_vd` | 2 |  | 1 | -1 | -1:0,1; 0:0,1 |  | E,R,M,Psi,P (exact) |
| `Z2_vdd` | 2 |  | 1 | -1 | 0:1 |  | gamma (exact) |
| `Z2_vv` | 2 |  | 1 | -1 | -1:0,1; 0:0,1 |  | A,G,L,N,Phi,Omega (exact) |
| `Z2_vvd` | 2 |  | 1 | -1 | 0:0,1 |  | beta,Psi (exact) |
| `Z2_vvv` | 2 |  | 1 | -1 | 0:0,1 |  | alpha,Phi (exact) |
| `A3_base` | 3 |  | 2 | -1 | -1:0,1; 0:0,1; 1:0,1; 2:0,1 |  | c,f,b,G,q,k,R,J,L,M,N,Phi,Psi,Omega,Q,P,K |
| `A3_d` | 3 |  | 2 | -1 | 0:0,1; 1:0,1 |  | p,q,R,M,Psi,Q,P |
| `A3_dd` | 3 |  | 2 | -1 | 0:1 |  | V,Q |
| `A3_v` | 3 |  | 2 | -1 | -1:0,1; 0:0,1; 1:0,1; 2:0,1 |  | a,f,b,G,k,J,L,M,N,Phi,Psi,Omega,P,K |
| `A3_vd` | 3 |  | 2 | -1 | 0:0,1; 1:0,1 |  | E,R,M,Psi,P |
| `A3_vdd` | 3 |  | 2 | -1 | 0:1 |  | gamma |
| `A3_vv` | 3 |  | 2 | -1 | 0:0,1; 1:0,1 |  | A,G,L,N,Phi,Omega |
| `A3_vvd` | 3 |  | 2 | -1 | 0:0,1 |  | beta,Psi |
| `A3_vvv` | 3 |  | 2 | -1 | 0:0,1 |  | alpha,Phi |
| `EA3_base` | 3 | E | 3 | -1 | 0:0; 1:0 |  | b,G,k,J,N,Omega,P,K |
| `EA3_d` | 3 | E | 3 | -1 | 0:0 |  | R,Psi,P |
| `EA3_v` | 3 | E | 3 | -1 | 0:0; 1:0 |  | G,N,Phi,Omega |
| `EA3_vd` | 3 | E | 3 | -1 | 0:0 |  | Psi |
| `EA3_vv` | 3 | E | 3 | -1 | 0:0 |  | Phi |
| `EQ4_base` | 4 | E | 4 | -1 | 0:0; 1:0 |  | k,J,N,Omega,K |
| `EQ4_d` | 4 | E | 4 | -1 | 0:0 |  | P |
| `EQ4_v` | 4 | E | 4 | -1 | 0:0 |  | N,Omega |
| `EZ4_base` | 4 | E | 4 | -1 | -1:0; 0:0 |  | J,Omega,K |
| `EZ4_v` | 4 | E | 4 | -1 | 0:0 |  | Omega |
| `Q4_base` | 4 |  | 3 | -1 | -1:0,1; 0:0,1; 1:0,1; 2:0,1 | -2:0,1 | c,b,G,k,R,J,N,Psi,Omega,P,K |
| `Q4_d` | 4 |  | 3 | -1 | 0:0,1; 1:0,1 |  | q,R,Psi,P |
| `Q4_dd` | 4 |  | 3 | -1 | 0:1 |  | Q |
| `Q4_v` | 4 |  | 3 | -1 | 0:0,1; 1:0,1 |  | f,G,k,J,N,Phi,Psi,Omega,K |
| `Q4_vd` | 4 |  | 3 | -1 | 0:0,1 |  | M,Psi,P |
| `Q4_vv` | 4 |  | 3 | -1 | 0:0,1 |  | L,N,Phi,Omega |
| `Z4_base` | 4 |  | 3 | -2 | -2:0,1; -1:0,1; 0:0,1; 1:0,1 | 2:0,1 | b,k,J,N,Omega,P,K |
| `Z4_d` | 4 |  | 3 | -2 | -1:0,1; 0:0,1 |  | R,P |
| `Z4_v` | 4 |  | 3 | -2 | -2:0,1; -1:0,1; 0:0,1; 1:0,1 |  | G,J,N,Omega,K |
| `Z4_vd` | 4 |  | 3 | -2 | 0:1 |  | Psi |
| `Z4_vv` | 4 |  | 3 | -2 | 0:0,1 |  | Phi,Omega |
| `A5_base` | 5 |  | 4 | -2 | 0:0,1; 1:0,1 |  | b,k,J,N,Omega,P,K |
| `A5_d` | 5 |  | 4 | -2 | 0:1 |  | R,P |
| `A5_v` | 5 |  | 4 | -2 | 0:0,1; 1:0,1 |  | G,J,N,Omega,K |
| `A5_vd` | 5 |  | 4 | -2 | 0:1 |  | Psi |
| `A5_vv` | 5 |  | 4 | -2 | 0:0,1 |  | Phi,Omega |
| `EA5_base` | 5 | E | 5 | -2 | 0:0 |  | J,Omega,K |
| `EA5_v` | 5 | E | 5 | -2 | 0:0 |  | Omega |
| `EQ6_base` | 6 | E | 6 | -2 | 0:0 |  | K |
| `Q6_base` | 6 |  | 5 | -2 | 0:0,1; 1:0,1 |  | k,J,Omega,K |
| `Q6_d` | 6 |  | 5 | -2 | 0:1 |  | P |
| `Q6_v` | 6 |  | 5 | -2 | 0:0,1 |  | N,Omega,K |
| `Z6_base` | 6 |  | 5 | -3 | -1:0,1; 0:0,1 |  | J,K |
| `Z6_v` | 6 |  | 5 | -3 | 0:1 |  | Omega |
| `A7_base` | 7 |  | 6 | -3 | 0:1 |  | J,K |
| `A7_v` | 7 |  | 6 | -3 | 0:1 |  | Omega |
| `Q8_base` | 8 |  | 7 | -3 | 0:1 |  | K |

Integrand of every atom: `spec_definitions.json` -> `DEFINITIONS.raw_atoms.<atom>.integrand_at_v1_delta0`.

Hardest pieces: A7_v [eps^0 l^1] (6-dim, Omega); Q8_base [eps^0 l^1] (7-dim, K); A7_base [eps^0 l^1] (J,K); EQ6_base [eps^0 l^0] (6-dim absolute, K only, via lambda6); Q6_{base,v,d} (5-dim; P, N, K); Z6_{base,v} (Z6_base at eps^-1 and eps^0); A5_{vd,vv,d,v,base}; EA5_{base,v} [eps^0 l^0] (5-dim absolute).

## 7. Validation targets (archive-free)

Provenance tags: **note** = stated in the note (line given); **note-closed-forms** = a relation evaluated with the note closed forms of the old inputs; **derived-here-exact** = exact derivation from the spec definitions (script named); **note-implied** = fixed by a note closed form through this spec's own definitions; **independent-numeric** = project-internal numerical computation, not exact.

Symbols: z2..z6 = zeta(2)..zeta(6), L2 = log 2, L3 = log 3, Li2h = Li2(-1/2), Li4h = Li4(1/2), P4,R4,S5 = note eq:periods-low (l.527-533).

| id | series | eps^p | l^k | exact | value | provenance | source |
|---|---|---|---|---|---|---|---|
| Z2.m1.l0 | `Z2_base` | -1 | 0 | `1` | 1.0 | note | note/LRI_perturbation_compendium.tex l.388 Z2 = 1/eps + l - 1 |
| Z2.0.l1 | `Z2_base` | 0 | 1 | `1` | 1.0 | note | note/LRI_perturbation_compendium.tex l.388 |
| Z2.0.l0 | `Z2_base` | 0 | 0 | `-1` | -1.0 | note | note/LRI_perturbation_compendium.tex l.388 |
| Q2.0.l1 | `Q2_base` | 0 | 1 | `-1` | -1.0 | note | note/LRI_perturbation_compendium.tex l.388 Q2 = -l - 1 + eps |
| Q2.0.l0 | `Q2_base` | 0 | 0 | `-1` | -1.0 | note | note/LRI_perturbation_compendium.tex l.388 |
| Q2.1.l0 | `Q2_base` | 1 | 0 | `1` | 1.0 | note | note/LRI_perturbation_compendium.tex l.388 |
| C3.l2 | `C3[v0d0]` | 0 | 2 | `2` | 2.0 | note | note/LRI_perturbation_compendium.tex eq lo:eq:C3 (l.550) |
| C3.l1 | `C3[v0d0]` | 0 | 1 | `5` | 5.0 | note | note/LRI_perturbation_compendium.tex eq lo:eq:C3 (l.550) |
| C3.l0 | `C3[v0d0]` | 0 | 0 | `3 - 2*z2` | -0.289868133696452872944 | note | note/LRI_perturbation_compendium.tex eq lo:eq:C3 (l.550) |
| K4.l3 | `K4[v0d0]` | 0 | 3 | `-4/3` | -1.333333333333333333333 | note | note/LRI_perturbation_compendium.tex eq lo:eq:K4 (l.551-552), P4 eq:periods-low |
| K4.l2 | `K4[v0d0]` | 0 | 2 | `-6` | -6.0 | note | note/LRI_perturbation_compendium.tex eq lo:eq:K4 (l.551-552), P4 eq:periods-low |
| K4.l1 | `K4[v0d0]` | 0 | 1 | `4*z2 - 8` | -1.420263732607094254110 | note | note/LRI_perturbation_compendium.tex eq lo:eq:K4 (l.551-552), P4 eq:periods-low |
| K4.l0 | `K4[v0d0]` | 0 | 0 | `L2**2 + 3*L3 + 2*Li2h + 8*z2 + 8*z3/3 - 12` | 7.2444190759533010134786 | note | note/LRI_perturbation_compendium.tex eq lo:eq:K4 (l.551-552), P4 eq:periods-low |
| C5.l4 | `C5[v0d0]` | 0 | 4 | `10/3` | 3.3333333333333333333333 | note | note/LRI_perturbation_compendium.tex eq lo:eq:C5 (l.553-556), S5 eq:periods-low |
| C5.l3 | `C5[v0d0]` | 0 | 3 | `62/3` | 20.666666666666666666666 | note | note/LRI_perturbation_compendium.tex eq lo:eq:C5 (l.553-556), S5 eq:periods-low |
| C5.l2 | `C5[v0d0]` | 0 | 2 | `95/2 - 24*z2` | 8.0215823956425655246620 | note | note/LRI_perturbation_compendium.tex eq lo:eq:C5 (l.553-556), S5 eq:periods-low |
| C5.l1 | `C5[v0d0]` | 0 | 1 | `-4*L2**2 - 12*L3 - 8*Li2h - 84*z2 - 152*z3/3 + 99` | -111.5965239063047501664 | note | note/LRI_perturbation_compendium.tex eq lo:eq:C5 (l.553-556), S5 eq:periods-low |
| C3v.l3 | `C3[v1d0]` | 0 | 3 | `-8/3` | -2.666666666666666666666 | note | note/LRI_perturbation_compendium.tex eq lo:eq:C3v (l.2231-2234) |
| C3v.l2 | `C3[v1d0]` | 0 | 2 | `-3` | -3.0 | note | note/LRI_perturbation_compendium.tex eq lo:eq:C3v (l.2231-2234) |
| C3v.l1 | `C3[v1d0]` | 0 | 1 | `4 - 4*z2` | -2.579736267392905745889 | note | note/LRI_perturbation_compendium.tex eq lo:eq:C3v (l.2231-2234) |
| C3v.l0 | `C3[v1d0]` | 0 | 0 | `-8*L2 - 14*z2 - 15*z3 + 18` | -28.60510792774864686694 | note | note/LRI_perturbation_compendium.tex eq lo:eq:C3v (l.2231-2234) |
| C3d.l4 | `C3[v0d1]` | 0 | 4 | `-1` | -1.0 | note | note/LRI_perturbation_compendium.tex eq lo:eq:C3delta (l.2263-2264); [l^1] = p - |
| C3d.l3 | `C3[v0d1]` | 0 | 3 | `-1` | -1.0 | note | note/LRI_perturbation_compendium.tex eq lo:eq:C3delta (l.2263-2264); [l^1] = p - |
| C3d.l2 | `C3[v0d1]` | 0 | 2 | `-2*z2` | -3.289868133696452872944 | note | note/LRI_perturbation_compendium.tex eq lo:eq:C3delta (l.2263-2264); [l^1] = p - |
| C3d.l1 | `C3[v0d1]` | 0 | 1 | `-8*L2 - 2*z2 - 7*z3 + 4` | -13.24944390029317534608 | note | note/LRI_perturbation_compendium.tex eq lo:eq:C3delta (l.2263-2264); [l^1] = p - |
| EQ4.0.l0 | `EQ4_base` | 0 | 0 | `-12*z2 - 54*z3 - 25*z4 + 6` | -105.7083624155752634371 | note | note/LRI_perturbation_compendium.tex eq:ep-exact (l.603); appendix l.2673 (boxed |
| EA3v.0.l0 | `EA3_v` | 0 | 0 | `16*L2 + 60*z2 + 22*z3 - 34*z4 - 108` | -8.567339176814913093729 | note | note/LRI_perturbation_compendium.tex eq:ep-exact (l.602) |
| EQ2.0.l0 | `EQ2_base` | 0 | 0 | `-2*z2` | -3.289868133696452872944 | derived-here-exact | EQ2(eps) = int_eps^1 r^-1 [2(1-r)log(1-r) + 2 r log r] dr (inner X1 integral don |
| EZ2.0.l0 | `EZ2_base` | 0 | 0 | `2*z2 - 2` | 1.2898681336964528729448 | derived-here-exact | EZ2(eps) = int_eps^1 r^-2 [2(1-r)log(1-r) + 2 r log r] dr; [eps^0] = -l^2 + 2 l  |
| EZ2.0.l1 | `EZ2_base` | 0 | 1 | `2` | 2.0 | derived-here-exact | same derivation as EZ2.0.l0 |
| EZ2.0.l2 | `EZ2_base` | 0 | 2 | `-1` | -1.0 | derived-here-exact | same derivation as EZ2.0.l0 |
| EA3.0.l0 | `EA3_base` | 0 | 0 | `10*z2 - 26` | -9.550659331517735635275 | note-implied | solving this spec's definition of b (out/input_definitions.json) = note eq:oldbe |
| A3dd_half.l6 | `A3_dd/2` | 0 | 6 | `1/3` | 0.3333333333333333333333 | note-closed-forms | lower-flow relation [l^6..l^2] in terms of a, A, p, E (relation as in the archiv |
| A3dd_half.l5 | `A3_dd/2` | 0 | 5 | `-1/15` | -0.066666666666666666666 | note-closed-forms | lower-flow relation [l^6..l^2] in terms of a, A, p, E (relation as in the archiv |
| A3dd_half.l4 | `A3_dd/2` | 0 | 4 | `z2 - 1/3` | 1.3116007335148931031390 | note-closed-forms | lower-flow relation [l^6..l^2] in terms of a, A, p, E (relation as in the archiv |
| A3dd_half.l3 | `A3_dd/2` | 0 | 3 | `8*L2 - 4*z2/3 + 5*z3/3 - 4` | 1.3553601939479177023742 | note-closed-forms | lower-flow relation [l^6..l^2] in terms of a, A, p, E (relation as in the archiv |
| A3dd_half.l2 | `A3_dd/2` | 0 | 2 | `-L2**4/3 + 2*L2**2*z2 - 4*L2**2 - 7*L2*z3 + 4*L2 - 8*Li4h + 7*z2 - 11*` | -10.83193833709230504051 | note-closed-forms | lower-flow relation [l^6..l^2] in terms of a, A, p, E (relation as in the archiv |
| C7.l6 | `C7[v0d0]` | 0 | 6 | `244/45` | 5.4222222222222222222222 | note | note/LRI_perturbation_compendium.tex l.719-723 |
| C7.l5 | `C7[v0d0]` | 0 | 5 | `170/3` | 56.666666666666666666666 | note | note/LRI_perturbation_compendium.tex l.719-723 |
| C7.l4 | `C7[v0d0]` | 0 | 4 | `247 - 316*z2/3` | 73.733611625320148691572 | note | note/LRI_perturbation_compendium.tex l.719-723 |
| C5d.l6 | `C5[v0d1]` | 0 | 6 | `-142/45` | -3.155555555555555555555 | note | note/LRI_perturbation_compendium.tex l.726-730 |
| C5d.l5 | `C5[v0d1]` | 0 | 5 | `-71/5` | -14.2 | note | note/LRI_perturbation_compendium.tex l.726-730 |
| C5d.l4 | `C5[v0d1]` | 0 | 4 | `14*z2/3 - 55/3` | -10.65697435470827662979 | note | note/LRI_perturbation_compendium.tex l.726-730 |
| C7v.l8 | `C7[v1d0]` | 0 | 8 | `0` | 0.0 | note | note/LRI_perturbation_compendium.tex l.1051-1056 |
| C7v.l7 | `C7[v1d0]` | 0 | 7 | `-6416/315` | -20.36825396825396825396 | note | note/LRI_perturbation_compendium.tex l.1051-1056 |
| C7v.l6 | `C7[v1d0]` | 0 | 6 | `-1622/9` | -180.2222222222222222222 | note | note/LRI_perturbation_compendium.tex l.1051-1056 |
| C7v.l5 | `C7[v1d0]` | 0 | 5 | `3848*z2/15 - 8824/15` | -166.2862473845349781636 | note | note/LRI_perturbation_compendium.tex l.1051-1056 |
| K8.l7 | `K8[v0d0]` | 0 | 7 | `-1088/315` | -3.453968253968253968253 | note | note/LRI_perturbation_compendium.tex l.1058-1062 |
| K8.l6 | `K8[v0d0]` | 0 | 6 | `-664/15` | -44.26666666666666666666 | note | note/LRI_perturbation_compendium.tex l.1058-1062 |
| K8.l5 | `K8[v0d0]` | 0 | 5 | `96*z2 - 3656/15` | -85.81966291590359543198 | note | note/LRI_perturbation_compendium.tex l.1058-1062 |
| input.a | `a` |  |  | `-4*z2` | -6.579736267392905745889 | note | note/LRI_perturbation_compendium.tex eq:oldbetas (l.516) |
| input.c | `c` |  |  | `-16` | -16.0 | note | note/LRI_perturbation_compendium.tex eq:oldbetas (l.516) |
| input.p | `p` |  |  | `-8*L2 - 2*z2 - 7*z3 + 8` | -9.249443900293175346080 | note | note/LRI_perturbation_compendium.tex eq:oldbetas (l.517); also eq:panswer (l.226 |
| input.b | `b` |  |  | `-4*L2**2 + 32*L2 - 12*L3 - 8*Li2h - 6*z2 + 28*z3/3 - 18` | -5.987542724649181096285 | note | note/LRI_perturbation_compendium.tex eq:oldbetas (l.518-519) |
| input.f | `f` |  |  | `16*L2**2 - 64*L2 + 48*L3 + 32*Li2h - 136*z3/3 + 32` | -20.78328237520096457069 | note | note/LRI_perturbation_compendium.tex eq:oldbetas (l.520-521) |
| input.A | `A` |  |  | `16*L2 - 4*z2 - 2*z3 - 8` | -5.893495184752969366013 | note | note/LRI_perturbation_compendium.tex Sec. sec:D3 (l.580) |
| input.E | `E` |  |  | `-2*L2**4/3 + 4*L2**2*z2 - 8*L2**2 - 14*L2*z3 + 8*L2 - 16*Li4h + 14*z2 ` | -21.66387667418461008102 | note | note/LRI_perturbation_compendium.tex eq:Eexact (l.581-584) |
| input.calR | `2*G + k + 2*q - 2*b - f` |  |  | `16*L2**4/3 - 32*L2**2*z2 + 64*L2**2 + 112*L2*z3 - 64*L2 + 128*Li4h + 6` | -4.163136732698216735447 | note | note/LRI_perturbation_compendium.tex l.629-634 ("exact period certificate"); fix |
| invariant.D2 | `D2` |  |  | `2*z2 + 5/2` | 5.7898681336964528729448 | note | note/LRI_perturbation_compendium.tex l.568 (boxed) |
| invariant.T2 | `T2` |  |  | `-2*z2 - 4*z3 + 2` | -6.098095746334830014543 | note | note/LRI_perturbation_compendium.tex l.568 (boxed) |
| invariant.C3 | `C3` |  |  | `2*z2 + 39/16` | 5.7273681336964528729448 | note | note/LRI_perturbation_compendium.tex l.570 (text) |
| invariant.C4 | `C4` |  |  | `-4*z2 - 8*z3 + 4` | -12.19619149266966002908 | note | note/LRI_perturbation_compendium.tex l.570 (text) |
| invariant.D3 | `D3` |  |  | `-13*z2 + 11*z3 + 11*z4 + 21/4` | 8.9940386365511135719317 | note | note/LRI_perturbation_compendium.tex l.638 (boxed) |
| invariant.C5 | `C5` |  |  | `-361*z2/16 + 24*z3 + 49*z4/2 + 11249/1024` | 29.237811580990039568826 | note | note/LRI_perturbation_compendium.tex l.642-643 (boxed) |
| period.P4 | `P4` |  |  | `L2**2 + 3*L3 + 2*Li2h + 4*z2 + 8*z3/3 - 2` | 10.664682808560395267589 | note | note/LRI_perturbation_compendium.tex eq:periods-low (l.527-533) |
| period.R4 | `R4` |  |  | `-16*L2 - 20*z2 - 30*z3 + 24` | -56.05074332071148224211 | note | note/LRI_perturbation_compendium.tex eq:periods-low (l.527-533) |
| period.S5 | `S5` |  |  | `4*L2**2 + 12*L3 + 8*Li2h + 44*z2 + 152*z3/3 - 3` | 141.79916123237569270757 | note | note/LRI_perturbation_compendium.tex eq:periods-low (l.527-533) |

**Exact two-kink raw atoms** (`out/two_kink_exact.json`, derived-here-exact): every Z2_* and Q2_* atom, full eps/log expansion, exact rationals. They may be used directly as inputs (`assemble_from_raw.py --fill-two-kink-exact`).

**Independent input values** (project-internal, not exact):

* beta input V = -19.518741011574465808242207110067 (abs. accuracy 1e-26; review/three_kink_independent.py (dps 30; from-scratch semi-analytic eps expansion, 1D tanh-sinh quadratures; its a, p, A, E agree with the note closed forms to 1e-28))
* beta input alpha = -1.6576510838700072279237784615477 (abs. accuracy 1e-26; review/three_kink_independent.py (dps 30; from-scratch semi-analytic eps expansion, 1D tanh-sinh quadratures; its a, p, A, E agree with the note closed forms to 1e-28))
* beta input beta = -16.027908690418506113987594422297 (abs. accuracy 1e-26; review/three_kink_independent.py (dps 30; from-scratch semi-analytic eps expansion, 1D tanh-sinh quadratures; its a, p, A, E agree with the note closed forms to 1e-28))
* beta input gamma = -44.0096840647677915237145400082 (abs. accuracy 1e-26; review/three_kink_independent.py (dps 30; from-scratch semi-analytic eps expansion, 1D tanh-sinh quadratures; its a, p, A, E agree with the note closed forms to 1e-28))

**Finite-cutoff cross-checks.** full ordered integral over Omega_n(eps) of the differentiated kernel at (v,delta)=(1,0), BEFORE any eps expansion (the translation reduction gives the same number). E moments: reflected first source derivative. Compute each cross-check quantity by two independent routes inside the project (engine: exact/Mellin value of the full moment at that eps; direct: Gauss/RQMC cubature) and require agreement within the stated errors. Archived values of the same quantities are sealed in comparison/archive_comparison.json (archive_finite_cutoff_values) for the final comparison step only. Finite-cutoff cubature validates integrand conventions; it cannot isolate the [eps^0 l^1] single logs of the 6-8 kink atoms.

| moment | eps | value | provenance |
|---|---|---|---|
| `EQ2_base` | 0.125 | -2.2780480909636724890379342968793 | derived-here-exact (1D integral, mpmath 40 digits) |
| `EZ2_base` | 0.125 | -7.3208112918902553409491664341251 | derived-here-exact (1D integral, mpmath 40 digits) |
| `EQ2_base` | 0.1 | -2.43446660471477413170405553873 | derived-here-exact (1D integral, mpmath 40 digits) |
| `EZ2_base` | 0.1 | -8.7189250268096921899755113578928 | derived-here-exact (1D integral, mpmath 40 digits) |
| `A3_d` | 1/8 | -18.062881247394966 | independent-numeric (scipy cubature, ~1e-10) |
| `Z4_d` | 1/8 | -36.58665668378288 | independent-numeric (scipy cubature, ~1e-10) |
| `EQ2_base` | 1/8 | -2.2780480909636713 | independent-numeric (scipy cubature, ~1e-10) |

Cross-check quantities (no archive-free value yet; compute by two independent routes): `A3_d`(1/8), `Z4_d`(1/8), `A5_d`(1/8), `A7_base`(1/8), `Q6_v`(1/8), `EA5_base`(1/8), `A7_v`(1/10), `Q8_base`(1/10), `Q4_dd`(1/10).

Archive-derived predictions (sealed, comparison step only): [l^7], [l^3] of C7[v0d0]; [l^7], [l^3], [l^2] of C5[v0d1]; [l^2]..[l^8] of K4[v0d2]/2 (second tail of K4); archived finite-cutoff values of the cross-check quantities; (location: comparison/archive_comparison.json -> archive_derived_validation_predictions, archive_finite_cutoff_values).

## 8. Archive-free checks performed on this spec

* derive_requirements.py: C3..C7, K2..K8, EC3, EC5, EK2..EK6 equal the note formulas (symbolic assertions)
* algebra: {'note_B_old_C6': True, 'note_D3': True, 'note_D2_T2': True, 'note_D4_new_coefficients': True, 'higher_unknown_terms_do_not_enter_T3_D4': True, 'full_jacobian_equals_fixed_point_form': True, 'note_old_input_closed_forms_give_boxed_D2_T2': True, 'note_old_input_closed_forms_and_calR_give_boxed_D3': True}
* closed-form consistency: {'C3 == D2-1/16': True, 'C5 == 2D3 - T2/2 + (D2-1/16)^2/4': True, 'C7(note) == 4D4 - C6/4 - T2^2 + C3*C5/2': True, 'C7 - 4 D4 (known additive)': '-20*z2*z3 + 1011*z2/1024 - 16*z3**2 + 77*z3/4 - 1059*z4/64 + 68*z5 + 343*z6/8 + 94647/32768'}
* two-kink exact table: {'insertion_table_n2_matches': True, 'note_l388_Z2_Q2': True, 'supports_Z2_-1_0_Q2_0_1': True}
* validation internals: {'EQ2_base_eps0_numeric_minus_exact': '0.0', 'EZ2_base_eps0l0_numeric_minus_exact': '0.0', 'A_note_integral_l588_minus_closed_form': '0.0', 'E_note_integral_l592_minus_closed_form': '3.67e-40', 'S5_minus_4P4_equals_5+28z2+40z3': True, 'c_from_spec_definition_with_note_atoms': '-16', 'EA3_0_from_note_b': '10*z2 - 26'}
* reviewer, recurrence_from_jacobian: review/recurrence_from_jacobian.py: b3..h8 recurrence = order-by-order solution of J beta = R1 (extended one order, EXTRAPOLATIONS lambda6)
* reviewer, algebra_independent: {'T3_free_of_extras': True, 'D4_free_of_extras': True, 'T2_free_of_extras': True, 'D3_free_of_extras': True, 'D2_equals_spec': True, 'T2_equals_spec': True, 'D3_equals_spec': True, 'T3_equals_spec': True, 'D4_equals_spec': True, 'C6_coeff_V_ok': True, 'C6_coeff_R_ok': True, 'C6_coeff_J_ok': True, 'C6_coeff_L_ok': True, 'C6_coeff_M_ok': True, 'C6_coeff_N_ok': True, 'B_old_C6_equals_spec': True, 'D4_coeff_alpha_ok': True, 'D4_coeff_beta_ok': True, 'D4_coeff_gamma_ok': True, 'D4_coeff_Phi_ok': True, 'D4_coeff_Psi_ok': True, 'D4_coeff_Omega_ok': True, 'D4_coeff_Q_ok': True, 'D4_coeff_P_ok': True, 'D4_coeff_K_ok': True, 'B_old_D4_equals_spec': True, 'new_C7_inputs_absent_from_T3': True}
* reviewer, old_inputs_from_note: {'K2_0': '-1', 'K2_0[v1d0]': '-2', 'EQ2_0_numeric_ok': True, 'EZ2_0_numeric_ok': True, 'c': {'from_spec_definition': '-16', 'minus_note_closed_form': '0'}, 'b': {'from_spec_definition': '-4*L2**2 + 32*L2 - 12*L3 - 8*Li2h - 6*z2 + 28*z3/3 - 18', 'minus_note_closed_form': '0'}, 'b_if_EA1_dropped_minus_note': '4'}
* reviewer, three_kink_independent: review/three_kink_independent.py: a, p, A, E from scratch equal the note closed forms to 1e-28; note log coefficients of C3, d_v C3, d_delta C3 and the A3_dd/2 higher logs reproduced

The archive comparisons (definitions reproduce the 25 archived inputs; the assembler on archived raw coefficients; targets vs archived series; tight-bound evidence) are in `comparison/archive_comparison.json` and `comparison/comparison_report.json`.

## 9. Ambiguities and discrepancies

* **matching-wording**: Note l.464 ("restore the canonical/matching contributions using eq:matching") and l.558 ("The explicit finite-tail factor (fugmatch) is needed for p") could suggest an extra matching term in the inputs. In this spec no fugmatch term is added to any single-log input: p = d_delta C3_1 + 4, where +4 = 2v d_delta j1 is the endpoint integral; fugmatch changes only l^4, l^3 (appendix l.2270-2289). *Resolution:* confirmed against the note's closed forms of a, p, A, E (review/three_kink_independent.py) and of c (review/old_inputs_from_note.py). The b check of review/old_inputs_from_note.py is NOT independent in this archive-free spec: EA3_base [eps^0 l^0] = -26 + 10 z2 is itself solved from the note's b (note-implied target EA3.0.l0), so the definition of b is tested only when a project route computes EA3_base [eps^0 l^0] and finds that value (gate-review note 2026-10-02). For the 4-8 kink inputs the prescription is not tested against any note closed form; a first-principles derivation of the finite-delta matching remains open..
* **derivative-vs-taylor**: Note eq:insertions writes [delta^2]W = (S3/3 + S2^2/2) W (Taylor coefficient); the raw atoms *_dd, *_vdd of this spec are FULL second derivatives (S2^2 + 2/3 S3 ...). The dictionary (V = b3_dd/2, gamma = b3_vdd/2, Q = -2 h4_dd) uses full derivatives; the second-tail validation targets refer to Taylor coefficients (A3_dd/2). *Resolution:* full derivatives everywhere; Taylor factors only in the dictionary and where a target says /2.
* **reflection**: The note defines E with U^odd/U^even; the reflected form 2 sum q_i f_delta(X_i) gives identical values for first source derivatives (also under delta and v derivatives). Second source derivatives (not needed) would need the unreflected form (note l.283). *Resolution:* either form for every atom in this spec.
* **EA1**: E A1 is not a moment integral: EA1 = j1 = -2/(1+delta) analytically (v-independent). It enters EC3, EC5 and generates the integer constants of a, p, E, V, gamma. *Resolution:* use the analytic value; dropping it shifts b by +4.
* **safe-vs-tight-bounds**: The generic leading-power bound -floor(n/2) (Q2: 0) is safe; the tight bounds of this spec rest on power counting (RAW_MOMENT_REQUIREMENTS.tight_bounds_argument). With the safe bound K8 formally needs Z4_base at eps^+2 and Q4_base at eps^-2. *Resolution:* supply the safe set; the assembler (--windows both) asserts the below-bound scalars vanish and that tight and safe assemblies agree.
* **h-vs-eta-names**: Archived notes/scripts call h4,h6 eta4,eta6 (not the endpoint source eta); some call normalized responses C_n,K_n (not thermal C_n). *Resolution:* naming only.
* **v-meaning**: In the recurrence v = b0^2 is the auxiliary reference charge (also the charge in W_n); the essential v = B^2 = b0^2 eps^delta. The Taylor variable z = v-1 of F,H is identified with b0^2-1 at the matching scale l=0. *Resolution:* definitional.
* **derive_D4-writes**: The archived derive_D4.py writes into the compendium (../verification/algebra relative to itself); it was NOT run. scripts/derive_invariants.py re-derives B_old^{D4} and D4 independently. *Resolution:* use the assemblies of this spec.
* **lambda6**: lambda6 is not defined in the note. *Resolution:* see EXTRAPOLATIONS.

## 10. C8 extension (2026-10-03): the ten new inputs of C8 = 8 T4

Contains NO archive-derived number. Every C8-era archive number (the ten inputs, A9_1, Z8_1, (EA7)_0, (EZ6)_0, D9_lower, A7_d_1, D_known, P6, P8, X_vv, X_E, S3, B_old, B_done, C_fixed, C8, rational projections) is sealed in comparison_C8/, which production code never reads.

Sources: note/LRI_perturbation_compendium.tex Secs. 14-18 (l.1100-1460): eq:C8trace, eq:C8F, eq:C8H (l.1106-1116), derivative dictionary (l.1120-1137), eq:K8norm, eq:C9norm, h8, eq:b9, j7 (l.1139-1158), eq:C8assembly (l.1162-1166), appendix app:C8polynomial (l.2781-2806); Secs. 3-6 for the integrals.

### 10.1 Claims and assembly

* **C8 = 8 T4**: note eq:C8trace (l.1104); C8 multiplies x^4 = t^8; no D5 enters (checked here by eigenvalue expansion)
* **C8_candidate**: 88 - 178 z2 + 110 z3 + 113 z4 + 4892 z5 - 2376 z2 z3 - (8630/3) z6 + 1872 z3^2 - 12168 z7 + 6048 z2 z5 + 1536 z3 z4  (note eq:C8-candidate-main l.92-100; UNPROVED in the note)
* **C8_assembly**: C8 = B_old + 4W + 2S + 3/4 U + 1/4 J9 + 3/32 L3 - 1/4 M21 + 1/2 M12 - 1/16 N2 + 1/8 Ndelta + 1/32 Kv (eq:C8assembly; reproduced exactly here, invariants_C8.json)
* **note_relations_tested_structurally**: ['N_delta = -4 P6 + known (eq:NdP6)', 'U = A7_d_1 - Z6_d_1 + 2(EA5_d)_0 - 2(EZ4_d)_0 + D_lower', 'K_v = -4 P8 + 16 X_vv - 8 X_E + S3', 'J9 = A9_1 - Z8_1 + 2(EA7)_0 - 2(EZ6)_0 + D9_lower', 'C8 = C_fixed - P6/2 (eq:C8short): dC8/d[eps^0 l^1]Q6_vd = -1/2 (budget_C8.json)']

Claims of the note about C8 (expressions only). Their decimal values are archive numbers or would coincide with them to ~1e-86; they are sealed in comparison_C8/ and not reproduced here.

```
C8 = 8 T4 = B_old + (4)*W + (2)*S + (3/4)*U + (1/4)*J9 + (3/32)*L3 + (-1/4)*M21 + (1/2)*M12 + (-1/16)*N2 + (1/8)*Ndelta + (1/32)*Kv
B_old (61 terms, equal to the note appendix) = -3*A*a/16 + A*b/8 - 3*A*c/64 + A*p/2 + E*a/2 - E*b/4 + E*c/8 - E*p + 3*G*a/16 - G*b/8 + 3*G*c/32 - G*p/2 - J*a/16 - 9*J*c/64 - K/64 + L*a/16 - L*b/16 + 3*L*c/64 - L*p/4 + 3*L/64 - M*c/16 - M/16 - 3*N*c/128 - N/64 - 3*Omega/16 - P/16 + Phi/8 - Psi/2 - Q/4 - R*a/4 - R*c/4 - V*a - V*c/4 - a**3/16 + a**2*b/16 - 3*a**2*c/64 + a**2*p/4 + 3*a*b*c/64 - 5*a*c**2/256 + a*c*p/8 - a*f/64 + a*k/32 + a*q/8 - alpha/16 + 5*b*c**2/128 + 3*b*f/64 - b*k/16 - b*q/4 + beta/4 - 5*c**3/1024 + 5*c**2*f/512 + c**2*p/32 + c*f/256 + 5*c*k/256 + c*q/16 + f**2/64 - f*k/64 - f*q/16 - gamma - k*p/16 - p*q/4
```

### 10.2 Definitions

| input | definition | C8 coefficient | terms | max kinks | uses lambda6 | normalized atoms |
|---|---|---|---|---|---|---|
| W | d_delta^3 b3 / 6  at (v,delta)=(1,0) | 4 | 2 | 3 | False | 1 |
| S | d_delta^2 b5 / 2  at (v,delta)=(1,0) | 2 | 27 | 5 | False | 21 |
| U | d_delta b7  at (v,delta)=(1,0) | 3/4 | 106 | 7 | False | 31 |
| J9 | b9  at (v,delta)=(1,0) | 1/4 | 157 | 9 | True | 25 |
| L3 | -(2/3) d_v^3 h4  at (v,delta)=(1,0) | 3/32 | 10 | 4 | False | 12 |
| M21 | -2 d_v^2 d_delta h4  at (v,delta)=(1,0) | -1/4 | 14 | 4 | False | 16 |
| M12 | -2 d_v d_delta^2 h4  at (v,delta)=(1,0) | 1/2 | 16 | 4 | False | 16 |
| N2 | -2 d_v^2 h6  at (v,delta)=(1,0) | -1/16 | 85 | 6 | False | 30 |
| Ndelta | -4 d_v d_delta h6  at (v,delta)=(1,0) | 1/8 | 121 | 6 | False | 40 |
| Kv | -4 d_v h8  at (v,delta)=(1,0) | 1/32 | 231 | 8 | True | 36 |

W = C3_1[v0d3]/6 + 4 ; full expansions of all 35 inputs: out/C8/input_definitions_C8.json (the 25 old ones identical to out/input_definitions.json).

Recurrence through ninth order:

```
j1       = -2/(1+delta)
j3       = -2 d_v C3_0 + EC3_0
j5       = -2 d_v C5_0 + EC5_0
j7       = -2 d_v C7_0 + EC7_0  (note l.1156)
lambda2  = -2 Q2_0 - 4 v d_v Q2_0 + 2 v EQ2_0
lambda4  = -2 K4_0 - 4 v d_v K4_0 + 2 v EK4_0
lambda6  = -2 K6_0 - 4 v d_v K6_0 + 2 v EK6_0  [pattern extension; EXTRAPOLATIONS]
b3       = C3_1 + 2 v j1
h4       = K4_1 - 2 Q2_0 b3 + lambda2
b5       = C5_1 - 3 C3_0 b3 - 2 v j1 h4 + 2 v j3
h6       = K6_1 - 2 Q2_0 b5 - 4 K4_0 b3 - lambda2 h4 + lambda4
b7       = C7_1 - 3 C3_0 b5 - 5 C5_0 b3 - 2 v j1 h6 - 2 v j3 h4 + 2 v j5
h8       = K8_1 - 2 Q2_0 b7 - 4 K4_0 b5 - 6 K6_0 b3 - lambda2 h6 - lambda4 h4 + lambda6  (note l.1149-1151)
b9       = C9_1 - 3 C3_0 b7 - 5 C5_0 b5 - 7 C7_0 b3 - 2 v j1 h8 - 2 v j3 h6 - 2 v j5 h4 + 2 v j7  (note eq:b9, l.1152-1155)
rules    = all quantities functions of (v,delta), v = b0^2; derivatives act on the FULL recurrence (explicit v, j1(delta), lambda_n, j_n) before (v,delta) = (1,0); normalized products are formed with full eps/log expansions before extraction (note l.1157-1158: an unavailable raw scalar is an error, not a zero)
```

Normalized responses (E differentiates every factor, EA1 = -2/(1+delta)):

```
C3   = A3(v, d) - Z2(v, d)
C5   = -A3(v, d)*Z2(v, d) + A5(v, d) + Z2(v, d)**2 - Z4(v, d)
C7   = (Z2(v, d)**2 - Z4(v, d))*A3(v, d) - A5(v, d)*Z2(v, d) + A7(v, d) - Z2(v, d)**3 + 2*Z2(v, d)*Z4(v, d) - Z6(v, d)
C9   = (Z2(v, d)**2 - Z4(v, d))*A5(v, d) + (-Z2(v, d)**3 + 2*Z2(v, d)*Z4(v, d) - Z6(v, d))*A3(v, d) - A7(v, d)*Z2(v, d) + A9(v, d) + Z2(v, d)**4 - 3*Z2(v, d)**2*Z4(v, d) + 2*Z2(v, d)*Z6(v, d) + Z4(v, d)**2 - Z8(v, d)
K2   = Q2(v, d)
K4   = -Q2(v, d)*Z2(v, d) + Q4(v, d)
K6   = (Z2(v, d)**2 - Z4(v, d))*Q2(v, d) - Q4(v, d)*Z2(v, d) + Q6(v, d)
K8   = (Z2(v, d)**2 - Z4(v, d))*Q4(v, d) + (-Z2(v, d)**3 + 2*Z2(v, d)*Z4(v, d) - Z6(v, d))*Q2(v, d) - Q6(v, d)*Z2(v, d) + Q8(v, d)
EC3  = EA3(v, d) - EZ2(v, d) + 2*Z2(v, d)/(d + 1)
EC5  = -A3(v, d)*EZ2(v, d) - EA3(v, d)*Z2(v, d) + EA5(v, d) + 2*EZ2(v, d)*Z2(v, d) - EZ4(v, d) - 2*(Z2(v, d)**2 - Z4(v, d))/(d + 1)
EC7  = (2*EZ2(v, d)*Z2(v, d) - EZ4(v, d))*A3(v, d) + (Z2(v, d)**2 - Z4(v, d))*EA3(v, d) - A5(v, d)*EZ2(v, d) - EA5(v, d)*Z2(v, d) + EA7(v, d) - 3*EZ2(v, d)*Z2(v, d)**2 + 2*EZ2(v, d)*Z4(v, d) + 2*EZ4(v, d)*Z2(v, d) - EZ6(v, d) - 2*(-Z2(v, d)**3 + 2*Z2(v, d)*Z4(v, d) - Z6(v, d))/(d + 1)
EK2  = EQ2(v, d)
EK4  = -EQ2(v, d)*Z2(v, d) + EQ4(v, d) - EZ2(v, d)*Q2(v, d)
EK6  = (2*EZ2(v, d)*Z2(v, d) - EZ4(v, d))*Q2(v, d) + (Z2(v, d)**2 - Z4(v, d))*EQ2(v, d) - EQ4(v, d)*Z2(v, d) + EQ6(v, d) - EZ2(v, d)*Q4(v, d)
```

New derivative insertions (full derivatives; S_j = sum_{i<k} q_i q_k log^j(X_k - X_i)): **ddd**: `S2^3 + 2*S2*S3 + S4/2`; **vvvv**: `16*S1^4`; **vvvd**: `8*S1^3*S2 + 12*S1^2*S2`; **vvdd**: `4*S1^2*S2^2 + 8*S1^2*S3/3 + 8*S1*S2^2 + 8*S1*S3/3 + 2*S2^2`; **vvv**: `8*S1^3`; **vvd**: `4*S1^2*S2 + 4*S1*S2`; **vdd**: `2*S1*S2^2 + 4*S1*S3/3 + 2*S2^2 + 2*S3/3`; **dd**: `S2^2 + 2*S3/3`.

E pieces: e_j = d_delta^j e at delta = 0 = (2/(j+1)) sum_i q_i log^{j+1} X_i: e0 = 2 sum q log X, e1 = sum q log^2 X, e2 = (2/3) sum q log^3 X, e3 = (1/2) sum q log^4 X; d_delta^b (E M) = sum_j binom(b,j) e_j * [insertion of d_v^a d_delta^(b-j)]

### 10.3 Raw requirements

C8 (all 35 inputs): tight set 309 scalars in 104 raw atoms (114 beyond the C7 set, 29 new atoms); safe set 324 (12 below the tight bound must vanish, 3 genuine positive-power extras). 76 tight scalars are Z2_*/Q2_* (exact rationals) and all EZ2_*/EQ2_* scalars are exact too (out/C8/two_kink_exact_C8.json). Only l^0, l^1 of a raw coefficient reach a beta input; the higher-log and pole targets need the same atoms with all log powers (poles_C8.json lists the extra negative powers).

New raw atoms: A3_ddd, A5_dd, A7_d, A9_base, EA3_dd, EA5_d, EA7_base, EQ2_vdd, EQ2_vvd, EQ2_vvv, EQ4_vd, EQ4_vv, EQ6_v, EZ2_dd, EZ4_d, EZ6_base, Q2_vvdd, Q2_vvvd, Q2_vvvv, Q4_vdd, Q4_vvd, Q4_vvv, Q6_vd, Q6_vv, Q8_v, Z2_ddd, Z4_dd, Z6_d, Z8_base.

| raw atom | kinks | E? | tight pmin | needed (tight) [eps^p : l^k] | safe additions | new | used by |
|---|---|---|---|---|---|---|---|
| EQ2_base | 2 | E | 0 | 0:[0] 1:[0] 2:[0] | -1:[0] |  | S, U, J9, N2, Ndelta, Kv |
| EQ2_d | 2 | E | 0 | 0:[0] 1:[0] |  |  | S, U, Ndelta |
| EQ2_dd | 2 | E | 0 | 0:[0] |  |  | S, M12 |
| EQ2_v | 2 | E | 0 | 0:[0] 1:[0] 2:[0] | -1:[0] |  | N2, Ndelta, Kv |
| EQ2_vd | 2 | E | 0 | 0:[0] 1:[0] |  |  | M21, Ndelta |
| EQ2_vdd | 2 | E | 0 | 0:[0] |  | NEW | M12 |
| EQ2_vv | 2 | E | 0 | 0:[0] 1:[0] |  |  | L3, N2 |
| EQ2_vvd | 2 | E | 0 | 0:[0] |  | NEW | M21 |
| EQ2_vvv | 2 | E | 0 | 0:[0] |  | NEW | L3 |
| EZ2_base | 2 | E | 0 | 0:[0] 1:[0] 2:[0] | -1:[0] |  | U, J9, N2, Ndelta, Kv |
| EZ2_d | 2 | E | 0 | 0:[0] 1:[0] | -1:[0] |  | U, Ndelta |
| EZ2_dd | 2 | E | 0 | 0:[0] |  | NEW | S |
| EZ2_v | 2 | E | 0 | 0:[0] 1:[0] | -1:[0] 2:[0] |  | N2, Ndelta, Kv |
| EZ2_vd | 2 | E | 0 | 0:[0] | -1:[0] |  | Ndelta |
| EZ2_vv | 2 | E | 0 | 0:[0] | -1:[0] |  | N2 |
| Q2_base | 2 |  | 0 | 0:[0, 1] 1:[0, 1] |  |  | S, U, J9, L3, M21, M12, N2, Ndelta, Kv |
| Q2_d | 2 |  | 0 | 0:[0, 1] 1:[0, 1] |  |  | S, U, M21, M12, Ndelta |
| Q2_dd | 2 |  | 0 | 0:[0, 1] 1:[0, 1] |  |  | S, M12 |
| Q2_v | 2 |  | 0 | 0:[0, 1] 1:[0, 1] |  |  | S, U, J9, L3, M21, M12, N2, Ndelta, Kv |
| Q2_vd | 2 |  | 0 | 0:[0, 1] 1:[0, 1] |  |  | S, U, M21, M12, Ndelta |
| Q2_vdd | 2 |  | 0 | 0:[0, 1] 1:[0, 1] |  |  | S, M12 |
| Q2_vv | 2 |  | 0 | 0:[0, 1] 1:[0, 1] |  |  | L3, M21, N2, Ndelta, Kv |
| Q2_vvd | 2 |  | 0 | 0:[0, 1] 1:[0, 1] |  |  | M21, Ndelta |
| Q2_vvdd | 2 |  | 0 | 0:[0] |  | NEW | M12 |
| Q2_vvv | 2 |  | 0 | 0:[0, 1] 1:[0, 1] |  |  | L3, N2 |
| Q2_vvvd | 2 |  | 0 | 0:[0] |  | NEW | M21 |
| Q2_vvvv | 2 |  | 0 | 0:[0] |  | NEW | L3 |
| Z2_base | 2 |  | -1 | -1:[0, 1] 0:[0, 1] |  |  | S, U, J9, L3, M21, M12, N2, Ndelta, Kv |
| Z2_d | 2 |  | -1 | -1:[0, 1] 0:[0, 1] |  |  | S, U, M21, M12, Ndelta |
| Z2_dd | 2 |  | -1 | -1:[0, 1] 0:[0, 1] |  |  | S, M12 |
| Z2_ddd | 2 |  | -1 | 0:[1] |  | NEW | W |
| Z2_v | 2 |  | -1 | -1:[0, 1] 0:[0, 1] |  |  | U, J9, L3, M21, M12, N2, Ndelta, Kv |
| Z2_vd | 2 |  | -1 | -1:[0, 1] 0:[0, 1] |  |  | U, M21, M12, Ndelta |
| Z2_vdd | 2 |  | -1 | -1:[0, 1] 0:[0, 1] |  |  | S, M12 |
| Z2_vv | 2 |  | -1 | -1:[0, 1] 0:[0, 1] |  |  | L3, M21, N2, Ndelta, Kv |
| Z2_vvd | 2 |  | -1 | -1:[0, 1] 0:[0, 1] |  |  | M21, Ndelta |
| Z2_vvv | 2 |  | -1 | -1:[0, 1] 0:[0, 1] |  |  | L3, N2 |
| A3_base | 3 |  | -1 | -1:[0, 1] 0:[0, 1] 1:[0, 1] 2:[0, 1] 3:[0, 1] |  |  | S, U, J9, L3, M21, M12, N2, Ndelta, Kv |
| A3_d | 3 |  | -1 | -1:[0, 1] 0:[0, 1] 1:[0, 1] 2:[0, 1] |  |  | S, U, M21, M12, Ndelta |
| A3_dd | 3 |  | -1 | 0:[0, 1] 1:[0, 1] |  |  | S, M12 |
| A3_ddd | 3 |  | -1 | 0:[1] |  | NEW | W |
| A3_v | 3 |  | -1 | -1:[0, 1] 0:[0, 1] 1:[0, 1] 2:[0, 1] |  |  | U, J9, L3, M21, M12, N2, Ndelta, Kv |
| A3_vd | 3 |  | -1 | 0:[0, 1] 1:[0, 1] |  |  | U, M21, M12, Ndelta |
| A3_vdd | 3 |  | -1 | 0:[0, 1] |  |  | S, M12 |
| A3_vv | 3 |  | -1 | 0:[0, 1] 1:[0, 1] |  |  | L3, M21, N2, Ndelta, Kv |
| A3_vvd | 3 |  | -1 | 0:[0, 1] |  |  | M21, Ndelta |
| A3_vvv | 3 |  | -1 | 0:[0, 1] |  |  | L3, N2 |
| EA3_base | 3 | E | -1 | -1:[0] 0:[0] 1:[0] 2:[0] |  |  | U, J9, N2, Ndelta, Kv |
| EA3_d | 3 | E | -1 | 0:[0] 1:[0] |  |  | U, Ndelta |
| EA3_dd | 3 | E | -1 | 0:[0] |  | NEW | S |
| EA3_v | 3 | E | -1 | 0:[0] 1:[0] |  |  | N2, Ndelta, Kv |
| EA3_vd | 3 | E | -1 | 0:[0] |  |  | Ndelta |
| EA3_vv | 3 | E | -1 | 0:[0] |  |  | N2 |
| EQ4_base | 4 | E | -1 | 0:[0] 1:[0] |  |  | U, J9, Kv |
| EQ4_d | 4 | E | -1 | 0:[0] |  |  | U, Ndelta |
| EQ4_v | 4 | E | -1 | 0:[0] 1:[0] |  |  | N2, Kv |
| EQ4_vd | 4 | E | -1 | 0:[0] |  | NEW | Ndelta |
| EQ4_vv | 4 | E | -1 | 0:[0] |  | NEW | N2 |
| EZ4_base | 4 | E | -1 | -1:[0] 0:[0] 1:[0] | -2:[0] |  | J9, Kv |
| EZ4_d | 4 | E | -1 | 0:[0] |  | NEW | U |
| EZ4_v | 4 | E | -1 | -1:[0] 0:[0] |  |  | Kv |
| Q4_base | 4 |  | -1 | -1:[0, 1] 0:[0, 1] 1:[0, 1] 2:[0, 1] | -2:[0, 1] |  | S, U, J9, N2, Ndelta, Kv |
| Q4_d | 4 |  | -1 | 0:[0, 1] 1:[0, 1] |  |  | S, U, Ndelta |
| Q4_dd | 4 |  | -1 | 0:[1] |  |  | S |
| Q4_v | 4 |  | -1 | -1:[0, 1] 0:[0, 1] 1:[0, 1] 2:[0, 1] | -2:[0, 1] |  | U, J9, N2, Ndelta, Kv |
| Q4_vd | 4 |  | -1 | 0:[0, 1] 1:[0, 1] |  |  | U, Ndelta |
| Q4_vdd | 4 |  | -1 | 0:[1] |  | NEW | M12 |
| Q4_vv | 4 |  | -1 | 0:[0, 1] 1:[0, 1] |  |  | N2, Kv |
| Q4_vvd | 4 |  | -1 | 0:[0, 1] |  | NEW | M21, Ndelta |
| Q4_vvv | 4 |  | -1 | 0:[0, 1] |  | NEW | L3, N2 |
| Z4_base | 4 |  | -2 | -2:[0, 1] -1:[0, 1] 0:[0, 1] 1:[0, 1] 2:[0, 1] |  |  | U, J9, N2, Ndelta, Kv |
| Z4_d | 4 |  | -2 | -2:[0, 1] -1:[0, 1] 0:[0, 1] 1:[0, 1] |  |  | U, Ndelta |
| Z4_dd | 4 |  | -2 | 0:[1] |  | NEW | S |
| Z4_v | 4 |  | -2 | -2:[0, 1] -1:[0, 1] 0:[0, 1] 1:[0, 1] | 2:[0, 1] |  | J9, N2, Ndelta, Kv |
| Z4_vd | 4 |  | -2 | -1:[0, 1] 0:[0, 1] |  |  | U, Ndelta |
| Z4_vv | 4 |  | -2 | -1:[0, 1] 0:[0, 1] |  |  | N2, Kv |
| A5_base | 5 |  | -2 | -2:[0, 1] -1:[0, 1] 0:[0, 1] 1:[0, 1] 2:[0, 1] |  |  | U, J9, N2, Ndelta, Kv |
| A5_d | 5 |  | -2 | 0:[0, 1] 1:[0, 1] |  |  | U, Ndelta |
| A5_dd | 5 |  | -2 | 0:[1] |  | NEW | S |
| A5_v | 5 |  | -2 | 0:[0, 1] 1:[0, 1] |  |  | J9, N2, Ndelta, Kv |
| A5_vd | 5 |  | -2 | 0:[0, 1] |  |  | U, Ndelta |
| A5_vv | 5 |  | -2 | 0:[0, 1] |  |  | N2, Kv |
| EA5_base | 5 | E | -2 | 0:[0] 1:[0] |  |  | J9, Kv |
| EA5_d | 5 | E | -2 | 0:[0] |  | NEW | U |
| EA5_v | 5 | E | -2 | 0:[0] |  |  | Kv |
| EQ6_base | 6 | E | -2 | 0:[0] |  |  | J9, Kv |
| EQ6_v | 6 | E | -2 | 0:[0] |  | NEW | Kv |
| EZ6_base | 6 | E | -2 | 0:[0] |  | NEW | J9 |
| Q6_base | 6 |  | -2 | 0:[0, 1] 1:[0, 1] |  |  | U, J9, Kv |
| Q6_d | 6 |  | -2 | 0:[1] |  |  | U |
| Q6_v | 6 |  | -2 | 0:[0, 1] 1:[0, 1] |  |  | J9, Kv |
| Q6_vd | 6 |  | -2 | 0:[1] |  | NEW | Ndelta |
| Q6_vv | 6 |  | -2 | 0:[0, 1] |  | NEW | N2, Kv |
| Z6_base | 6 |  | -3 | -3:[0, 1] -2:[0, 1] -1:[0, 1] 0:[0, 1] 1:[0, 1] |  |  | J9, Kv |
| Z6_d | 6 |  | -3 | 0:[1] |  | NEW | U |
| Z6_v | 6 |  | -3 | -1:[0, 1] 0:[0, 1] |  |  | J9, Kv |
| A7_base | 7 |  | -3 | 0:[0, 1] 1:[0, 1] |  |  | J9, Kv |
| A7_d | 7 |  | -3 | 0:[1] |  | NEW | U |
| A7_v | 7 |  | -3 | 0:[0, 1] |  |  | J9, Kv |
| EA7_base | 7 | E | -3 | 0:[0] |  | NEW | J9 |
| Q8_base | 8 |  | -3 | 0:[1] |  |  | J9 |
| Q8_v | 8 |  | -3 | 0:[1] |  | NEW | Kv |
| Z8_base | 8 |  | -4 | 0:[1] |  | NEW | J9 |
| A9_base | 9 |  | -4 | 0:[1] |  | NEW | J9 |

Below the tight bound (must vanish): EQ2_base [eps^-1 l^0], EQ2_v [eps^-1 l^0], EZ2_base [eps^-1 l^0], EZ2_d [eps^-1 l^0], EZ2_v [eps^-1 l^0], EZ2_vd [eps^-1 l^0], EZ2_vv [eps^-1 l^0], EZ4_base [eps^-2 l^0], Q4_base [eps^-2 l^0], Q4_base [eps^-2 l^1], Q4_v [eps^-2 l^0], Q4_v [eps^-2 l^1]. Genuine positive-power extras: EZ2_v [eps^2 l^0], Z4_v [eps^2 l^0], Z4_v [eps^2 l^1].

Precision budget: exact dC8/dx for the 85 non-exact new scalars (51 constant): e.g. A9[eps^0 l^1] +1/4, Z8 -1/4, (EA7)_0 +1/2, (EZ6)_0 -1/2, A7_d[eps^0 l^1] +3/4, Z6_d -3/4, Q8_v[eps^0 l^1] -1/8, Q6_vv[eps^0 l^0] +1/2, (d_v EQ6)_0 -1/4, Q6_vd[eps^0 l^1] -1/2, A3_ddd +2/3, A5_dd +1; a 1e-4 test of C8 needs each of these to ~1e-4/|dC8/dx| absolute (`out/C8/budget_C8.json`).

Hardest: A9_base [eps^0 l^1] (8-dim, J9); Z8_base [eps^0 l^1] (7-dim, J9); Q8_v [eps^0 l^1] (7-dim, Kv); A7_d [eps^0 l^1] (6-dim, U); EA7_base [eps^0 l^0] (7-dim absolute, J9); Q6_vd [eps^0 l^1] (5-dim, Ndelta); Q6_vv [eps^0 l^0, l^1] (Kv, N2); EQ6_v, EZ6_base [eps^0 l^0] (6-dim absolute); Z6_d [eps^0 l^1] (U).

### 10.4 Validation targets (archive-free)

| id | series | eps^p | l^k | exact | value | provenance |
|---|---|---|---|---|---|---|
| A7d.0.l8 | A7_d | 0 | 8 | `-2362/315` | -7.498412698412698412698 | note |
| A7d.0.l9 | A7_d | 0 | 9 | `0` | 0 | note |
| EQ2_base.0.l0 | EQ2_base | 0 | 0 | `(-2)*z2` | -3.289868133696452872944 | derived-here-exact |
| EQ2_d.0.l0 | EQ2_d | 0 | 0 | `(6)*z2 + (6)*z3 + (4)*z4` | 21.411238754891477097296 | derived-here-exact |
| EQ2_dd.0.l0 | EQ2_dd | 0 | 0 | `(-84)*z2 + (-84)*z3 + (-70)*z4 + (-72)*z5 + (8)*z2*z3 + (-48)*z6` | -422.5826983836344384999 | derived-here-exact |
| EQ2_v.0.l0 | EQ2_v | 0 | 0 | `(-4)*z2 + (-4)*z3` | -11.38796388003128288748 | derived-here-exact |
| EQ2_vd.0.l0 | EQ2_vd | 0 | 0 | `(36)*z2 + (36)*z3 + (29)*z4 + (24)*z5` | 158.76531482134543177331 | derived-here-exact |
| EQ2_vdd.0.l0 | EQ2_vdd | 0 | 0 | `(-888)*z2 + (-888)*z3 + (-776)*z4 + (-824)*z5 + (64)*z2*z3 + (-676)*z6 + (24)*z3^2 + (-480)*z7` | -5232.944786428301259087 | derived-here-exact |
| EQ2_vv.0.l0 | EQ2_vv | 0 | 0 | `(-16)*z2 + (-16)*z3 + (-16)*z4` | -62.86902725950334261421 | derived-here-exact |
| EQ2_vvd.0.l0 | EQ2_vvd | 0 | 0 | `(288)*z2 + (288)*z3 + (260)*z4 + (272)*z5 + (-16)*z2*z3 + (192)*z6` | 1547.0747878224024145895 | derived-here-exact |
| EQ2_vvv.0.l0 | EQ2_vvv | 0 | 0 | `(-96)*z2 + (-96)*z3 + (-96)*z4 + (-96)*z5` | -476.7592280507835686130 | derived-here-exact |
| EZ2_base.0.l0 | EZ2_base | 0 | 0 | `(-2)*1 + (2)*z2` | 1.2898681336964528729448 | derived-here-exact |
| EZ2_d.0.l0 | EZ2_d | 0 | 0 | `(6)*1 + (-4)*z2 + (2)*z3 + (-4)*z4` | -2.504915395918269941154 | derived-here-exact |
| EZ2_dd.0.l0 | EZ2_dd | 0 | 0 | `(-52)*1 + (40)*z2 + (-32)*z3 + (42)*z4 + (-24)*z5 + (-8)*z2*z3 + (48)*z6` | 28.916883638124155898544 | derived-here-exact |
| EZ2_v.0.l0 | EZ2_v | 0 | 0 | `(4)*1 + (-4)*z2 + (4)*z3` | 2.2284913452454713957092 | derived-here-exact |
| EZ2_vd.0.l0 | EZ2_vd | 0 | 0 | `(-24)*1 + (20)*z2 + (-16)*z3 + (19)*z4 + (-24)*z5` | -14.65635379651823243009 | derived-here-exact |
| EZ2_vv.0.l0 | EZ2_vv | 0 | 0 | `(-16)*1 + (16)*z2 + (-16)*z3 + (16)*z4` | 8.4032063583963254814188 | derived-here-exact |
| C3[base].l2 | C3[base] | 0 | 2 | `2` | 2.0 | derived-here-exact |
| C3[base].l3 | C3[base] | 0 | 3 | `0` | 0.0 | derived-here-exact |
| C3[base].l4 | C3[base] | 0 | 4 | `0` | 0.0 | derived-here-exact |
| C3[v].l2 | C3[v] | 0 | 2 | `-3` | -3.0 | derived-here-exact |
| C3[v].l3 | C3[v] | 0 | 3 | `-8/3` | -2.666666666666666666666 | derived-here-exact |
| C3[v].l4 | C3[v] | 0 | 4 | `0` | 0.0 | derived-here-exact |
| C3[v].l5 | C3[v] | 0 | 5 | `0` | 0.0 | derived-here-exact |
| C3[d].l2 | C3[d] | 0 | 2 | `a/2` | -3.289868133696452872944 | derived-here-exact |
| C3[d].l3 | C3[d] | 0 | 3 | `-1` | -1.0 | derived-here-exact |
| C3[d].l4 | C3[d] | 0 | 4 | `-1` | -1.0 | derived-here-exact |
| C3[d].l5 | C3[d] | 0 | 5 | `0` | 0.0 | derived-here-exact |
| C3[d].l6 | C3[d] | 0 | 6 | `0` | 0.0 | derived-here-exact |
| C3[vv].l2 | C3[vv] | 0 | 2 | `-2*a - 8` | 5.1594725347858114917793 | derived-here-exact |
| C3[vv].l3 | C3[vv] | 0 | 3 | `4/3` | 1.3333333333333333333333 | derived-here-exact |
| C3[vv].l4 | C3[vv] | 0 | 4 | `4` | 4.0 | derived-here-exact |
| C3[vv].l5 | C3[vv] | 0 | 5 | `0` | 0.0 | derived-here-exact |
| C3[vv].l6 | C3[vv] | 0 | 6 | `0` | 0.0 | derived-here-exact |
| C3[vd].l2 | C3[vd] | 0 | 2 | `A + a/2 - p + 4` | 4.0660805818437531071226 | derived-here-exact |
| C3[vd].l3 | C3[vd] | 0 | 3 | `-a - 7/3` | 4.2464029340595724125563 | derived-here-exact |
| C3[vd].l4 | C3[vd] | 0 | 4 | `-1/2` | -0.5 | derived-here-exact |
| C3[vd].l5 | C3[vd] | 0 | 5 | `8/5` | 1.6 | derived-here-exact |
| C3[vd].l6 | C3[vd] | 0 | 6 | `0` | 0.0 | derived-here-exact |
| C3[vd].l7 | C3[vd] | 0 | 7 | `0` | 0.0 | derived-here-exact |
| C3[dd].l2 | C3[dd] | 0 | 2 | `E` | -21.66387667418461008102 | derived-here-exact |
| C3[dd].l3 | C3[dd] | 0 | 3 | `2*A/3 + a/3 - 2*p/3 + 8/3` | 2.7107203878958354047484 | derived-here-exact |
| C3[dd].l4 | C3[dd] | 0 | 4 | `-a/2 - 1/2` | 2.7898681336964528729448 | derived-here-exact |
| C3[dd].l5 | C3[dd] | 0 | 5 | `-1/3` | -0.333333333333333333333 | derived-here-exact |
| C3[dd].l6 | C3[dd] | 0 | 6 | `2/3` | 0.6666666666666666666666 | derived-here-exact |
| C3[dd].l7 | C3[dd] | 0 | 7 | `0` | 0.0 | derived-here-exact |
| C3[dd].l8 | C3[dd] | 0 | 8 | `0` | 0.0 | derived-here-exact |
| C3[vvv].l2 | C3[vvv] | 0 | 2 | `-6*A` | 35.360971108517816196080 | derived-here-exact |
| C3[vvv].l3 | C3[vvv] | 0 | 3 | `4*a + 16` | -10.31894506957162298355 | derived-here-exact |
| C3[vvv].l4 | C3[vvv] | 0 | 4 | `2` | 2.0 | derived-here-exact |
| C3[vvv].l5 | C3[vvv] | 0 | 5 | `-32/5` | -6.4 | derived-here-exact |
| C3[vvv].l6 | C3[vvv] | 0 | 6 | `0` | 0.0 | derived-here-exact |
| C3[vvv].l7 | C3[vvv] | 0 | 7 | `0` | 0.0 | derived-here-exact |
| C3[vvd].l2 | C3[vvd] | 0 | 2 | `2*A - 2*E + 3*alpha + 8` | 34.567809727253259746242 | derived-here-exact |
| C3[vvd].l3 | C3[vvd] | 0 | 3 | `-10*A/3 - 2*a + 4*p/3 - 8` | 12.471864616904808917049 | derived-here-exact |
| C3[vvd].l4 | C3[vvd] | 0 | 4 | `2*a + 5` | -8.159472534785811491779 | derived-here-exact |
| C3[vvd].l5 | C3[vvd] | 0 | 5 | `4` | 4.0 | derived-here-exact |
| C3[vvd].l6 | C3[vvd] | 0 | 6 | `-8/3` | -2.666666666666666666666 | derived-here-exact |
| C3[vvd].l7 | C3[vvd] | 0 | 7 | `0` | 0.0 | derived-here-exact |
| C3[vvd].l8 | C3[vvd] | 0 | 8 | `0` | 0.0 | derived-here-exact |
| C3[vdd].l2 | C3[vdd] | 0 | 2 | `E - 2*V + 2*beta - 8` | -22.68221203187269069251 | derived-here-exact |
| C3[vdd].l3 | C3[vdd] | 0 | 3 | `2*A - 2*E + a/3 + 2*alpha - 2*p/3 + 16/3` | 37.531844655521081956256 | derived-here-exact |
| C3[vdd].l4 | C3[vdd] | 0 | 4 | `-2*A - 5*a/3 + p - 31/6` | 8.3371069148676062957620 | derived-here-exact |
| C3[vdd].l5 | C3[vdd] | 0 | 5 | `a + 14/15` | -5.646402934059572412556 | derived-here-exact |
| C3[vdd].l6 | C3[vdd] | 0 | 6 | `23/9` | 2.5555555555555555555555 | derived-here-exact |
| C3[vdd].l7 | C3[vdd] | 0 | 7 | `-8/7` | -1.142857142857142857142 | derived-here-exact |
| C3[vdd].l8 | C3[vdd] | 0 | 8 | `0` | 0.0 | derived-here-exact |
| C3[vdd].l9 | C3[vdd] | 0 | 9 | `0` | 0.0 | derived-here-exact |
| C3[ddd].l2 | C3[ddd] | 0 | 2 | `3*gamma` | -132.0290521943033745711 | derived-here-exact |
| C3[ddd].l3 | C3[ddd] | 0 | 3 | `E - 2*V + 2*beta - 8` | -22.68221203187269069251 | derived-here-exact |
| C3[ddd].l4 | C3[ddd] | 0 | 4 | `3*A/2 - 3*E/2 + a/4 + 3*alpha/2 - p/2 + 2` | 26.148883491640811467192 | derived-here-exact |
| C3[ddd].l5 | C3[ddd] | 0 | 5 | `-6*A/5 - a + 3*p/5 - 27/10` | 5.4022641489205637774572 | derived-here-exact |
| C3[ddd].l6 | C3[ddd] | 0 | 6 | `a/2` | -3.289868133696452872944 | derived-here-exact |
| C3[ddd].l7 | C3[ddd] | 0 | 7 | `9/7` | 1.2857142857142857142857 | derived-here-exact |
| C3[ddd].l8 | C3[ddd] | 0 | 8 | `-1/2` | -0.5 | derived-here-exact |
| C3[ddd].l9 | C3[ddd] | 0 | 9 | `0` | 0.0 | derived-here-exact |
| C3[ddd].l10 | C3[ddd] | 0 | 10 | `0` | 0.0 | derived-here-exact |
| K4[base].l2 | K4[base] | 0 | 2 | `-6` | -6.0 | derived-here-exact |
| K4[base].l3 | K4[base] | 0 | 3 | `-4/3` | -1.333333333333333333333 | derived-here-exact |
| K4[base].l4 | K4[base] | 0 | 4 | `0` | 0.0 | derived-here-exact |
| K4[base].l5 | K4[base] | 0 | 5 | `0` | 0.0 | derived-here-exact |
| K4[v].l2 | K4[v] | 0 | 2 | `-a + c/2 - 4*z2` | -8.0 | derived-here-exact |
| K4[v].l3 | K4[v] | 0 | 3 | `8` | 8.0 | derived-here-exact |
| K4[v].l4 | K4[v] | 0 | 4 | `8/3` | 2.6666666666666666666666 | derived-here-exact |
| K4[v].l5 | K4[v] | 0 | 5 | `0` | 0.0 | derived-here-exact |
| K4[v].l6 | K4[v] | 0 | 6 | `0` | 0.0 | derived-here-exact |
| K4[d].l2 | K4[d] | 0 | 2 | `-a - f/8 - p + 8` | 26.427090464586201663306 | derived-here-exact |
| K4[d].l3 | K4[d] | 0 | 3 | `-2*a/3 + c/6 - 4*z2/3 + 8/3` | 2.1932454224643019152965 | derived-here-exact |
| K4[d].l4 | K4[d] | 0 | 4 | `8/3` | 2.6666666666666666666666 | derived-here-exact |
| K4[d].l5 | K4[d] | 0 | 5 | `14/15` | 0.9333333333333333333333 | derived-here-exact |
| K4[d].l6 | K4[d] | 0 | 6 | `0` | 0.0 | derived-here-exact |
| K4[d].l7 | K4[d] | 0 | 7 | `0` | 0.0 | derived-here-exact |
| K4[vv].l2 | K4[vv] | 0 | 2 | `-2*A + 4*a + f - 24*z2 - 16*z3 + 48` | -46.02656513017759186395 | derived-here-exact |
| K4[vv].l3 | K4[vv] | 0 | 3 | `4*a - 4*c/3 + 16*z2/3 + 16` | 19.787369953618918010960 | derived-here-exact |
| K4[vv].l4 | K4[vv] | 0 | 4 | `-12` | -12.0 | derived-here-exact |
| K4[vv].l5 | K4[vv] | 0 | 5 | `-88/15` | -5.866666666666666666666 | derived-here-exact |
| K4[vv].l6 | K4[vv] | 0 | 6 | `0` | 0.0 | derived-here-exact |
| K4[vv].l7 | K4[vv] | 0 | 7 | `0` | 0.0 | derived-here-exact |
| K4[vd].l2 | K4[vd] | 0 | 2 | `-2*A - E - L/4 - 3*a - f/8 + 2*p + q/2 + 12*z2 + 12*z3 + 8*z4` | None | derived-here-exact |
| K4[vd].l3 | K4[vd] | 0 | 3 | `-4*A/3 + 4*a/3 + c/6 + f/2 + 2*p - 16*z2/3 - 8*z3/3 + 16/3` | -39.11731719665620723959 | derived-here-exact |
| K4[vd].l4 | K4[vd] | 0 | 4 | `13*a/6 - c/2 + 2*z2 + 14/3` | 1.7004395543451570901838 | derived-here-exact |
| K4[vd].l5 | K4[vd] | 0 | 5 | `-16/5` | -3.2 | derived-here-exact |
| K4[vd].l6 | K4[vd] | 0 | 6 | `-32/15` | -2.133333333333333333333 | derived-here-exact |
| K4[vd].l7 | K4[vd] | 0 | 7 | `0` | 0.0 | derived-here-exact |
| K4[vd].l8 | K4[vd] | 0 | 8 | `0` | 0.0 | derived-here-exact |
| K4[dd].l2 | K4[dd] | 0 | 2 | `-2*E - M/4 - 2*V + 4*a - 112` | None | derived-here-exact |
| K4[dd].l3 | K4[dd] | 0 | 3 | `-4*A/3 - 4*E/3 - L/6 - 2*a/3 - f/12 + 4*p/3 + q/3 + 8*z2 + 8*z3 + 16*z4/3 - 112/3` | None | derived-here-exact |
| K4[dd].l4 | K4[dd] | 0 | 4 | `-A + a/2 + c/12 + f/4 + 4*p/3 - 2*z2/3 - 20/3` | -24.02140812103344273536 | derived-here-exact |
| K4[dd].l5 | K4[dd] | 0 | 5 | `16*a/15 - c/5 + 4*z2/5 + 8/15` | -1.969104765073851646437 | derived-here-exact |
| K4[dd].l6 | K4[dd] | 0 | 6 | `-46/45` | -1.022222222222222222222 | derived-here-exact |
| K4[dd].l7 | K4[dd] | 0 | 7 | `-4/5` | -0.8 | derived-here-exact |
| K4[dd].l8 | K4[dd] | 0 | 8 | `0` | 0.0 | derived-here-exact |
| K4[dd].l9 | K4[dd] | 0 | 9 | `0` | 0.0 | derived-here-exact |
| K4[vvv].l2 | K4[vvv] | 0 | 2 | `12*A + 3*L + 24*a - 6*alpha - 144*z2 - 144*z3 - 96*z4 + 576` | None | derived-here-exact |
| K4[vvv].l3 | K4[vvv] | 0 | 3 | `12*A - 8*a - 4*f + 48*z2 + 32*z3` | 182.47173353273335794118 | derived-here-exact |
| K4[vvv].l4 | K4[vvv] | 0 | 4 | `-14*a + 4*c - 8*z2 - 48` | -33.04316479128513104932 | derived-here-exact |
| K4[vvv].l5 | K4[vvv] | 0 | 5 | `96/5` | 19.2 | derived-here-exact |
| K4[vvv].l6 | K4[vvv] | 0 | 6 | `208/15` | 13.866666666666666666666 | derived-here-exact |
| K4[vvv].l7 | K4[vvv] | 0 | 7 | `0` | 0.0 | derived-here-exact |
| K4[vvv].l8 | K4[vvv] | 0 | 8 | `0` | 0.0 | derived-here-exact |
| K4[vvd].l2 | K4[vvd] | 0 | 2 | `-12*A + 4*E - L/2 - 3*L3/4 + M - 20*a - 6*alpha - 2*beta + 8*p + 168*z2 + 168*z3 + 132*z4 + 96*z5 - 592` | None | derived-here-exact |
| K4[vvd].l3 | K4[vvd] | 0 | 3 | `4*A + 4*E + 5*L/3 + 12*a - 4*alpha + f - 8*p/3 - 4*q/3 - 40*z2 - 112*z3/3 - 64*z4/3 + 80/3` | None | derived-here-exact |
| K4[vvd].l4 | K4[vvd] | 0 | 4 | `22*A/3 + a/3 - c - 2*f - 14*p/3 + 16*z2 + 8*z3 + 4` | 95.253826469299047423786 | derived-here-exact |
| K4[vvd].l5 | K4[vvd] | 0 | 5 | `-106*a/15 + 8*c/5 - 16*z2/5 - 316/15` | -5.433652724337790659091 | derived-here-exact |
| K4[vvd].l6 | K4[vvd] | 0 | 6 | `104/45` | 2.3111111111111111111111 | derived-here-exact |
| K4[vvd].l7 | K4[vvd] | 0 | 7 | `544/105` | 5.1809523809523809523809 | derived-here-exact |
| K4[vvd].l8 | K4[vvd] | 0 | 8 | `0` | 0.0 | derived-here-exact |
| K4[vvd].l9 | K4[vvd] | 0 | 9 | `0` | 0.0 | derived-here-exact |
| K4[vdd].l2 | K4[vdd] | 0 | 2 | `8*A - 6*E - M/4 - M21/2 + Q + 4*V + 32*a - 4*beta - 2*gamma - 8*p + 16*z2*z3 - 168*z2 - 168*z3 - 140*z4 - 144*z5 - 96*z6` | None | derived-here-exact |
| K4[vdd].l3 | K4[vdd] | 0 | 3 | `-20*A/3 + 8*E/3 - L/2 - L3/2 + M + 4*V - 10*a - 4*alpha - 8*beta/3 - f/12 + 4*p + q/3 + 64*z2 + 64*z3 + 148*z4/3 + 32*z5 - 736/3` | None | derived-here-exact |
| K4[vdd].l4 | K4[vdd] | 0 | 4 | `A + 13*E/3 + L + 29*a/6 - 3*alpha + c/12 + 5*f/6 - 2*p/3 - q - 44*z2/3 - 40*z3/3 - 8*z4 - 8` | None | derived-here-exact |
| K4[vdd].l5 | K4[vdd] | 0 | 5 | `68*A/15 + 5*a/3 - 2*c/3 - f - 10*p/3 + 76*z2/15 + 8*z3/5 + 36/5` | 42.055647076729609823316 | derived-here-exact |
| K4[vdd].l6 | K4[vdd] | 0 | 6 | `-17*a/5 + 2*c/3 - 4*z2/3 - 328/45` | 2.2223023311160220651727 | derived-here-exact |
| K4[vdd].l7 | K4[vdd] | 0 | 7 | `-8/21` | -0.380952380952380952380 | derived-here-exact |
| K4[vdd].l8 | K4[vdd] | 0 | 8 | `208/105` | 1.9809523809523809523809 | derived-here-exact |
| K4[vdd].l9 | K4[vdd] | 0 | 9 | `0` | 0.0 | derived-here-exact |
| K4[vdd].l10 | K4[vdd] | 0 | 10 | `0` | 0.0 | derived-here-exact |

Independent values: input.W = -37.708111514952555112588560 (and the full eps^0 log polynomials of C3_ddd, A3_ddd in out/C8/validation_targets_C8.json).

* **structural_zeros**: `{"top_log": "for a jet d_v^i d_delta^j of a normalized response of order n (C_n, K_n), [eps^0 l^k] = 0 for k > n - 1 + i + 2j; checked by the RG formulas (the predicted [l^(top+1)] vanishes identically) and on the phase-2 data", "raw_A7_d": "[eps^0 l^9] A7_d = 0 (note)", "pole_cancellation": {"source": "out/C8/poles_C8.json", "n_jets": 74, "n_new_jets": 28, "statement": "every [eps^p l^k], p < 0, of every normalized jet vanishes; the raw windows needed for the new jets are poles_C8.json -> raw_needed_for_new_jets (all log powers)"}, "below_tight_bound": "the 12 safe-minus-tight scalars below the tight bound (raw_requirements_C8.json -> safe_minus_tight) vanish"}`
* **data_dependent_RG**: `{"source": "out/C8/rg_logs_C8.json -> second_log_formulas, higher_log_formulas", "statement": "for every C/K jet of order n >= 5 used by the C8 inputs (incl. C9, d_delta C7, d_v K8, d_v^2 K6, d_v d_delta K6, d_delta^2 C5) the coefficients [eps^0 l^k], k = 2 .. top+1, are predicted from lower-order data (normalized C, K and E jets at log powers < k) and the beta inputs", "extra_normalized_atoms_for_the_second_log": ["EC3_1[v0d0]", "EC3_1[v0d1]", "EC3_1[v0d2]", "EC3_1[v1d0]", "EC3_1[v1d1]", "EC3_1[v2d0]", "EC5_1[v0d0]", "EC5_1[v0d1]", "EC5_1[v1d0]", "EC7_1[v0d0]", "EK4_1[v0d0]", "EK4_1[v0d1]", "EK4_1[v1d0]", "EK4_1[v1d1]", "EK4_1[v2d0]", "EK6_1[v0d0]", "EK6_1[v1d0]"], "validation": {"phase2_engine_checks": 79, "max_abs_pull": 2.618, "rms_pull": 0.7600614157410264, "source": "review/rg_logs_vs_engine_phase2.json"}, "l0_identity": "the [l^0] part of the same identity reproduces the recurrenc`
* **finite-cutoff cross-check quantities**: A3_ddd(1/8), Q4_vvv(1/8), Q4_vvd(1/8), Q4_vdd(1/8), EQ4_vd(1/8), EQ4_vv(1/8), A5_dd(1/8), EA5_d(1/8), Z6_d(1/10), Q6_vv(1/10), Q6_vd(1/10), EQ6_v(1/10), EZ6_base(1/10), A7_d(1/10), EA7_base(1/10), Q8_v(1/10), Z8_base(1/10), A9_base(1/10)
* **sealed (comparison step only)**: rational projections pi_0 of the ten inputs, R6, R8, R_tail, R9, C8^(0) = 88 and the raw rational scalars (note l.1176-1227); singular rational predictions of Q6_vd and Q8_v (note l.1236-1246); every C8-era decimal of the note Secs. 16-17 and of the archive records (comparison_C8/archive_C8_values.json)

### 10.5 Checks performed (archive-free)

* **normalization**: `{"generating_function_equals_note_and_explicit_product_rule": {"C3": true, "C5": true, "C7": true, "C9": true, "K2": true, "K4": true, "K6": true, "K8": true, "EC3": true, "EC5": true, "EC7": true, "EK2": true, "EK4": true, "EK6": true}}`
* **regression_vs_phase1**: `{"25_old_input_expansions_identical": true, "common_normalized_atoms_identical_leibniz_and_windows": true, "C7_part_of_requirements_identical_to_out/raw_requirements.json": true}`
* **note_F1_F4_structure**: `{"Ndelta: coefficient of Q6_vd[eps^0 l^1]": {"derived": "-4", "note_implied": "-4", "agree": true, "note": "N_delta = -4 P6 + ..., P6 = [eps^0 l] Q6_vd (eq:NdP6, l.1328-1331)"}, "Ndelta: coefficient of Q4_vvd[eps^0 l^0]": {"derived": "16", "note_implied": "16", "agree": true, "note": "(lambda4)_vd = -6 k_vd - 4 k_vvd + 2 e_d + 2 e_vd (l.1319-1321): -4 * (-4) = +16 on (Q4_vvd)_0"}, "Ndelta: coefficient of EQ4_vd[eps^0 l^0]": {"derived": "-8", "note_implied": "-8", "agree": true, "note": "same line: -4 * 2 = -8 on (EE Q4_vd)_0"}, "U: coefficient of A7_d[eps^0 l^1]": {"derived": "1", "note_implied": "1", "agree": true, "note": "U = A7_d_1 - Z6_d_1 + 2 (EE A5_d)_0 - 2 (EE Z4_d)_0 + D_lower (l.13`
* **trace_algebra**: `{"higher_terms_do_not_enter_T4 (22 generic monomials)": true, "full_jacobian_trace_equals_2uFu_plus_(1+z)Hz": true, "T2_T3_equal_phase1": true, "C8 = 8 T4 by eigenvalue expansion (no D5)": true, "note_eq:C8assembly_new_coefficients": true, "note_appendix_B_old_polynomial (61 terms)": true, "new_inputs_enter_linearly": true}`
* **rg_l0_identity_equals_recurrence_all_35**: `true`
* **rg_C3_jets_vs_three_kink_max_rel_diff**: `"1.33e-28"`
* **rg_note_checks**: `{"C3 l^2 = 2 (l.550)": true, "d_v C3 l^3 = -8/3, l^2 = -3 (l.2231-2234)": true, "d_delta C3 l^4 = -1, l^3 = -1, l^2 = -2 z2 (l.2263-2264; a = -4 z2)": true, "A3_dd/2 l^6..l^2 = phase-1 note-closed-forms relation (1/3, -1/15, -1/3 - a/4, 4/3 + a/6 + A/3 - p/3, E/2)": true, "K4 l^3 = -4/3, l^2 = -6 (l.551-552)": true}`
* **rg_vs_phase2_engine**: `{"n_checks": 79, "max_abs_pull": 2.618, "rms_pull": 0.7600614157410264}`
* **two_kink**: `{"phase1_Z2_Q2_atoms_identical": true, "EQ2_base_eps0_l0 = -2 z2 (phase-1 target EQ2.0.l0)": true, "EZ2_base_eps0 = -l^2 + 2 l + 2 z2 - 2 (phase-1 targets EZ2.0.l*)": true, "supports": "Z2 in {-1,0}, Q2 in {0,1}; EZ2, EQ2 start at eps^0 (no eps^-1: the below-tight-bound safe extras vanish)"}`
* **framework_cross_check**: `{"expansions_all_35_identical": true, "endpoint_two_kink_max_abs_difference": "9.4e-38"}`
* **W_independent_three_kink**: `{"value": "-37.7081115149525551125885600025", "definition": "W = C3_1[v0d3]/6 + 4 = d_delta^3 b3 / 6", "abs_accuracy": "1e-25 (dps 30 quadratures)"}`
* **framework_assembly_on_synthetic_data_max_rel_diff (35 inputs, C5..C8)**: `"3.41e-35"`
* **assembler_regression_test**: `"scripts/test_assembler_C8.py (synthetic): all six checks pass"`

### 10.6 Reference assembler

* **script**: scripts/assemble_from_raw_C8.py raw.json [--windows both|tight|safe] [--fill-two-kink-exact] [--out result.json]
* **layout**: plain {atom: {p: {k: value}}}, full derivatives, E = reflected first source derivative (as phase 1)
* **outputs**: all 35 inputs, D2..D4, C3..C7, B_old_C8, B_done_C8 (B_old + the six inherited-record terms), T4, C8 (= B_old + linear part, checked against 8 T4)
* **strictness**: as phase 1 (missing scalar = error; below-bound scalars must vanish; tight/safe agreement); in addition C3_1[v0d0] must equal 5 (the tree normalization b3(1,0) = 1 assumed by the invariant algebra)
* **compares_with**: nothing: the C8 claims are sealed in comparison_C8/

### 10.7 Extrapolations, ambiguities

* **lambda6**: lambda6 = -2 K6_0 - 4 v d_v K6_0 + 2 v EK6_0. Still not written in the note. It now enters K (old), Kv = -4 h8_v and J9 = b9 (through -2 v j1 h8); the other eight new inputs do not depend on it (exact test, definition_chain_C8.json -> lambda6_dependence). Support: the [l^0] part of the Callan-Symanzik identity of scripts/rg_logs_C8.py (response model F_H = h + sqrt2 b_h sum g^n N^n K_n, essential flow autonomous) gives exactly this lambda6 and the whole recurrence for all 35 inputs / framework/framework.md Sec. 3 derives lambda_n = -2 K_n0 - 4 v d_v K_n0 + 2 v E K_n0 from J0 beta = R1 / the note F3 decomposition K_v = -4 P8 + 16 X_vv - 8 X_E + S3 (l.1363) has exactly the coefficients this lambda6 implies (+16 on [eps^0 l^0] Q6_vv, -8 on [eps^0 l^0] d_v E Q6; definition_chain_C8.json).
* **lambda6**: lambda6 is used in h8 but not defined in the note; it now affects Kv and J9 as well as K. *Resolution:* see EXTRAPOLATIONS (derived from the response Jacobian / CS identity; the note F3 structure agrees).
* **raw-vs-normalized-leading-log**: The note leading log -2362/315 refers to the RAW d_delta A7, not to the normalized d_delta C7; products with Z2 ~ 1/eps mix positive-power raw logs into the normalized one. *Resolution:* target A7d.0.l8 is on the raw atom; the normalized jets have their own RG predictions.
* **inherited-six**: The note says W, S, L3, M21, M12, N2 enter the archive assembly as inherited numerical records without a reconstructed exact expression (l.1240-1252). *Resolution:* definitions here are the note dictionary only; W is computed independently (three-kink code); the other five need the engine. No archive record is used..
* **E-on-delta-derivatives**: d_delta acts on the endpoint factor as well as on the kernel (note l.421 "Tail derivatives also act on endpoint factors"). *Resolution:* raw_atoms integrands: sum_j binom(b,j) e_j * insertion(a,b-j).
* **reflection**: Only first source derivatives are needed (j7 = -2 d_v C7_0 + (E C7)_0, lambda6 with E K6); the reflected form is valid for all of them, with any d_v, d_delta. *Resolution:* either form.
* **b3-normalization**: The CS identity and the trace algebra use b3(1,0) = 1 (F = z + u + ...), which the input expansions write as C3_1[v0d0] - 4; they agree because C3_1[v0d0] = 5 (note l.550). Data that violate it give inputs and invariants on different footings (the framework then differs from the spec assembler). *Resolution:* the C8 assembler rejects data with |C3_1[v0d0] - 5| > agree-tol.
* **structural-zeros**: As in phase 2, some needed scalars are exact zeros (e.g. A3 at eps^-1 l^1, eps^3 l^1, Z4 eps^-2 l^1; every EZ2/EQ2 eps^-1). They must be supplied explicitly. *Resolution:* two_kink_exact_C8.json; A3 closed form of framework/review_gate_phase2.

