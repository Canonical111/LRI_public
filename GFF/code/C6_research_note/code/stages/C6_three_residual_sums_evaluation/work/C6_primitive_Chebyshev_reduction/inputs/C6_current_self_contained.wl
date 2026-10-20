(* Current complete C6(1) representation, consolidated from the supplied derivations.
   r6 = 2187 C6(1). This is NOT a finite special-value-only closed form.
   All three remaining infinite series are explicit and INACTIVE.
   No external project files or packages are loaded.
   This source has not been executed in a Wolfram kernel in this session. *)
BeginPackage["C6Current`"];
C6CurrentExpression::usage = "C6CurrentExpression[] returns the full C6(1), with its three remaining series as Inactive[Sum].";
C6CurrentBlocks::usage = "C6CurrentBlocks[] returns all eight contributions in r6 units; none of the three remaining blocks is omitted.";
C6CurrentStatus::usage = "C6CurrentStatus[] states normalization and limitations without evaluating special values.";
Begin["`Private`"];

binCoef[n_] := Binomial[2 n, n]/4^n;
harmh[n_] := Log[2] + HarmonicNumber[n] - HarmonicNumber[2 n];
delta[n_] := Pi^2/3 - 4 HarmonicNumber[2 n, 2] + 2 HarmonicNumber[n, 2];

seventhCoefficient[n_] := Module[{y, u, v, tt, kk},
  y = n + 1/4;
  u = 1 - 14 y harmh[n];
  v = 196 y harmh[n]^2 - 28 harmh[n] + 7 y (delta[n] - Pi^2);
  tt = 80 Pi^2 y - 26 Pi u + 11 v;
  kk = 28 Pi^2 y - 10 Pi u + 3 v;
  (98 HarmonicNumber[2 n] + 74 Log[2] - 6 Pi) tt - 98 Pi kk
    - 98 (11 u - 13 Pi y) (Pi^2/3 + 4 HarmonicNumber[2 n, 2])
    - 8624 y (Zeta[3] - HarmonicNumber[2 n, 3])
];

primitiveCoefficient[m_, n_] := Module[{k, tm, tn, em, en, h2},
  k = m + n;
  tm = 8 harmh[m] + HarmonicNumber[k] - HarmonicNumber[m];
  tn = 8 harmh[n] + HarmonicNumber[k] - HarmonicNumber[n];
  em = 4 delta[m] + HarmonicNumber[k, 2] - HarmonicNumber[m, 2];
  en = 4 delta[n] + HarmonicNumber[k, 2] - HarmonicNumber[n, 2];
  h2 = HarmonicNumber[k, 2];
  15 tm tn (tm + tn) + 15 (tm en + tn em)
    + 72 Pi (tm tn + h2) + (30 h2 + 7 Pi^2) (tm + tn)
    + 28 Pi^3 - 60 (Zeta[3] - HarmonicNumber[k, 3])
];

C6CurrentBlocks[] := Module[
  {aa, qq, gg, ep, e, bp, hpl, x4, y4, rho4, alpha4,
   rho8, d8, eta8, ap, am, g4, x35, x44, g8, n, m, rw, r7, ra},
  If[Names["System`HarmonicPolyLog"] === {},
    Return[Failure["MissingBuiltIn", <|
      "MessageTemplate" -> "This installation does not expose System`HarmonicPolyLog. No custom substitute was installed."
    |>]]
  ];
  hpl = ToExpression["System`HarmonicPolyLog"];
  aa = Pi + 4 Log[2];
  qq = Gamma[1/4]^4/Pi;
  gg = Catalan;
  ep = 21 aa^5/640 + 7 aa^3 Pi^2/64 + 1149 aa^2 Pi^3/64
    + 7863 aa^2 Zeta[3]/16 + 192 aa gg (16 gg + 3 Pi^2)
    + 14853 aa Pi^4/640 - 544 gg Pi^3/3 + 37631 Pi^5/128
    + 722279 Pi^2 Zeta[3]/48 - 805959 Zeta[5]/8;
  e = qq/8 (63 aa^3 + 120 aa gg + 79 aa Pi^2 + 2013 Pi^3 + 54204 Zeta[3])
    + qq^2 (29 Pi - 249 aa) + ep;
  bp = 4352 ((32 gg + 9 Pi^2) Im[PolyLog[1, 2, I]]
    - 64 Re[hpl[{0, 1, 1, 0, 1}, I]]);

  x4 = 42 aa^2 + 18 aa Pi + 1227 Pi^2 - 96 qq;
  y4 = 105 aa^2/4 + 9 aa Pi + 2469 Pi^2/4 - 60 qq;
  rho4 = Sqrt[x4^2 + y4^2];
  alpha4 = ArcTan[y4/x4]/Pi;
  g4 = MeijerG[
    {{1/2, 1/2, 1/2}, {1/2, alpha4}},
    {{0, 0}, {0, 0, alpha4}}, 1];
  x35 = MeijerG[
    {{1/2, 1/2, 1/2, 1/2, 1/2}, {1/2}},
    {{0, 0, 0}, {0, 0, 0}}, 1];
  x44 = MeijerG[
    {{1/2, 1/2, 1/2, 1/2}, {1/2, 1/2}},
    {{0, 0, 0, 0}, {0, 0}}, 1];

  rho8 = Sqrt[2177203 - 1028322 Sqrt[2]];
  d8 = ArcTan[556/(1233 - 417 Sqrt[2])]/(2 Pi);
  eta8 = ArcCosh[(1233 - 139 Sqrt[2])/rho8]/(2 Pi);
  ap = d8 + I eta8;
  am = d8 - I eta8;
  g8 = MeijerG[
    {{-1/4, 1/2, 1/2, 1/2, 1/2, 1/2, 1/2, 1/2}, {1/2, ap, am}},
    {{0, 0, 0}, {0, 0, 0, 0, 0, 3/4, ap, am}}, 1];

  (* Zero-included wheel. Do not replace this by the old n>=1 wheel
     without its constant correction. *)
  rw = With[{term = -393 Pi^3 binCoef[n]^4
       (8 + 5 Pi (4 n + 1) binCoef[n]^2) delta[n]},
    Inactive[Sum][term, {n, 0, Infinity}]];
  (* Complete seventh sector: includes the old five finite Z terms. *)
  r7 = With[{term = 24 Pi^3 (-1)^n binCoef[n]^7 seventhCoefficient[n]},
    Inactive[Sum][term, {n, 0, Infinity}]];
  (* Pa = 2 Pi^2 PaCubic; the contribution here is 96 Pa. *)
  ra = With[{term = 192 Pi^2 binCoef[m]^4 binCoef[n]^4
        primitiveCoefficient[m, n]/Binomial[m+n, m]},
    Inactive[Sum][term, {m, 0, Infinity}, {n, 0, Infinity}]];

  <|"KnownPolynomial" -> e, "FinitePolylogarithms" -> bp,
    "LowerPeriodBlock" -> -4 Pi^2 rho4 g4,
    "SixthPowerBlock" -> 192 Pi (13 x35 + 11 x44),
    "EighthPowerBlock" -> 16 Pi^3 rho8 g8,
    "Wheel" -> rw, "CompleteSeventhSector" -> r7, "Primitive" -> ra|>
];

C6CurrentExpression[] := Module[{b = C6CurrentBlocks[]},
  If[FailureQ[b], b, Total[Values[b]]/2187]
];
C6CurrentStatus[] := <|
  "Normalization" -> "r6 = 2187 C6(1)",
  "AllBlocksIncluded" -> True,
  "RemainingSeries" -> {"zero-included wheel", "complete seventh sector", "cubic primitive"},
  "FiniteBuiltInClosedFormEstablished" -> False,
  "ParameterDerivativeOrLimitInExpression" -> False,
  "SourceCorrectionAlreadyIncluded" -> True,
  "PhysicalGraphRGIdentification" -> "Inherited from the supplied derivation",
  "WolframKernelExecutedHere" -> False
|>;
End[];
EndPackage[];
