# Clean-room exact Rayleigh–Schrödinger check of the 2D LRI Hamiltonian-truncation coefficients

This directory holds an independent implementation of the computation defined in `../SPEC.md`:
the eps-Taylor coefficients C_0..C_8 of Delta_eps(eps; L) = E_2 − E_0 for the truncated
GFF + phi^2 + phi^4 Hamiltonian in d = 2, in the three schemes raw / consistent / literal.
Everything below was derived from SPEC.md alone. No other code, notes or numerical values were used.

Contents:

| file | role |
|---|---|
| `ref_fraction.py` | reference implementation: `fractions.Fraction`, full J=0 sector (both reflection parities), operators built by expanding `:phi^k:` over **ordered** tuples of modes and applying ladder operators one at a time |
| `fast_modular.py` | production implementation: the same RS recursion in the reflection-even orbit basis, vertices from the closed multiset formula (sec. 4), exact arithmetic modulo 72 primes near 2^23, then CRT and rational reconstruction verified on 8 held-out primes |
| `closed_forms.py` | closed forms at order eps^2: E_v^(2)(L), S_p(L), C_2(L) (sec. 9) |
| `diag_check.py` | non-perturbative check: the Hermitian truncated Hamiltonian is built at numeric eps in the orthonormal basis with a third, pairwise matrix-element formula, diagonalised in mpmath (110 digits) by shifted inverse iteration, and compared with the series (residual must be O(eps^9)) |
| `export_results.py` | writes `results/<scheme>_L<L>.json` and runs the exact cross-checks |
| `make_tables.py` | prints the Markdown tables of sec. 12 from `results/` |
| `run_*.sbatch` | Slurm wrappers used on symmetry |
| `results/` | one JSON per (scheme, L) |
| `raw_out/` | raw outputs of the cluster runs (fast_modular JSON per (L, K), Fraction reference JSON) |
| `logs/` | Slurm logs and diag-check logs copied back from symmetry |

---------------------------------------------------------------------------------------------------

## 1. Model and conventions

x = x(eps) = 1/2 − eps/4. Modes m = (a, b), a, b ≥ 0, with level |m| = a + b, angular momentum
J_m = a − b and weight w_m(x) = (x)_a (x)_b / (a! b!). On the unit circle

  phi(theta) = sum_m sqrt(w_m) ( e^{+i J_m theta} A_m^dag + e^{−i J_m theta} A_m ).

Check of the normalisation: <0|phi(t1) phi(t2)|0> = sum_{a,b} w_ab z^a zbar^b with z = e^{i(t2−t1)},
= (1−z)^{−x} (1−zbar)^{−x} = |1 − z|^{−2x} = |2 sin((t1−t2)/2)|^{−2x}, as stated in the spec.

H0 = sum_m n_m (x + |m|) = N + P x, M = <:phi^2:>_theta, V = <:phi^4:>_theta / 12,
H(eps) = H0 + r(eps) M + g(eps) V + D, r = sum_{k≥1} r_k eps^k, g = sum_{k≥1} g_k eps^k.

Space at cutoff l: occupation states with total J = sum n_m J_m = 0, level N = sum n_m |m| ≤ l, fixed
field parity (−1)^P, reflection-even. J = 0 forces N even (N ≡ J mod 2).

## 2. Fock basis, sectors, reflection

* **J = 0**: the theta average of e^{i(J_created − J_annihilated) theta} is the Kronecker delta, so M and V
  conserve J; only J = 0 states are kept.
* **Parity**: M and V change P by 0, ±2 (M) or 0, ±2, ±4 (V); the even-P and odd-P sectors are separate.
  References p = 0, 2 live in the even sector, p = 1, 3 in the odd sector.
* **Reflection** R: (a, b) → (b, a). Since w_ab = w_ba, R maps phi(theta) to phi(−theta) and commutes with the
  theta-averaged vertices, with H0 and with D. The references |p> (zero modes only) are R-invariant, so
  every RS vector stays in the reflection-even subspace. `ref_fraction.py` therefore simply works in the
  full J = 0 space (the odd states are never populated), while `fast_modular.py` uses the orbit basis
  e_o = m + R m (|o| = 2) or e_o = m (|o| = 1). If m_o is the representative of o, then

    K_{o'o} = (|o| / |o'|) · sum_{m'' in o'} H_{m'', m_o},

  which is what `fast_modular.py` accumulates (each generated transition m_o → m'' contributes
  H_{m'',m_o} |o|/|o'(m'')|). Both codes give identical exact results (sec. 11), which checks this reduction.
* **Particle cap**: the level cutoff does not bound P (zero modes are free). The channel with reference |p>
  keeps P ≤ p + K; K = 16 is exact through eps^8 (sec. 8).

## 3. Similarity frame with rational matrix elements

sqrt(w_m(x)) is irrational, so work with H~ = S^{-1} H S, S = prod_m w_m^{N_m / 2} (N_m the number operator),
and the unnormalised monomial basis |n) = prod_m (A_m^dag)^{n_m} |0>. Then

  S^{-1} sqrt(w_m) A_m^dag S = A_m^dag,   S^{-1} sqrt(w_m) A_m S = w_m A_m,

so H~ is built from phi~(theta) = sum_m ( e^{iJ theta} A_m^dag + w_m e^{−iJ theta} A_m ); in the monomial basis
A^dag raises with coefficient 1 and A lowers with coefficient n. All entries are polynomials in eps with
rational coefficients. Both S and the monomial normalisation are diagonal in the occupation basis, so they
commute with P_l, H0, D and the sector projectors; for each eps the spectra of P_l H P_l and P_l H~ P_l
coincide, and because w_00 ≡ 1 the reference vectors |p> are unchanged. Hence the eigenvalue branch through
|p>, and every Taylor coefficient of it, is the same. RS for the non-symmetric H~ uses the left reference
vector e_p^T (H0 is diagonal), see sec. 6.

## 4. Vertex matrix elements

Write :phi~^k: = sum_{c=0}^{k} C(k, c) (phi~^−)^c (phi~^+)^{k−c}, phi~^− = sum_m e^{iJ_m theta} A_m^dag,
phi~^+ = sum_m w_m e^{−iJ_m theta} A_m. A term with created multiset S (|S| = c, multiplicities s_m) and
annihilated multiset T (|T| = k − c, multiplicities t_m) arises from c!/prod s_m! ordered creation tuples and
(k−c)!/prod t_m! ordered annihilation tuples; prod_m A_m^{t_m} on |n) gives prod n_m!/(n_m − t_m)!. The theta
average imposes J(S) = J(T). Therefore, for |n') = |n − T + S),

  (n' | :phi~^k:_theta | n) = k! · prod_m [ w_m(x)^{t_m} · C(n_m, t_m) / s_m! ],

and with the normalisations of the spec

  M : (n'|M|n) = 2 prod_m w_m^{t_m} C(n_m, t_m) / s_m!,      V : (n'|V|n) = (4!/12) prod (…) = 2 prod_m w_m^{t_m} C(n_m, t_m) / s_m!.

Examples: (p|M|p) = 2p, (p|V|p) = p(p−1)/2 on the zero-mode states.

Three different constructions are used:
* `fast_modular.py`: the closed formula above (sub-multisets T of the occupied modes × precomputed tables of
  created multisets S by (|S|, J, level)).
* `ref_fraction.py`: no formula; literally the sum over ordered annihilation tuples (applying A one at a
  time, coefficient n) and ordered creation tuples, with weight C(k, c) prod w.
* `diag_check.py`: orthonormal basis, pairwise: for states n, n' put S0 = (n' − n)_+, T0 = (n − n')_+ and sum
  over spectator multisets U (annihilated and recreated), S = S0 + U, T = T0 + U, |S| + |T| = k:

    <n'| :phi^k:_theta |n> = k! sum_U prod_m w_m^{(s_m + t_m)/2} sqrt(n_m! n'_m!) / ( (n_m − t_m)! s_m! t_m! ).

## 5. eps expansion of the Hamiltonian

(x + i)/(i + 1) = ((2i + 1)/2 − eps/4)/(i + 1), so (x)_a/a! = prod_{i<a} (2(2i+1) − eps)/(4(i+1)) and w_ab(eps)
is a polynomial of degree a + b with rational coefficients. Writing M(eps) = sum_j eps^j M_j,
V(eps) = sum_j eps^j V_j and D = sum_{k≥2} eps^k D_k (diagonal),

  H~(eps) = H0(0) + sum_{k≥1} eps^k W_k,       H0(0) = N + P/2,
  W_k = −δ_{k1} P/4 + sum_{j=0}^{k−1} ( r_{k−j} M_j + g_{k−j} V_j ) + D_k.

M_j and V_j with j ≤ 7 are needed for W_1..W_8.

## 6. Rayleigh–Schrödinger recursion (full order, no 2n+1 rule)

Reference |p>, E^(0) = p/2. **Non-degeneracy**: for a state k of the same sector,
E_k^(0) − p/2 = N_k + (P_k − p)/2 with N_k even and P_k ≡ p (mod 2); it vanishes only if N_k = 0 and P_k = p,
i.e. k = |p> (the unique level-0 state with p quanta). So the resolvent R = Q/(p/2 − H0) has the integer
denominators −(N_k + (P_k − p)/2) and is well defined (Q = 1 − |p><p|).

With intermediate normalisation <p|psi_n> = 0 (n ≥ 1), psi_0 = |p>, order n of (H~ − E)psi = 0 gives

  RHS_n = sum_{k=1}^{n} W_k psi_{n−k} − sum_{k=1}^{n−1} E^(k) psi_{n−k},
  E^(n) = <p| RHS_n,         psi_n = R Q RHS_n.

E^(8) needs psi_0..psi_7 and all of them are computed in full (every component inside the truncated
space, no pruning, no Wigner 2n+1 shortcut). psi_8 does not enter E^(8) in this formulation and is
therefore not computed.

## 7. Tuning order by order, and the schemes

Because w_00 ≡ 1, the zero-mode diagonal elements are eps independent: <p|M_j|p> = 2p δ_{j0},
<p|V_j|p> = p(p−1)/2 δ_{j0}, and D(0) = 0. Hence r_n and g_n enter E_p^(n) only through W_n psi_0:

  E_p^(n) = X_p^(n) + 2p r_n + p(p−1)/2 g_n,

where X_p^(n) is RHS_n[p] evaluated with r_n = g_n = 0 (it contains only r_k, g_k, D_k with k < n, plus
r_{n−j} M_j, g_{n−j} V_j with j ≥ 1). With x_1 = −1/4, x_n = 0 (n ≥ 2), the conditions
E_1 − E_0 = x and E_3 − E_0 = 2 − x give at each order n ≥ 1

  r_n = ( x_n − X_1 + X_0 ) / 2,       g_n = ( −x_n − X_3 + X_0 − 6 r_n ) / 3,
  C_n = X_2 − X_0 + 4 r_n + g_n.

(determinant 2·3 − 0·6 = 6 ≠ 0.) Order 1: X_p = −p/4, so r_1 = 0, g_1 = 1/3, C_1 = −1/2 + 1/3 = −1/6 for
every L, as required.

**Schemes.** Every Hamiltonian uses the same r(eps), g(eps), determined from the primaries at cutoff L.

* raw: D = 0. Channels: p = 0..3 at L.
* consistent: channels = the vacua at every l = 0, 2, …, L, each in its own corrected Hamiltonian
  P_l(H0 + rM + gV)P_l + D_l, D_l(N) = E_v(l) − E_v(l − N), plus p = 1, 2, 3 at L in the same corrected
  Hamiltonian at L; E_0 = E_v(L).
* literal: channels = raw vacua at every l (D = 0), plus p = 0..3 at L with D_L(N) = E_v^raw(L) − E_v^raw(L − N).

**Ordering within one order n** (all channels advance together):
1. RHS_n with r_n = g_n = 0 for every channel; the D_k needed there have k ≤ n − 1 (D_n multiplies psi_0,
   which sits at level 0 where D vanishes).
2. Vacuum channels: E_v^(n)(l) = RHS_n[0] exactly at this point, since <0|M_0|0> = <0|V_0|0> = 0, so the
   vacuum at order n does not depend on r_n, g_n.
3. r_n, g_n from the p = 0, 1, 3 channels at cutoff L; C_n.
4. Add r_n M_0 psi_0 + g_n V_0 psi_0 to every RHS_n, record E^(n), form psi_n.
5. D_n(l, N) = E_v^(n)(l) − E_v^(n)(l − N) is now known for every l, ready for order n + 1.

This makes the consistent scheme's self-consistency (E_v(l) of the Hamiltonian that already contains D_l)
exact order by order: E_v starts at eps^2, so D starts at eps^2.

## 8. Particle-number cap (exactness through eps^8)

Each W_k is of order ≥ eps (r, g start at eps; D at eps^2; −P/4 at eps), and changes P by at most 4
(V: 0, ±2, ±4; M: 0, ±2; D and P diagonal). A contribution to E_p^(n) is a closed path |p> → … → |p> with at
most n vertices; its highest point is at most p + 4·floor(n/2). For n = 8: P ≤ p + 16, reached by
four creation-only V vertices followed by four annihilation-only ones (all at order eps via g_1 V_0), which
exist at every L (zero modes alone suffice). Hence:

* the relative cap K = 16 (P ≤ p + 16 in the channel of |p>; vacua: P ≤ 16) is exact for all E^(n ≤ 8),
  r_n, g_n, C_n, vacua;
* K = 14 must differ, and first at order 8.

Demonstrated for every L ≤ 16 (sec. 11): K = 18 (all L ≤ 16) and K = 20 (L ≤ 12) reproduce the K = 16
rationals identically (every C, r, g, E_p and vacuum coefficient), while K = 14 changes C_8 and nothing below.
The Fraction reference also gives identical results for K = 16 and K = 18 at L ≤ 8. L = 18 was run only with
K = 16 and relies on the L-independent argument above.

## 9. Closed forms at order eps^2

At order 2 only W_1 = −P/4 + V_0/3 matters (r_1 = 0), and the diagonal −P/4 drops out of the second-order
sum, so S_p := E_p^(2) − 2p r_2 − p(p−1)/2 g_2 = sum_k |<k|V_0/3|p>|^2 / (p/2 − E_k^(0)) (Hermitian basis).

Split phi = phi_0 + phi' into the zero mode phi_0 = A_00 + A_00^dag and the rest. Acting on |p> only the
creation part of phi' survives, so V|p> = (1/12) sum_{m=0}^{4} C(4, m) :phi_0^{4−m}: [ (phi'^−)^m ]_theta |p>.
The intermediate state has q zero modes and m non-zero quanta at level N (energy q/2 + m/2 + N), and the
squared matrix element factorises:

  S_p = −(1/1296) sum_{m=0}^{4} C(4,m)^2 sum_q Z_{m,q}(p) sum_{N ≤ L} F_m(N) / (N + (q − p + m)/2),  (m, q) ≠ (0, p),

  Z_{m,q}(p) = |<q| :phi_0^{4−m}: |p>|^2 = C(k, j)^2 p! q! / ((p − k + j)!)^2,  k = 4 − m, q = p + 2j − k,

  F_m(N) = m! [u^{N/2} v^{N/2}] ( (1−u)^{−1/2} (1−v)^{−1/2} − 1 )^m
         = m! sum_{i=0}^{m} C(m, i) (−1)^{m−i} ( (i/2)_{N/2} / (N/2)! )^2.

(F_m(N) is the norm of the theta-averaged m-quantum state at level N; with x = 1/2,
sum_ab w_ab u^a v^b = (1−u)^{−1/2}(1−v)^{−1/2}.) The order-2 tuning gives r_2 = −s_1/2, g_2 = s_1 − s_3/3 and

  **C_2(L) = s_2 − s_1 − s_3/3**,   s_p = S_p − S_0.

**Vacuum.** For p = 0 all terms combine into the full norm of <:phi^4:>_theta|0> at level N,
4! [u^{N/2} v^{N/2}] (1−u)^{−2}(1−v)^{−2} = 24 (N/2 + 1)^2, with energy N + 2:

  **E_v^(2)(L) = −(1/1296) sum_{n=0}^{L/2} 24 (n+1)^2 / (2(n+1)) = −(L + 2)(L + 4) / 864**

(the same in every scheme, since D first acts on the vacuum at eps^4).

Values (exact): C_2(0) = 17/81, C_2(2) = 19/72, C_2(4) = 179/640, C_2(6) = 833719/2903040,
C_2(8) = 54170191/185794560, C_2(10) = 1203434671/4087480320, C_2(12) = 252028633693/850195906560,
C_2(14) = 4052830189501/13603134504960. Order-2 check by hand at L = 0: S_0 = −1/108, S_1 = −13/108,
S_2 = −79/108, S_3 = −89/36 gives C_2(0) = 17/81.

The closed form is cheap at any L; it converges like 1/L, and Richardson extrapolation of
L = 800 … 25600 gives C_2(∞) ≈ 0.30806541358 (not used anywhere else; quoted only as an aside).

## 10. Where the schemes start to differ (derived, then confirmed)

* D_l(N) = O(eps^2) and D(0) = 0, so D enters E_p only between two other vertices: the first contribution is
  <p|W_1 R D_2 R W_1|p> at **eps^4**. Raw vs consistent/literal therefore first differ at **C_4**
  (r_4, g_4 and E_p^(4) differ too).
* Raw and consistent vacua agree through eps^3 (same argument for the vacuum), so the consistent and literal
  D agree through eps^3 and differ at eps^4. That difference first reaches E_p at order 1 + 4 + 1 = **eps^6**.
  Consistent vs literal therefore first differ at **C_6** (and in r_6, g_6, E_p^(6)).

Both statements hold for every L > 0 in the exact results. At L = 0 all three schemes coincide identically
(D_0 ≡ 0).

## 11. Exact arithmetic and validation

* `ref_fraction.py`: exact `Fraction` arithmetic throughout. Run for L = 0, 2, …, 12 (K = 16) and
  L ≤ 8 (K = 18). At L = 10 it takes 5 minutes on one core.
* `fast_modular.py`: every quantity is computed modulo 72 primes q < 2^23 (int64 sparse products cannot
  overflow: row length × q^2 < 2^63 is asserted). Chinese remaindering over 64 primes gives a modulus of about
  10^443, and rational reconstruction gives |num|, den ≤ sqrt(modulus/2). Every reconstructed rational is
  then verified against the 8 unused primes. The largest rational (numerator digits + denominator digits)
  has 204 digits at L = 14 and 258 at L = 18, so the margin is ample. Agreement with the Fraction code for
  every number at L ≤ 12 confirms the reconstruction directly. Wall time on one 64-core AMD node: about 1 s
  per L up to L = 10, 14 s at L = 12, 81 s at L = 14, 6 min at L = 16, and 17 min at L = 18 (24 workers).

Checks (all pass; details in `results/*.json` → `checks` and in sec. 12):

1. C_0 = 1, C_1 = −1/6, r_1 = 0, g_1 = 1/3 for every L and scheme.
2. C_2(L) equals the closed form of sec. 9 for every L and scheme; E_p^(2) − 2p r_2 − p(p−1)/2 g_2 = S_p(L)
   for p = 0..3; E_v^(2)(l) = −(l+2)(l+4)/864 for every vacuum.
3. Tuning identities E_1 − E_0 = x, E_3 − E_0 = 2 − x hold exactly at all orders; C = E_2 − E_0.
4. `fast_modular` = `ref_fraction` identically for every C, r, g, E_p and vacuum coefficient
   (two independent operator constructions, reflection reduction vs full J = 0 space, Fraction vs modular).
5. Particle cap: K = 16 vs 18 (vs 20) identical, K = 14 differs first at C_8 (sec. 8).
6. Non-perturbative check (`diag_check.py`: third construction, Hermitian orthonormal basis, P ≤ p + 24
   (L ≤ 4) or p + 20 (L = 6), 110-digit mpmath, shifted inverse iteration plus Rayleigh quotient). The exact
   series r(eps), g(eps) and E_v(l)(eps) are inserted into the Hamiltonian, and the eigenvalues are computed
   at eps = 1e−3, 1e−5 and 1e−8. They reproduce the tuning conditions, every E_p series, the Delta series and
   every vacuum series. The residual R(eps) divided by eps^9 tends to a constant as eps → 0 (e.g. L = 4,
   consistent, Delta: −35019.8, −35043.13, −35043.36). An error δ in any eps^8 coefficient would add
   δ/eps to R/eps^9, i.e. 1e8·δ at eps = 1e−8, so every coefficient through eps^8 is confirmed to
   |δ| ≲ 1e−8. Done for L = 0, 2, 4 (Kdiag 24) and L = 6 (Kdiag 20; 443/463-dimensional sectors), all
   schemes, every channel; all pass. Example at L = 6, consistent, R_Delta/eps^9 = −52327.9, −52373.07 and
   −52373.51 at the three eps. The logs are in `logs/diag_*_L{0,2,4}.log` and `logs/diag_v2_*_L6.log`.
7. Scheme differences appear first at C_4 (raw vs consistent) and C_6 (consistent vs literal), as derived.

## 12. Results

All cutoffs L = 0, 2, …, 18 were computed **exactly** (rational numbers), for all three schemes: the
requested L = 0..14 and, as an extra, L = 16 and 18. No floating-point arithmetic was needed, so the
"high-precision floating" fallback was not used. Every number in `results/*.json` is an exact rational
(string). The `*_float` fields are those rationals rounded to double precision.

| L | reflection-even states (even / odd sector, K = 16) | full J=0 states | V nonzeros (even sector) | exact via |
|---|---|---|---|---|
| 0 | 10 / 10 | 10 / 10 | 41 | Fraction reference + modular (identical) |
| 2 | 28 / 29 | 28 / 29 | 269 | Fraction reference + modular (identical) |
| 4 | 88 / 92 | 105 / 110 | 1733 | Fraction reference + modular (identical) |
| 6 | 259 / 273 | 357 / 377 | 9354 | Fraction reference + modular (identical) |
| 8 | 772 / 818 | 1203 / 1277 | 46823 | Fraction reference + modular (identical) |
| 10 | 2198 / 2339 | 3719 / 3962 | 212299 | Fraction reference + modular (identical) |
| 12 | 6217 / 6638 | 11134 / 11897 | 889912 | Fraction reference + modular (identical) |
| 14 | 16973 / 18180 | 31551 / 33810 | 3444644 | modular (CRT + verified reconstruction) |
| 16 | 45355 / 48729 | 86413 / 92869 | 12459472 | modular (CRT + verified reconstruction) |
| 18 | 117789 / 126945 | 228068 / 245842 | 42377990 | modular (CRT + verified reconstruction) |

The tables below give C_n rounded to 16 significant digits. The exact rationals are in the JSON files. Example (L = 14):
C_2 = 4052830189501/13603134504960 in every scheme; C_4(raw) = 28393875020715706171653467696528910724367/
9509405883363376253087346044788801536000.

**raw** (exact rationals in `results/raw_L<L>.json`; floats below are the rationals rounded)

| L | C_2 | C_3 | C_4 | C_5 | C_6 | C_7 | C_8 |
|---|---|---|---|---|---|---|---|
| 0 | 0.2098765432098765 | -0.3591678097850937 | 1.366437196226862 | -6.614619888818012 | 39.57285833251968 | -275.2245057531179 | 2150.062543744354 |
| 2 | 0.2638888888888889 | -0.4523533950617284 | 1.705181630801326 | -9.814448980947629 | 64.308054553649 | -493.4069591330721 | 4262.4835402156 |
| 4 | 0.2796875 | -0.5349641022858797 | 2.0339591987416 | -12.16722629450343 | 84.93068524007323 | -687.6536141515722 | 6270.127253784335 |
| 6 | 0.2871882578262787 | -0.5903301684422997 | 2.305134105212472 | -14.03801283436162 | 101.6917090460711 | -852.6419820928468 | 8044.850754582982 |
| 8 | 0.2915596183225171 | -0.6293596476853364 | 2.525876798381225 | -15.57557348138863 | 115.62246060869 | -993.4524450440877 | 9600.048603322704 |
| 10 | 0.2944196856708047 | -0.6583267501538553 | 2.706936135593405 | -16.87078480436969 | 127.4433927270064 | -1115.067054768191 | 10968.79416109304 |
| 12 | 0.2964359528767195 | -0.6807145699637507 | 2.857999678795397 | -17.98037203790623 | 137.652736971282 | -1221.436560640821 | 12182.94049842055 |
| 14 | 0.2979335525957822 | -0.6985706342065742 | 2.985872657974411 | -18.94492129994541 | 146.5947384291834 | -1315.515134966029 | 13268.70768015148 |
| 16 | 0.299089688332686 | -0.7131706320802813 | 3.095663602806875 | -19.79300955290829 | 154.5190854838515 | -1399.542210628951 | 14247.14074593466 |
| 18 | 0.3000091339608719 | -0.7253497702780002 | 3.191025875788506 | -20.54627569257611 | 161.6096712435778 | -1475.224417872434 | 15134.95433366229 |

**consistent** (exact rationals in `results/consistent_L<L>.json`; floats below are the rationals rounded)

| L | C_2 | C_3 | C_4 | C_5 | C_6 | C_7 | C_8 |
|---|---|---|---|---|---|---|---|
| 0 | 0.2098765432098765 | -0.3591678097850937 | 1.366437196226862 | -6.614619888818012 | 39.57285833251968 | -275.2245057531179 | 2150.062543744354 |
| 2 | 0.2638888888888889 | -0.4523533950617284 | 1.705674600622999 | -9.812407442881785 | 64.30971655553829 | -493.420491204029 | 4262.49698117575 |
| 4 | 0.2796875 | -0.5349641022858797 | 2.034869272829963 | -12.1643724615812 | 84.93272703434197 | -687.690167139803 | 6270.278877673589 |
| 6 | 0.2871882578262787 | -0.5903301684422997 | 2.306457230994448 | -14.03471504876836 | 101.6952407430931 | -852.7094595947319 | 8045.252975729627 |
| 8 | 0.2915596183225171 | -0.6293596476853364 | 2.527614950485046 | -15.57203629232749 | 115.6286983614567 | -993.5587315188708 | 9600.80381868634 |
| 10 | 0.2944196856708047 | -0.6583267501538553 | 2.709091946729079 | -16.86714519732541 | 127.4533747551847 | -1115.220116410551 | 10969.99340588526 |
| 12 | 0.2964359528767195 | -0.6807145699637507 | 2.860575563376496 | -17.9767304490653 | 137.6673561993592 | -1221.643713172778 | 12184.66667452825 |
| 14 | 0.2979335525957822 | -0.6985706342065742 | 2.988870684723028 | -18.94135543382845 | 146.6147475527296 | -1315.783194240792 | 13271.03548371568 |
| 16 | 0.299089688332686 | -0.7131706320802813 | 3.099085520609257 | -19.78958173628117 | 154.5451342940529 | -1399.877348845486 | 14250.13838232427 |
| 18 | 0.3000091339608719 | -0.7253497702780002 | 3.194873166191791 | -20.54303724687485 | 161.6423192722781 | -1475.632311601669 | 15138.68382342731 |

**literal** (exact rationals in `results/literal_L<L>.json`; floats below are the rationals rounded)

| L | C_2 | C_3 | C_4 | C_5 | C_6 | C_7 | C_8 |
|---|---|---|---|---|---|---|---|
| 0 | 0.2098765432098765 | -0.3591678097850937 | 1.366437196226862 | -6.614619888818012 | 39.57285833251968 | -275.2245057531179 | 2150.062543744354 |
| 2 | 0.2638888888888889 | -0.4523533950617284 | 1.705674600622999 | -9.812407442881785 | 64.30971427327059 | -493.4205097212686 | 4262.496926947592 |
| 4 | 0.2796875 | -0.5349641022858797 | 2.034869272829963 | -12.1643724615812 | 84.93271892369181 | -687.6902260115428 | 6270.278722694786 |
| 6 | 0.2871882578262787 | -0.5903301684422997 | 2.306457230994448 | -14.03471504876836 | 101.6952231943182 | -852.7095772055833 | 8045.252677598907 |
| 8 | 0.2915596183225171 | -0.6293596476853364 | 2.527614950485046 | -15.57203629232749 | 115.6286676683868 | -993.558924760984 | 9600.803328848224 |
| 10 | 0.2944196856708047 | -0.6583267501538553 | 2.709091946729079 | -16.86714519732541 | 127.4533271439651 | -1115.220401178885 | 10969.99267004508 |
| 12 | 0.2964359528767195 | -0.6807145699637507 | 2.860575563376496 | -17.9767304490653 | 137.6672878479815 | -1221.644104620128 | 12184.66563279741 |
| 14 | 0.2979335525957822 | -0.6985706342065742 | 2.988870684723028 | -18.94135543382845 | 146.6146546035475 | -1315.783706939178 | 13271.03407170761 |
| 16 | 0.299089688332686 | -0.7131706320802813 | 3.099085520609257 | -19.78958173628117 | 154.5450128620899 | -1399.877996897756 | 14250.13653150546 |
| 18 | 0.3000091339608719 | -0.7253497702780002 | 3.194873166191791 | -20.54303724687485 | 161.6421654509737 | -1475.633108722737 | 15138.68146186535 |

**r_n, g_n (consistent scheme)**

| L | r_2 | r_3 | r_4 | r_5 | r_6 | r_7 | r_8 |
|---|---|---|---|---|---|---|---|
| 0 | 0.05555555556 | 0.1687242798 | 0.09005868008 | 0.3276417326 | -1.177073376 | 8.16378152 | -60.01089005 |
| 2 | 0.1041666667 | 0.4225501543 | 0.5221652003 | 1.023455263 | -2.999057962 | 20.94346776 | -181.57413 |
| 4 | 0.1519097222 | 0.6833544319 | 1.005652022 | 1.906094571 | -5.112626037 | 37.90874731 | -353.5527971 |
| 6 | 0.1993815104 | 0.9505928027 | 1.529713559 | 2.912073702 | -7.459374238 | 57.20974733 | -561.8005223 |
| 8 | 0.2467346191 | 1.223090176 | 2.086310833 | 4.012879941 | -9.970869686 | 78.05170558 | -797.1574642 |
| 10 | 0.2940254211 | 1.499959959 | 2.669779135 | 5.185012859 | -12.64883712 | 99.78545892 | -1054.051529 |
| 12 | 0.3412795067 | 1.780550805 | 3.276210518 | 6.415833302 | -15.46888727 | 122.1019758 | -1328.410536 |
| 14 | 0.3885101527 | 2.064372444 | 3.90264321 | 7.694509026 | -18.43076225 | 144.7023841 | -1617.577514 |
| 16 | 0.4357249282 | 2.351045206 | 4.546831178 | 9.01421771 | -21.52287633 | 167.4273296 | -1919.42248 |
| 18 | 0.4829284621 | 2.640267453 | 5.206966616 | 10.36886598 | -24.7451764 | 190.1086151 | -2232.485121 |

| L | g_2 | g_3 | g_4 | g_5 | g_6 | g_7 | g_8 |
|---|---|---|---|---|---|---|---|
| 0 | 0.7098765432 | 0.4093507087 | 1.226690969 | -3.945987694 | 27.12231873 | -195.5841594 | 1577.7084 |
| 2 | 0.9953703704 | 1.239904835 | 2.349257687 | -4.850520947 | 38.07497339 | -318.5467387 | 2839.906502 |
| 4 | 1.146354167 | 1.734158639 | 3.22628856 | -5.127310108 | 47.38234285 | -422.4292768 | 3979.332269 |
| 6 | 1.249754395 | 2.105555061 | 3.959714653 | -5.170464906 | 54.48184089 | -507.3897388 | 4940.345561 |
| 8 | 1.328508472 | 2.408475892 | 4.596303657 | -5.079994915 | 60.04363017 | -577.5688253 | 5749.492053 |
| 10 | 1.39214295 | 2.666516792 | 5.159926795 | -4.929452287 | 64.41777381 | -636.7783604 | 6436.62393 |
| 12 | 1.445543019 | 2.89243652 | 5.667809652 | -4.741080035 | 67.93286436 | -687.5414507 | 7026.876004 |
| 14 | 1.4915512 | 3.094040526 | 6.130988517 | -4.534965518 | 70.76740707 | -731.8145123 | 7539.148248 |
| 16 | 1.531968411 | 3.276501268 | 6.557809214 | -4.31827063 | 73.07693399 | -770.9182313 | 7988.09706 |
| 18 | 1.568008064 | 3.443445337 | 6.954195389 | -4.098385528 | 74.95453752 | -805.9009918 | 8384.769901 |

**First order at which the schemes differ** (C; r; g; E_0..E_3)

| L | raw vs consistent | consistent vs literal |
|---|---|---|
| 0 | none; none; none; none; none; none; none | none; none; none; none; none; none; none |
| 2 | 4; 4; 4; 4; 4; 4; 4 | 6; 6; 6; 6; 6; 6; 6 |
| 4 | 4; 4; 4; 4; 4; 4; 4 | 6; 6; 6; 6; 6; 6; 6 |
| 6 | 4; 4; 4; 4; 4; 4; 4 | 6; 6; 6; 6; 6; 6; 6 |
| 8 | 4; 4; 4; 4; 4; 4; 4 | 6; 6; 6; 6; 6; 6; 6 |
| 10 | 4; 4; 4; 4; 4; 4; 4 | 6; 6; 6; 6; 6; 6; 6 |
| 12 | 4; 4; 4; 4; 4; 4; 4 | 6; 6; 6; 6; 6; 6; 6 |
| 14 | 4; 4; 4; 4; 4; 4; 4 | 6; 6; 6; 6; 6; 6; 6 |
| 16 | 4; 4; 4; 4; 4; 4; 4 | 6; 6; 6; 6; 6; 6; 6 |
| 18 | 4; 4; 4; 4; 4; 4; 4 | 6; 6; 6; 6; 6; 6; 6 |


## 13. Spec reading, ambiguities and remarks

I found no genuine ambiguity or inconsistency in SPEC.md. These are the points where a reading had to be
fixed, with the one used:

1. **Reflection-even sector.** H commutes with R and every reference and D is R-even, so restricting to the
   reflection-even subspace or not gives identical eigenvalue branches. Both versions are run and agree
   exactly.
2. **r, g at smaller cutoffs.** As the spec says, r(eps), g(eps) are fixed once, by tuning the primaries at
   cutoff L, and reused in every vacuum Hamiltonian at l < L (consistent and literal). Hence the consistent
   vacua E_v(l < L) reported in `consistent_L<L>.json` depend on L through r, g; they are not the vacua of
   a run with cutoff l.
3. **Literal scheme.** E_0 is the p = 0 eigenvalue of the corrected Hamiltonian at L. It differs from the
   raw vacuum E_v^raw(L) (listed under `vacua`) from eps^4 on. Both are reported.
4. **"E_p analytically connected to |p>".** |p> is non-degenerate in its sector at eps = 0 (sec. 6), so the
   branch is unique and RS gives its Taylor series. The non-perturbative diagonalisation (check 6) picks
   the eigenvalue by inverse iteration from |p> with shift at the series value and confirms it.
5. **psi_1 … psi_8.** In the standard RS formulation used here, E^(8) = <p|sum_k W_k psi_{8−k}> involves
   psi_0 … psi_7 only; these are computed in full. psi_8 is not needed for anything reported. No 2n+1 or
   Wigner rule is used anywhere.
6. **D on level-0 states.** D_l(0) = E_v(l) − E_v(l) = 0, so zero-mode states (including |p>) get no shift.
   That is what keeps <p|W_n|p> independent of D and makes the order-by-order solve well founded (sec. 7).
7. **Particle cap.** The spec leaves the cap to the implementer. A cap relative to the reference
   (P ≤ p + 16) is used and proven exact (sec. 8). An absolute cap P ≤ 19 for both sectors would be
   equivalent for these observables.

Physics remarks (not problems with the spec):
* The series alternates in sign and grows roughly like n! (|C_8/C_7| ≈ 8–10). This is expected for an
  asymptotic eps-expansion.
* For L ≥ 2, the scheme differences are small (relative 10^-4 at C_8) and enter exactly at the orders
  predicted in sec. 10.
* C_2(L) approaches C_2(∞) ≈ 0.308065 like 1/L (sec. 9). It is not compared with the continuum two-loop
  result, which is outside this check.

## 14. Reproducing

Local (seconds): `python3 closed_forms.py 18`, `python3 export_results.py raw_out/fast_L<L>_K16.json --refdir raw_out
--outdir results --capcheck raw_out/fast_L<L>_K14.json raw_out/fast_L<L>_K18.json [raw_out/fast_L<L>_K20.json]`,
`python3 make_tables.py`.

Cluster (symmetry, Slurm, venv `~/indep2d_rs/venv`: Python 3.11, numpy 2.4.6, scipy 1.17.1, mpmath 1.4.1 + gmpy2,
python-flint 0.9.0; work dir `<SCRATCH>/indep2d/rs_exact/{code,out,logs,results}`):

| job id | name | partition | what | log |
|---|---|---|---|---|
| 571685 | indep2d-rs-test | amddebugq | fast_modular L = 0..12, K = 16, 40+8 primes (first test; outputs superseded by 571689) | logs/test_fast_571685.log |
| 571686 | indep2d-rs-ref | amddebugq | ref_fraction L = 0..8, K = 16 and 18, all schemes | logs/ref_small_571686.log |
| 571689 | indep2d-rs-prodK16 | amdq | fast_modular L = 0..16, K = 16, 64+8 primes (production) | logs/prod_K16_571689.log |
| 571690 | indep2d-rs-L18 | amdq | fast_modular L = 18, K = 16, 64+8 primes, 24 workers | logs/prod_L18_571690.log |
| 571691 | indep2d-rs-capchk | amdq | fast_modular L = 0..16 with K = 14 and K = 18 | logs/capchk_571691.log |
| 571692 | indep2d-rs-capK20 | amdq | fast_modular L = 0..12 with K = 20 | logs/capK20_571692.log |
| 571693 | indep2d-rs-ref810 | amdq | ref_fraction L = 8, 10, K = 16 | logs/ref_L8_L10_571693.log |
| 571694 | indep2d-rs-ref8K18 | amdq | cancelled by me while pending (redundant with 571686) | – |
| 571696 | indep2d-rs-diag024 | amddebugq | diag_check L = 0, 2, 4 at eps = 1e−3, 5e−4 (first version) | logs/diag_L024_571696.log, logs/diag_old_eps/ |
| 571697 | indep2d-rs-diag68 | amdq | cancelled by me while pending (replaced by 571702) | – |
| 571702 | indep2d-rs-diag6 | amdq | diag_check L = 6 with the first (slow, re-factorising) LU code; cancelled by me after 571722 finished (its partial logs agree) | logs/diag_L6_571702.log, logs/diag_*_L6.log |
| 571709 | indep2d-rs-diag024b | amddebugq | diag_check L = 0, 2, 4, Kdiag = 24, eps = 1e−3, 1e−5, 1e−8 | logs/diag_L024b_571709.log, logs/diag_*_L{0,2,4}.log |
| 571713 | indep2d-rs-ref12 | amdq | ref_fraction L = 12, K = 16 | logs/ref_L12_571713.log |
| 571722 | indep2d-rs-diag6v2 | amddebugq | diag_check L = 6, Kdiag = 20, eps = 1e−3, 1e−5, 1e−8 (LU factorised once) | logs/diag_L6v2_571722.log, logs/diag_v2_*_L6.log |

Per-run timing and memory: `logs/time_fast_L<L>_K<K>.txt` (GNU time), and `logs/ref_<scheme>_L<L>_K<K>.log`.

