(* refcheck: independent Mathematica evaluation of per-spin spectral integrals (gs:w12, gs:LZspectral, gs:Kweights)
   at d = 5/4 for spins l = 0, 3.  (1/Pi) Int_0^Inf of t^3, t^4, 4 t^4 w1, t^3 (w1^2 + w2/3), t^2 Kw,
   to compare with routeA_spectral.perspin / routeB_residue.inner_sum.  WorkingPrecision 32. *)
d = 5/4; q = d/4; wp = 32;
cs = N[PolyGamma[0, 1] + PolyGamma[0, 2 q], wp]; p0q = N[PolyGamma[0, q], wp]; g2q = N[Gamma[2 q], wp];
vals[l_, nu_?NumericQ] := Module[{a = l/2 + q/2, b, za, zb, t, p0a, p0b, p1a, p1b, p2a, p2b, w1, w2, p, h, j, k, r, E2},
   b = a + q; za = a + I nu; zb = b + I nu;
   t = g2q Abs[Gamma[za]/Gamma[zb]]^2;
   p0a = PolyGamma[0, za]; p0b = PolyGamma[0, zb]; p1a = PolyGamma[1, za]; p1b = PolyGamma[1, zb];
   p2a = PolyGamma[2, za]; p2b = PolyGamma[2, zb];
   w1 = -p0q + Re[p0a + p0b]/2; w2 = Re[p1a - p1b]/8;
   p = Re[p0a + p0b]; h = Im[p0a - p0b]; j = Re[p1a - p1b]; k = Im[p1a + p1b]; r = Re[p2a + p2b];
   E2 = -h^2/2 - 5 j/8;
   {t^3, t^4, 4 t^4 w1, t^3 (w1^2 + w2/3), t^2 ((cs - p) E2 - h k/2 - 5 r/32)}];
comp[i_, l_, nu_?NumericQ] := vals[l, nu][[i]];
res = TimeConstrained[Table[
   {l, Table[NIntegrate[comp[i, l, nu], {nu, 0, Infinity}, WorkingPrecision -> wp, PrecisionGoal -> 22,
       MaxRecursion -> 30, Method -> {"DoubleExponential", "SymbolicProcessing" -> 0}]/Pi, {i, 1, 5}]},
   {l, {0, 3}}], 1500, $Failed];
If[res === $Failed, Print["TIMEOUT"], Do[Print["l=", r[[1]], " ", StringRiffle[ToString[NumberForm[#, 26]] & /@ r[[2]], "  "]], {r, res}]];
Quiet@CloseKernels[];
Exit[0];
