(* Independent numerical check (not a proof step): the ORIGINAL position-space master at d=2,
   J_t = (1/pi^2) Int d^2x d^2y |x|^-1 |x-1|^-1 |y|^-1 |y-1|^(t-2) |x-y|^-1,  t = 2 tau,
   against Pi^2 (F(tau)^2 + F(1-tau)^2).  The inner x integral Phi(y) is first compared with
   8 Re[K(y) Conj[K(1-y)]] (parameter convention) at sample points; then that form is used for y. *)
FF[t_?NumericQ] := HypergeometricPFQ[{1/2, 1/2, t}, {1, 1}, 1];
phiNum[y_] := Module[{xs = Sort[{0, Re[y], 1}], ys = Sort[{0, Im[y]}]},
   NIntegrate[1/(Sqrt[x1^2 + x2^2] Sqrt[(x1 - 1)^2 + x2^2] Sqrt[(x1 - Re[y])^2 + (x2 - Im[y])^2]),
    Evaluate[Join[{x1, -Infinity}, xs, {Infinity}]], Evaluate[Join[{x2, -Infinity}, ys, {Infinity}]],
    PrecisionGoal -> 9, MaxRecursion -> 30]];
phiK[y_] := 8 Re[EllipticK[y] Conjugate[EllipticK[1 - y]]];
Do[Print["Phi check y=", y, ":  direct = ", NumberForm[phiNum[y], 12], "   8Re[K conj K'] = ", NumberForm[phiK[y], 12]],
  {y, {0.3 + 0.4 I, 2.1 + 0.7 I, -0.8 + 0.5 I, 1.7 - 0.05 I}}];
Jnum[tau_] := (2/Pi^2) NIntegrate[
    phiK[y1 + I y2]/(Sqrt[y1^2 + y2^2] ((y1 - 1)^2 + y2^2)^(1 - tau)),
    {y1, -Infinity, 0, 1, Infinity}, {y2, 0, Infinity}, PrecisionGoal -> 9, MaxRecursion -> 30];
Do[Print["J check tau=", tau, ":  position space = ", NumberForm[Jnum[tau], 12],
   "   Pi^2(F^2+F'^2) = ", NumberForm[N[Pi^2 (FF[tau]^2 + FF[1 - tau]^2), 15], 12]], {tau, {0.3, 0.6, 0.45}}];
Quiet@CloseKernels[];
Exit[0];
