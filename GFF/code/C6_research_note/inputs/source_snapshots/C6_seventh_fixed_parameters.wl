(* Optional lower-order constant-parameter seventh-sector basis.
   The accepted nine-value formula is not replaced by this ten-value option.
   No Wolfram-kernel execution was performed during construction. *)
ClearAll[C6J7Left, C6J7Right, C6SeventhOrdinaryFixed,
  C6SeventhBlockFixed, C6SeventhBasisStatus];
C6J7Left[] := With[{alpha = ArcTan[75/32]/Pi},
  MeijerG[
    {Join[{-1/4}, ConstantArray[1/2, 6]], {1/2, alpha}},
    {ConstantArray[0, 3], Join[ConstantArray[0, 4], {3/4, alpha}]},
    1
  ]
];
C6J7Right[] := With[{alpha = ArcTan[89/75]/Pi},
  MeijerG[
    {Join[{-1/4}, ConstantArray[1/2, 7]], {alpha}},
    {ConstantArray[0, 2], Join[ConstantArray[0, 5], {3/4, alpha}]},
    1
  ]
];
C6SeventhOrdinaryFixed[a_: Pi + 4 Log[2]] :=
  ((407 a - 1127 Pi) Sqrt[6649] C6J7Left[] +
    (259 a - 49 Pi) Sqrt[13546] C6J7Right[])/75;
(* h7unit is the already defined fixed bivariate value, not assumed built-in. *)
C6SeventhBlockFixed[h7unit_, a_: Pi + 4 Log[2]] :=
  24 Pi^(3/2) (C6SeventhOrdinaryFixed[a] +
    196 Pi Sqrt[185] h7unit);
C6SeventhBasisStatus[] := <|
  "DefaultFixedValueCount" -> 9,
  "AlternativeFixedValueCount" -> 10,
  "AlternativeSeventhOrdinaryOrders" -> {{9,9},{9,9}},
  "AlternativeSeventhParametersDependOnA" -> False,
  "KnownPolynomialShift" -> 0,
  "FullC6ReturnedByThisPatch" -> False,
  "WolframKernelExecutedDuringConstruction" -> False,
  "NewIntervalCertificate" -> False
|>;
