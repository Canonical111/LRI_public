# Source excerpts from the supplied GFF archive

Original member: `GFF/note/long_range_ising_condensed.tex`

SHA-256: `2663275fd14f7cbd39e35719396bf9125392a454e5c9400b0e02b72425805f01`

These excerpts are copied from the user-supplied note. The a_n one-point coefficients are separate inputs from the earlier conversation, not results quoted in this archive.

## General-dimensional C coefficients (original TeX lines 3287–3330)

```tex
Here $d$ is the physical spatial dimension, not the exponent-shift
parameter $d$ of Section~\ref{sec:shifts}. Set
\begin{equation}
 q=\frac d4,\qquad \epsilon=2s-d,\qquad
 \Delta_\phi=\frac{d-\epsilon}{4},\qquad
 \Delta_{\mathcal E}=\sum_{j=0}^5 C_j(d)\epsilon^j+O(\epsilon^6).
 \label{gs:conventions}
\end{equation}
The physical perturbative range is fixed $0<d<4$ and sufficiently small
positive $\epsilon$. The endpoint $d=4$ is not substituted into
unrenormalized power-subgraph formulas. Define
\begin{equation}\begin{aligned}
 A&=\psi_0(2q)+\psi_0(1)-2\psi_0(q),&
 R&=\psi_1(2q)-\psi_1(1),\\
 U&=\psi_2(q),& V&=\psi_2(1)+\psi_2(2q),&
 X&=\psi_3(2q)-\psi_3(1).
\end{aligned}\label{gs:psiBasis}\end{equation}
Here and below $Q=Q_d$, $P_4=P_4(d)$ and $P_5=P_5(d)$ have the
normalization of \eqref{gd:primitiveNormalization}: $P_3=3Q$.
The three additional dimension-dependent functions are denoted by
$\mathcal K_d,\mathcal L_d,Z_d$. Explicit series definitions are
\eqref{gs:Lseries}, \eqref{gs:Zseries} and \eqref{gs:Kseries}.
They are not free parameters. Sections~\ref{gdr:section} and
\ref{gdk:section} give shorter finite-sample evaluations of all three, and
\eqref{gdr:C5reduced} is \eqref{gs:C5} written in them.

The complete collected coefficients are
\begin{equation}\boxed{\begin{aligned}
 C_0(d)&=\frac d2,&C_1(d)&=-\frac16,&C_2(d)&=\frac A9,\\
 C_3(d)&=\frac{A^2+R-8Q}{108},\\
 648C_4(d)&=16P_4-A^3-8AQ-3AR+\frac{53}{2}U-3V.
\end{aligned}}\label{gs:C0C4}\end{equation}
\begin{equation}\boxed{\begin{aligned}
46656 C_5(d)={}&-1536\bigl(P_5+\mathcal K_d\bigr)
       +384AP_4-576\mathcal L_d-1728Q^2\\
 &+720A^2Q+1008QR+7152Z_d\\
 &-15A^4-90A^2R+414AU-108AV-117R^2-75X.
\end{aligned}}\label{gs:C5}\end{equation}
In particular, the extra Gamma factor associated with power-divergent
mass subgraphs cancels from the explicit coefficients of both physical
answers. It must nevertheless be retained until the graph and
fixed-point assembly is complete.

\paragraph{Exact one-dimensional specialization.}
```

## Tetrahedron Hessian in d=2 (original TeX lines 3916–3935)

```tex
\eqref{gs:etaTheta}. With $\gamma_C(x)=\Gamma(x)/\Gamma(1-x)$,
its normalized value simplifies to
\begin{equation}\boxed{
 W_3(2;b)=\frac12\frac{\gamma_C(b/4)^3}{\gamma_C(3b/4)}.
}\label{gs:W3d2}\end{equation}
All convergence inequalities hold in a neighborhood of $b=1$:
$0<b<4/3$ suffices for the displayed two-screening integral.
At $b=1$ its logarithmic derivative vanishes, and its logarithmic
second derivative is
\[
 \frac34\{\psi_1(1/4)-\psi_1(3/4)\}=12\Cat.
\]
Combining this with \eqref{gs:wheelJets} gives the exact check
\begin{equation}\boxed{
 Z_2=4\Cat\,Q_2,\qquad
 Q_2=\frac16\left[\frac{\Gamma(1/4)}{\Gamma(3/4)}\right]^4.
}\label{gs:Z2exact}\end{equation}
This is a derivation from a convergent integral identity, not an
integer-relation fit to the numerical value of $Z_2$.

```

## Closed nonprimitive masters in d=2 (original TeX lines 3955–4011)

```tex
At $d=2$ the tetrahedron normalization \eqref{gd:Qdef}, with $\mathcal T_2$ from
\eqref{gd:d2exact}, gives
\begin{equation}\boxed{
 Q_2=\frac16\left[\frac{\Gamma(1/4)}{\Gamma(3/4)}\right]^4
     =\frac{\Gamma(1/4)^8}{24\pi^4}.
}\label{gc:Q2}\end{equation}
Indeed, reflection gives $\Gamma(1/4)\Gamma(3/4)=\pi\sqrt2$, so the fourth
power of the ratio is $\Gamma(1/4)^8/(4\pi^4)$ \cite{DLMF5}. The factor
$1/6$ is that of $Q_d=\mathcal T_d/6$ in \eqref{gd:Qdef}; it must not be
dropped. Numerically,
\begin{equation}
 Q_2=12.7713811986469576577497636845240084220372849859347\ldots,
 \qquad Z_2=\frac{\Cat\,\Gamma(1/4)^8}{6\pi^4}.
 \label{gc:Q2number}
\end{equation}
The second identity is $Z_2=4\Cat Q_2$ of \eqref{gs:Z2exact}, written in the
same Gamma normalization.

For $a=\log2$, the dimension-two specialization of all coefficients is
\begin{equation}\boxed{\begin{aligned}
 C_0(2)&=1,&C_1(2)&=-\frac16,&C_2(2)&=\frac{4a}{9},\\
 C_3(2)&=\frac{4a^2}{27}-\frac{\Gamma(1/4)^8}{324\pi^4},\\
 648C_4(2)&=16P_4(2)-64a^3-32aQ_2-359\zeta(3),\\
 46656C_5(2)&=-1536\{P_5(2)+\mathcal K_2\}
 +1536aP_4(2)-576\mathcal L_2-1728Q_2^2\\
 &\quad +(11520a^2+28608\Cat)Q_2
 -3840a^4-21456a\zeta(3).
\end{aligned}}\label{gc:d2coefficients}\end{equation}
The remaining dimension-two masters in this display are the fixed
hypergeometric functions specified below, not new undetermined constants; the two
nonprimitive ones, $\mathcal K_2$ and $\mathcal L_2$, are evaluated in closed form in
Section~\ref{gc:d2closedForms}.
None of these identities is inferred from numerical values.

% Update of 2 October 2026: closed forms of L_2 and K_2 at d=2 (LRI_C5_d2_proof/, LRI_C5_d2_simplify/proof/); proofs in Sections gc:L2proof, gc:K2proof
\subsection{Closed forms of the two-dimensional nonprimitive masters}
\label{gc:d2closedForms}
The two masters of \eqref{gc:d2coefficients} that are neither primitive periods nor
Gamma values have closed forms in constants that are already present:
\begin{equation}\boxed{
 \LL_2=-2\log2\,P_4(2)=-\frac A2\,P_4(2)
 =-\frac{\log2}{2\pi^3}\bigl(B_-^2-B_+^2\bigr),
}\label{gc:L2closed}\end{equation}
\begin{equation}\boxed{
 \KK_2=32\Cat^2-28\zeta(3)\log2
 =\frac12\Bigl[\frac{\{\psi_1(\frac14)-\psi_1(\frac34)\}^2}{4}+AU\Bigr].
}\label{gc:K2closed}\end{equation}
Here $A=4\log2$ and $U=\psi_2(\frac12)=-14\zeta(3)$ are the values of
\eqref{gs:psiBasis} at $d=2$, $B_\pm$ are the retained one-dimensional values of
\eqref{fp:inheritedValues}, and $\psi_1(\frac14)-\psi_1(\frac34)=16\Cat$ by
\eqref{eq:quarterPolygamma}. The second form of \eqref{gc:K2closed} reads
$\KK_2=\frac12[\Phi_2+AU]$ with $\Phi_2=64\Cat^2$. The one-dimensional result
\eqref{eq:KprovedFinal} has the same shape, $\KK=\frac12[\Phi_1+AU]$ with
$\Phi_1=\psi_1(\frac14)\{3\psi_1(\frac14)-\psi_1(\frac34)\}$ and the $d=1$ values of
$A$ and $U$.

\paragraph{Status.}
```

## Qualification of the generic-dimensional master formulas (original TeX lines 571–612)

```tex
\subsection{Status of the analytic results}\label{c1:status}
The table separates what this note proves from what it takes as an input or
confirms only numerically. ``Proved here'' means that the note contains the
complete argument; ``conditional'' names the unproved input; ``numerical''
means agreement between independent evaluations, without an interval bound
unless one is stated. The numerical coefficients $C_6(d)$ for $d=2,3$,
$C_7(d)$ and $C_8(d)$ are sampling estimates with the allowances of
Section~\ref{sec:guide} and are not listed.
{\small
\begin{longtable}{@{}>{\raggedright\arraybackslash}p{0.33\textwidth}>{\raggedright\arraybackslash}p{0.22\textwidth}>{\raggedright\arraybackslash}p{0.39\textwidth}@{}}
\toprule Statement & Where & Status\\\midrule\endhead
\multicolumn{3}{@{}l}{\emph{One dimension}}\\
Graph weights, subtraction and RG assembly of $C_0$--$C_5$ & Secs.~\ref{sec:RG}, \ref{sec:graphs}, \ref{sec:assembly}; App.~\ref{app:certificate} & proved here; every four- and five-loop residue is listed exactly\\
$\KK$ \eqref{eq:KprovedFinal} & Sec.~\ref{app:KpsiProof} & proved here\\
Wheel reduction of $\LL$ & Sec.~\ref{app:LreductionProof} & proved here\\
$P_5(1)$ in five fixed values \eqref{eq:P5FixedAnswer} & Sec.~\ref{sec:P5FixedProof} & proved here\\
Graph integration of $C_5(1)$ & Sec.~\ref{sec:checks} & numerical: agrees with the closed form to $6\cdot10^{-13}$; not a bound\\
$C_6(1)=14331.68703275805\ldots$ \eqref{c1:c6nine} & Secs.~\ref{c1:c6analytic}, \ref{c6:analytic} & conditional: exact evaluation of a reduced expression that is taken as an input and derived neither here nor in \path{C6_research_note/}; confirmed numerically by the graph sum to $3\cdot10^{-11}$ relative\\
$C_6(1)=14331.6870328(5)$, graph sum & Sec.~\ref{app:C6Numerical} & numerical: exact sum over all graphs at quadrature degree 22, with an empirical convergence allowance\\
\multicolumn{3}{@{}l}{\emph{Two dimensions}}\\
$Q_2=\Gamma(\frac14)^8/(24\pi^4)$ & \eqref{gd:d2exact}, \eqref{gc:Q2} & proved here (complex Selberg integral, gamma reflection)\\
$Z_2=4\Cat Q_2$ \eqref{gs:Z2exact} & Sec.~\ref{gs:Z2section} & proved here: a complex Selberg integral for the two-screening integral \eqref{gs:W3d2}, with the wheel jets \eqref{gs:wheelJets}\\
$P_4(2)=(B_-^2-B_+^2)/(4\pi^3)$ \eqref{fp:P4two} & Sec.~\ref{fp:twoDimensional} & proved here: finite-Fourier two-mode theorem and the elliptic moments of Section~\ref{sec:oldmasters}; the mixed-moment integral and Stieltjes identity of \cite{Wan} are cited, not reproved (a proof without the Stieltjes identity is in \path{LRI_C5_d2_simplify/proof/})\\
$P_5(2)$, quadratic in $X_0$, $X_\pm$ \eqref{fp:P5two} & Sec.~\ref{fp:twoDimensional} & proved here: square-lattice factorization \eqref{fp:primitiveSquare}, the one-dimensional three-mode function \eqref{fx:eq:abc} and exact residue algebra\\
$\LL_2=-2\log2\,P_4(2)$ \eqref{gc:L2closed}, for the series \eqref{gs:Lseries} & Sec.~\ref{gc:L2proof} & proved here: elliptic lemmas of Section~\ref{sec:oldmasters} and one contour integral, with the Stieltjes identity of \cite{Wan} cited. A second proof is outlined there (full text in \path{LRI_C5_d2_proof/L2_structural/PROOF_L2.md}); two more, which avoid that identity, are in \path{LRI_C5_d2_simplify/proof/}\\
$\KK_2=32\Cat^2-28\zeta(3)\log2$ \eqref{gc:K2closed}, for the master-path definition \eqref{gs:Kdefinition} & Sec.~\ref{gc:K2proof} & proved here: position-space proof (rotation lemma, sum of two squares, Laurent extraction) with the one-dimensional lemmas of Section~\ref{app:KpsiProof}\\
$\KK_2$ also equals the series \eqref{gs:Kseries} and the spectral form \eqref{gs:Kspectral} & Sec.~\ref{gc:K2further} (outline) & proved in companion files: \path{LRI_C5_d2_proof/K2_gauss/proof_K2.md} and \path{LRI_C5_d2_simplify/proof/K2-parseval/}\\
Mixed-trace step \eqref{gs:RS}, for $0<\tau<\frac12$ & Sec.~\ref{gc:K2further} & proved in companion files: \path{LRI_C5_d2_proof/K2_d1template/proof_v2.md} (Corollary 2); at other $d$ it is input (M) of Section~\ref{gdk:conventions}\\
Closed form of $C_5(2)$ \eqref{gc:C5twoClosed} & Sec.~\ref{app:generalClosed} & proved here: exact algebra from the rows above and \eqref{gs:C5}\\
Finite-Fourier theorem and finite evaluation rules for $Q_d$, $P_4(d)$, $P_5(d)$ & Sec.~\ref{app:generalPeriodization} & proved here for $\frac12<q<1$, then by continuation\\
Finite Horn representation of $\LL_d$, $Z_d$, $\KK_d$ \eqref{gc:finiteClosure} & Sec.~\ref{app:generalClosed} & proved here for $\frac23<d<2$, then by continuation of the complete combination\\
\multicolumn{3}{@{}l}{\emph{General dimension}}\\
$C_0$--$C_5(d)$ \eqref{gs:C0C4}, \eqref{gs:C5} & Sec.~\ref{gs:patterns} & proved by exact computation: exact symbolic residues of the 26 four-loop and 129 five-loop classes (certificate and exact audit in \path{lri_general_special_functions_update/})\\
Spectral and series forms of $Q_d$, $P_4$, $\LL_d$, $Z_d$ \eqref{gs:primitiveWheel}, \eqref{gs:LZspectral}, \eqref{gs:QPseries}--\eqref{gs:Zseries} & Secs.~\ref{gs:logWheel}, \ref{gs:residueProof} & proved here\\
Spectral and series forms of $\KK_d$ \eqref{gs:Kspectral}, \eqref{gs:Kseries} & Secs.~\ref{gs:singleKernel}, \ref{gdk:status} & at $d=2$ proved in companion files (Section~\ref{gc:K2further}); at other $d$ conditional on input (M) and on extracting $[\tau^2]$ under the trace\\
Finite Fourier theorem, top-mode theorem and its product form, residue functional & Secs.~\ref{gdr:finite}, \ref{gdr:top}, \ref{gdr:residue}; status in \ref{gdr:status} & proved here; written proofs also in \path{LRI_C5_general_d/foundation/}, reviewed independently\\
Sample formulas for $\LL_d$, $Z_d$ and the reduced $C_5(d)$ & Secs.~\ref{gdr:samples}--\ref{gdr:C5}; checks in \ref{gdr:checks} & exact algebra on the rows above, rederived symbolically in an independent check; confirmed numerically to about $10^{-48}$\\
Sample formulas for $\KK_d$ & Secs.~\ref{gdk:threeNode}, \ref{gdk:continuation}; status in \ref{gdk:status} & at $d=2$ through the companion proofs of Section~\ref{gc:K2further}; elsewhere conditional on (M), on (J), and on (H) on the jet circle\\
Barnes representation of $\KK_d$ \eqref{gdk:KMB} & Sec.~\ref{gdk:positionSpace} & derived here without (M), (J), (H); not independently reviewed\\
\multicolumn{3}{@{}l}{\emph{Three dimensions}}\\
Determinant and rank-two identification of $Q_3$, $P_4(3)$, $P_5(3)$ & Secs.~\ref{d3:determinantProof}, \ref{app:d3RankTwo} & proved here\\
Specialization of $\LL_d$ and $Z_d$ to $d=3$ & Sec.~\ref{gdr:special}; conditions in \ref{gdr:status} & conditional: two identities derived in \path{LRI_C5_d3/} but not written out here; confirmed numerically to $10^{-51}$\\
```

