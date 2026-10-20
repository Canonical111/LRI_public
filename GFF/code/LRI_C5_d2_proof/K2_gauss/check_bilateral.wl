(* bilateral lemma: P(u) = sum_{k in Z} f(k+u), f(K) = Gamma(K+1/2)^3/(pi Gamma(K+1)^2 Gamma(K+1/2+tau)),
   claimed P(u) = Lhat sec^2(pi u) + c3 pi^3 tan(pi u) sec^2(pi u), c3 = -sin(pi tau)Gamma(1-tau)F(1-tau)/pi^3 *)
wp = 30;
chk[tau_, u_] := Module[{Spos, Sneg, Tt, Lh, c3, pred},
  Spos = Gamma[1/2 + u]^3/(Pi Gamma[1 + u]^2 Gamma[1/2 + tau + u]) HypergeometricPFQ[{1/2 + u, 1/2 + u, 1/2 + u, 1}, {1 + u, 1 + u, 1/2 + tau + u}, 1];
  Tt = Sin[Pi (u + 1)]^2 Sin[Pi (u + 1/2 + tau)]/Sin[Pi (u + 1/2)]^3;
  Sneg = Tt/Pi Gamma[1 - u]^2 Gamma[3/2 - u - tau]/Gamma[3/2 - u]^3 HypergeometricPFQ[{1 - u, 1 - u, 3/2 - u - tau, 1}, {3/2 - u, 3/2 - u, 3/2 - u}, 1];
  Lh = Sqrt[Pi]/Gamma[1/2 + tau] HypergeometricPFQ[{1/2, 1/2, 1/2}, {1, 1/2 + tau}, 1];
  c3 = -Sin[Pi tau] Gamma[1 - tau] HypergeometricPFQ[{1/2, 1/2, 1 - tau}, {1, 1}, 1]/Pi^3;
  pred = Lh Sec[Pi u]^2 + c3 Pi^3 Tan[Pi u] Sec[Pi u]^2;
  {N[Spos + Sneg, 25], N[pred, 25]}];
(* direct check of reflection form of f at a sample negative point *)
tau0 = 3/10; K0 = -37/10 + 1/5;
fdir = Gamma[K0 + 1/2]^3/(Pi Gamma[K0 + 1]^2 Gamma[K0 + 1/2 + tau0]);
frefl = (Sin[Pi (K0 + 1)]^2 Sin[Pi (K0 + 1/2 + tau0)]/Sin[Pi (K0 + 1/2)]^3)/Pi Gamma[-K0]^2 Gamma[1/2 - tau0 - K0]/Gamma[1/2 - K0]^3;
Print["reflection check: ", N[{fdir, frefl}, 20]];
Do[Print["tau=", tau, " u=", u, " : ", chk[tau, u]], {tau, {3/10, 1/7}}, {u, {1/5, 1/3, -2/7}}];

Quiet@CloseKernels[];
Exit[0];
