(* Explicit Laurent data used in the write-up (exact). *)
Bd[d_, a_, b_] := Gamma[d/2] Gamma[(d - a)/2] Gamma[(d - b)/2] Gamma[(a + b - d)/2]/(Gamma[a/2] Gamma[b/2] Gamma[(2 d - a - b)/2]);
JG[t_] := Bd[2, 1, 2 - t]^2 + (2/t) (Bd[2, 1, 2 - t] - Bd[2, 1 + 2 t, 2 - t]);
ser = Series[JG[2 tau], {tau, 0, 2}];
Print["J^Gamma_{2tau} Laurent coefficients tau^-2..tau^2:"];
Do[Print["  ", k, " : ", FullSimplify[FunctionExpand[SeriesCoefficient[ser, k]]]], {k, -2, 2}];
Q2 = (Pi Gamma[1 + tau]/(Gamma[1 - tau] Gamma[1/2 + tau]^2))^2;
sq = Series[Q2, {tau, 0, 4}];
Print["Q(tau)^2 coefficients tau^0..tau^4:"];
Do[Print["  ", k, " : ", FullSimplify[FunctionExpand[SeriesCoefficient[sq, k]]]], {k, 0, 4}];
Print["log Q^2 series: ", FullSimplify[FunctionExpand[Normal[Series[Log[Q2], {tau, 0, 4}]]]]];
(* compare with the note's general-d [t^2] J^Gamma at q = 1/2 *)
q = 1/2;
A = PolyGamma[0, 2 q] + PolyGamma[0, 1] - 2 PolyGamma[0, q]; R = PolyGamma[1, 2 q] - PolyGamma[1, 1];
U = PolyGamma[2, q]; V = PolyGamma[2, 1] + PolyGamma[2, 2 q]; X = PolyGamma[3, 2 q] - PolyGamma[3, 1];
noteJG = A^4/6 - A^2 R/2 + R^2/8 + A (V + U)/6 - X/48;
Print["[t^2]J^Gamma (direct) - note formula = ", FullSimplify[FunctionExpand[SeriesCoefficient[ser, 2]/4 - noteJG]]];
Print["A2 = ", FullSimplify[FunctionExpand[A]], "   U2 = ", FullSimplify[FunctionExpand[U]]];
Quiet@CloseKernels[]; Exit[0];
