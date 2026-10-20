(* Diagnostic identities for the existing C6 primitive.
   This file is NOT an integration-free evaluation of the complete C6.
   All sums/arrays used below are finite algebra. No external package needed.
   The code has not been executed in a Wolfram kernel in this environment. *)

BeginPackage["C6PrimitiveFirstMoments`"];
C6PrimitiveFirstMomentValues::usage =
  "Returns exact values J01=Pi/2 and J12-J02=Pi; J uses weight 2x-1.";
C6PrimitiveContourAlgebraChecks::usage =
  "Checks the exterior branch polynomials, basis changes, and leading asymptotic coefficients.";
C6PrimitiveFirstMomentStatus::usage =
  "Reports that the accepted C6 expression has not changed.";
Begin["`Private`"];

C6PrimitiveFirstMomentValues[] := <|
  "J01" -> Pi/2,
  "J12MinusJ02" -> Pi,
  "EllipticFirstMoment1" -> Pi^5/32,
  "EllipticFirstMoment2" -> Pi^5/16
|>;

C6PrimitiveFirstMomentStatus[] := <|
  "FullFiniteC6Established" -> False,
  "AcceptedC6FormulaChanged" -> False,
  "KnownPolynomialChanged" -> False,
  "NewCompletedC6Blocks" -> 0,
  "UnresolvedBlocks" -> {"Wheel", "SeventhLogarithmic", "PrimitivePa"},
  "Scope" -> "First-moment companion identities; not the unweighted primitive."
|>;

C6PrimitiveContourAlgebraChecks[] := Module[
  {u,r,a,b,ll,ca,da,cb,db,c0,d0,pairs,patterns,vec,num,
   exterior,t,aq,bq,phase,lead,expected,inf},
  c0={{-3,0,1},{0,-4,0},{1,0,1}};
  d0={{0,-4,0},{4,0,0},{0,0,0}};
  ca={{0,-4,0},{4,0,0},{0,0,0}};
  da={{5,0,-1},{0,0,0},{-1,0,1}};
  cb={{0,1,0},{-1,0,-1},{0,1,0}};
  db=DiagonalMatrix[{-2,2,0}];
  pairs={{c0,d0},{ca,da},{cb,db}};
  patterns={{u,r-I u,a-I b,a+I b},{a+I b,a-I b,u,r+I u}};
  vec[x_,y_]:={x^2,x y,y^2};
  num[pair_,pat_]:=
    vec[pat[[1]],pat[[2]]].(pair[[1]]+I pair[[2]]).
      vec[pat[[3]],pat[[4]]];
  exterior=Flatten[Table[
    Expand[ComplexExpand[Im[Expand[num[pair,pat]]]]]===0,
    {pair,pairs},{pat,patterns}
  ]];
  t={{1,0,0},{-1,1,0},{1,-2,1}};
  aq=Transpose[t].ca.t;
  bq=Transpose[t].cb.t;
  phase=(1+I)/Sqrt[2];
  lead={phase (ll-I Pi)/Sqrt[2],
        ll+Pi-phase (ll-I Pi)/Sqrt[2],
        ll/Sqrt[2],
        phase (ll+Pi-I Pi)-ll/Sqrt[2]};
  inf=FullSimplify[Expand[num[#,lead]]]& /@ pairs;
  expected={0,-2 Pi^4,-Pi^4};
  <|
    "ExteriorReality" -> And@@exterior,
    "FirstMomentMatrixA" -> (aq==={{0,-4,0},{4,0,0},{0,0,0}}),
    "FirstMomentMatrixB" -> (bq==={{0,0,1},{0,0,-1},{-1,1,0}}),
    "LeadingPolynomials" -> inf,
    "LeadingPolynomialCheck" -> (inf===expected),
    "MomentValues" -> C6PrimitiveFirstMomentValues[],
    "Status" -> C6PrimitiveFirstMomentStatus[]
  |>
];
End[];
EndPackage[];
