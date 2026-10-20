# Clean-room non-perturbative check: Cauchy-integral extraction of C_0..C_8

This directory computes the eps-Taylor coefficients of
Delta(eps; L) = E_2 - E_0 for the 2D long-range Ising Hamiltonian-truncation problem of `../SPEC.md`
without any perturbation theory: at every point of a circle |eps| = rho in the complex eps plane the finite
truncated Hamiltonian is built at the exact complex x(eps) = 1/2 - eps/4, the tuning conditions are solved
for complex r, g by Newton's method, and the Taylor coefficients are read off by the discrete Cauchy formula

    C_n = (1/K) sum_{k=0}^{K-1} Delta(eps_k) eps_k^(-n),   eps_k = rho exp(2 pi i k/K).

Everything (basis, matrix elements, algorithms) was derived and written from `SPEC.md` alone. No other code,
note or result was read (see "Independence" at the end).

Results: `results/<scheme>_L<L>.json` (scheme = raw, consistent, literal; L = 0, 2, 4, 6, 8).
A summary table is at the end of this file (section 10).

--------------------------------------------------------------------------------------------------------------

## 1. Fock basis

Modes m = (a, b), a, b >= 0, level lev_m = a + b, angular momentum J_m = a - b, energy x + lev_m.
Normalized occupation states |{n_m}> = prod_m (A_m^dag)^{n_m} / sqrt(n_m!) |0>;
level N = sum n_m lev_m, particle number P = sum n_m, J = sum n_m J_m.

At cutoff L only modes with lev_m <= L can occur. The basis of one field-parity sector (P mod 2 fixed) is

* J = 0, N <= L, P <= Pcap (the particle cap, section 4),
* reflection R: (a, b) -> (b, a) acts on occupations; the reflection-even states are
  |s>_+ = (|s> + |Rs>)/sqrt 2 for Rs != s and |s>_+ = |s> for Rs = s, one per R-orbit
  (representative = lexicographically smaller occupation tuple).

Enumeration (`basis.py`): all multisets of non-zero modes (a+b >= 1) with J = 0 and level <= L, times
n_00 = 0, 1, ... up to the cap. States are sorted by (level, P, occupation) so that the basis at any smaller
cutoff l is a prefix; the reference states |p> = (A_00^dag)^p/sqrt(p!)|0> are the level-0 states.
Dimensions with Pcap = 19 (even / odd sector): L=0: 10/10, L=2: 28/29, L=4: 88/92, L=6: 259/273
(L=8: 772/818).

## 2. Matrix elements of M and V (as functions of x, not expanded)

With c_m = sqrt(w_m(x)), w_ab(x) = (x)_a (x)_b/(a! b!),

    phi(theta) = sum_m c_m ( e^{i J_m theta} A_m^dag + e^{-i J_m theta} A_m ).

Because the creation parts commute among themselves and so do the annihilation parts, the normal-ordered
power is the binomial expansion with all creators to the left:

    :phi^K: = sum_{kc=0}^{K} binom(K, kc) sum_{m_1..m_K} c_{m_1}...c_{m_K}
              e^{i(J_{m_1}+...+J_{m_kc} - J_{m_kc+1} - ... - J_{m_K}) theta}
              A^dag_{m_1}...A^dag_{m_kc} A_{m_kc+1}...A_{m_K}.

The theta average imposes J(creators) = J(annihilators). Grouping ordered tuples into multisets
C = {c_m} (creators, size kc) and D = {d_m} (annihilators, size ka = K - kc), the number of ordered tuples is
kc!/prod c_m! * ka!/prod d_m!, and for occupation n:

    prod_m (A_m^dag)^{c_m} (A_m)^{d_m} |n> = prod_m sqrt( n_m!/(n_m-d_m)! * (n_m-d_m+c_m)!/(n_m-d_m)! ) |n - d + c>.

Hence, for occupation states,

    <n'| <:phi^K:>_theta |n> = sum_{(C,D): n' = n - D + C, J(C) = J(D)} binom(K,kc) (kc!/prod c!) (ka!/prod d!)
                               prod_m c_m^{c_m + d_m} prod_m sqrt( n_m!(n_m-d_m+c_m)! ) / (n_m-d_m)! ,

with M = <:phi^2:>_theta and V = <:phi^4:>_theta / 12. The projection P_l . P_l keeps only targets with
N' <= l and P' <= Pcap. In the reflection-even basis
<t_+|O|s_+> = (1/(nu_t nu_s)) sum_{t' in orbit(t)} sum_{s' in orbit(s)} <t'|O|s'>, nu = sqrt 2 or 1.
Every matrix element is stored exactly as sum (rational) * sqrt(integer) * prod_m c_m^{e_m} and evaluated at
the complex x(eps) in the working precision. H0 = N + P x is diagonal.

Checks (`tests.py`): (i) the weights reproduce sum_ab w_ab e^{-i(a-b)theta} = |2 sin(theta/2)|^{-2x};
(ii) M and V agree to 1e-12 with an independent brute-force construction (explicit loop over all ordered
mode tuples with explicit Fock action, explicit theta quadrature, explicit reflection isometry) at a generic
x for L = 2 (cap 5) and L = 4 (cap 4); (iii) M, V are symmetric; (iv) <p|M|p> = 2p and <p|V|p> = p(p-1)/2.

First order (used only as a check and as the starting guess): E_p = p x + 2p r + p(p-1)/2 g + O(2), so the
tuning conditions give r_1 = 0, g_1 = 1/3 and Delta = 1 - eps/2 + eps/3 = 1 - eps/6 for every L.

Analyticity. w_m(x) is a polynomial in eps with w_m(1/2) > 0; for |eps| < 2 every factor x + k has positive
real part and |arg w_m| < pi, so the principal sqrt is analytic and the truncated H(eps) is an analytic,
complex-symmetric (H^T = H, not Hermitian) matrix function of (eps, r, g). (Equivalently, the non-unitary
similarity S = prod_m c_m^{N_m} makes all entries polynomials in the w_m; the spectrum is unchanged.)
H(conj eps) = conj H(eps), so all Taylor coefficients are real (|Im C_n| is used as an error indicator).

## 3. Schemes as finite-dimensional problems at fixed complex eps

For given (eps, r, g):

* raw: E_p = eigenvalue of P_L(H0 + rM + gV)P_L connected to |p> (p = 0, 2 even sector; 1, 3 odd sector).
* consistent: for l = 0, 2, ..., L the vacuum E_v(l) is defined self-consistently by
  E_v(l) = eigenvalue of H_l(E_v(l)), H_l(E) = P_l(H0 + rM + gV)P_l + diag(D_l(N)),
  D_l(N) = E - E_v(l-N) for N >= 2, D_l(0) = 0. Writing A_l = P_l(H0 + rM + gV)P_l - diag(E_v(l-N))_{N>=2},
  H_l(E) = A_l + E Pi_{N>=2}, and H_l(E) psi = E psi is equivalent to the LINEAR generalized eigenproblem

      A_l psi = E Pi_0 psi,     Pi_0 = projector on the level-0 (pure zero-mode) states.

  So the non-perturbative fixed point is solved exactly (no iteration on E): E_v(l) is the eigenvalue of the
  pencil (A_l, Pi_0) connected to |0>, computed recursively l = 0, 2, ..., L (A_l needs E_v(l') for l' < l).
  Equivalently E_v(l) is an eigenvalue of the Schur complement A_00 - A_0Q A_QQ^{-1} A_Q0 on the level-0
  block; this is evaluated in double precision as a check (agreement 1e-21 to 1e-18, i.e. double-precision
  level, `gaps64.vac*_schur_check` in the point files).
  Primaries: P_L(H0 + rM + gV)P_L + diag(D_L), D_L(N) = E_v(L) - E_v(L-N), both parity sectors;
  E_0 = E_v(L) (checked: the p = 0 eigenvalue of the primary matrix equals E_v(L) to ~1e-80).
* literal: E_v^raw(l) = vacuum of the raw P_l(H0 + rM + gV)P_l for l = 0..L; primaries p = 0..3 of
  P_L(H0 + rM + gV)P_L + diag(E_v^raw(L) - E_v^raw(L-N)); E_0 = p = 0 primary of that matrix.

Eigenvalues: Rayleigh-quotient iteration (inverse iteration with shift = bilinear Rayleigh quotient
y^T A y / y^T B y, transpose not conjugate, which is stationary for complex-symmetric matrices and pencils;
cubic convergence), started from the eigenvector of the previous Newton iterate / continuation step.
Derivatives: Hellmann-Feynman, dE = psi^T (dA) psi / psi^T B psi, including the chain rule through
D_L and through the recursion for E_v(l) in the consistent and literal schemes (verified against finite
differences in `tests.py`).

Tuning: Newton's method in (r, g) on F1 = E_1 - E_0 - x, F2 = E_3 - E_0 - (2 - x); the Jacobian at eps = 0
is [[2, 0], [6, 3]] (det 6), so r(eps), g(eps) exist and are analytic near 0 (implicit function theorem),
with r(0) = g(0) = 0.

Branch selection ("analytically connected to |p>"): eps_k is reached along the straight ray t*eps_k,
t = 0.25, 0.5, 0.75, 1 ("path" variant: t = 0.1, 0.2, ..., 1), starting at the first step from r = 0,
g = t eps/3 and the unit vectors |p>, |0> (vacua); later steps start from polynomial extrapolation in t
(including r = g = 0 at t = 0) and from the previous eigenvectors. This continuation is done in double
precision (numpy/LAPACK; Newton to |F| < 1e-11). At t = 1 the full spectrum of every primary matrix is
computed in double precision and the distance of each tracked eigenvalue to the rest of the spectrum is
recorded (`gaps64`; it stays ~1 since |eps| = 1/64 is small, i.e. no near-crossing). The double-precision
solution (r, g, all eigenvectors) is then refined at full precision (python-flint `acb_mat`, 256 bits) by
Newton + RQI until max|F| < 2^-(prec-24) (quadratic convergence, typically 1e-11 -> 1e-22 -> 1e-44 -> 0).
Reference weights |psi_p[p]|^2/||psi_p||^2 are > 0.999 at every point.

## 4. Particle cap (exact through eps^8)

The level cutoff does not bound P because the zero mode costs no level. Expanding E_p in eps
(Rayleigh-Schroedinger), each term of order n is a sum over closed paths |p> -> s_1 -> ... -> |p> of
off-diagonal hops of rM or gV, with diagonal pieces (H0 including -eps P/4, diagonal parts of M, V, and D)
in the energy denominators. Every hop carries at least one power of eps (g = O(eps), r = O(eps^2) since
r_1 = 0; D is diagonal). V changes P by at most 4 and M by at most 2. A path that reaches particle number
P from p and returns needs >= 2 ceil((P-p)/4) hops, hence contributes at order >= 2 ceil((P-p)/4).
Through eps^8 only P <= p + 16 is visited. The tuning at order n uses E_0, E_1, E_3 at order n and the
observable uses E_2, so P <= 3 + 16 = 19 (odd sector) and P <= 2 + 16 = 18 (even sector) suffice:
cap Pcap = 19 (P <= 19; even sector effectively P <= 18). Matrix elements between kept states are exact
(projection), so the capped problem has the same Taylor coefficients C_0..C_8 (also r_n, g_n, E_p,n for
n <= 8; E_v(l) needs only P <= 16), while C_9, C_10, ... do depend on the cap.

Numerical demonstration (every scheme and L): cap 21 and cap 23 reproduce C_0..C_8 of cap 19 to the
numerical precision (~1e-40 or better), whereas cap 18 (odd sector P <= 17, so r_8, g_8 from E_3 change) and
cap 17 (even P <= 16, odd P <= 17) change C_8 and only C_8 (see `cap_controls_C_minus_base` in each results
file). Hence 19 is the smallest exact uniform cap.

## 5. Error control (rho, K, precision)

The discrete Cauchy sum returns c_n = C_n + sum_{j>=1} C_{n+jK} rho^{jK} (aliasing) plus rounding.
The capped finite problem has a finite radius of convergence R; the observed growth |C_{n+1}/C_n| -> 11-18
(it grows with the cap, reflecting the factorial growth of the uncapped zero-mode problem) gives
R ~ 0.06-0.09. With rho = 1/64 the aliasing on C_n is ~ |C_n| (rho/R)^K ~ |C_n| 0.25^128 ~ 1e-77 |C_n|.
Rounding: the point values are converged to max|F| < 2^-(prec-24) and are accurate to ~1e-75 at 256 bits;
amplified by rho^-n <= 64^8 = 2.8e14 this gives ~1e-63 on C_8 (observed: the 352-bit, 10-step-path and
cap-21/23 runs agree with the base run to ~1e-64 on C_8 and ~1e-76 on C_0). Both estimates are confirmed
empirically by the variants (all with the full pipeline):

| variant | change | purpose |
|---|---|---|
| base | rho = 1/64, K = 128, 256 bits, cap 19, t = 0.25..1 | reference |
| rhoK | rho = 1/40, K = 96 | different circle and number of points (aliasing ~ (0.31)^96 ~ 1e-49) |
| prec | 352 bits | rounding and all solver tolerances (tolerances scale with precision) |
| path | 10 radial steps | branch tracking / continuation |
| cap21, cap23 | larger particle cap | cap exactness |
| cap17, cap18 | smaller cap | negative controls (must change C_8) |

The quoted error of each coefficient is max over {rhoK, prec, path, cap21, cap23} of |Re(variant - base)|
and of |Im| of all runs. These are very conservative: the quoted error is set by the rhoK run's own
aliasing ((rho/R)^96 with rho = 1/40, i.e. ~1e-45 on C_8), while the base run itself is good to ~1e-63.

Interior check (`check_interior.py`; stored under `interior_check` in each results file): the full Fourier series
sum_{n<K} c_n eps^n built from the circle reproduces an independent direct solution at four points inside
the circle (eps = 0.01, -0.012+0.005i, -0.014i, 0.001) to ~1e-77, and C_0..C_8 alone to |C_9 eps^9|. This
would fail if any of the circle values belonged to a wrong eigenvalue branch.

Self-checks: C_0 = 1 and C_1 = -1/6 to the quoted accuracy for every scheme and L; at L = 0 a hand
second-order calculation (zero-mode oscillator only) gives r_2 = 1/18, g_2 = 115/162, C_2 = 17/81, reproduced
to all digits; consistent vs raw differ first at C_4 and consistent vs literal first at C_6, as expected from
D = O(eps^2) entering energies at second order and E_v^cons - E_v^raw = O(eps^4); conjugation symmetry
(|Im C_n| tiny).

## 6. Code and how to run

* `basis.py` — modes, sectors, exact operator structure (cached as `cache/ops_L<L>_P<cap>.pkl`).
* `hamil.py` — evaluation at complex eps (python-flint `acb`, and a float64 copy for continuation).
* `solve.py` — RQI, schemes, Hellmann-Feynman, Newton, radial continuation, full-precision refinement.
* `run_points.py` — all K circle points (multiprocessing), writes every point value as decimal strings.
* `cauchy.py` — discrete Cauchy sums; `make_results.py` — variants -> `results/*.json` with errors.
* `tests.py` — self-tests (seconds). `jobs/` — Slurm scripts used on symmetry (`campaign.sh` runs the
  variants); `timing.py` — the timing probe; `check_interior.py` — interior check; `table.py` — summary table.
* `runs/` — the raw point files of every run (copied back from the cluster).

    python run_points.py --scheme consistent --L 4 --rho 1/64 --K 128 --prec 256 --cap 19 --procs 64 --out runs/consistent_L4_base.json
    python make_results.py runs results

Environment: Python 3.11, python-flint 0.9.0 (Arb `acb_mat` approximate LU), mpmath 1.4.1, numpy 2.4.

## 7. Limitations

* The method is numerical; the numbers are not proven exact. The rational candidates in the JSON files are
  continued-fraction identifications accepted only if consistent with the error estimate and with
  denominator^2 * error < 1e-6; they are suggestions, not proofs.
* The cap argument (section 4) and its numerical demonstration establish that C_0..C_8 do not depend on the
  particle cap; C_n for n >= 9 (not reported) do.

## 8. Independence

Only `../SPEC.md` and this directory were read (plus one `ls` of `../`, which showed the sibling
directories `rs_exact/` and `continuum/` empty at the time; their contents were never opened). No file of the production solver, of the other independent
checks (`../rs_exact`, `../continuum`), of `../../results`, or any other HT/LRI material was opened, and no
existing values of these coefficients were consulted. On symmetry only `~/indep2d_cauchy` (venv) and
`<SCRATCH>/indep2d/cauchy/` were used.

## 9. Compute record (symmetry, Slurm; AMD EPYC 7532 nodes)

Data and logs: `<SCRATCH>/indep2d/cauchy/{code,runs,logs}`; venv `~/indep2d_cauchy/venv`.

| job id | partition | content | log |
|---|---|---|---|
| 571682 | amddebugq | timing probe with an earlier, slower version of the continuation (cancelled by me after the L=6 numbers) | logs/timing_571682.log |
| 571700 | amddebugq | L = 0, 2, 4: all schemes x all 8 variants | logs/campaign_L024_571700.log |
| 571701 | amdq | L = 6 (cancelled while pending, replaced by 571703-5) | - |
| 571703 / 571704 / 571705 | amddebugq | L = 6 raw / consistent / literal, all variants | logs/campaign_L6_<scheme>_<id>.log |
| 571706 / 571707 / 571708 | amdq | L = 8 raw / consistent / literal, all variants | logs/campaign_L8_<scheme>_<id>.log |
| 571712 / 571719 | amddebugq | interior checks L = 6 / L = 8 | logs/interior_<id>.log |

Per-run logs (one line per circle point, with timing, Newton history lengths and reference weights):
`runs/<scheme>_L<L>_<variant>.log`. Cost: L <= 4 seconds per run; L = 6 about 25 s per point
(64 points in parallel), L = 8 about 8 min per point (64 in parallel, memory-bandwidth bound).

## 10. Results (C_2..C_8; C_0 = 1 and C_1 = -1/6 in every case)

Values are shortened to 30 significant digits here; `results/*.json` carry each number to the digits
allowed by its error estimate (40-58 digits). The error column is the conservative estimate of section 5.
"rational candidate" = continued-fraction identification (all 882 identified coefficients in the result
files, including r, g, E_p and vacua, have denominators of the form 2^a 3^b 5^c 7^d, which is strong
evidence that these coefficients are exactly rational, as expected since all matrix elements become
rational along closed paths; not a proof).

| scheme | L | n | C_n (30 significant digits) | error estimate | rational candidate |
|---|---|---|---|---|---|
| raw | 0 | 2 | 0.20987654320987654320987654321 | 2.87e-57 | 17/81 |
| raw | 0 | 3 | -0.359167809785093735711019661637 | 3.14e-56 | -1571/4374 |
| raw | 0 | 4 | 1.36643719622686243628173212078 | 3.44e-55 | 322747/236196 |
| raw | 0 | 5 | -6.61461988881801241028323620747 | 3.76e-54 | -84366725/12754584 |
| raw | 0 | 6 | 39.5728583325196825096155407516 | 4.11e-53 | 9085236223/229582512 |
| raw | 0 | 7 | -275.224505753117899760846153906 | 4.49e-52 | -3412083603317/12397455648 |
| raw | 0 | 8 | 2150.06254374435372734516639629 | 4.9e-51 | 1439386471430821/669462604992 |
| raw | 2 | 2 | 0.263888888888888888888888888889 | 1.47e-53 | 19/72 |
| raw | 2 | 3 | -0.452353395061728395061728395062 | 1.75e-52 | -2345/5184 |
| raw | 2 | 4 | 1.70518163080132601737540009145 | 2.08e-51 | 19093669/11197440 |
| raw | 2 | 5 | -9.81444898094762929939541736524 | 2.46e-50 | -7912562659/806215680 |
| raw | 2 | 6 | 64.3080545536489965343048428706 | 2.92e-49 | 18664618295321/290237644800 |
| raw | 2 | 7 | -493.4069591330721025248507853 | 3.46e-48 | -90219322460428999/182849716224000 |
| raw | 2 | 8 | 4262.48354021559944540693215857 | 4.09e-47 | 31425162279351855854947/7372500558151680000 |
| raw | 4 | 2 | 0.2796875 | 1.99e-51 | 179/640 |
| raw | 4 | 3 | -0.53496410228587962962962962963 | 2.49e-50 | -236651/442368 |
| raw | 4 | 4 | 2.03395919874160012084394800444 | 3.1e-49 | 63770381053/31352832000 |
| raw | 4 | 5 | -12.1672262945034309334076308924 | 3.86e-48 | -281255363973770227/23115815976960000 |
| raw | 4 | 6 | 84.930685240073232383772176734 | 4.8e-47 |  |
| raw | 4 | 7 | -687.653614151572210851878079695 | 5.96e-46 |  |
| raw | 4 | 8 | 6270.12725378433556286808663954 | 7.39e-45 |  |
| raw | 6 | 2 | 0.287188257826278659611992945326 | 4.22e-50 | 833719/2903040 |
| raw | 6 | 3 | -0.590330168442299725906737866614 | 5.42e-49 | -9476363569/16052649984 |
| raw | 6 | 4 | 2.3051341052124719562350691706 | 6.95e-48 | 12532645119057536593/5436839917780992000 |
| raw | 6 | 5 | -14.0380128343616170747970047124 | 8.91e-47 |  |
| raw | 6 | 6 | 101.691709046071078957930956591 | 1.14e-45 |  |
| raw | 6 | 7 | -852.641982092846776046783562924 | 1.46e-44 |  |
| raw | 6 | 8 | 8044.85075458298124813088581667 | 1.86e-43 |  |
| raw | 8 | 2 | 0.291559618322517085537918871252 | 3.23e-49 | 54170191/185794560 |
| raw | 8 | 3 | -0.629359647685336323198374173185 | 4.23e-48 | -344845316722219/547930452787200 |
| raw | 8 | 4 | 2.52587679838122502973862582483 | 5.53e-47 |  |
| raw | 8 | 5 | -15.5755734813886313367673568372 | 7.22e-46 |  |
| raw | 8 | 6 | 115.622460608689978892871122853 | 9.4e-45 |  |
| raw | 8 | 7 | -993.452445044087682385477688195 | 1.22e-43 |  |
| raw | 8 | 8 | 9600.04860332270409995940459953 | 1.59e-42 |  |
| consistent | 0 | 2 | 0.20987654320987654320987654321 | 2.87e-57 | 17/81 |
| consistent | 0 | 3 | -0.359167809785093735711019661637 | 3.14e-56 | -1571/4374 |
| consistent | 0 | 4 | 1.36643719622686243628173212078 | 3.44e-55 | 322747/236196 |
| consistent | 0 | 5 | -6.61461988881801241028323620747 | 3.76e-54 | -84366725/12754584 |
| consistent | 0 | 6 | 39.5728583325196825096155407516 | 4.11e-53 | 9085236223/229582512 |
| consistent | 0 | 7 | -275.224505753117899760846153906 | 4.49e-52 | -3412083603317/12397455648 |
| consistent | 0 | 8 | 2150.06254374435372734516639629 | 4.9e-51 | 1439386471430821/669462604992 |
| consistent | 2 | 2 | 0.263888888888888888888888888889 | 1.47e-53 | 19/72 |
| consistent | 2 | 3 | -0.452353395061728395061728395062 | 1.75e-52 | -2345/5184 |
| consistent | 2 | 4 | 1.70567460062299954275262917238 | 2.08e-51 | 19099189/11197440 |
| consistent | 2 | 5 | -9.81240744288178567799624041051 | 2.46e-50 | -7910916739/806215680 |
| consistent | 2 | 6 | 64.3097165555382841915894708914 | 2.92e-49 | 3733020134167/58047528960 |
| consistent | 2 | 7 | -493.42049120402903152607301254 | 3.46e-48 | -60147864530508931/121899810816000 |
| consistent | 2 | 8 | 4262.4969811757499724481217522 | 4.09e-47 | 10475087124279355903349/2457500186050560000 |
| consistent | 4 | 2 | 0.2796875 | 1.99e-51 | 179/640 |
| consistent | 4 | 3 | -0.53496410228587962962962962963 | 2.49e-50 | -236651/442368 |
| consistent | 4 | 4 | 2.03486927282996317525638513293 | 3.1e-49 | 63798914453/31352832000 |
| consistent | 4 | 5 | -12.1643724615812034718926179371 | 3.86e-48 | -281189395297111027/23115815976960000 |
| consistent | 4 | 6 | 84.9327270343419627782626831902 | 4.8e-47 |  |
| consistent | 4 | 7 | -687.690167139802963578785079568 | 5.96e-46 |  |
| consistent | 4 | 8 | 6270.27887767358885011658732034 | 7.39e-45 |  |
| consistent | 6 | 2 | 0.287188257826278659611992945326 | 4.22e-50 | 833719/2903040 |
| consistent | 6 | 3 | -0.590330168442299725906737866614 | 5.42e-49 | -9476363569/16052649984 |
| consistent | 6 | 4 | 2.30645723099444734069612382565 | 6.96e-48 | 12539838742125225553/5436839917780992000 |
| consistent | 6 | 5 | -14.034715048768359993831905742 | 8.91e-47 |  |
| consistent | 6 | 6 | 101.69524074309309407793663707 | 1.14e-45 |  |
| consistent | 6 | 7 | -852.709459594731924653199661375 | 1.46e-44 |  |
| consistent | 6 | 8 | 8045.25297572962700484178537828 | 1.86e-43 |  |
| consistent | 8 | 2 | 0.291559618322517085537918871252 | 3.24e-49 | 54170191/185794560 |
| consistent | 8 | 3 | -0.629359647685336323198374173185 | 4.24e-48 | -344845316722219/547930452787200 |
| consistent | 8 | 4 | 2.52761495048504575312376367817 | 5.54e-47 |  |
| consistent | 8 | 5 | -15.5720362923274951788907104298 | 7.22e-46 |  |
| consistent | 8 | 6 | 115.628698361456661499091036165 | 9.41e-45 |  |
| consistent | 8 | 7 | -993.558731518870779855290865519 | 1.22e-43 |  |
| consistent | 8 | 8 | 9600.80381868633963925338573348 | 1.59e-42 |  |
| literal | 0 | 2 | 0.20987654320987654320987654321 | 2.87e-57 | 17/81 |
| literal | 0 | 3 | -0.359167809785093735711019661637 | 3.14e-56 | -1571/4374 |
| literal | 0 | 4 | 1.36643719622686243628173212078 | 3.44e-55 | 322747/236196 |
| literal | 0 | 5 | -6.61461988881801241028323620747 | 3.76e-54 | -84366725/12754584 |
| literal | 0 | 6 | 39.5728583325196825096155407516 | 4.11e-53 | 9085236223/229582512 |
| literal | 0 | 7 | -275.224505753117899760846153906 | 4.49e-52 | -3412083603317/12397455648 |
| literal | 0 | 8 | 2150.06254374435372734516639629 | 4.9e-51 | 1439386471430821/669462604992 |
| literal | 2 | 2 | 0.263888888888888888888888888889 | 1.47e-53 | 19/72 |
| literal | 2 | 3 | -0.452353395061728395061728395062 | 1.75e-52 | -2345/5184 |
| literal | 2 | 4 | 1.70567460062299954275262917238 | 2.08e-51 | 19099189/11197440 |
| literal | 2 | 5 | -9.81240744288178567799624041051 | 2.46e-50 | -7910916739/806215680 |
| literal | 2 | 6 | 64.3097142732705912586016133494 | 2.92e-49 | 3733020001687/58047528960 |
| literal | 2 | 7 | -493.420509721268598100725702114 | 3.46e-48 | -60147866787756931/121899810816000 |
| literal | 2 | 8 | 4262.49692694759241443350585672 | 4.09e-47 | 10475086991013648615349/2457500186050560000 |
| literal | 4 | 2 | 0.2796875 | 1.99e-51 | 179/640 |
| literal | 4 | 3 | -0.53496410228587962962962962963 | 2.49e-50 | -236651/442368 |
| literal | 4 | 4 | 2.03486927282996317525638513293 | 3.1e-49 | 63798914453/31352832000 |
| literal | 4 | 5 | -12.1643724615812034718926179371 | 3.86e-48 | -281189395297111027/23115815976960000 |
| literal | 4 | 6 | 84.9327189236918035884372839455 | 4.8e-47 |  |
| literal | 4 | 7 | -687.6902260115427469357922544 | 5.96e-46 |  |
| literal | 4 | 8 | 6270.27872269478586755278591064 | 7.39e-45 |  |
| literal | 6 | 2 | 0.287188257826278659611992945326 | 4.22e-50 | 833719/2903040 |
| literal | 6 | 3 | -0.590330168442299725906737866614 | 5.42e-49 | -9476363569/16052649984 |
| literal | 6 | 4 | 2.30645723099444734069612382565 | 6.96e-48 | 12539838742125225553/5436839917780992000 |
| literal | 6 | 5 | -14.034715048768359993831905742 | 8.91e-47 |  |
| literal | 6 | 6 | 101.695223194318243929162754708 | 1.14e-45 |  |
| literal | 6 | 7 | -852.709577205583258268908490228 | 1.46e-44 |  |
| literal | 6 | 8 | 8045.25267759890711510724008784 | 1.86e-43 |  |
| literal | 8 | 2 | 0.291559618322517085537918871252 | 3.24e-49 | 54170191/185794560 |
| literal | 8 | 3 | -0.629359647685336323198374173185 | 4.24e-48 | -344845316722219/547930452787200 |
| literal | 8 | 4 | 2.52761495048504575312376367817 | 5.54e-47 |  |
| literal | 8 | 5 | -15.5720362923274951788907104298 | 7.22e-46 |  |
| literal | 8 | 6 | 115.628667668386803783052438887 | 9.41e-45 |  |
| literal | 8 | 7 | -993.558924760984008203762233572 | 1.22e-43 |  |
| literal | 8 | 8 | 9600.80332884822293871677636376 | 1.59e-42 |  |

| scheme | L | abs(C_0 - 1) | abs(C_1 + 1/6) | max |dC_n| cap21/cap23 | C_8(cap17) - C_8 | C_8(cap18) - C_8 | min ref. weight |
|---|---|---|---|---|---|---|---|
| raw | 0 | 6.5e-78 | 3.4e-76 | 4.2e-64 | -0.068403 | -0.12997 | 0.99938 |
| raw | 2 | 8.6e-78 | 3.8e-76 | 3.1e-64 | -0.169 | -0.33518 | 0.99928 |
| raw | 4 | 7.6e-78 | 4.6e-76 | 1.9e-64 | -0.28671 | -0.59149 | 0.99924 |
| raw | 6 | 6.1e-78 | 2.6e-76 | 5.3e-64 | -0.41284 | -0.88322 | 0.99922 |
| raw | 8 | 6.1e-78 | 2.5e-76 | 1.9e-64 | -0.54292 | -1.2016 | 0.99920 |
| consistent | 0 | 6.5e-78 | 3.4e-76 | 4.2e-64 | -0.068403 | -0.12997 | 0.99938 |
| consistent | 2 | 4.0e-78 | 2.2e-76 | 3.0e-64 | -0.169 | -0.33518 | 0.99928 |
| consistent | 4 | 7.1e-78 | 3.6e-76 | 6.7e-64 | -0.28671 | -0.59149 | 0.99924 |
| consistent | 6 | 8.9e-78 | 3.4e-76 | 4.9e-64 | -0.41284 | -0.88322 | 0.99922 |
| consistent | 8 | 8.3e-78 | 4.3e-76 | 7.6e-64 | -0.54292 | -1.2016 | 0.99920 |
| literal | 0 | 6.5e-78 | 3.4e-76 | 4.2e-64 | -0.068403 | -0.12997 | 0.99938 |
| literal | 2 | 4.9e-78 | 3.2e-76 | 3.6e-64 | -0.169 | -0.33518 | 0.99928 |
| literal | 4 | 6.7e-78 | 3.7e-76 | 6.3e-64 | -0.28671 | -0.59149 | 0.99924 |
| literal | 6 | 6.4e-78 | 3.0e-76 | 4.5e-64 | -0.41284 | -0.88322 | 0.99922 |
| literal | 8 | 7.2e-78 | 2.1e-76 | 4.7e-64 | -0.54292 | -1.2016 | 0.99920 |

Notes on the second table: abs(C_0 - 1) and abs(C_1 + 1/6) are from the full-precision base runs; "max |dC_n|
cap21/cap23" is the largest change of any C_0..C_8 when the cap is raised from 19 to 21 or 23; the cap17/cap18
columns are the changes of C_8 (C_0..C_7 change by < 1e-64), identical in the three schemes as expected
(the leading order-8 cap effect comes from paths of eight g_1 V-vertices, independent of D).

Scheme structure observed (as expected): raw, consistent and literal agree through C_3 for every L;
consistent = literal through C_5; they differ from C_4 (raw vs corrected) and from C_6 (consistent vs
literal) on. At L = 0 all schemes coincide (D_0 = 0).

## 11. Remarks on the specification

* No inconsistency found. Interpretations used: (i) "level" counts only non-zero modes (zero mode costs no
  level); (ii) D_l(N) is applied to every basis state of level N >= 2 in both parity sectors of the cutoff-L
  primary Hamiltonian, D_l(0) = 0; (iii) in the consistent scheme the vacua at l < L are each defined in their
  own corrected Hamiltonian (exact self-consistency, solved as the linear pencil A_l psi = E Pi_0 psi);
  (iv) the particle cap is my own device (not part of the model) and is shown not to affect C_0..C_8.
* Physics remark (not an inconsistency): the uncapped problem at fixed L contains the zero-mode quartic
  oscillator with complex coupling g ~ eps/3, so the eps-series of the uncapped problem is presumably only
  asymptotic; with a cap the radius of convergence is finite but shrinks as the cap grows (growth ratio
  |C_{n+1}/C_n| ~ 11 at cap 19, ~15-18 at cap 27, L = 0). This is irrelevant for C_0..C_8 (cap independent)
  but means Cauchy radii must be chosen well inside ~1/(growth ratio) for every cap used.
