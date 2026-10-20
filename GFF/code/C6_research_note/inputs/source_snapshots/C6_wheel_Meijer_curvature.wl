(* Diagnostic identities, NOT a completed fixed-value formula for C6(1).
   No Mathematica kernel was used to execute this file in the supplied checks.
   Derivatives below are deliberately inactive: activating them is a research
   operation, not an established elimination of the wheel constant. *)
BeginPackage["C6WheelCurvature`"];
C6WheelG13::usage = "C6WheelG13[u] is the ordinary G44^(1,3) family used to organize D4.";
C6WheelG22::usage = "C6WheelG22[u] is the ordinary G44^(2,2) family used to organize D6.";
C6WheelCurvatureDiagnostics::usage = "C6WheelCurvatureDiagnostics[] returns exact intermediate identities with inactive parameter derivatives.";
C6WheelCurvatureStatus::usage = "Reports the unchanged status of the complete C6 fixed-value reduction.";
Begin["`Private`"];
C6WheelG13[u_] := MeijerG[
  {{1/2-u, 1/2+u, 1/2}, {1/2}},
  {{0}, {u, -u, 0}}, 1];
C6WheelG22[u_] := MeijerG[
  {{1/2-u, 1/2+u}, {1/2, 1/2}},
  {{0, 0}, {0, 0}}, 1];
C6WheelCurvatureDiagnostics[] := Module[
  {a, q, cd, cs, csCombined, a2, b2, a0, b0},
  a = Pi + 4 Log[2];
  q = Gamma[1/4]^4/Pi;
  cd = 96 q - 42 a^2 - 18 a Pi - 1227 Pi^2;
  cs = 60 q - 105 a^2/4 - 9 a Pi - 2469 Pi^2/4;
  csCombined = 60 q - 105 a^2/4 - 9 a Pi - 126 Pi^2;
  a2 = Inactive[Derivative][2][C6WheelG13][0];
  b2 = Inactive[Derivative][2][C6WheelG22][0];
  a0 = C6WheelG13[0];
  b0 = C6WheelG22[0];
  <|
    "D4" -> a2/(2 Pi),
    "D6" -> b2/Pi^2-b0,
    "WheelZeroIncludedR6" -> -393 Pi^2 (4 a2+5 b2)+1965 Pi^4 b0,
    "LowerPlusWheelR6" -> 4 Pi^2 (cd a0+csCombined b0)-393 Pi^2 (4 a2+5 b2),
    "LowerCoefficientCheck" -> FullSimplify[cs+1965 Pi^2/4-csCombined],
    "ParameterNeighborhood" -> "Abs[u]<1/8 suffices",
    "UncomputedParameterDerivativesRemain" -> True,
    "NotTheFullC6" -> True
  |>
];
C6WheelCurvatureStatus[] := <|
  "AcceptedExpressionChanged" -> False,
  "KnownPolynomialShift" -> 0,
  "NewFixedValueBlockEliminated" -> False,
  "FullIntegralAndSumFreeC6Established" -> False,
  "UnevaluatedBlocks" -> {"Wheel", "Seventh logarithmic sector", "Primitive Pa"},
  "ParameterDerivativesEvaluatedInFixedValues" -> False,
  "MathematicaKernelExecutedInThisPackage" -> False,
  "NewFullC6NumericalEvaluation" -> False
|>;
End[];
EndPackage[];
