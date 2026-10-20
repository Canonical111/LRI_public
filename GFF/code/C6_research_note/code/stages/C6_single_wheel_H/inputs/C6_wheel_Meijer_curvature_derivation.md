# The two wheel components in fourth-order Meijer-G parameter families

## Result and limits

The accepted input is `inputs/accepted_expression.json`, an unchanged copy of
`C6_lower_MeijerG_expression.json`. Its normalization is r6=2187 C6(1).
This note proves a lower-order **intermediate** representation of the actual
sixth-power wheel, alongside the fourth-power component. The new target is a
second parameter derivative of G_(4,4)^(2,2), rather than of a 7F6 family.
The derivative is not evaluated in finitely many fixed special-function values.
Consequently no new block is removed from the accepted coefficient, the known
polynomial is unchanged, and no complete integration/sum/derivative-free C6 is
claimed. The seventh logarithmic sector and primitive are unchanged.

The input's physical identification and source correction are inherited.
In particular the following project identity is used, not proved anew:

    sum_(n>=0) a_n^4 (8 h_n delta_n + tau_n) = pi^2 D6.

Its complete derivation is in the supplied central-binomial wheel note,
Section 2. It is an identity between convergent sums, not a termwise identity.

## 1. Definitions

Use

    a_n = (1/2)_n/n!,
    h_n = log(2)+H_n-H_(2n),
    delta_n = pi^2/3-4 H_(2n)^(2)+2 H_n^(2),
    tau_n = 12 zeta(3)-16 H_(2n)^(3)+4 H_n^(3),
    D4 = sum_(n>=0) a_n^4 delta_n,
    D6 = sum_(n>=0) (4n+1) a_n^6 delta_n.

The sums here identify the existing targets; they are not new final residuals.
The original central wheel starts at n=1 and is

    Wc = 8 D4 + 5 pi D6 - (8+5 pi) pi^2/3.

The current zero-index-included wheel contribution is

    BW = -3144 pi^3 D4 - 1965 pi^4 D6.

No additional zero-index compensation may be added when using this BW.

Define ordinary Meijer G families by their complete Mathematica splits:

```wolfram
G13[u_] := MeijerG[
 {{1/2-u,1/2+u,1/2},{1/2}}, {{0},{u,-u,0}}, 1];
G22[u_] := MeijerG[
 {{1/2-u,1/2+u},{1/2,1/2}}, {{0,0},{0,0}}, 1];
```

These are not the scalar constant A=pi+4log(2), nor Catalan's constant.
Their parameters depend on the auxiliary variable u, not the physical epsilon.
Both are even and holomorphic in a neighborhood of zero; |u|<1/8 suffices.
In all derivatives below the function argument remains exactly one.

The identities are

    D4 = G13''(0)/(2 pi),
    D6 = G22''(0)/pi^2 - G22(0).                 (1)

At zero, the known lower-period identities give

    G13(0) = pi U4,
    G22(0) = pi^2 U6/2.

The first identity in (1) is the gamma-normalized form of the earlier
opposite-shift 4F3 direction. The second is the new order-lowering step.
Neither second derivative is removed from the research target by (1).

## 2. Mellin kernels and differentiation

We use the inverse-Mellin version of the ordinary Meijer-G definition [1,2].
Contours run upward along Re(s)=1/4. The kernels specified by the parameter
lists above are

    A(s,u) = Gamma(s) Gamma(1/2-s-u) Gamma(1/2-s+u) Gamma(1/2-s)
             /[Gamma(1-s-u) Gamma(1-s+u) Gamma(1-s) Gamma(1/2+s)],

    B(s,u) = Gamma(s)^2 Gamma(1/2-s-u) Gamma(1/2-s+u)
             /[Gamma(1-s)^2 Gamma(1/2+s)^2].

At zero these become

    M1(s) = Gamma(s) Gamma(1/2-s)^3
            /[Gamma(1-s)^3 Gamma(1/2+s)],
    M2(s) = Gamma(s)^2 Gamma(1/2-s)^2
            /[Gamma(1-s)^2 Gamma(1/2+s)^2].

The second kernel obeys M2(1/2-s)=M2(s).
Gamma reflection gives, with R(s)=[Gamma(s)/Gamma(s+1/2)]^4,

    M1(s)=R(s) tan(pi s)^3,
    M2(s)=R(s) tan(pi s)^2.

On the fixed line |tan(pi s)|=1. Standard gamma-ratio asymptotics [4] show that
both kernels are O((1+|Im(s)|)^(-2)). The two parameter shifts have cancelling
sum, so this bound is uniform on compact u-disks with |u|<1/8. The relevant
trigamma factors also have uniform polynomial bounds. A small Cauchy contour
in the u-plane, or direct dominated differentiation, justifies differentiating
the Barnes integrals twice.

Define d(s)=psi_1(1/2-s)-psi_1(1-s). Differentiation gives

    A_uu(s,0)=2 M1(s) d(s),
    B_uu(s,0)=2 M2(s) psi_1(1/2-s).              (2)

First derivatives vanish by u-evenness. There are no moving left numerator
poles in either family on the specified neighborhood.

## 3. The fourth-power component

At s=-n+e, the retained gamma/polygamma expansion is

    Gamma(-n+e)/Gamma(1/2-n+e)
       = a_n/(sqrt(pi)*e) * (1+2 h_n e+O(e^2)).

Therefore M1 has simple residue pi a_n^4 at s=-n. Since d(-n)=delta_n,
the first identity of (2) has residue 2 pi a_n^4 delta_n. Summing the
absolutely convergent residues proves G13''(0)=2 pi D4.

An independent normalization check is the ordinary hypergeometric expression

    G13(u) = [tan(pi u)/u]
      4F3(1/2+u,1/2-u,1/2,1/2;1+u,1-u,1;1).

The prefactor is analytically continued at zero with value pi. This identity
is used only as a check; no new parameter limit is proposed as a final answer.
Its quadratic coefficient gives exactly the earlier D4 derivative formula.

## 4. The sixth-power component: contour reflection removes one insertion

Use proof-only integrals

    IP = (1/(2 pi i)) int M2(s) psi_1(1/2-s) ds,
    IQ = (1/(2 pi i)) int M2(s) psi_1(1-s) ds.

By (2), G22''(0)=2 IP.
Near s=-n+e,

    M2(s)=a_n^4/e^2 * (1+8 h_n e+O(e^2)).

The polygamma recurrences [3] give

    d(-n)=delta_n,
    d'(-n)=psi_2(n+1)-psi_2(n+1/2)=tau_n.

Hence the residue of M2(s)d(s) is a_n^4(8 h_n delta_n+tau_n).
The inherited project identity stated at the beginning now yields

    IP-IQ=pi^2 D6.                              (3)

The residues can be justified first at a real argument below one and then
by dominated convergence. Equivalently, closing the difference kernel at
one on left contours separated from its integer poles is valid: the gamma
ratio and the trigamma difference have uniform polynomial decay there.
The polygamma factors introduce no additional left poles.

Next reflect the IQ contour about Re(s)=1/4. Orientation and the Jacobian
cancel, while M2 is unchanged. This gives

    IQ = (1/(2 pi i)) int M2(s) psi_1(1/2+s) ds.

Trigamma reflection [3] states

    psi_1(1/2-s)+psi_1(1/2+s)=pi^2 sec(pi s)^2.

Introduce the proof-only gamma kernel

    M0(s)=Gamma(1/2-s)^4/Gamma(1-s)^4.

Exact gamma reflection gives M2(s) sec(pi s)^2=M2(s)+M0(s).
The contour integral of M0 at argument one is zero. Here is a direct proof
rather than a formal omission of a boundary term. M0 is analytic throughout
Re(s)<1/2. Shift its vertical contour from Re(s)=1/4 to Re(s)=-R. On that
line the gamma-ratio bound gives

    |M0(-R+it)| <= C/(R^2+t^2)

for sufficiently large R, with a constant independent of t and R. Horizontal
segments vanish when their heights tend to infinity. Thus the absolute
integral on the shifted line is O(1/R), and sending R to infinity gives zero.
This follows from the standard ratio asymptotic uniformly in the corresponding
right half-plane [4]; no regularized value is used.

It follows that

    IP+IQ=pi^2 G22(0).                          (4)

Adding (3) and (4) and using G22''(0)=2 IP proves

    G22''(0)=pi^2 [D6+G22(0)],

which is the second identity in (1). This is an exact global consequence of
the retained wheel relation and contour reflection. It is not a pointwise
coefficient identity between the original fourth- and sixth-power sums.

## 5. Collect the actual weighted expression

Substitution of (1) gives

    BW = -393 pi^2 [4 G13''(0)+5 G22''(0)]
         +1965 pi^4 G22(0).                    (5)

Retain the known lower-period coefficients

    Cd = 96 Q -42 A^2 -18 A pi -1227 pi^2,
    Cs = 60 Q -105 A^2/4 -9 A pi -2469 pi^2/4.

The existing lower block is 4 pi^2 [Cd G13(0)+Cs G22(0)]. Combining it with
(5), its coefficient of G22(0) is changed, within this intermediate identity,
to

    CsTilde = Cs +1965 pi^2/4
            =60 Q -105 A^2/4 -9 A pi -126 pi^2.

Consequently

    Lower+BW = 4 pi^2 [Cd G13(0)+CsTilde G22(0)]
               -393 pi^2 [4 G13''(0)+5 G22''(0)].              (6)

The complete wheel direction now lives in two fourth-order Meijer-G families.
However, the final term in (6) still contains parameter derivatives. Equation
(6) is NOT installed as the user's requested final fixed-value expression.
No term in the accepted known polynomial is moved or changed. In particular,
no n=0 term, source correction, or elliptic primitive normalization is altered.

## 6. Numerical and exact checks

`verify.py` executes 47 finite checks: both full parameter-list identifications,
parameter parity and derivative factors, reflection algebra, integer and
half-integer polygamma recurrences at 12 indices, residue polynomials, the
linear two-integral elimination, and the complete weighted collection.
These finite tests do not independently prove the inherited core identity,
the contour convergence argument, or the physical graph/RG identification.

`numerical.py` evaluates the new Barnes kernels directly, with no use of a
reference value to construct an integrand. It compares the result with the
midpoints of the supplied exact wheel-component intervals. Those comparison
intervals were obtained in the previous standard-even calculation; their two
values F4,F6 equal D4/3,D6/3 respectively.

At 70 working decimal digits the new results are

    G13(0)  = 3.5142998559532377760924899462867170996085242281670731747433759893...
    G13''(0)=20.8012523427666160949877828560526039380037327211094676471014482151...
    G22(0)  = 5.6720109396954355002489582639189178306468844804866440480429353553...
    G22''(0)=88.7066853389184449809370366836439263998446087996380770674223266713...

They give

    D4=3.3106221328531753153524813631844503710928574491220805877231229395...
    D6=3.3158554158321918585143241125768512077640154194020057865224965985...

The D4 difference from the reference midpoint rounds to zero at that working
precision; the D6 discrepancy is approximately 1.449e-70. A separate 35-digit
run is retained. These are floating-point cross-checks, NOT new rigorous
interval certificates. The literal 1024-term sums are also recorded and have
remaining differences about 1.574e-11 and 2.004e-11; they are not treated as
high-precision reference values.

No Mathematica kernel execution and no fresh all-sector C6 evaluation were
performed. The Wolfram file deliberately exposes inactive derivatives and a
machine-readable status flag denying a completed fixed-value reduction.

## 7. Reproduction and output

Python 3 with SymPy and mpmath:

    python verify.py
    python numerical.py 35
    python numerical.py 70

`results/diagnostic_state.json` embeds the accepted input without modifying any
of its entries, records its SHA-256 hash, and appends the diagnostic identities
outside it. The known polynomial shift is zero. This diagnostic is not a
replacement numerical evaluator for C6.

## Sources

[1] NIST DLMF 16.17, Meijer G definition and hypergeometric expansion.
https://dlmf.nist.gov/16.17

[2] Wolfram Language, MeijerG parameter grouping and built-in interface.
https://reference.wolfram.com/language/ref/MeijerG.html

[3] NIST DLMF 5.15, polygamma recurrences, half-integer values, reflection.
https://dlmf.nist.gov/5.15

[4] NIST DLMF 5.11, gamma-ratio asymptotics.
https://dlmf.nist.gov/5.11

[5] Supplied C6_central_binomial_wheel_reduction.md, Section 2, especially
sum a_n^4(8 h_n delta_n+tau_n)=pi^2 D6. The project-specific proof and its
upstream qualifications remain inherited.

[6] Supplied C6_lower_MeijerG_expression.json and derivation. Accepted finite
lower-period normalization and full known polynomial; retained unchanged.
