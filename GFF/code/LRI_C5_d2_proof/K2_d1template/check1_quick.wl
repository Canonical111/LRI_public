(* quick numerical tests of J_{2tau} = Pi^2 (FF[tau]^2 + FF[1-tau]^2) at d=2 *)
$MaxExtraPrecision = 200;
FF[t_] := HypergeometricPFQ[{1/2, 1/2, t}, {1, 1}, 1];
GG[t_] := HypergeometricPFQ[{t, t, t}, {1/2 + t, 1/2 + t}, 1];
prec = 40;
(* 1. tetrahedron value: J at tau=1/2 should be 3 Q2 = Gamma(1/4)^8/(8 Pi^4) *)
v1 = N[2 Pi^2 FF[1/2]^2, prec];
v2 = N[Gamma[1/4]^8/(8 Pi^4), prec];
Print["J(1/2) = ", v1, "   3Q2 = ", v2, "   diff = ", v1 - v2];
(* 2. Hessian: Z2 = (Pi^2/2)(F'(1/2)^2 + F(1/2) F''(1/2)) vs 4 G Q2 *)
dF[t0_?NumericQ, k_] := Module[{r = 1/5, M = 64, pts},
   pts = Table[t0 + r Exp[2 Pi I j/M], {j, 0, M - 1}];
   k!/M Sum[FF[pts[[j + 1]]] (r Exp[2 Pi I j/M])^(-k), {j, 0, M - 1}]];
f0 = N[FF[1/2], prec]; f1 = Chop[N[dF[1/2, 1], prec]]; f2 = Chop[N[dF[1/2, 2], prec]];
z2 = (Pi^2/2) (f1^2 + f0 f2);
Print["Z2 from formula = ", z2, "   4 G Q2 = ", N[4 Catalan Gamma[1/4]^8/(24 Pi^4), prec]];
(* 3. Thomae check F(1-t) = Gamma(t) G(t)/(Gamma(1-t) Gamma(1/2+t)^2) at t = 3/10 *)
Print["Thomae: ", N[FF[1 - 3/10] - Gamma[3/10] GG[3/10]/(Gamma[7/10] Gamma[1/2 + 3/10]^2), 30]];
Quiet@CloseKernels[]; Exit[0];
