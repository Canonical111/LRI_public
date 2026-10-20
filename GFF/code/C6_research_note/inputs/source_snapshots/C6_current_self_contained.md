# Current self-contained formula for C6(1)

This consolidates the accepted `C6_lower_MeijerG_expression.json`. Later wheel-curvature and primitive first-moment diagnostics did not change the coefficient. The completed finite Meijer-G reductions are retained. For compactness, the five ordinary seventh-sector terms and their logarithmic remainder are recombined using the already-established central-seventh identity.

The formula below is a complete representation of the retained corrected analytic coefficient, **not yet a finite special-value-only closed form**. Three explicitly defined convergent series remain. The physical graph/RG identification remains an inherited input.

## 1. Complete coefficient

Put
\[
\ell=\log2,\qquad A=\pi+4\ell,\qquad
Q=\frac{\Gamma(1/4)^4}{\pi},\qquad G=\operatorname{Catalan}.
\]
Then
\[
\boxed{\begin{aligned}
C_6(1)=\frac1{2187}\Big\{&E+B_{\mathrm{pol}}
-4\pi^2\rho_4\mathcal G_4
+192\pi(13X_{35}+11X_{44})
+16\pi^3\rho_8\mathcal G_8\\
&+R_W+24\pi^3\mathscr M_7
+192\pi^2\mathscr P_{\mathrm c}^{(3)}\Big\}.
\end{aligned}}
\]
Every quantity on the right is specified below. All displayed block coefficients are in r6 units, where r6=2187 C6(1).

## 2. Entire known polynomial

\[
\boxed{\begin{aligned}
E={}&\frac Q8\left[63A^3+120AG+79A\pi^2+2013\pi^3+54204\zeta(3)\right]
+Q^2(29\pi-249A)+P,\\
P={}&\frac{21}{640}A^5+\frac7{64}A^3\pi^2
+\frac{1149}{64}A^2\pi^3+\frac{7863}{16}A^2\zeta(3)\\
&+192AG(16G+3\pi^2)+\frac{14853}{640}A\pi^4
-\frac{544}{3}G\pi^3+\frac{37631}{128}\pi^5\\
&+\frac{722279}{48}\pi^2\zeta(3)-\frac{805959}{8}\zeta(5).
\end{aligned}}
\]
This is the full 18-monomial accepted polynomial. The source correction is already included; no additional source-repair polynomial is to be added. The old separated term -144 Q^3/pi has been absorbed by the full sixth-power Meijer-G replacement and is not present here.

## 3. Finite polylogarithmic block

In the standard multiple-polylogarithm convention,
\[
\boxed{B_{\mathrm{pol}}=4352\left[
(32G+9\pi^2)\Im\operatorname{Li}_{2,1}(i,1)
-64\Re\operatorname{Li}_{2,1,2}(i,1,1)\right].}
\]
To fix the software convention exactly, this is

```wolfram
4352 ((32 Catalan + 9 Pi^2) Im[PolyLog[1, 2, I]]
  - 64 Re[HarmonicPolyLog[{0, 1, 1, 0, 1}, I]])
```

Here `PolyLog[1,2,i]` is the Nielsen S_(1,2), equal to Li_(2,1)(i,1); the HPL word 01101 equals Li_(2,1,2)(i,1,1). Principal branches are used.

## 4. Four ordinary Meijer-G values

A superscript [j] on a parameter means j repetitions. The ordered parameter convention is the usual one: for G_(p,q)^(m,n), the first n upper parameters and first m lower parameters belong to numerator gamma groups. The remaining parameters belong to denominator gamma groups.

\[
\mathcal G_4=G_{5,5}^{2,3}\!\left(1\;\middle|\;
\begin{matrix}(\tfrac12)^{[4]},\alpha_4\\0^{[4]},\alpha_4\end{matrix}\right),
\]
\[
X_{35}=G_{6,6}^{3,5}\!\left(1\;\middle|\;
\begin{matrix}(\tfrac12)^{[6]}\\0^{[6]}\end{matrix}\right),\qquad
X_{44}=G_{6,6}^{4,4}\!\left(1\;\middle|\;
\begin{matrix}(\tfrac12)^{[6]}\\0^{[6]}\end{matrix}\right),
\]
\[
\mathcal G_8=G_{11,11}^{3,8}\!\left(1\;\middle|\;
\begin{matrix}-\tfrac14,(\tfrac12)^{[8]},\alpha_+,\alpha_-\\
0^{[8]},\tfrac34,\alpha_+,\alpha_-\end{matrix}\right).
\]

The lower-block parameters are
\[
X_4=42A^2+18A\pi+1227\pi^2-96Q,
\]
\[
Y_4=\frac{105}{4}A^2+9A\pi+\frac{2469}{4}\pi^2-60Q,
\]
\[
\boxed{\rho_4=\sqrt{X_4^2+Y_4^2},\qquad
\alpha_4=\frac1\pi\arctan\frac{Y_4}{X_4}.}
\]
For these fixed constants X4,Y4 are positive, fixing the real principal arctangent branch.

The eighth-block parameters are
\[
\rho_8=\sqrt{2177203-1028322\sqrt2},
\]
\[
d_8=\frac1{2\pi}\arctan\!\left(\frac{556}{1233-417\sqrt2}\right),
\qquad
\eta_8=\frac1{2\pi}\operatorname{arcosh}\!\left(\frac{1233-139\sqrt2}{\rho_8}\right),
\]
\[
\boxed{\alpha_\pm=d_8\pm i\eta_8.}
\]
The inverse functions take their principal real values. The repeated alpha entries in the Meijer-G lists do not cancel: they occur in two denominator groups. The accompanying `.wl` file spells out all four parameter splits.

## 5. Common finite harmonic quantities

For nonnegative integers N, define
\[
H_N^{(j)}=\sum_{r=1}^{N}\frac1{r^j},\qquad
H_N=H_N^{(1)},\qquad H_0^{(j)}=0,
\]
\[
a_n=\frac{\binom{2n}{n}}{4^n},\qquad
h_n=\ell+H_n-H_{2n},\qquad
\delta_n=\frac{\pi^2}{3}-4H_{2n}^{(2)}+2H_n^{(2)}.
\]
Only these ordinary finite harmonic numbers are used in the remaining series.

## 6. Wheel contribution, with its correct lower index

\[
\boxed{R_W=-393\pi^3\sum_{n=0}^{\infty}
a_n^4\left[8+5\pi(4n+1)a_n^2\right]\delta_n.}
\]
This wheel convention includes n=0. That term equals -1048 pi^5 -655 pi^6, and is already inside the sum. In particular this is not simply -393 pi^3 times the earlier wheel Wcentral, which started at n=1. Equivalently, R_W=-393 pi^3 Wcentral-1048 pi^5-655 pi^6. No extra correction is to be added to E.

## 7. Complete seventh-power sector

Set
\[
y_n=n+\frac14,\qquad u_n=1-14y_nh_n,
\]
\[
v_n=196y_nh_n^2-28h_n+7y_n(\delta_n-\pi^2),
\]
\[
T_n=80\pi^2y_n-26\pi u_n+11v_n,\qquad
K_n=28\pi^2y_n-10\pi u_n+3v_n.
\]
Then
\[
\boxed{\begin{aligned}
F_n={}&(98H_{2n}+74\ell-6\pi)T_n-98\pi K_n\\
&-98(11u_n-13\pi y_n)\left(\frac{\pi^2}{3}+4H_{2n}^{(2)}\right)\\
&-8624y_n\left[\zeta(3)-H_{2n}^{(3)}\right],
\end{aligned}}
\]
\[
\boxed{\mathscr M_7=\sum_{n=0}^{\infty}(-1)^na_n^7F_n.}
\]
This is the whole seventh sector, including the five ordinary Z-values appearing separately in the most recent finite-part files. Do not also add those five terms: they have been recombined here, using the retained exact central-seventh identity.

## 8. Cubic primitive

For m,n>=0 let k=m+n and define
\[
t_{m,k}=8h_m+H_k-H_m,\qquad
e_{m,k}=4\delta_m+H_k^{(2)}-H_m^{(2)}.
\]
In the next expression t_m,e_m mean t_(m,k),e_(m,k), and similarly for n:
\[
\boxed{\begin{aligned}
T_{m,n}={}&15t_mt_n(t_m+t_n)+15(t_me_n+t_ne_m)\\
&+72\pi(t_mt_n+H_k^{(2)})
+(30H_k^{(2)}+7\pi^2)(t_m+t_n)\\
&+28\pi^3-60\left[\zeta(3)-H_k^{(3)}\right].
\end{aligned}}
\]
\[
\boxed{\mathscr P_{\mathrm c}^{(3)}=
\sum_{m,n\ge0}\frac{a_m^4a_n^4}{\binom{m+n}{m}}\,T_{m,n}.}
\]
Both zero indices are included. Its normalization is P_a=2 pi^2 P_c^(3), so the master formula contains 96 P_a, as required. No initial term is separately added to E.

## 9. Recorded numerical value and scope

The inherited numerical value of the corrected analytic representation is
\[
C_6^{\mathrm{rep}}(1)=
14331.6870327580543204454632552462171183173230619887904582031423\ldots.
\]
No new all-sector numerical evaluation or physical graph/RG verification is claimed by this consolidation. The source interval certificate concerns the retained analytic representation.

The three remaining series are absolutely convergent in the supplied derivations. The current formula is fully specified, but a finite combination of fixed Mathematica built-in special-function values for all three residual sectors has not been established.

## Wolfram source

```wolfram
Get["C6_current_self_contained.wl"];
C6CurrentStatus[]
blocks = C6CurrentBlocks[];   (* every block is in r6 units *)
expr = C6CurrentExpression[]; (* full expression, divided by 2187 *)
```

The file defines every helper locally and loads no earlier project package. The infinite series remain `Inactive[Sum]`; it neither omits them nor replaces them with a numerical target. A missing built-in `HarmonicPolyLog` is reported explicitly. The source was statically checked but was not executed in a Wolfram kernel here.

## Source basis and finite transcription audit

- `C6_lower_MeijerG_expression.json`: accepted known polynomial, finite polylogarithmic block, and all four Meijer-G parameter lists.
- `C6_lower_MeijerG_derivation.md`: lower-period transformation and real parameter branch.
- `C6_even_sector_derivation.md`: complete even-sector weighting and zero-included wheel normalization.
- `C6_central_seventh_derivation.md`: exact recombination of the whole seventh sector.
- `C6_primitive_cubic_derivation.md`: cubic primitive coefficients and P_a normalization.
- `C6_primitive_first_moments_derivation.md`: confirms that subsequent moment diagnostics leave the accepted formula unchanged.
- `C6_certified_digits.txt`: inherited reference value.
- Wolfram documentation for `MeijerG`, `PolyLog`, and `HarmonicPolyLog`: software parameter and function conventions only, not the source of the Ising identities.

`C6_current_transcription_checks.json` records 25 finite transcription/algebra checks. These check consistency of this consolidation with the supplied formulas; they are not independent proofs of every inherited identity.
