(* Numerical check (NOT a proof step) of Lemma 1 of proof_v2.md:
     Phi(y) = Int_C d^2x / (|x| |1-x| |x-y|) = 8 Re[ K(y) Conjugate[K(1-y)] ],  y in C \ ((-oo,0] U [1,oo)).
   Independent evaluation of the left side: Feynman parameters, Cheng-Wu chart beta3 = 1,
   beta1 = s^2, beta2 = t^2, polar (s,t) = rho (cos psi, sin psi), and the elementary rho-integral
     Int_0^oo d rho / Sqrt[(1+rho^2)(A + B rho^2)] = K(1 - B/A)/Sqrt[A]   (A, B > 0),
   give the one-dimensional representation
     Phi(y) = 4 Int_0^{Pi/2} dpsi K(1 - B/A)/Sqrt[A],
     A = |y|^2 cos^2 psi + |1-y|^2 sin^2 psi,   B = cos^2 psi sin^2 psi.
   It uses neither the Stokes argument nor the closed form. K = EllipticK (parameter convention). *)
wp = 60;
phiFeyn[y_] := Module[{a2 = Abs[y]^2, b2 = Abs[1 - y]^2},
   4 NIntegrate[
     With[{A = a2 Cos[p]^2 + b2 Sin[p]^2, B = Cos[p]^2 Sin[p]^2}, EllipticK[1 - B/A]/Sqrt[A]],
     {p, 0, Pi/4, Pi/2}, WorkingPrecision -> wp, PrecisionGoal -> 45, MaxRecursion -> 40,
     Method -> "DoubleExponential"]];
phiClosed[y_] := 8 Re[EllipticK[y] Conjugate[EllipticK[1 - y]]];
ys = {1/2, 3/10 + 2/5 I, -6/5 + 7/10 I, 5/2 - 3/10 I, 1/2 + 2 I, 1 + I, -3 - 4 I, 1/2 + 10^-3 I,
      -7/10 + 10^-20 I, -7/10 - 10^-20 I, 3 + 10^-20 I, 3 - 10^-20 I, 1/10 + 1/100 I, 99/100 - 1/50 I};
Do[
  Module[{f = phiFeyn[y], c = N[phiClosed[SetPrecision[y, wp]], wp]},
   Print["y = ", InputForm[y], "   Phi (Feynman) = ", ToString[N[f, 40], InputForm], "\n      8Re[K conj K'] = ",
    ToString[N[c, 40], InputForm], "\n      log10|diff| ", If[f - c == 0, "< " <> ToString[N[-Accuracy[f - c], 3]],
      "= " <> ToString[N[Log10[Abs[f - c]], 3]]]]],
  {y, ys}];
Print["=== done ==="];
Quiet@CloseKernels[]; Exit[0];
