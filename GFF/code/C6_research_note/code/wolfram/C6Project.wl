(* Portable interface for the C6 research archive.
   This file and the inherited Wolfram sources were NOT executed in a Wolfram
   kernel by the archive producer. Python checks are recorded separately.
   All filenames are resolved relative to this file, never to /mnt/data.
   The real Ls/Cl and bivariate H specification is returned as data: no rare
   function is misrepresented as System`MeijerG or as a numerical constant. *)
BeginPackage["C6Project`"];
C6Capabilities::usage = "C6Capabilities[] reports installed Wolfram capabilities and package scope.";
C6BuiltinSeries::usage = "C6BuiltinSeries[] returns the full inherited built-in expression with three explicit inactive residual sums. Requires System`HarmonicPolyLog.";
C6BuiltinQuadrature::usage = "C6BuiltinQuadrature[] returns the full built-in expression with the finite polylog block and three explicit inactive quadratures. Requires System`HarmonicPolyLog.";
C6HistoricalQuadrature4::usage = "C6HistoricalQuadrature4[] returns the earlier complete classical-PolyLog form with four explicit quadrature blocks and no HPL requirement.";
C6EvaluateHistoricalQuadrature::usage = "C6EvaluateHistoricalQuadrature[d] delegates to the historical four-quadrature numerical evaluator. Precision goals are not certified bounds.";
C6RecommendedSpecification::usage = "C6RecommendedSpecification[] returns the complete adopted nine-value real specification as a JSON association. It is not a built-in evaluator for bivariate H.";
Begin["`Private`"];
$projectRoot = DirectoryName[DirectoryName[DirectoryName[$InputFileName]]];
sourcePath[name_] := FileNameJoin[{$projectRoot,"inputs","source_snapshots",name}];
stagePath[stage_,name_] := FileNameJoin[{$projectRoot,"code","stages",stage,name}];
load[path_] := If[FileExistsQ[path], Get[path], Failure["MissingFile",<|"Path"->path|>]];
missingHPL[] := Failure["MissingBuiltIn",<|"MessageTemplate"->"System`HarmonicPolyLog is unavailable. Use C6HistoricalQuadrature4[] instead; no substitute head is installed."|>];
C6Capabilities[] := <|
 "HarmonicPolyLogAvailable" -> (Names["System`HarmonicPolyLog"] =!= {}),
 "MultiplePolyLogAvailable" -> (Names["System`MultiplePolyLog"] =!= {}),
 "MeijerGAvailable" -> (Names["System`MeijerG"] =!= {}),
 "ProducerExecutedWolframKernel" -> False,
 "FiniteBuiltInOnlyFullClosedFormEstablished" -> False,
 "RealFiniteFormulaUsesNonBuiltInBivariateFunctions" -> True,
 "Normalization" -> "r6 = 2187 C6(1)"
|>;
C6BuiltinSeries[] := Module[{},
 If[Names["System`HarmonicPolyLog"] === {}, Return[missingHPL[]]];
 load[sourcePath["C6_current_self_contained.wl"]];
 C6Current`C6CurrentExpression[]
];
C6BuiltinQuadrature[] := Module[{x, aa, qq, pol, known, ordinary, integrand},
 If[Names["System`HarmonicPolyLog"] === {}, Return[missingHPL[]]];
 load[stagePath["C6_Mathematica_native","C6Native.wl"]];
 load[stagePath["C6_finite_polylog","C6_finite_polylog_patch.wl"]];
 aa=Pi+4 Log[2]; qq=Gamma[1/4]^4/Pi;
 pol=C6FinitePolylog`C6FinitePolylogR6[];
 known=C6FinitePolylog`C6FiniteKnownPolynomial[aa,qq,Catalan];
 (* This polynomial includes -144 Q^3/Pi; the corresponding ungrouped
    three sixth-period values are all present in ordinaryExact[]. *)
 ordinary=C6Native`Private`ordinaryExact[];
 integrand=C6Native`Private`wheelKernel[x]+C6Native`Private`seventhKernel[x]+C6Native`Private`primitiveKernel[x];
 (known+pol+ordinary+With[{f=integrand},Inactive[Integrate][f,{x,0,1}]])/2187
];
C6HistoricalQuadrature4[] := Module[{},
 load[stagePath["C6_Mathematica_native","C6Native.wl"]];
 C6Native`C6NativeExpression[]
];
C6EvaluateHistoricalQuadrature[d_Integer:25] := Module[{},
 load[stagePath["C6_Mathematica_native","C6Native.wl"]];
 C6Native`C6NativeEvaluate[d]
];
C6RecommendedSpecification[] := Import[
 FileNameJoin[{$projectRoot,"inputs","canonical","recommended_real_nine.json"}],"RawJSON"];
End[];
EndPackage[];
