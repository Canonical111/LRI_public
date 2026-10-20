(* Fragment check 2: symbolic Laurent expansion of Delta(tau) = J^Gamma_{2tau} - C(tau)^2 X_d(tau)^2 at general q.
   Claim in the fragment: Delta = (3/2) U tau + A U tau^2 + O(tau^3), A, U of gs:psiBasis. *)
Cc[t_] := Gamma[2 q] Gamma[t]/Gamma[2 q - t];
Xd[t_] := (Gamma[q - t/2]/Gamma[q + t/2])^2;
Bd[d_, a_, b_] := Gamma[d/2] Gamma[(d - a)/2] Gamma[(d - b)/2] Gamma[(a + b - d)/2]/(Gamma[a/2] Gamma[b/2] Gamma[(2 d - a - b)/2]);
JG[t_] := Bd[4 q, 2 q, 4 q - 2 t]^2 + (Bd[4 q, 2 q, 4 q - 2 t] - Bd[4 q, 2 q + 4 t, 4 q - 2 t])/t;
ser = Series[JG[tau] - (Cc[tau] Xd[tau])^2, {tau, 0, 2}];
coefs = Table[SeriesCoefficient[ser, k], {k, -2, 2}];
AA = PolyGamma[0, 2 q] + PolyGamma[0, 1] - 2 PolyGamma[0, q]; UU = PolyGamma[2, q];
claimed = {0, 0, 0, 3/2 UU, AA UU};
Print["Delta Laurent coefficients minus claim (k=-2..2): ", FullSimplify[coefs - claimed]];
(* numerical spot check of the same difference at q = 0.3, 0.7 with 40 digits *)
Print["numeric q=0.3: ", N[(coefs - claimed) /. q -> 3/10, 40]];
Print["numeric q=0.7: ", N[(coefs - claimed) /. q -> 7/10, 40]];
(* W_2 identity: B_d(d-b',2b') at b' = d/2 - tau equals C X_d *)
Print["W2 identity: ", FullSimplify[Bd[4 q, 2 q + tau, 4 q - 2 tau]/(Cc[tau] Xd[tau]) - 1]];
Quiet@CloseKernels[];
Exit[0];
