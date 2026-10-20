(* Appendix A checks: 2D elliptic star F2(y) = (1/pi) int d^2x/(|x||x-1||x-y|) = pi [F(y) conj F(1-y) + c.c.],
   F = 2F1(1/2,1/2;1;.), and J_t(2D) = int d^2y |y|^-1 |1-y|^(t-2) * 2 Re[F(y) conj F(1-y)] = pi^2 F(t/2)^2 + sin^2 Gamma^4 G^2/Gamma^4 *)
Fh[z_] := Hypergeometric2F1[1/2, 1/2, 1, z];
F2closed[y_] := Pi (Fh[y] Conjugate[Fh[1 - y]] + Conjugate[Fh[y]] Fh[1 - y]);
(* direct 2D integral in polar coordinates around 0 *)
F2direct[y_?NumericQ] := 1/Pi NIntegrate[r/(r Abs[r Exp[I th] - 1] Abs[r Exp[I th] - y]), {r, 0, Abs[y], 1, 2, Infinity}, {th, 0, Arg[y], Pi, 2 Pi}, Method -> "GlobalAdaptive", MaxRecursion -> 30, PrecisionGoal -> 8, WorkingPrecision -> 20];
Print["F2 at y=0.3      : direct ", F2direct[3/10], "  closed ", N[Re[F2closed[3/10]], 12]];
Print["F2 at y=0.4+0.7i : direct ", F2direct[4/10 + 7/10 I], "  closed ", N[Re[F2closed[4/10 + 7/10 I]], 12]];
(* J_t with t=3/5 (tau=3/10): integrate over y in polar coords around y=1 to tame |1-y|^(t-2) *)
t = 3/5; tau = t/2;
Jint[w_?NumericQ, ph_?NumericQ] := Module[{y = 1 + w Exp[I ph]}, w Abs[y]^-1 w^(t - 2) Re[F2closed[y]]/Pi];
Jdirect = NIntegrate[Jint[w, ph], {w, 0, 1/2, 1, 2, Infinity}, {ph, 0, Pi/2, Pi, 3 Pi/2, 2 Pi}, Method -> "GlobalAdaptive", MaxRecursion -> 30, PrecisionGoal -> 7, WorkingPrecision -> 20];
fF = HypergeometricPFQ[{1/2, 1/2, tau}, {1, 1}, 1]; fG = HypergeometricPFQ[{tau, tau, tau}, {1/2 + tau, 1/2 + tau}, 1];
Print["J_t direct ", Jdirect, "   closed ", N[Pi^2 fF^2 + Sin[Pi tau]^2 Gamma[tau]^4 fG^2/Gamma[1/2 + tau]^4, 12]];

Quiet@CloseKernels[];
Exit[0];
