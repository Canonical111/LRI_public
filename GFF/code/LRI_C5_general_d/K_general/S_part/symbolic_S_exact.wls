(* exact (symbolic in q) versions of checks 3 and 4 of symbolic_S.wls *)
Cc[t_] := Gamma[2 q] Gamma[t]/Gamma[2 q - t];
Xd[t_] := (Gamma[q - t/2]/Gamma[q + t/2])^2;
basis = {A -> PolyGamma[0, 2 q] + PolyGamma[0, 1] - 2 PolyGamma[0, q], R -> PolyGamma[1, 2 q] - PolyGamma[1, 1],
   U -> PolyGamma[2, q], V -> PolyGamma[2, 1] + PolyGamma[2, 2 q], X -> PolyGamma[3, 2 q] - PolyGamma[3, 1]};
ser = Series[Cc[tau]^2 Xd[tau]^2, {tau, 0, 2}];
coefs = Table[SeriesCoefficient[ser, k], {k, -2, 2}];
claimed = {1, 2 A, 2 A^2 - R, (4 A^3)/3 - 2 A R + (2 V - U)/6, 2 A^4/3 - 2 A^2 R + R^2/2 + A (2 V - U)/3 - X/12} /. basis;
Print["3exact [tau^k](C^2X^2) - claimed: ", Simplify[coefs - claimed]];
eps = {PolyGamma[0, 1] + PolyGamma[0, 2 q] - 4 PolyGamma[0, q], (PolyGamma[1, 1] - PolyGamma[1, 2 q])/2,
   (PolyGamma[2, 1] + PolyGamma[2, 2 q] - PolyGamma[2, q])/6, (PolyGamma[3, 1] - PolyGamma[3, 2 q])/24};
sk = CoefficientList[Normal[Series[Exp[Sum[eps[[k]] x^k, {k, 1, 4}]], {x, 0, 4}]], x];
serS = Series[Cc[tau] Xd[tau]^2, {tau, 0, 3}];
Print["4exact s_k - Bell form: ", Simplify[Table[SeriesCoefficient[serS, k], {k, -1, 3}] - sk[[1 ;; 5]]]];
Quiet@CloseKernels[];
Exit[0];
