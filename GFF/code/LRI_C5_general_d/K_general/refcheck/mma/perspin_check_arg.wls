(* refcheck: independent Mathematica evaluation of ONE per-spin spectral integral vector (gs:w12, gs:LZspectral, gs:Kweights).
   usage: wolframscript -file perspin_check_arg.wls d l      (d, l rationals, e.g. 5/4 0)
   prints (1/Pi) Int_0^Inf of t^3, t^4, 4 t^4 w1, t^3 (w1^2 + w2/3), t^2 Kw  at WorkingPrecision 32 *)
args = $ScriptCommandLine; d = ToExpression[args[[2]]]; l = ToExpression[args[[3]]];
q = d/4; wp = 32;
cs = N[PolyGamma[0, 1] + PolyGamma[0, 2 q], wp]; p0q = N[PolyGamma[0, q], wp]; g2q = N[Gamma[2 q], wp];
vals[nu_?NumericQ] := vals[nu] = Module[{a = l/2 + q/2, b, za, zb, t, p0a, p0b, p1a, p1b, p2a, p2b, w1, w2, p, h, j, k, r, E2},
   b = a + q; za = a + I nu; zb = b + I nu;
   t = g2q Abs[Gamma[za]/Gamma[zb]]^2;
   p0a = PolyGamma[0, za]; p0b = PolyGamma[0, zb]; p1a = PolyGamma[1, za]; p1b = PolyGamma[1, zb];
   p2a = PolyGamma[2, za]; p2b = PolyGamma[2, zb];
   w1 = -p0q + Re[p0a + p0b]/2; w2 = Re[p1a - p1b]/8;
   p = Re[p0a + p0b]; h = Im[p0a - p0b]; j = Re[p1a - p1b]; k = Im[p1a + p1b]; r = Re[p2a + p2b];
   E2 = -h^2/2 - 5 j/8;
   {t^3, t^4, 4 t^4 w1, t^3 (w1^2 + w2/3), t^2 ((cs - p) E2 - h k/2 - 5 r/32)}];
comp[i_, nu_?NumericQ] := vals[nu][[i]];
st = AbsoluteTime[];
res = Table[NIntegrate[comp[i, nu], {nu, 0, Infinity}, WorkingPrecision -> wp, PrecisionGoal -> 22, MaxRecursion -> 30,
      Method -> {"DoubleExponential", "SymbolicProcessing" -> 0}]/Pi, {i, 1, 5}];
Print["d=", d, " l=", l, " ", StringRiffle[ToString[NumberForm[#, 26]] & /@ res, "  "], "   seconds=", Round[AbsoluteTime[] - st]];
Quiet@CloseKernels[];
Exit[0];
