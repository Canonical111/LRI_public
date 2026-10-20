(* Check: on the Mellin line s = i nu, C(tau)*Re[R_tau(s) - S_tau(s)] = E2 tau + W tau^2 + O(tau^3),
   with E2, W as in gs:Kweights / gs:Kspectral, for general real a, b (here only b-a=q enters through C(tau)).
   Polygamma values at z_a = a + i nu, z_b = b + i nu are independent complex symbols:
   psi_k(z_a) = xa[k] + I ya[k], psi_k(z_b) = xb[k] + I yb[k]; conj values at conj arguments. *)
ClearAll["Global`*"];
K = 4;
pa[k_] := xa[k] + I ya[k]; pac[k_] := xa[k] - I ya[k];
pb[k_] := xb[k] + I yb[k]; pbc[k_] := xb[k] - I yb[k];
(* log R_tau(s) = lnG(a+s) - lnG(a+tau+s) + lnG(b-tau-s) - lnG(b-s), s = i nu: a+s=z_a, b-s=conj(z_b) *)
logR = Sum[-pa[k - 1] tau^k/k! + pbc[k - 1] (-tau)^k/k!, {k, 1, K}];
logRm = Sum[-pac[k - 1] tau^k/k! + pb[k - 1] (-tau)^k/k!, {k, 1, K}];   (* s -> -s *)
(* log S_tau = 2[lnG(a-t/4+s)-lnG(a+s)+lnG(a-t/4-s)-lnG(a-s)-lnG(b+t/4+s)+lnG(b+s)-lnG(b+t/4-s)+lnG(b-s)] *)
logS = 2 Sum[((-tau/4)^k (pa[k - 1] + pac[k - 1]) - (tau/4)^k (pb[k - 1] + pbc[k - 1]))/k!, {k, 1, K}];
D2 = Series[(Exp[logR] + Exp[logRm])/2 - Exp[logS], {tau, 0, 3}];
(* C(tau) = Gamma(2q)Gamma(tau)/Gamma(2q-tau) = 1/tau + cs + O(tau) *)
CC = 1/tau + cs + c1 tau;
expr = Series[CC Normal[D2], {tau, 0, 2}];
p = xa[0] + xb[0]; h = ya[0] - yb[0]; j = xa[1] - xb[1]; kk = ya[1] + yb[1]; r = xa[2] + xb[2];
E2 = -h^2/2 - 5 j/8;
W = (cs - p) E2 - h kk/2 - 5 r/32;
Print["[tau^0]: ", Simplify[SeriesCoefficient[expr, 0]]];
Print["[tau^1] - E2: ", Simplify[ComplexExpand[SeriesCoefficient[expr, 1] - E2]]];
Print["[tau^2] - W: ", Simplify[ComplexExpand[SeriesCoefficient[expr, 2] - W]]];

Quiet@CloseKernels[];
Exit[0];
