(* Euler-Maclaurin summation sum_{k>=0} f(k) for f analytic in Re k > -1/2 with algebraic-log decay.
   head to NN-1, tail integral by NIntegrate, odd derivatives at NN by a Cauchy/FFT circle of radius NN/2. *)
$wp = 130;
emsum[f_, NN_:160, J_:30, P_:256] := Module[{head, tail, r = NN/2, vals, d, w = $wp, k},
  head = Sum[f[SetPrecision[kk, w]], {kk, 0, NN - 1}];
  tail = NIntegrate[f[k], {k, NN, Infinity}, WorkingPrecision -> w, PrecisionGoal -> w - 45,
     MaxRecursion -> 40, Method -> "DoubleExponential"];
  vals = Table[f[SetPrecision[NN + r Exp[2 Pi I p/P], w]], {p, 0, P - 1}];
  d[n_] := n!/r^n Sum[vals[[p + 1]] Exp[-2 Pi I n p/P], {p, 0, P - 1}]/P;
  head + tail + f[SetPrecision[NN, w]]/2 - Sum[BernoulliB[2 j]/(2 j)! d[2 j - 1], {j, 1, J}]];
re[z_] := If[Abs[Im[z]] < 10^-($wp - 40) Max[1, Abs[z]], Re[z], z];
