(* Copy of review_K2_d1template_numerics_r0/rC_position.wl (reviewer script), rerun by K2_d1template_fix1 at a new tau. *)
(* Review r0: original position-space master J_{2tau} = (1/pi^2) Int d^2y |y|^-1 |1-y|^(2tau-2) S(y),
   S(y) = Int d^2x/(|x||1-x||x-y|) = 8 Re[K(y) conj K(1-y)].
   Region split by Re y = 1/2, y -> 1-y symmetry of S, y -> conj y symmetry; polar coordinates around 0.
   Run at tau = 1/2 first (must equal 3 Q2 = Gamma(1/4)^8/(8 pi^4)) to validate code + star formula. *)
$MaxExtraPrecision = 200;
tau = ToExpression[$ScriptCommandLine[[2]]];
wp = ToExpression[$ScriptCommandLine[[3]]]; pg = ToExpression[$ScriptCommandLine[[4]]];
S[y_] := 8 Re[EllipticK[y] Conjugate[EllipticK[1 - y]]];
f[r_?NumericQ, ph_?NumericQ] := Module[{y = r Exp[I ph], ay, a1},
   ay = r; a1 = Abs[1 - y];
   r (ay^-1 a1^(2 tau - 2) + a1^-1 ay^(2 tau - 2)) S[y]];
inA[ph_?NumericQ] := NIntegrate[f[r, ph], {r, 0, 1/(2 Cos[ph])}, WorkingPrecision -> wp, PrecisionGoal -> pg + 3, MaxRecursion -> 30, Method -> "DoubleExponential"];
inB[ph_?NumericQ] := NIntegrate[f[r, ph], {r, 0, 1, Infinity}, WorkingPrecision -> wp, PrecisionGoal -> pg + 3, MaxRecursion -> 30, Method -> "DoubleExponential"];
t0 = AbsoluteTime[];
JA = NIntegrate[inA[ph], {ph, 0, Pi/2}, WorkingPrecision -> wp, PrecisionGoal -> pg, MaxRecursion -> 30, Method -> "DoubleExponential"];
JB = NIntegrate[inB[ph], {ph, Pi/2, Pi}, WorkingPrecision -> wp, PrecisionGoal -> pg, MaxRecursion -> 30, Method -> "DoubleExponential"];
Jps = 2 (JA + JB)/Pi^2;
F[t_] := HypergeometricPFQ[{1/2, 1/2, t}, {1, 1}, 1];
Jcf = N[Pi^2 (F[tau]^2 + F[1 - tau]^2), wp];
Print["tau = ", tau, "  position space J = ", N[Jps, pg + 2]];
Print["   pi^2(F^2+F'^2)          = ", N[Jcf, pg + 2]];
dd = SetPrecision[Jps, wp] - SetPrecision[Jcf, wp];
Print["   difference              = ", ScientificForm[N[SetPrecision[dd, 20], 5]], "   relative ", ScientificForm[N[SetPrecision[dd/Jcf, 20], 5]]];
If[tau == 1/2, Print["   3Q2 - pos space = ", ScientificForm[N[SetPrecision[N[Gamma[1/4]^8/(8 Pi^4), wp] - SetPrecision[Jps, wp], 20], 5]]]];
Print["   InputForm[Jps] = ", InputForm[Jps], "\n   InputForm[Jcf] = ", InputForm[Jcf], "\n   InputForm[Jps - Jcf] = ", InputForm[Jps - Jcf], "   Precision[Jps] = ", Precision[Jps]];
Print["   control: Jps - Jcf(tau + 10^-40) = ", InputForm[Jps - N[Pi^2 (F[tau + 10^-40]^2 + F[1 - tau - 10^-40]^2), wp]]];
Print["   time (s) = ", Round[AbsoluteTime[] - t0]];
Quiet@CloseKernels[]; Exit[0];
