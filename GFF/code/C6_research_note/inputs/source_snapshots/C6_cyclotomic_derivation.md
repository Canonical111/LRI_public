# Two fourth-root-of-unity values for the complete C6 polylogarithmic block

## Result and scope

Input: `inputs/cubic_expression.json`, the supplied
`C6_primitive_cubic_expression.json`. The normalization remains
`r6 = 2187 C6(1)`.

This continuation replaces the three active inputs Lambda, H3real, H5real by
two absolutely convergent multiple-polylogarithm values at fourth roots of
unity. The standalone H5 term cancels exactly. The collected known polynomial
has 18 expanded monomials, rather than 20; its A^4*pi and A^2*G*pi terms vanish.

The three elliptic quantities Ecentral, M7central and PaCubic are UNCHANGED,
including the primitive normalization P_a=2*pi^2*PaCubic. This is not a
reduction of the primitive's two summation indices and is not a proof that
there are fewer arithmetically independent periods. The new weight-five MPL
has depth three instead of the old depth two. This is the relevant tradeoff
for the reduced number of named special-value inputs and simpler arguments.

The source repair and all upstream physical graph/RG identifications remain
inherited. No independent physical six-loop derivation or new interval
certificate is claimed. No full-C6 numerical target determines a coefficient.

## 1. Definitions and full reduced coefficient

Put
\[
 \ell=\log2,\qquad A=\pi+4\ell,\qquad
 Q=\frac{\Gamma(1/4)^4}{\pi},\qquad G=\beta(2).
\]
Use the strict convention
\[
 \operatorname{Li}_{s_1,\ldots,s_d}(z_1,\ldots,z_d)
 =\sum_{n_1>\cdots>n_d\ge1}
 \frac{z_1^{n_1}\cdots z_d^{n_d}}
      {n_1^{s_1}\cdots n_d^{s_d}}.
\]
The two new fixed values are
\[
 \boxed{\mathcal D_3=\Im\operatorname{Li}_{2,1}(i,1),\qquad
 \mathcal D_5=\Re\operatorname{Li}_{2,1,2}(i,1,1).}                 \tag{1}
\]
The subscripts 3 and 5 denote weight, not loop order. Equivalently,
\[
 \mathcal D_3=\sum_{n\ge1}\frac{\sin(n\pi/2)}{n^2}H_{n-1},
\]
\[
 \mathcal D_5=\sum_{n\ge1}\frac{\cos(n\pi/2)}{n^2}
          \sum_{m=1}^{n-1}\frac{H_{m-1}^{(2)}}m.                 \tag{2}
\]
All harmonic sums with upper bound zero vanish. Both series converge
absolutely; neither final value requires endpoint regularization.

The complete active formula is
\[
 \boxed{\begin{aligned}
 2187C_6(1)={}&E_{\rm cyc}
    +4352(32G+9\pi^2)\mathcal D_3-278528\mathcal D_5\\
    &+\pi^3\mathcal E_{\rm c}+24\pi^3\mathscr M_7
      +192\pi^2\mathscr P_{\rm c}^{(3)}.
 \end{aligned}}                                                 \tag{3}
\]
Here
\[
 \boxed{\begin{aligned}
 E_{\rm cyc}={}&\frac Q8\left[
 63A^3+120AG+79A\pi^2+2013\pi^3+54204\zeta(3)\right]\\
 &+Q^2(29\pi-249A)+\mathcal P_{\rm cyc},
 \end{aligned}}                                                 \tag{4}
\]
with the complete remaining elementary polynomial
\[
 \boxed{\begin{aligned}
 \mathcal P_{\rm cyc}={}&
 \frac{21}{640}A^5+\frac7{64}A^3\pi^2
 +\frac{1149}{64}A^2\pi^3+\frac{7863}{16}A^2\zeta(3)\\
 &+192AG(16G+3\pi^2)+\frac{14853}{640}A\pi^4
 -\frac{544}{3}G\pi^3\\
 &+\frac{37631}{128}\pi^5
 +\frac{722279}{48}\pi^2\zeta(3)-\frac{805959}{8}\zeta(5).
 \end{aligned}}                                                 \tag{5}
\]
The Q-dependent block is unchanged. No explicit pi^6 term is reintroduced.
The three elliptic definitions are retained in full in the exported JSON.

## 2. Two identities that perform the entire substitution

The inherited half-argument functions are
\[
 H_3=\sum_{n\ge0}\frac{\binom{2n}{n}}{8^n(2n+1)^3},\qquad
 H_5=2\operatorname{Li}_5(1/2).
\]
Define the finite elementary polynomials
\[
 K_3=\frac{7\pi^3}{192}+\frac{G\ell}{2}+\frac{\pi\ell^2}{16},     \tag{6}
\]
\[
 \boxed{\begin{aligned}
 K_5={}&-\frac14G^2\ell+\frac{29}{1152}G\pi^3
       +\frac1{32}G\pi\ell^2-\frac{13}{3072}\pi^4\ell\\
      &+\frac{2683}{9216}\pi^2\zeta(3)-\frac{\pi^2\ell^3}{768}
       -\frac{6447}{2048}\zeta(5)+\frac{\ell^5}{128}.
 \end{aligned}}                                                 \tag{7}
\]
Then
\[
 \boxed{\sqrt2H_3=\mathcal D_3+K_3,}                             \tag{8}
\]
\[
 \boxed{\Lambda=-\frac{\mathcal D_5+G\mathcal D_3}{3}
                   -\frac{15}{32}H_5+K_5.}                     \tag{9}
\]
The original definition is
\[
 \Lambda=\Re\operatorname{Li}_{3,2}(z,1/z),\qquad z=(1+i)/2.
\]
Equation (9) is a relation of convergent fixed values, proved below by finite
word operations and a published fifth-order summation. It is not an assumed
integer relation.

Inserting (8)-(9) into the COMPLETE old block gives
\[
 \boxed{\begin{aligned}
 &835584\Lambda+391680H_5
       +13056\sqrt2(32G+3\pi^2)H_3\\
 &\qquad=-278528\mathcal D_5+4352(32G+9\pi^2)\mathcal D_3
         +\Delta E,
 \end{aligned}}                                                 \tag{10}
\]
where
\[
 \Delta E=835584K_5+13056(32G+3\pi^2)K_3.                       \tag{11}
\]
In particular,
\[
 391680-835584\frac{15}{32}=0.
\]
There is no replacement special value for H5: its coefficient is zero.
The H3 and Lambda replacements contribute only the two values (1).

For independent coefficient checking,
\[
 \boxed{\begin{aligned}
 \Delta E={}&\frac{108800}{3}G\pi^3+19584G\pi^2\ell
  +52224G\pi\ell^2+1428\pi^5-3536\pi^4\ell\\
 &+2448\pi^3\ell^2+\frac{729776}{3}\pi^2\zeta(3)
 -1088\pi^2\ell^3-2630376\zeta(5)+6528\ell^5.
 \end{aligned}}                                                 \tag{12}
\]
Equivalently,
\[
 \boxed{\begin{aligned}
 \Delta E={}&\frac{51}{8}A^5-\frac{255}{8}A^4\pi
 +\frac{187}{4}A^3\pi^2+3264A^2G\pi+\frac{561}{4}A^2\pi^3\\
 &-1632AG\pi^2-\frac{9673}{8}A\pi^4
 +\frac{103904}{3}G\pi^3+\frac{19805}{8}\pi^5\\
 &+\frac{729776}{3}\pi^2\zeta(3)-2630376\zeta(5).
 \end{aligned}}                                                 \tag{13}
\]
Adding (13) to the complete INPUT polynomial gives exactly (4)-(5).
The original source-correction object is preserved, NOT added again.
No zero-index elliptic summand is moved into the polynomial.

## 3. A direct log-sine proof of the H3 identity

For 0<t<1, the binomial expansion followed by elementary integration gives
\[
 \int_0^t\frac{\log^2(t/x)}{\sqrt{1-x^2}}\,dx
 =2\sum_{n\ge0}\frac{a_nt^{2n+1}}{(2n+1)^3},\qquad
 a_n=\frac{\binom{2n}{n}}{4^n}.
\]
At t=1/sqrt(2), put x=sin(theta) and alpha=pi/4. This is
\[
 \sqrt2H_3=\int_0^{\pi/4}
  \left[\log(2\sin\theta)-\frac\ell2\right]^2d\theta.          \tag{14}
\]
The iterated integral H_011(w)=Li_(2,1)(w,1) satisfies
\[
 \frac{d}{dw}H_{011}(w)=\frac{\log^2(1-w)}{2w}.
\]
For 0<theta<pi,
\[
 \log(1-e^{2i\theta})=\log(2\sin\theta)+i(\theta-\pi/2).
\]
Consequently
\[
 \int_0^{\pi/4}\log^2(2\sin\theta)d\theta
 =\Im H_{011}(i)+\int_0^{\pi/4}(\theta-\pi/2)^2d\theta
 =\mathcal D_3+\frac{7\pi^3}{192}.                            \tag{15}
\]
At the lower endpoint H_011(1)=zeta(3) is real; it contributes no imaginary
constant. Also
\[
 \int_0^{\pi/4}\log(2\sin\theta)d\theta=-G/2.
\]
Substitution into (14) gives (8). The endpoint logarithms are integrable.
The HPL conventions, derivative rules and shuffle identities are standard
[2,3]; the log-sine reduction (14)-(15) fixes every normalization here.

## 4. Exact word reduction of Lambda

### 4.1 Reduce the strict double series to harmonic-polylogarithm words

Since z*(1/z)=1, set n=m+r in the defining strict sum. Absolute convergence
allows this reindexing:
\[
 \operatorname{Li}_{3,2}(z,1/z)=F(z)=\sum_{r\ge1}z^r C_r,
\]
\[
 C_r=\frac{\zeta(3)-H_r^{(3)}}{r^2}
       +\frac{3\zeta(2)-2H_r^{(2)}}{r^3}-\frac{3H_r}{r^4}.      \tag{16}
\]
For example, (16) follows from the exact partial fraction
\[
 \frac1{m^2(m+r)^3}=\frac1{r^3m^2}-\frac3{r^4m}
 +\frac3{r^4(m+r)}+\frac2{r^3(m+r)^2}+\frac1{r^2(m+r)^3}.
\]
Write H_w(z) using omega0=dz/z and omega1=dz/(1-z). Then
\[
 \boxed{\begin{aligned}
 F(z)={}&\zeta(3)H_{01}(z)+3\zeta(2)H_{001}(z)\\
 &-H_{01001}(z)-2H_{00101}(z)-3H_{00011}(z)-6H_{00001}(z).
 \end{aligned}}                                                 \tag{17}
\]
In particular Lambda=Re F(z) at z=(1+i)/2.

### 4.2 Finite transformation certificate, including endpoint constants

Only three exact operations are used: shuffle multiplication, reflection,
and the pullback phi(z)=z/(z-1). They obey [2,3]
\[
 H_uH_v=\sum_{w\in u\shuffle v}H_w,
\]
\[
 H_{a_1\ldots a_n}(1-z)=
 \sum_{j=0}^n(-1)^jH_{1-a_1,\ldots,1-a_j}(z)
             H_{a_{j+1},\ldots,a_n}(1),                         \tag{18}
\]
\[
 \phi^*\omega_0=\omega_0+\omega_1,\qquad
 \phi^*\omega_1=-\omega_1.                                    \tag{19}
\]
Endpoint values in (18) are shuffle-regularized inside the proof. In
particular H_0(1)=H_1(1)=0 in this convention. All final values (1), (8), (9)
are ordinary convergent values, with no regularization.

For transparency, the admissible endpoint identities through weight five
are generated by duality, shuffle and stuffle together with
\[
 \zeta(2,1)=\zeta(3),\quad
 \zeta(3,1)=\zeta(4)/4,\quad \zeta(2,2)=3\zeta(4)/4,
\]
\[
 \zeta(4,1)=2\zeta(5)-\zeta(2)\zeta(3),
\]
\[
 \zeta(3,2)=3\zeta(2)\zeta(3)-\tfrac{11}{2}\zeta(5),\quad
 \zeta(2,3)=\tfrac92\zeta(5)-2\zeta(2)\zeta(3).
\]
The last two follow by combining the weight-five shuffle and stuffle
products once Euler's formula for zeta(4,1) is inserted. Also
zeta(4)=2*zeta(2)^2/5. The full finite endpoint table is in the script.

Apply (18)-(19) to
\[
 \begin{aligned}
 &F(z)+F(1-z)
 +\frac13\big[H_{01101}(\phi(z))+H_{01101}(\phi(1-z))\big]\\
 &\quad+6\big[\operatorname{Li}_5(z)+\operatorname{Li}_5(1-z)\big]
 -\frac12\big[\operatorname{Li}_5(\phi(z))+
              \operatorname{Li}_5(\phi(1-z))\big].
 \end{aligned}                                                   \tag{20}
\]
Every independent weight-five HPL and every weight-four HPL cancels. The
remaining polynomial is exported verbatim in
`results/shuffle_certificate.json`. `shuffle_certificate.py` derives it
from the word rules instead of comparing two lists of decimal constants.

At z=(1+i)/2, use
\[
 1-z=\bar z,\qquad \phi(z)=-i,\qquad\phi(1-z)=i,
\]
\[
 H_0=-\ell/2+i\pi/4,\quad H_1=\ell/2+i\pi/4,
\]
\[
 H_{01}=\frac{5\pi^2}{96}-\frac{\ell^2}{8}
              +i\left(G-\frac{\pi\ell}{8}\right),
\]
\[
 \Re H_{001}=\frac{35}{64}\zeta(3)
                -\frac{5\pi^2\ell}{192}+\frac{\ell^3}{48}.
\]
Reflection fixes H_011 from H_001 and its conjugate. Write
J=Im Li3(z). The exact specialized result is
\[
 \boxed{\Lambda+\frac{\mathcal D_5}{3}
 +6\Re\operatorname{Li}_5(z)-\frac12\Re\operatorname{Li}_5(i)
 =R,}                                                           \tag{21}
\]
where
\[
 \boxed{\begin{aligned}
 R={}&-\frac{G^2\ell}{12}+\frac{GJ}{3}
 +\frac{5G\pi^3}{288}+\frac{G\pi\ell^2}{48}
 -\frac{473\pi^4\ell}{30720}\\
 &+\frac{2683\pi^2\zeta(3)}{9216}
 +\frac{\pi^2\ell^3}{192}+\frac{\ell^5}{640}.
 \end{aligned}}                                                 \tag{22}
\]
The finite shuffle certificate checks (21)-(22) symbolically.
There are no untracked constants from differentiation or analytic continuation.
The relevant paths avoid 0 and 1; principal branches at the stated points
are fixed by continuation from their convergent power series.

### 4.3 Remove the classical fifth-order and third-order intermediates

The required fifth-order identity is Broadhurst's PROVED equation (68),
with proof in Section 3.1 of [1], not one of that paper's unproved
higher-order ladder conjectures. In the present normalization it is
\[
 \boxed{\begin{aligned}
 \Re\operatorname{Li}_5((1+i)/2)={}&
 \frac5{32}\operatorname{Li}_5(1/2)+\frac{2139}{4096}\zeta(5)\\
 &-\frac{343}{184320}\pi^4\ell
 +\frac5{4608}\pi^2\ell^3-\frac{\ell^5}{960}.
 \end{aligned}}                                                 \tag{23}
\]
For an exact normalization check, his
B_5=16*ReLi5(z), A_5=Li5(1/2), and L_n=(-ell)^n/n! give
\[
 \widetilde B_5=16\Re\operatorname{Li}_5(z)
 -\frac52\operatorname{Li}_5(1/2)+\frac{\ell^5}{60}
 -\frac5{48}\zeta(2)\ell^3+\frac{343}{128}\zeta(4)\ell
 =\frac{69}{8}\frac{31}{32}\zeta(5).
\]
This is exactly equivalent to (23); it is checked in `formula.py`.

The elementary phase filter gives
\[
 \Re\operatorname{Li}_5(i)=-\frac{15}{512}\zeta(5).              \tag{24}
\]
Reflection of H_011 and inversion of Li3 [2,4] give
\[
 \boxed{J=-\mathcal D_3+\frac{3\pi^3}{128}
                  +\frac{\pi\ell^2}{32}-\frac{G\ell}{2}.}       \tag{25}
\]
For a branch check, put L=log(1-i)=ell/2-i*pi/4. Then
\[
 H_{011}(i)=\zeta(3)+\zeta(2)L-\tfrac12\log(i)L^2
              -\operatorname{Li}_2(i)L-\operatorname{Li}_3(1-i),
\]
with Li2(i)=-pi^2/48+iG. In the inversion formula use
log(-(1-i))=ell/2+3i*pi/4. Its imaginary part is
\[
 \Im[\operatorname{Li}_3(1-i)-\operatorname{Li}_3((1+i)/2)]
 =-\frac{3\pi\ell^2}{32}-\frac{7\pi^3}{128}.
\]
These equations prove (25), including its signs.

Substitute (23)-(25) into (21)-(22). Exact collection yields (9) with the
polynomial (7). The bridge between the word certificate and the exported
Lambda identity is checked independently in `verify.py`.

## 5. Convergence and evaluation

For n>=2,
\[
 H_{n-1}\le1+\log n,\qquad
 \sum_{m<n}\frac{H_{m-1}^{(2)}}m\le\zeta(2)(1+\log n).
\]
This proves absolute convergence of (2). For literal truncation at n<=N,
N>=1, integral comparison gives
\[
 |\mathcal D_3-\mathcal D_{3,N}|\le\frac{\log N+2}{N},\qquad
 |\mathcal D_5-\mathcal D_{5,N}|\le
 \zeta(2)\frac{\log N+2}{N}.                                   \tag{26}
\]
These are exact-arithmetic direct-tail bounds, excluding numerical rounding.
They are not being used to label a small literal cutoff as highly accurate.

For the numerical checks, the new values are evaluated independently of
Lambda. `numerical.py` starts their own strict multiple sums at i/2, and
continues all suffix HPLs to 3i/4 and then i. For a step z=c+delta*t, write
H_(a,w)=sum b_n*t^n and H_w=sum a_n*t^n. Their exact Taylor recurrences are
\[
 b_{n+1}=\frac{\delta}{c(n+1)}(a_n-nb_n),\quad a=0,
\]
\[
 b_{n+1}=\frac{\delta}{(1-c)(n+1)}(a_n+nb_n),\quad a=1.         \tag{27}
\]
Both steps remain inside the analytic disks about c. This evaluates the new
MPL definitions, not the right side of (9). Lambda is separately computed
from the geometric diagonal series (16), and H3,H5 from their original
half-argument series. This implementation uses floating point and is NOT a
new interval certificate.

Values begin
\[
 \mathcal D_3=-0.113648917599903643441539501971145908418275607824704791929109\ldots,
\]
\[
 \mathcal D_5=0.032383901800869146760958099191565832743421490993408168591163619729\ldots.
\]
The executable runs give:

| Working decimal digits | H3 identity residual | Lambda identity residual | Complete weighted polylog block residual |
|---:|---:|---:|---:|
| 90 | 2.455e-91 | 1.535e-91 | 0 at working precision |
| 140 | 2.625e-141 | 3.199e-141 | 2.752e-135 |
| 200 | 1.634e-201 | 7.757e-201 | 8.562e-195 |

Zero at working precision is not a proof of exact equality. The analytic
word and substitution identities above provide the proof.

Using INHERITED interval midpoints for the unchanged elliptic quantities,
the new formula reassembles to
\[
 C_6^{\rm rep}(1)=14331.6870327580543204454632552462171183173230619887904582031423\ldots.
\]
Digits beyond the accuracy of those inherited intervals are not being
certified by the 200-digit working run. This remains the value of the saved
analytic representation, not an independent physical normalization check.

## 6. Exact tests, reproduction and provenance

`verify.py` passes 43 grouped exact checks, including all 196 shuffle
products of total weight at most five, the specialized lower polynomial,
the bridge to (9), the published Li5 normalization, the two eliminated
monomials, and preservation of every active elliptic definition and source
correction. These are implementation checks, not 43 independent theorems.

Run, without network access:

```text
python shuffle_certificate.py
python formula.py
python verify.py
python numerical.py 60
python numerical.py 110
python numerical.py 170
```

The complete formula, with all three inherited elliptic summands, is in
`results/updated_expression.json`. Earlier formula objects remain explicitly
marked as provenance. No old H3,H5 or Lambda appears in the active formula
or active special-value lists.

## References

[1] D. J. Broadhurst, *Polylogarithmic ladders, hypergeometric series and the ten
millionth digits of zeta(3) and zeta(5)*, arXiv:math/9803067. Definitions
(25)-(35),(58); proved identity (68); proof Section 3.1.
https://arxiv.org/html/math/9803067

[2] E. Remiddi and J. A. M. Vermaseren, *Harmonic Polylogarithms*,
arXiv:hep-ph/9905237. Iterated integrals, shuffle products, endpoint reduction,
and argument transformations. These are general tools, not an Ising result.
https://arxiv.org/html/hep-ph/9905237

[3] E. Panzer, *Algorithms for the symbolic integration of hyperlogarithms with
applications to Feynman integrals*, arXiv:1403.3385. General iterated-integral
and shuffle context; the finite certificate (17)-(22) is supplied here.
https://arxiv.org/html/1403.3385

[4] NIST DLMF Section 25.12, *Polylogarithms*, series, reflection and inversion
conventions. https://dlmf.nist.gov/25.12

[5] Supplied `C6_primitive_cubic_expression.json` and preceding derivations:
complete starting coefficients, special-function normalizations, cubic
primitive, source repair, and inherited graph/RG assumptions.
