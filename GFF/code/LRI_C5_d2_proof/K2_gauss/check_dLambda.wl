wp = 50;
check[tau_] := Module[{f, S, Lh, dLh, X, Y, fF, fG, s, c, pred},
  f[x_] := HypergeometricPFQ[{1/2 + x, 1/2 + x, 1/2 + x, 1}, {1 + x, 1 + x, 1/2 + tau + x}, 1];
  S[x_] := Gamma[1/2 + x]^3/(Pi Gamma[1 + x]^2 Gamma[1/2 + tau + x]) f[x];
  dLh = Module[{e = 10^-20}, N[(S[e] - S[-e])/(2 e), wp]];
  fG = N[HypergeometricPFQ[{tau, tau, tau}, {1/2 + tau, 1/2 + tau}, 1], wp];
  X = N[Pi/2 Gamma[tau]^2/Gamma[1/2 + tau]^2, wp] fG;
  s = N[Sin[Pi tau], wp];
  pred = -2 s^2 N[Gamma[1 - tau], wp]/N[Pi, wp] X;
  {N[dLh, 30], N[pred, 30], N[dLh - pred, 5]}];
Do[Print[N[tau, 6], " ", check[tau]], {tau, {3/10, 2718/10000, 1/7}}];

Quiet@CloseKernels[];
Exit[0];
