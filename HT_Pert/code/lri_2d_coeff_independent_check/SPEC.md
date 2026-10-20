# Independent check of the 2D long-range Ising Hamiltonian-truncation coefficients: physics specification

This file defines WHAT must be computed. It deliberately contains no code and no numerical results of the
implementation under test. Derive every formula you use yourself from the definitions below.

## 1. Physics

- 2D long-range Ising model near its upper critical range: a generalized free field (GFF) phi in d = 2 with
  two-point function <phi(x) phi(0)> = |x|^(-2 Delta), perturbed by phi^2 and phi^4.
- Expansion parameter eps = 2 s - 2 (s = long-range exponent, coupling ~ 1/r^(d+s)). The field dimension is
  Delta = x(eps) = 1/2 - eps/4 (exactly, all orders; phi is not renormalized in the long-range model).
- Radial quantization: states on the unit circle, Hamiltonian = dilatation operator.

## 2. Fock space and operators

- Single-particle modes are labelled (a, b), a, b = 0, 1, 2, ... (descendants d^a dbar^b phi). Mode energy
  x + a + b, angular momentum J = a - b. Bosonic creation/annihilation operators A_{ab}^dagger, A_{ab},
  [A_{ab}, A_{a'b'}^dagger] = delta delta.
- Field on the unit circle (time zero):
      phi(theta) = sum_{a,b} sqrt(w_ab) ( e^{+i(a-b)theta} A_{ab}^dagger + e^{-i(a-b)theta} A_{ab} ),
      w_ab(x) = (x)_a (x)_b / (a! b!),   (x)_n = Pochhammer symbol x(x+1)...(x+n-1).
  (Check: this reproduces <phi(theta1) phi(theta2)> = |2 sin((theta1-theta2)/2)|^(-2x).)
- Occupation-number states |{n_ab}>; level N = sum n_ab (a+b); particle number P = sum n_ab;
  H0 = sum n_ab (x + a + b) = N + P x = N + P/2 - eps P/4.
- Vertices (theta average <f>_theta = (1/2pi) int_0^{2pi} f dtheta; normal ordering w.r.t. A, A^dagger):
      M = < :phi^2: >_theta,      V = < :phi^4: >_theta / 12.
  Both depend on eps through w_ab(x(eps)). Both conserve J and commute with spatial reflection (a,b)->(b,a).
- Full Hamiltonian:  H(eps) = H0 + r(eps) M + g(eps) V + D   (D defined per scheme in section 4),
  r(eps) = sum_{k>=1} r_k eps^k,  g(eps) = sum_{k>=1} g_k eps^k  (no eps^0 terms).

## 3. Truncation, sectors, reference states, tuning, observable

- Cutoff L (even integer). The truncated space at cutoff l keeps the states with J = 0, reflection-even, and
  total level N <= l. (J = 0 implies N even.) Field parity (-1)^P is conserved; even-P and odd-P sectors are
  separate. Truncated operators are the projections P_l H P_l. Nothing else is truncated or added.
- The level cutoff does not bound P (zero modes (0,0) cost no level). For eps-Taylor coefficients through eps^8
  only finitely many particle numbers can contribute; you must establish yourself which cap is exact and
  demonstrate it (results unchanged when the cap is raised).
- Reference states (eps = 0 eigenstates of H0, non-degenerate in their sector):
      |p> = (A_00^dagger)^p / sqrt(p!) |0>,  p = 0, 1, 2, 3,  with H0 eigenvalue p/2 at eps = 0.
  E_p(eps) denotes the energy of the eigenstate of the truncated H(eps) that is analytically connected to |p>.
- Tuning conditions (exact in eps, order by order), which fix r_k and g_k:
      E_1 - E_0 = x = 1/2 - eps/4,           E_3 - E_0 = 2 - x = 3/2 + eps/4.
- Observable:  Delta_eps(eps; L) = E_2 - E_0 = sum_{n=0}^{8} C_n(L) eps^n.  Compute C_0..C_8.
- Sanity check you may rely on: C_0 = 1 and C_1 = -1/6 for every L (one-loop result).

## 4. Schemes (definitions of D)

All schemes use one and the same r(eps), g(eps) for every Hamiltonian that appears (all cutoffs).
Let E_v(l) be a "vacuum energy at cutoff l" (eps series), l = 0, 2, ..., L. D is diagonal in the
occupation basis; for a state of level N in a Hamiltonian at cutoff l it equals D_l(N) as below.

- raw:        D = 0. (E_0 is simply the vacuum of the raw truncated H at cutoff L.)
- consistent: D_l(N) = E_v(l) - E_v(l - N), where E_v(l) is the vacuum (p = 0 channel) energy of the
              CONSISTENT Hamiltonian at cutoff l, i.e. of P_l (H0 + r M + g V) P_l + D_l, for every
              l = 0, 2, ..., L (each vacuum in its own corrected Hamiltonian; D_l(0) = 0, so the definition is
              self-consistent order by order: E_v starts at order eps^2, hence D starts at eps^2). The primaries
              p = 0..3 at cutoff L use the same Hamiltonian P_L (H0 + r M + g V) P_L + D_L; E_0 = E_v(L).
- literal:    the vacua E_v(l), l = 0..L, are those of the RAW Hamiltonians at their cutoffs; the primary
              channels p = 0..3 at cutoff L use P_L(H0 + r M + g V)P_L + D_L with D_L(N) = E_v^raw(L) -
              E_v^raw(L - N). Tuning and the observable use these primary energies (so E_0 here is the p = 0
              primary of the corrected Hamiltonian, not E_v^raw(L)).

## 5. What to report (per scheme and cutoff)

C_0..C_8; r_1..r_8 and g_1..g_8 (with M and V normalized exactly as in section 2); E_p coefficients
(p = 0..3, orders 0..8); and for consistent/literal the vacuum series E_v(l) for every l <= L.
JSON, one file per (scheme, L), with the precision/exactness of each number stated.
