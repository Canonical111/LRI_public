(* Section 4 of proof_K2.md: numeric checks of the closed forms of the single lattice sums.
   Lhat   = sum_k Lambda_tau(k)                 = cos(pi tau) Gamma(tau) G(tau)/Gamma(1/2+tau)^2 + pi F(tau)/Gamma(tau)
   Phihat = sum_k Phi_tau(k)                    = Gamma(tau) Gamma(1-tau)^2 F(tau)
   Lhat'  = sum_k d/dK Lambda_tau(K)|_{K=k}     = -pi sin(pi tau) Gamma(tau) G(tau)/Gamma(1/2+tau)^2   (bilateral lemma + Thomae)
   gammahat  = sum_k Gamma(k+x)^2/k!^2          = Gamma(x)^2 Gamma(1-2x)/Gamma(1-x)^2                  (Gauss)
   gammahat' = sum_k d/dK[Gamma(K+x)^2/Gamma(K+1)^2]_{K=k} = -2 pi cot(pi x) gammahat                    (bilateral lemma)
   x = 1/2 - tau/2.  All sums are evaluated independently through HypergeometricPFQ (shifted-argument sums by a
   central finite difference in the shift v). *)
fF[t_] := HypergeometricPFQ[{1/2, 1/2, t}, {1, 1}, 1];
fG[t_] := HypergeometricPFQ[{t, t, t}, {1/2 + t, 1/2 + t}, 1];
Do[
  s = Sin[Pi tau]; c = Cos[Pi tau]; x = 1/2 - tau/2;
  SL[v_] := Gamma[1/2 + v]^3/(Pi Gamma[1 + v]^2 Gamma[1/2 + tau + v]) HypergeometricPFQ[{1/2 + v, 1/2 + v, 1/2 + v, 1}, {1 + v, 1 + v, 1/2 + tau + v}, 1];
  Sg[v_] := Gamma[v + x]^2/Gamma[v + 1]^2 HypergeometricPFQ[{v + x, v + x, 1}, {v + 1, v + 1}, 1];
  Lh = N[SL[0], 60];
  dLh = Module[{e = 10^-22}, (N[SL[e], 80] - N[SL[-e], 80])/(2 e)];
  Ph = N[Gamma[1 - tau]^3/Gamma[3/2 - tau]^2 fG[1 - tau], 60];
  gh = N[Sg[0], 60];
  dgh = Module[{e = 10^-22}, (N[Sg[e], 80] - N[Sg[-e], 80])/(2 e)];
  Print["tau = ", tau];
  Print["  Lhat   - closed : ", N[Lh - (c Gamma[tau] fG[tau]/Gamma[1/2 + tau]^2 + Pi fF[tau]/Gamma[tau]), 5]];
  Print["  Phihat - closed : ", N[Ph - Gamma[tau] Gamma[1 - tau]^2 fF[tau], 5]];
  Print["  Lhat'  - closed : ", N[dLh + Pi s Gamma[tau] fG[tau]/Gamma[1/2 + tau]^2, 5], "   (finite-difference error ~1e-40)"];
  Print["  Thomae F(1-t) - Gamma(t)G(t)/(Gamma(1-t)Gamma(1/2+t)^2) : ", N[fF[1 - tau] - Gamma[tau] fG[tau]/(Gamma[1 - tau] Gamma[1/2 + tau]^2), 5]];
  Print["  Gauss  gammahat - closed  : ", N[gh - Gamma[x]^2 Gamma[1 - 2 x]/Gamma[1 - x]^2, 5]];
  Print["  gammahat' + 2 pi cot(pi x) gammahat : ", N[dgh + 2 Pi Cot[Pi x] gh, 5], "   (finite-difference error ~1e-40)"];
  , {tau, {3/10, 1/7, 2718/10000}}];

Quiet@CloseKernels[];
Exit[0];
