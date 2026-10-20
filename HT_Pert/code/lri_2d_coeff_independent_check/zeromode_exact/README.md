# Exact zeromode window scheme for the 2D LRI Hamiltonian truncation (reference oracle)

This directory defines the "zeromode" window scheme precisely and computes it **exactly** (rational
numbers) through eps^8 for L = 0, 2, ..., 18. The results are meant as the reference oracle for a later
implementation in the production solver. The model and conventions are those of `../SPEC.md`; the solver is
an extension of `../rs_exact/` (copied here, the originals untouched). The non-perturbative cross-check
adapts `../cauchy/` (copied into `np_check/`, untouched).

| file | role |
|---|---|
| `zeromode_modular.py` | production solver: exact RS with degenerate partners, all channels (z, l) in lock step, modulo 88 primes, CRT + rational reconstruction checked on 8 held-out primes; has a `consistent` mode (regression vs `../rs_exact`) and a `garbage` mode (closure test) |
| `zeromode_fraction.py` | independent second implementation in `fractions.Fraction` (ordered-tuple operators of `ref_fraction_orig.py`, full J=0 space, one basis per cutoff, explicit B-equation by Gaussian elimination) |
| `bookkeeping.py` | which (z, order) of E_z(l) enter C_0..C_8 (sec. 3) |
| `degeneracy.py` | exact degeneracy analysis of the channels |z> (sec. 4); output `results/degeneracy.json` |
| `closed_form_dC4.py` | exact closed form of C_4(zeromode) − C_4(consistent) (sec. 7, check b) |
| `np_check/` | non-perturbative check: `zm_point.py` (hierarchy at complex eps), `run_zm_points.py`, `zm_cauchy.py` (Cauchy coefficients vs exact); `basis.py hamil.py solve.py cauchy.py run_points.py` are unmodified copies of `../cauchy/` |
| `export_results.py`, `make_tables.py`, `compare_frac_mod.py` | write `results/zeromode_L<L>.json` running all exact checks; tables; Fraction-vs-modular comparison |
| `fast_modular_orig.py`, `ref_fraction_orig.py` | unmodified copies of `../rs_exact/fast_modular.py`, `../rs_exact/ref_fraction.py` |
| `jobs/` | Slurm scripts used on symmetry; `logs/` their logs; `raw_out/` raw solver outputs |
| `results/zeromode_L<L>.json` | **the oracle**: C, r, g, E_p, the full E_z(l) table, all exact (strings) + floats, and the checks |

---------------------------------------------------------------------------------------------------------

## 1. Definition implemented

Everything not mentioned is as in `../SPEC.md` (GFF on the unit circle, x = 1/2 − eps/4,
w_ab = (x)_a (x)_b/(a! b!), M = <:phi^2:>_theta, V = <:phi^4:>_theta/12, J = 0 reflection-even sectors, level
cutoff N <= l, H0 = N + P x, r(eps), g(eps) without eps^0 terms, tuning E_1 − E_0 = x and E_3 − E_0 = 2 − x
at cutoff L, observable C_n of E_2 − E_0).

* For an occupation state s let **z_s = n_00(s)** (its number of (0,0) quanta) and N_s its level. The zero-mode
  number and the level are reflection invariant, so D is well defined on the reflection-even orbit basis.
* In the Hamiltonian at cutoff l the window is diagonal,

      D_l(s) = E_{z_s}(l) − E_{z_s}(l − N_s)   (N_s >= 2),      D_l(s) = 0   (N_s = 0).

* **E_z(l)** is the eigenvalue of H_l = P_l (H0 + r M + g V) P_l + D_l on the branch analytically connected to
  |z> = (A_00^dag)^z/sqrt(z!)|0> (sec. 4: the branch is unique for every z). H_l contains D_l, which contains
  E_{z'}(l) for all z' at the same cutoff: the E_z(l) are defined **self-consistently** (all z at once at each
  l, and recursively in l through E_{z'}(l − N)), exactly like the consistent scheme's vacua.
* One r(eps), g(eps) for every Hamiltonian, fixed by the tuning on the primaries at cutoff L. The primary
  E_p is E_{z=p}(L) (p = 0..3: level-0 states, so D = 0 on them); E_0 = E_{z=0}(L).

Points that had to be fixed (none is a genuine ambiguity):
1. The definition requires E_z(l) for every z that occurs on a level >= 2 state (non-perturbatively, up to the
   particle cap). Through eps^8 only z <= 14 at limited orders enters (sec. 3); the oracle tabulates exactly
   those. Non-perturbatively (np_check) the full hierarchy over every z on the circle was solved (sec. 8),
   and also a hierarchy truncated at z <= 14; both reproduce the exact series.
2. The caller's remark "z = 0 reproduces the consistent window exactly" holds for the **form** of the window on
   states without zero modes, D_l(0, N) = E_0(l) − E_0(l − N); but E_0(l) here is the vacuum of the
   zeromode-corrected Hamiltonian, which equals the consistent vacuum E_v(l) only through eps^3 (eps^4 for
   l = 0) and differs from eps^4 on (checked exactly).
3. As in the consistent scheme, the E_z(l) at l < L depend on L through r and g; they are not the values of a
   run at cutoff l.

## 2. Perturbative structure (as in ../rs_exact, similarity frame)

H~ = S^{-1} H S with S = prod_m w_m^{N_m/2} has polynomial-in-eps rational matrix elements in the monomial
basis (w_00 = 1, so |z> is unchanged), H~(eps) = H0(0) + sum_k eps^k W_k with

    W_k = −delta_{k1} P/4 + sum_{j<k} ( r_{k−j} M_j + g_{k−j} V_j ) + D_k,     D_k(s) = E_{z_s}^(k)(l) − E_{z_s}^(k)(l − N_s).

r_1 = 0 and g_1 = 1/3 in every scheme (order 1 is window independent); D starts at eps^2. Because w_00 = 1,
<z|M_j|z> = 2z delta_j0, <z|V_j|z> = z(z−1)/2 delta_j0 and D vanishes on |z>, so r_n, g_n enter E_z^(n)
only through 2z r_n + z(z−1)/2 g_n; the tuning formulas of ../rs_exact sec. 7 are unchanged:
r_n = (x_n − X_1 + X_0)/2, g_n = (−x_n − X_3 + X_0 − 6 r_n)/3, C_n = X_2 − X_0 + 4 r_n + g_n.

## 3. Which E_z(l) and which orders are needed (z range and order bookkeeping)

Cost counting for a contribution to E_z^(n) (a closed path |z> -> ... -> |z>):
* every off-diagonal hop costs >= eps^1 (g = O(eps), r = O(eps^2)); V changes P by <= 4, M by <= 2; diagonal
  pieces (−P/4, diagonal of V, D) do not change P;
* D^(k) acts only on level >= 2 states, never on |z>, so it needs a hop in and a hop out: **D^(k) enters
  E_z^(n) only for k <= n − 2**;
* a level >= 2 state s that carries D^(k) inside a term of total order n has
  P_s <= z + 4 floor((n − k)/2), hence **z_s <= P_s − 1 <= z + 4 floor((n − k)/2) − 1**;
* degenerate partners (sec. 4) bring a resolvent G_B = O(eps^-1); but B is never adjacent to |z>, every
  passage through B costs at least one net order (entry hop + exit hop − 1), and B states have P < z, so
  B-visits neither raise the reachable particle number nor make a D insertion cheaper than k + 2. The bounds
  above hold unchanged (the garbage, sharpness and cap tests below confirm it exactly);
* the particle numbers visited by E_z^(n) satisfy P <= z + 4 floor(n/2) (channel cap).

Closure from the primaries (z = p <= 3 at n = 8), `bookkeeping.py`:

| z | highest order k_max of E_z^(k)(l) that enters C_0..C_8 | channel cap P <= | degenerate partner levels |
|---|---|---|---|
| 0..4 | 6 | z + 12 | none |
| 5, 6 | 6 | 17, 18 | 2 |
| 7, 8 | 4 | 15, 16 | 2 |
| 9, 10 | 4 | 17, 18 | 2, 4 |
| 11, 12 | 2 | 15, 16 | 2, 4 |
| 13, 14 | 2 | 17, 18 | 2, 4, 6 |
| >= 15 | never enters | – | – |

Largest z needed at order k: {2: 14, 3: 10, 4: 10, 5: 6, 6: 6}. The primaries need order 8 with P <= p + 16.
So **D through eps^8 needs E_z for z <= 14, not 19.** (P <= 19 is the largest particle number of a primary
channel, reached only at the midpoint of an order-8 path, where no order is left for a D insertion; the first
D^(2) on the way up to P = 15 with a single (1,1) quantum has z_s = 14.) Example of the extreme term:
|3> -> |7> -> |11> -> (1,1) + 14 zero modes (three g_1 V_0 hops), D^(2)(14, 2), three hops back: order 8 in E_3.

Demonstrated exactly (sec. 6):
* **garbage test**: D^(k)(z_s) for every (z_s, k) outside the table above replaced by random residues (per
  prime): every C, r, g, E_p and E_z(l) unchanged, L = 0..18;
* **sharpness** (L = 4): dropping z = 14 at order 2, or z = 10 at order 4, or z = 6 at order 6, changes C_8 and
  g_8 (and only those); adding z = 15 or one more order for every z changes nothing
  (`python3 zeromode_modular.py --L 4 --tiers 0-6:6,7-10:4,11-13:2 --variants zeromode,garbage --nprimes 40
  --ncheck 6 --out x.json`, likewise `0-6:6,7-9:4,10:3,11-14:2`, `0-5:6,6:5,7-10:4,11-14:2`,
  `0-6:6,7-10:4,11-14:2,15:2`, `0-6:7,7-10:5,11-14:3`; seconds each);
* **extended table**: z <= 6 to order 8, z <= 10 to 6, z <= 14 to 4, z <= 18 to 2 (caps up to P <= 22):
  identical results (L <= 14);
* **cap test**: every channel cap raised by 2: identical (L <= 16).

## 4. Degeneracy analysis (`degeneracy.py`, `results/degeneracy.json`)

At eps = 0 a J = 0 state of the same field parity is degenerate with |z> (energy z/2) iff N + P/2 = z/2, i.e.
P = z − 2N. N = 0 is |z> itself. N >= 2 (even) needs P = z − 2N >= 1 (a level >= 2 state holds a non-zero
quantum), so **partners exist iff z >= 5**, at levels N = 2, 4, ..., N <= (z − 1)/2 (and N <= l). The partner
block B_N(z) = {level N, P = z − 2N}; reflection-even dimensions (full J=0 dimensions in brackets):

| z | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 |
|---|---|---|---|---|---|---|---|---|---|---|
| N = 2 | 1 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 |
| N = 4 | – | – | – | – | 1 | 4 (5) | 6 (8) | 7 (9) | 7 (9) | 7 (9) |
| N = 6 | – | – | – | – | – | – | – | – | 1 | 6 (8) |

(N = 2: (1,1) + (z−5) zero modes and, for z >= 6, (1,0)+(0,1) + (z−6) zero modes; N = 4: e.g. (2,2) + (z−9)
zero modes, (1,1)^2 + (z−10), (2,1)+(1,2) + (z−10), ...). The solver's partner sets coincide with these
dimensions for every z <= 18, l <= 10 (`check_partner_sets.py`).

**The primaries p = 0..3 (and z = 4) are never degenerate.**

First order. W_1 = −P/4 + V_0/3 (r_1 = 0). Exact facts, checked for z <= 24:
1. **W_1 has no matrix element between |z> and any partner**: from level 0 to level N >= 2 with P -> P − 2N
   would need annihilating >= 2N + 1 zero modes and creating a level-N quantum, i.e. more than 4 ladder
   operators (V_0|z> applied explicitly: no partner reached). The same holds for every W_k (M, V have at most
   4 operators; D is diagonal), so the reference never couples directly to B at any order.
2. Blocks with different N are not coupled by W_1 (they differ in P by a multiple of 4 and in level in the
   opposite direction, impossible for a 4-operator vertex), so W_1 restricted to the degenerate space is
   diag(e1(z), W_1|B_2, W_1|B_4, ...), e1(z) = <z|W_1|z> = −z/4 + z(z − 1)/6.
3. **e1(z) is never an eigenvalue of W_1|B_N**: the exact determinants det(W_1|B_N − e1) are nonzero for all
   60 blocks with z <= 24 (full J=0 and reflection-even). The smallest separation is 7/3 (z = 5, N = 2); for
   N = 2 it is (4z − 13)/3; the N = 4, 6 blocks are separated by >= 10 (z = 9, N = 4). Smallest separations
   for z <= 14: z = 5: 7/3; 6: 11/3; 7: 5; 8: 19/3; 9: 23/3 (N=2), 10 (N=4); 10: 9, 38/3; 11: 31/3, 46/3;
   12: 35/3, 18; 13: 13, 62/3, 23 (N=6); 14: 43/3, 70/3, 27.

Hence the degeneracy is lifted at first order for every z, the branch through |z> is unique and analytic
(the matrix is similar to a real symmetric one for real eps), and its leading eigenvector is exactly |z>.
No case where the lifting fails or the "state connected to |z>" is ambiguous was found, so nothing had to be
guessed.

## 5. Algorithm (degenerate RS, all channels in lock step)

Channel (z, l): reference |z>, space = reflection-even J=0 states with N <= l and P <= cap(z) (sec. 3);
P0 = |z><z|, B = partners (sec. 4), Q' = the rest; R' = (z/2 − H0)^{-1} on Q' (integer denominators, never 0).
With intermediate normalisation <z|psi_n> = 0, the order-n equation (H0 − z/2) psi_n + sum_{k=1}^n
(W_k − E^(k)) psi_{n−k} = 0 is split:

* on Q':  psi_n^{Q'} = R' [ sum_{k=1}^n (W_k − E^(k)) psi_{n−k} ]_{Q'};
* on B (where H0 − z/2 = 0) it determines the B-part of the PREVIOUS order:

      (E^(1) − W_1^{BB}) psi_{n−1}^B = P_B [ W_1 psi_{n−1}^{Q'} + sum_{k=2}^{n} (W_k − E^(k)) psi_{n−k} ];

  G_B = (E^(1) − W_1^{BB})^{-1} exists by sec. 4. P_B W_n psi_0 = 0 (fact 1), so this needs neither r_n, g_n
  nor E^(n);
* on |z>:  E^(n) = <z| sum_k W_k psi_{n−k} > (the B part of psi_{n−1} does not contribute, fact 1).

Order n for one channel: (i) RHS_n = sum_k W_k psi_{n−k} − sum_{k<n} E^(k) psi_{n−k} with r_n = g_n = 0 and
psi_{n−1}^B still zero; (ii) solve the B equation for psi_{n−1}^B, add (W_1 − E^(1)) psi_{n−1}^B to RHS_n and
assert that its B part now vanishes and its |z> part is unchanged; (iii) after the tuning, add
r_n M_0|z> + g_n V_0|z>, read E^(n) = RHS_n[z], set psi_n = R' RHS_n (zero on z and B).
All channels advance together: at order n every active channel (k_max(z) >= n) does (i)-(ii), the primaries
(z = p, l = L) give X_p and hence r_n, g_n, every channel does (iii), and the new E_z^(n)(l) fill the table
from which D^(n) is formed for the next orders. Self-consistency is exact order by order because E_z^(n) needs
D^(k) only for k <= n − 2.

Implementation (`zeromode_modular.py`): the structure / vertex code of ../rs_exact/fast_modular.py with the
states sorted by (level, P), so that cutoff l is a leading block (sliced CSR matrices per l); D_k is
assembled per state from a table T[k][z, l]; G_B by Gauss-Jordan mod q (|B| <= 15); all arithmetic modulo
88 primes q < 2^23 (int64 sparse products asserted overflow free), CRT over 80 primes (554-digit modulus),
rational reconstruction, verification on 8 held-out primes. Largest rational: see the results table (sec. 9),
far below the reconstruction bound. Channels: z = 0..14 at every l = 0, 2, ..., L (z <= 3 at l = L are the
primaries, order 8, cap p + 16) — 15 (L/2 + 1) channels.

## 6. Exact checks (all pass; per-L flags in `results/zeromode_L<L>.json` -> `checks`)

| check | L |
|---|---|
| C_0 = 1, C_1 = −1/6, r_1 = 0, g_1 = 1/3; tuning identities at every order; C = E_2 − E_0; E_p = table entry E_{z=p}(L) | all |
| (a) **identical to consistent through eps^3** (C, r, g, E_0..E_3); **first difference at eps^4** in C, r, g and every E_p (L >= 2); identical at L = 0 (D_0 = 0) | all |
| (b) **C_4 − C_4(consistent), r_4 − r_4(cons), g_4 − g_4(cons) equal the exact closed form** of the order-eps^2 zero-mode window term (sec. 7) | all |
| C_2 = closed form; E_0(l) = consistent vacuum through eps^3 | all |
| identical to the independent Fraction implementation (every C, r, g, E_p, E_z(l)) | 0..10 |
| this code in `consistent` mode = ../rs_exact consistent results (C, r, g, E_p, vacua) | 0..6 |
| (d) garbage test (closure of sec. 3) | 0..18 |
| (d) every channel cap raised by 2 | 0..16 |
| (d) extended z / order table (and garbage outside it) | 0..14 |
| (c) non-perturbative Cauchy integral, all C, r, g, E_p and every tabulated E_z^(k)(l) | 0..6 |

## 7. Check (b): closed form of the eps^4 difference (`closed_form_dC4.py`)

Second order: E_z^(2)(l) = 2z r_2 + z(z−1)/2 g_2 + S_z(l), S_z(l) = (1/9) sum_s |<s|V_0|z>|^2/(z/2 − E_s) (no
partner appears, fact 1). Factorising phi = phi_0 + phi' (../rs_exact sec. 9):

    S_z(l) = −(1/1296) sum_{m=0}^4 C(4,m)^2 sum_q Zm(q|z) sum_{N<=l} F_m(N) / (N + (q − z + m)/2),
    Zm(q|z) = C(k,j)^2 z! q!/((z − k + j)!)^2 (k = 4 − m, q = z − k + 2j),
    F_m(N) = m! sum_i C(m,i)(−1)^{m−i} ((i/2)_{N/2}/(N/2)!)^2.

Both schemes agree through eps^3; at eps^4 the only difference is the order-2 window inside
<p|W_1 R D_2 R W_1|p>, with D'(q, N) = [S_q(L) − S_0(L)] − [S_q(L − N) − S_0(L − N)] (r_2, g_2 cancel):

    dE_p^(4) = (1/1296) sum_{m>=1} C(4,m)^2 sum_q Zm(q|p) sum_N F_m(N) D'(q, N)/(N + (q − p + m)/2)^2,
    dC_4 = dE_2 − dE_1 − dE_3/3 + dE_0/3,  dr_4 = (dE_0 − dE_1)/2,  dg_4 = (dE_0 − dE_3 − 6 dr_4)/3.

This is the construction of `../continuum/zero_mode_window.py`, here in exact arithmetic and at small L. It
equals the exact RS difference **identically (as rationals) for every L computed**, for dC_4, dr_4 and dg_4;
and its values agree with `../continuum/zm_corrected_fits.txt` (dC4zm, 8 digits) at every L = 2..30 printed
there: dC_4 = 0.112489998 (L=2), 0.115839940 (4), 0.112332521 (6), 0.108893845 (8), 0.106191025 (10),
0.104142557 (12), 0.102595620 (14), 0.101423756 (16), 0.100533480 (18), 0.099857094 (20), 0.098343060 (30).

## 8. Check (c): non-perturbative hierarchy + Cauchy integral (`np_check/`)

At each eps_k = rho e^{2 pi i k/K} the finite problem is solved without perturbation theory: unknowns
r, g and E_z(l) for z = 0..Zh, l = 0..L; for each (parity, l) ONE matrix A_{par,l} = P_l(H0 + rM + gV)P_l +
diag(D_s) built from the current E's (D_s = 0 for z_s > Zh); E_z(l) must equal the eigenvalue of
A_{z%2,l} on the branch through |z>; plus the two tuning equations. Newton's method on all unknowns at once with
the exact Hellmann-Feynman Jacobian (d lambda/dr = v^T M v/v^T v, d lambda/dg = v^T V v/v^T v,
d lambda_{z,l}/dE_{z'}(l') = sum_{s: z_s = z'} v_s^2 ([l' = l] − [l' = l − N_s])/v^T v), eigenpairs by
complex-symmetric Rayleigh-quotient iteration warm-started from the previous eigenvector (degenerate partners
are no problem: at eps != 0 they are split by O(eps)). The branch through |z> is selected by radial
continuation t eps, t = 0.25 ... 1 (variant: 0.1 ... 1) from the first-order guess and the unit vectors |z>,
in double precision; the final point is refined in python-flint (320 or 384 bits) to |F| < 2^-(prec-24).
Particle cap P <= 19 (P <= 21 in a variant); with Zh = cap − 1 every zero-mode number that occurs on a level
>= 2 state is self-consistent (the full hierarchy).

Radius. The high-z branches have small radii of convergence (E_18 with cap 19: R ~ 1/60, found in a double-
precision scan: at rho = 1/64 the Cauchy coefficients of E_18(L) stall at 3e-5, at 1/128 they decay, at 1/256
they reach the rounding floor by n = 16). The production circle is therefore rho = 1/256, K = 128 (half the
points + conjugation symmetry), 320 bits.

Variants: base (Zh = 18, rho = 1/256, K = 128, 320 bits, cap 19), zh14 (hierarchy truncated at z <= 14),
rhoK (rho = 1/400, K = 96), prec (384 bits), path (10 radial steps), cap21 (cap 21, Zh = 20).
Every run is compared with the exact rationals: C_0..8, r, g, E_0..3 (orders 0..8) and every tabulated
E_z^(k)(l) (k <= k_max(z), all z <= 14 and l <= L, including all degenerate channels). Results in sec. 9.

## 9. Results

All of L = 0, 2, ..., 18 were computed **exactly**; every number in `results/zeromode_L<L>.json` is an exact
rational (string; `*_float` = the rational rounded to double). Every check of sec. 6 passes at every L where it
was run. Coverage: garbage test L = 0..18; cap + 2 test L = 0..16; extended table (+ garbage) L = 0..14;
Fraction implementation L = 0..10; consistent-mode regression L = 0..6; non-perturbative Cauchy L = 0..6
(every C, r, g, E_p and every tabulated E_z^(k)(l)); closed form (b) every L.

| L | reflection-even states (even / odd, P <= 18 / 19) | channels (z,l) | max num+den digits | CRT modulus digits | wall on one 64-core AMD node (88 primes) |
|---|---|---|---|---|---|
| 0 | 10 / 10 | 15 | 29 | 554 | 1 s |
| 2 | 28 / 29 | 30 | 76 | 554 | 1 s |
| 4 | 88 / 92 | 45 | 94 | 554 | 1 s |
| 6 | 259 / 273 | 60 | 116 | 554 | 1 s |
| 8 | 772 / 818 | 75 | 148 | 554 | 2 s |
| 10 | 2198 / 2339 | 90 | 162 | 554 | 4 s |
| 12 | 6217 / 6638 | 105 | 182 | 554 | 15 s |
| 14 | 16973 / 18180 | 120 | 212 | 554 | 69 s |
| 16 | 45355 / 48729 | 135 | 256 | 554 | 4.5 min (40 workers) |
| 18 | 117789 / 126945 | 150 | 266 | 554 | 10.2 min (16 workers, 12.7 GB parent RSS) |

**C_2..C_8, zeromode next to consistent** (consistent = `../rs_exact/results/consistent_L<L>.json`; 13
significant digits; exact rationals in the JSON):

| L | scheme | C_2 | C_3 | C_4 | C_5 | C_6 | C_7 | C_8 |
|---|---|---|---|---|---|---|---|---|
| 0 | zeromode | 0.2098765432099 | -0.3591678097851 | 1.366437196227 | -6.614619888818 | 39.57285833252 | -275.2245057531 | 2150.062543744 |
| 0 | consistent | 0.2098765432099 | -0.3591678097851 | 1.366437196227 | -6.614619888818 | 39.57285833252 | -275.2245057531 | 2150.062543744 |
| 2 | zeromode | 0.2638888888889 | -0.4523533950617 | 1.818164598337 | -10.92480809839 | 78.1015930332 | -683.927295295 | 7117.341822554 |
| 2 | consistent | 0.2638888888889 | -0.4523533950617 | 1.705674600623 | -9.812407442882 | 64.30971655554 | -493.420491204 | 4262.496981176 |
| 4 | zeromode | 0.2796875 | -0.5349641022859 | 2.150709212807 | -13.36502659371 | 100.5979173761 | -912.3856103652 | 9764.002061295 |
| 4 | consistent | 0.2796875 | -0.5349641022859 | 2.03486927283 | -12.16437246158 | 84.93272703434 | -687.6901671398 | 6270.278877674 |
| 6 | zeromode | 0.2871882578263 | -0.5903301684423 | 2.418789752333 | -15.19093160806 | 117.0386988832 | -1076.646373841 | 11586.71448249 |
| 6 | consistent | 0.2871882578263 | -0.5903301684423 | 2.306457230994 | -14.03471504877 | 101.6952407431 | -852.7094595947 | 8045.25297573 |
| 8 | zeromode | 0.2915596183225 | -0.6293596476853 | 2.636508795404 | -16.67024052448 | 130.2708887121 | -1208.849709403 | 13033.07315093 |
| 8 | consistent | 0.2915596183225 | -0.6293596476853 | 2.527614950485 | -15.57203629233 | 115.6286983615 | -993.5587315189 | 9600.803818686 |
| 10 | zeromode | 0.2944196856708 | -0.6583267501539 | 2.815282971293 | -17.91344855448 | 141.3915633342 | -1320.710265434 | 14257.56689349 |
| 10 | consistent | 0.2944196856708 | -0.6583267501539 | 2.709091946729 | -16.86714519733 | 127.4533747552 | -1115.220116411 | 10969.99340589 |
| 12 | zeromode | 0.2964359528767 | -0.6807145699638 | 2.964718120611 | -18.97971177296 | 150.9823733852 | -1417.994994618 | 15329.41687079 |
| 12 | consistent | 0.2964359528767 | -0.6807145699638 | 2.860575563376 | -17.97673044907 | 137.6673561994 | -1221.643713173 | 12184.66667453 |
| 14 | zeromode | 0.2979335525958 | -0.6985706342066 | 3.091466304875 | -19.90869535445 | 159.3948898938 | -1504.058135266 | 16285.50352497 |
| 14 | consistent | 0.2979335525958 | -0.6985706342066 | 2.988870684723 | -18.94135543383 | 146.6147475527 | -1315.783194241 | 13271.03548372 |
| 16 | zeromode | 0.2990896883327 | -0.7131706320803 | 3.200509276236 | -20.72757832058 | 166.8696610757 | -1581.137403275 | 17149.08759877 |
| 16 | consistent | 0.2990896883327 | -0.7131706320803 | 3.099085520609 | -19.78958173628 | 154.5451342941 | -1399.877348845 | 14250.13838232 |
| 18 | zeromode | 0.3000091339609 | -0.725349770278 | 3.295406645898 | -21.45674823519 | 173.577701775 | -1650.818879291 | 17936.10951447 |
| 18 | consistent | 0.3000091339609 | -0.725349770278 | 3.194873166192 | -20.54303724687 | 161.6423192723 | -1475.632311602 | 15138.68382343 |

**zeromode − consistent** (both exact; C_4 difference = the closed form of sec. 7 exactly):

| L | C_4(zm) - C_4(cons) | C_5 diff | C_6 diff | C_7 diff | C_8 diff | C_8 rel. diff |
|---|---|---|---|---|---|---|
| 0 | +0 | +0 | +0 | +0 | +0 | +0.000 |
| 2 | +0.1124899977 | -1.112400656 | +13.79187648 | -190.5068041 | +2854.844841 | +0.670 |
| 4 | +0.11583994 | -1.200654132 | +15.66519034 | -224.6954432 | +3493.723184 | +0.557 |
| 6 | +0.1123325213 | -1.156216559 | +15.34345814 | -223.9369142 | +3541.461507 | +0.440 |
| 8 | +0.1088938449 | -1.098204232 | +14.64219035 | -215.2909779 | +3432.269332 | +0.357 |
| 10 | +0.1061910246 | -1.046303357 | +13.93818858 | -205.490149 | +3287.573488 | +0.300 |
| 12 | +0.1041425572 | -1.002981324 | +13.31501719 | -196.3512814 | +3144.750196 | +0.258 |
| 14 | +0.1025956202 | -0.9673399206 | +12.78014234 | -188.274941 | +3014.468041 | +0.227 |
| 16 | +0.1014237556 | -0.9379965843 | +12.32452678 | -181.2600544 | +2898.949216 | +0.203 |
| 18 | +0.1005334797 | -0.9137109883 | +11.9353825 | -175.1865677 | +2797.425691 | +0.185 |

C_2, C_3 are the same as in every other scheme. The window term changes C_4 by about +0.10 at all L (it
tends to ~ +0.098, cf. sec. 7), but C_5..C_8 by much more relative to their size: C_8 +67 % at L = 2,
+23 % at L = 14, +18.5 % at L = 18. A plausible origin is the strong z dependence of E_z(l) − E_z(l − N)
(the one-chi-line part of S_z(l) grows like z^3), which the high orders see through states with up to
14 zero modes.

**r_n, g_n (zeromode)** (r_1 = 0, g_1 = 1/3):

| L | r_2 | r_3 | r_4 | r_5 | r_6 | r_7 | r_8 |
|---|---|---|---|---|---|---|---|
| 0 | 0.05555555556 | 0.1687242798 | 0.09005868008 | 0.3276417326 | -1.177073376 | 8.16378152 | -60.01089005 |
| 2 | 0.1041666667 | 0.4225501543 | 0.5342715389 | 1.167368514 | -3.298861178 | 28.02418245 | -276.0927992 |
| 4 | 0.1519097222 | 0.6833544319 | 1.023052431 | 2.158097897 | -5.449453279 | 50.29951712 | -516.3851139 |
| 6 | 0.1993815104 | 0.9505928027 | 1.551281364 | 3.271853293 | -7.649421176 | 73.8981002 | -773.8395504 |
| 8 | 0.2467346191 | 1.223090176 | 2.111787982 | 4.485402899 | -9.879422197 | 98.69863385 | -1046.944574 |
| 10 | 0.2940254211 | 1.499959959 | 2.699156788 | 5.777047369 | -12.16133146 | 124.3580168 | -1334.340793 |
| 12 | 0.3412795067 | 1.780550805 | 3.30957784 | 7.134981446 | -14.47960475 | 150.7409546 | -1634.191385 |
| 14 | 0.3885101527 | 2.064372444 | 3.940136212 | 8.548821369 | -16.83851974 | 177.6428233 | -1945.113108 |
| 16 | 0.4357249282 | 2.351045206 | 4.588611418 | 10.01200736 | -19.22882527 | 204.9685462 | -2265.714429 |
| 18 | 0.4829284621 | 2.640267453 | 5.253210978 | 11.518608 | -21.65178898 | 232.5906403 | -2595.005112 |

| L | g_2 | g_3 | g_4 | g_5 | g_6 | g_7 | g_8 |
|---|---|---|---|---|---|---|---|
| 0 | 0.7098765432 | 0.4093507087 | 1.226690969 | -3.945987694 | 27.12231873 | -195.5841594 | 1577.7084 |
| 2 | 0.9953703704 | 1.239904835 | 2.577134774 | -5.649239842 | 52.22661189 | -501.343105 | 5553.080416 |
| 4 | 1.146354167 | 1.734158639 | 3.484275705 | -5.789102173 | 63.53390726 | -630.0771551 | 7199.891181 |
| 6 | 1.249754395 | 2.105555061 | 4.22924372 | -5.57978167 | 70.5772275 | -708.021504 | 8131.142874 |
| 8 | 1.328508472 | 2.408475892 | 4.874583391 | -5.236152863 | 75.82560462 | -764.7605729 | 8784.520198 |
| 10 | 1.39214295 | 2.666516792 | 5.446802506 | -4.847168142 | 79.9734569 | -810.1256307 | 9297.308256 |
| 12 | 1.445543019 | 2.89243652 | 5.963629141 | -4.434591358 | 83.41382298 | -848.0772414 | 9725.054756 |
| 14 | 1.4915512 | 3.094040526 | 6.436148548 | -4.015717326 | 86.31754255 | -880.7962916 | 10093.56503 |
| 16 | 1.531968411 | 3.276501268 | 6.8726553 | -3.595098876 | 88.82140492 | -909.4939903 | 10417.6509 |
| 18 | 1.568008064 | 3.443445337 | 7.279007822 | -3.178072111 | 90.9981286 | -935.0437453 | 10706.32345 |

Example (L = 2): C_4 = 6786263/3732480, C_5 = −10765029721/985374720, C_6 = 4799953746817577/61457821286400.

**Non-perturbative check (c)** (`np_check/results/np_L<L>_<variant>.json`): worst relative deviation,
over every compared coefficient, of the Cauchy coefficients from the exact rationals
(|diff|/max(|exact|, 1)); "min eigenvalue gap" = smallest distance (double precision, at t = 1) of a tracked
eigenvalue to the rest of its spectrum over all channels and points (0.0090 = the z = 5 partner splitting
(7/3)|eps| at |eps| = 1/256); "min weight" = smallest |v_ref|^2/|v|^2 of a tracked eigenvector.

| L | variant | Zh | rho | K | bits | cap | coefficients compared | worst rel. diff vs exact | min eigenvalue gap | min weight on reference | wall s |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | base | 18 | 1/256 | 128 | 320 | 19 | 152 | 9.2e-80 | 0.96 | 0.969 | 1 |
| 0 | zh14 | 14 | 1/256 | 128 | 320 | 19 | 152 | 1.0e-79 | 0.96 | 0.985 | 0 |
| 0 | rhoK | 18 | 1/400 | 96 | 320 | 19 | 152 | 7.0e-78 | 0.98 | 0.987 | 0 |
| 0 | prec | 18 | 1/256 | 128 | 384 | 19 | 152 | 5.8e-99 | 0.96 | 0.969 | 0 |
| 0 | path | 18 | 1/256 | 128 | 320 | 19 | 152 | 3.9e-80 | 0.96 | 0.969 | 0 |
| 0 | cap21 | 20 | 1/256 | 128 | 320 | 21 | 152 | 1.4e-79 | 0.95 | 0.952 | 0 |
| 2 | base | 18 | 1/256 | 128 | 320 | 19 | 233 | 1.3e-80 | 0.0090 | 0.968 | 1 |
| 2 | zh14 | 14 | 1/256 | 128 | 320 | 19 | 233 | 4.2e-81 | 0.0090 | 0.984 | 1 |
| 2 | rhoK | 18 | 1/400 | 96 | 320 | 19 | 233 | 2.5e-79 | 0.0058 | 0.987 | 1 |
| 2 | prec | 18 | 1/256 | 128 | 384 | 19 | 233 | 8.5e-84 | 0.0090 | 0.968 | 2 |
| 2 | path | 18 | 1/256 | 128 | 320 | 19 | 233 | 3.2e-81 | 0.0090 | 0.968 | 2 |
| 2 | cap21 | 20 | 1/256 | 128 | 320 | 21 | 233 | 4.8e-71 | 0.0090 | 0.950 | 2 |
| 4 | base | 18 | 1/256 | 128 | 320 | 19 | 314 | 9.0e-82 | 0.0090 | 0.967 | 21 |
| 4 | zh14 | 14 | 1/256 | 128 | 320 | 19 | 314 | 3.0e-81 | 0.0090 | 0.984 | 16 |
| 4 | rhoK | 18 | 1/400 | 96 | 320 | 19 | 314 | 2.7e-79 | 0.0058 | 0.987 | 19 |
| 4 | prec | 18 | 1/256 | 128 | 384 | 19 | 314 | 2.2e-82 | 0.0090 | 0.967 | 26 |
| 4 | path | 18 | 1/256 | 128 | 320 | 19 | 314 | 5.4e-81 | 0.0090 | 0.967 | 21 |
| 4 | cap21 | 20 | 1/256 | 128 | 320 | 21 | 314 | 2.3e-67 | 0.0090 | 0.949 | 30 |
| 6 | base | 18 | 1/256 | 128 | 320 | 19 | 395 | 4.5e-81 | 0.0090 | 0.967 | 400 |
| 6 | zh14 | 14 | 1/256 | 128 | 320 | 19 | 395 | 6.2e-81 | 0.0090 | 0.984 | 313 |
| 6 | rhoK | 18 | 1/400 | 96 | 320 | 19 | 395 | 4.2e-80 | 0.0058 | 0.987 | 373 |

At L = 6 the channels z = 13, 14 already contain level-6 partners, so every partner structure that enters
through eps^8 (N = 2, 4, 6) is covered by the non-perturbative check. The cap-21 runs are slightly less
accurate (1e-67..1e-71) because the z = 19, 20 branches of that hierarchy have even smaller radii; they enter
C_n only beyond eps^8 and still agree to 67 digits.

## 10. What a production implementation must handle

* Channels: E_z(l) for **z = 0..14 at every l = 0, 2, ..., L**, self-consistent in the zeromode-corrected
  Hamiltonians, with the same r, g. Orders: **z <= 6 through eps^6, 7 <= z <= 10 through eps^4,
  11 <= z <= 14 through eps^2**; primaries p = 0..3 at l = L through eps^8. Nothing with z >= 15, and no
  E_z^(7), E_z^(8) for any z other than the primaries at L, can enter C_0..C_8 (demonstrated, sec. 3/6).
* Particle caps per channel P <= z + 4 floor(k_max/2) (<= 18); primaries P <= p + 16; the even/odd sector
  bases with P <= 18 / 19 suffice for everything.
* D on a state needs its zero-mode number z_s and its level; D^(k) for k <= n − 2 at order n.
* **Degenerate channels z = 5..14** (partners at levels 2, 4, 6 with P = z − 2N, only those with N <= l
  present): the RS resolvent must not be applied on B. Use the B-projected equation of sec. 5
  (psi_{n−1}^B fixed at order n by G_B = (E^(1) − W_1^BB)^{-1}, |B| <= 15 reflection-even states). The
  splitting is large (>= 7/3 in units of eps), so G_B is harmless in floating point too. The reference
  never couples to B directly (fact 1), which is a cheap assertion. The primaries are never degenerate.
* In a non-perturbative (fixed-eps) implementation the high-z branches have small radii (E_18 ~ 1/60 with cap
  19); either keep |eps| well below that or truncate the self-consistent set to z <= 14 (allowed through
  eps^8; checked non-perturbatively).
* Size of the effect: the zeromode window changes C_4 by ~+0.10 (slowly decreasing towards ~+0.098 at L = 30,
  cf. continuum) and C_8 by a large amount at small L (+67 % at L = 2, +23 % at L = 14; sec. 9).

## 11. Compute record

All on symmetry (Slurm), work dir `<SCRATCH>/indep2d/zeromode/{code,out,logs,runs}`, venv
`~/indep2d_rs/venv` used read-only (Python 3.11, numpy 2.4.6, scipy 1.17.1, python-flint 0.9.0, mpmath 1.4.1).
amdq/defq had no free node (estimated starts 2026-10-10), so every job ran in the 1-hour debug partitions
(all finished well inside the hour). Logs were copied to `logs/` and `np_check/runs/*.log`.

| job id | name | partition / node | content | wall | log |
|---|---|---|---|---|---|
| 571821 | indep2d-zm-exactA | amddebugq <NODE> | zeromode + garbage L = 0..14; cap + 2 L = 0..14; extended table + garbage L = 0..10 | 3:09 | logs/exactA_571821.log, logs/time_{zm,capx2,ext}_L*.txt |
| 571822 | indep2d-zm-exactL18 | amddebugq <NODE> | zeromode L = 18 (16 workers) | 10:14 | logs/exactL18_571822.log |
| 571823 | indep2d-zm-exactL16 | amddebugq <NODE> | zeromode + garbage L = 16 (40 workers) | 4:33 | logs/exactL16_571823.log |
| 571824 | indep2d-zm-np024 | debugq <NODE> | non-perturbative L = 0, 2, 4, all six variants; Fraction implementation L = 8, 10 (background) | 12:27 | logs/np024_571824.log, np_check/runs/zm_L{0,2,4}_*.log, logs/frac_L{8,10}.log |
| 571825 | indep2d-zm-np6 | debugq <NODE> | non-perturbative L = 6: base, zh14, rhoK | 18:08 | logs/np6_571825.log, np_check/runs/zm_L6_*.log |
| 571828 | indep2d-zm-checksB | amddebugq <NODE> | extended table + garbage L = 12, 14; cap + 2 L = 16 | 5:47 | logs/checksB_571828.log |
| 571849 | indep2d-zm-garbL18 | amddebugq <NODE> | garbage test L = 18 | 10:01 | logs/garbL18_571849.log |

Local (Mac, seconds each): `degeneracy.py`, `bookkeeping.py`, `closed_form_dC4.py`, the Fraction
implementation for L <= 6 and the `consistent`-mode regression (`raw_out/test_L{0,2,4,6}.json`), the
sharpness test (sec. 3), double-precision radius scans, `zm_cauchy.py`, `export_results.py`.

Reproduce: `python3 export_results.py && python3 make_tables.py` (from `raw_out/` and `np_check/results/`);
the cluster commands are in `jobs/` (`run_exact.sbatch "L-list" VARIANTS NPRIMES NCHECK PROCS CAPEXTRA TIERS TAG`,
`run_np.sbatch "L-list" "variants" auto`, `run_frac.sbatch "L-list"`).
