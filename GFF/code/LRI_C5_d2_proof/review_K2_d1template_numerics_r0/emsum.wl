(* Euler-Maclaurin summation, independent of NSum:
   sum_{n>=n0} f(n) = sum_{n0}^{N-1} f(n) + Int_N^Inf f + f(N)/2 - sum_k B_{2k}/(2k)! f^{(2k-1)}(N),
   derivatives by a trapezoidal Cauchy circle of radius N/2; tail integral after x = N/u. *)
emSum[f_, n0_, Nn_, K_, wp_] := Module[{M = 320, R = Nn/2, vals, der, head, integ, g},
  head = Sum[N[f[n], wp], {n, n0, Nn - 1}];
  vals = Table[N[f[Nn + R Exp[2 Pi I j/M]], wp + 40], {j, 0, M - 1}];
  der[j_] := j!/M Total[vals Table[(R Exp[2 Pi I jj/M])^(-j), {jj, 0, M - 1}]];
  (* adaptive precision: LogGamma differences at z = Nn/u lose ~log10(z) digits *)
  g[u_?NumericQ] := Module[{z = SetPrecision[Nn/u, wp + 20 + Ceiling[Max[0, Log10[Nn/u]]]]}, N[f[z] Nn/u^2, wp]];
  (* the omitted piece u < 10^-1200 is O(Nn^-tau 10^(-1200 tau)/tau), below 10^-150 for tau >= 1/7 *)
  integ = NIntegrate[g[u], {u, 10^-1200, 10^-20, 1/10, 1/2, 1}, WorkingPrecision -> wp, PrecisionGoal -> wp - 15,
     MaxRecursion -> 40, Method -> "DoubleExponential"];
  Re[head + integ + N[f[Nn], wp]/2 - Sum[BernoulliB[2 k]/(2 k)! der[2 k - 1], {k, 1, K}]]];
