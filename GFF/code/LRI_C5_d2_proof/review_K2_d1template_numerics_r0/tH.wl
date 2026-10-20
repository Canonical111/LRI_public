$MaxExtraPrecision = 2000;
Get[FileNameJoin[{DirectoryName[$InputFileName], "emsum.wl"}]];
h[z_, ta_] := Exp[3 LogGamma[z + 1/2] - 2 LogGamma[z + 1] - LogGamma[z + 1/2 + ta]];
Ecl[a_, b_] := Pi/2 Beta[a, b] HypergeometricPFQ[{1/2, 1/2, a}, {1, a + b}, 1];
{t, v} = AbsoluteTiming[emSum[h[#, 1/7] &, 0, 60, 25, 50]];
Print["H0(1/7) wp50 EM time ", t, " diff: ", InputForm[N[v - N[2 Ecl[1/2, 1/7]/Gamma[1/7], 60], 5]]];
Quit[];
