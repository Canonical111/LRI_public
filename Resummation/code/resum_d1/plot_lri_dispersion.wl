(* ::Package:: *)
(* 2026-10-18, later (author request): the published MC also get one color per reference, besides their shapes, and the
   same color and shape in Figures 01, 05 and 06: Angelini et al. teal RGB(0.00,0.58,0.60) (triangle), Uzelac et al. rose
   RGB(0.84,0.33,0.58) (inverted triangle). No method color is used for them (checked below). This replaces the one neutral
   gray of the note just below. Previous version: history/pubcolors_before_20261018/. *)
(* 2026-10-18 (author request, after a reader's comment): one color per method as in the paper's Figs. 1-3 (Figure 05 follows Figure 01). NRG is orange
   (was gray); the published MC of both sources share one neutral gray, RGB(0.40,0.44,0.49), and the marker shape tells them
   apart (Uzelac et al. inverted triangle, was orange; Angelini et al. triangle, was blue). Only the new presentation
   (LRI_C8_1 = final) changes; LRI_C8_1 = previous still reproduces the previous figures. Data, layout and line styles
   unchanged. Previous version: history/palette_before_20261018/. *)
(* 2026-10-15 (author request): legend label of the project MC points 'MC (this work)' (was 'New MC'); data and layout unchanged.
   Previous version: history/MC_this_work_legend_before_20261015/. *)
(* 1d LRI method dispersion, updated 2026-10-12 (K=8 baseline); simplified 2026-10-13 to two resummation curves.
   Baseline: endpoint-v conformal Borel CB8, N=8, b_L=3, alpha=0, with the short-range series imposed through C^SR_8
   (update_2026-10-12/sr_endpoint.py). Display y = 1000 (Delta_epsilon(method) - Delta_epsilon(CB8, K=8)).
   Gray shading: envelope of the core prescription bands (N=6-8, b_L=2-4, alpha=-1..1) for K=5..8 short-range orders
   (sensitivity band). Blue dash-dot: GFF-only CB8 (direct, in epsilon; update_2026-10-13/fig05_gff_only_inputs.json);
   it lies below the frame for Delta_sigma < 0.088 and is clipped there (PlotRangeClipping), as the caption says.
   The archived K=4 CB8, core band and PB[5/3] curves and the CB8 K=5,6,7 lines were removed on 2026-10-13
   (previous version: history/clean_curves_before_20261013/).
   References: update_2026-10-12/references_refreshed.csv (final HT from dens_v1 to N=40; NRG flagged near s=1/2) plus
   six literature MC rows. HT at x=0.001 omitted as before (no continuum limit). Open markers: HT without a continuum
   value (unstable or no limit; finite-cutoff N=40 value shown), flagged NRG, MC with a status other than ACCEPTED.
   Inputs: update_2026-10-12/fig05_K8_inputs.json, update_2026-10-13/fig05_gff_only_inputs.json.
   Outputs: figures/05_method_dispersion{,_clean}.{pdf,png}, dispersion/reference_residuals_K8.csv.
   Earlier versions: history/1d_PB_K4_baseline_20261012/ (PB baseline), history/clean_curves_before_20261013/.
   2026-10-13 (afternoon), C8(1) FINAL = 8059766.723129955 +- 17000: environment LRI_C8_1 = final (default) reads
   update_2026-10-13/C8_1_ext/{fig05_K8_inputs.json, fig05_gff_only_inputs.json}, writes figures/05_method_dispersion*
   and dispersion/reference_residuals_K8.csv, and uses the new presentation: no K=5..8 band (its width at
   Delta_sigma = 0.05, 0.1, 0.15 and its maximum are stated in the caption), the _clean variant with the legend, caption
   numbers (GFF-only clipping) taken from the input. LRI_C8_1 = previous reads C8_1_ext/repro_previous/ and reproduces
   the previous figure (old presentation) in C8_1_ext/repro_previous/{figures,dispersion}/.
   Previous version of this script and figure: history/C8_1_before_ext_20261013/.
   2026-10-13 (late evening), NRG rev 2: with LRI_C8_1 = final the NRG rows come from
   update_2026-10-13/references_nrg_rev2.csv (settled late-window estimator; linear error sums, not standard deviations);
   Delta_sigma = 0.225, 0.24, 0.249 are 'not converged in chain depth' (open, settled value, no error bar, not used in
   the comparison). Previous figure: history/NRG_rev2_before_20261013/. *)
Begin["LRIDispersion`"];
$HistoryLength = 0;
base = Quiet@Check[If[$InputFileName =!= "",
   DirectoryName[ExpandFileName[$InputFileName]], NotebookDirectory[]], Directory[]];
Needs["MaTeX`", FileNameJoin[{base, "vendor", "MaTeX", "MaTeX.m"}]];
c8mode = Environment["LRI_C8_1"]; If[! StringQ[c8mode] || StringTrim[c8mode] === "", c8mode = "final"];
c8mode = ToLowerCase[StringTrim[c8mode]]; newStyle = (c8mode =!= "previous");
extDir = FileNameJoin[{base, "update_2026-10-13", "C8_1_ext"}];
inRoot = If[newStyle, extDir, FileNameJoin[{extDir, "repro_previous"}]];

result = Catch[Module[{},
 fail[tag_, detail_] := Throw[Failure[tag, <|"Detail" -> detail|>], "LRIPlotFailure"];
 require[test_, detail_] := If[! TrueQ[test], fail["Validation", detail]];
 require[MemberQ[{"final", "previous"}, c8mode], {"LRI_C8_1 must be final or previous", c8mode}];
 fix[v_, d_] := ToString[NumberForm[N[Round[v, 10^-d]], {d + 3, d}]];
 sci[v_, d_] := Module[{e = Floor[Log10[Abs[v]]], m}, m = v/10^e; If[Round[m, 10^-d] >= 10, e = e + 1; m = m/10];
   ToString[NumberForm[N[Round[m, 10^-d]], {d + 1, d}]] <> "\\times10^{" <> ToString[e] <> "}"];
 numericPattern = RegularExpression["[+-]?(?:[0-9]+(?:\\.[0-9]*)?|\\.[0-9]+)(?:[eE][+-]?[0-9]+)?"];
 signedInteger[s_String] := If[StringStartsQ[s, "-"], -1, 1] *
   FromDigits[StringTrim[s, "+" | "-"]];
 number[s_String] := number[s] = Module[{parts, mant, exponent, sign, digits, fraction},
   require[StringMatchQ[s, numericPattern], {"Bad numeric token", s}];
   parts = StringSplit[ToLowerCase[s], "e"];
   exponent = If[Length[parts] == 2, signedInteger[parts[[2]]], 0];
   sign = If[StringStartsQ[parts[[1]], "-"], -1, 1];
   mant = StringTrim[parts[[1]], "+" | "-"];
   fraction = If[StringContainsQ[mant, "."],
     StringLength[mant] - First@First@StringPosition[mant, "."], 0];
   digits = StringDelete[mant, "."];
   N[sign FromDigits[digits] 10^(exponent - fraction)]
 ];
 num[row_Association, key_String] := If[StringQ[row[key]], number[row[key]], row[key]];
 xy[rows_, key_, xkey_: "Delta_sigma"] := ({num[#, xkey], num[#, key]} & /@ rows);
 difference[rows_, first_, second_, factor_: 1] :=
   ({num[#, "Delta_sigma"], factor (num[#, first] - num[#, second])} & /@ rows);

 purple = RGBColor[0.48, 0.24, 0.68]; orange = RGBColor[0.85, 0.39, 0.08];
 blue = RGBColor[0.122, 0.467, 0.706]; green = RGBColor[0.12, 0.52, 0.38];
 gray = RGBColor[0.40, 0.44, 0.49]; black = GrayLevel[0.12]; lightgray = GrayLevel[0.64];
 tex[s_, size_: 16] := tex[s, size] = Module[{g},
   g = MaTeX`MaTeX[s, FontSize -> size, "Preamble" -> {"\\usepackage{color,txfonts}"}];
   require[Head[g] === Graphics, {"MaTeX failed", s}]; g];
 ticks[vals_] := ({N[#], tex[If[IntegerQ[#] || # == Round[#], Round[#], #], 14]} & /@ vals);
 xTicks = ticks[{0, .05, .10, .15, .20, .25}];
 stroke[col_, dash_: {}] := Directive[col, AbsoluteThickness[2.1], AbsoluteDashing[dash]];
 line[points_, col_, dash_: {}] := {stroke[col, dash], Line[points]};
 band[low_, high_, col_] := {col, Opacity[0.13], EdgeForm[None],
   Polygon[Join[low, Reverse[high]]]};
 zero[xrange_] := {GrayLevel[.65], AbsoluteThickness[.7], Line[{{First[xrange], 0}, {Last[xrange], 0}}]};
 marker[col_, shape_, filled_: True] := Graphics[
   {EdgeForm[Directive[col, AbsoluteThickness[1.2]]], FaceForm[If[filled, col, White]],
    Switch[shape, "square", Rectangle[{-.8, -.8}, {.8, .8}],
      "diamond", Polygon[{{0, 1}, {1, 0}, {0, -1}, {-1, 0}}],
      "triangle", Polygon[{{0,1},{-.9,-.7},{.9,-.7}}],
      "invtriangle", Polygon[{{0,-1},{-.9,.7},{.9,.7}}], _, Disk[{0, 0}, .8]]},
   PlotRange -> {{-1.1, 1.1}, {-1.1, 1.1}}, ImagePadding -> 0, ImageSize -> 11];
 markAt[pos_, col_, shape_, filled_: True] := Inset[marker[col, shape, filled], pos, Center, Scaled[.014]];
 errorAt[x_, y_, e_, col_, thick_: 1., cap_: 3] :=
   {col, AbsoluteThickness[thick], Line[{{x, y-e}, {x, y+e}}],
    Line[{Offset[{-cap, 0}, {x, y-e}], Offset[{cap, 0}, {x, y-e}]}],
    Line[{Offset[{-cap, 0}, {x, y+e}], Offset[{cap, 0}, {x, y+e}]}]};
 panel[prims_, xr_, yr_, ylabel_, title_, yticks_, clean_: False, xticks_: Automatic] :=
   Graphics[prims, Frame -> True, Axes -> False, FrameStyle -> Directive[black, AbsoluteThickness[1.]],
    FrameLabel -> {{tex[ylabel, 21], None}, {tex["\\Delta_\\sigma", 21], None}},
    FrameTicks -> {{ticks[yticks], None}, {If[xticks === Automatic, xTicks, xticks], None}},
    PlotLabel -> If[clean, None, tex[title, 17]],
    PlotRange -> {xr, yr}, PlotRangePadding -> None, PlotRangeClipping -> True,
    GridLines -> {None, yticks}, GridLinesStyle -> Directive[GrayLevel[.91], AbsoluteThickness[.5]],
    ImageSize -> 780, AspectRatio -> .62, ImagePadding -> {{76, 18}, {61, If[clean, 12, 36]}},
    Background -> White];
 lineKey[col_, dash_, text_] := {Graphics[{stroke[col, dash], Line[{{0, 0}, {1, 0}}]},
   ImageSize -> {40, 14}, ImagePadding -> 1, PlotRange -> {{0, 1}, {-.2, .2}}], tex[text, 14]};
 pointKey[col_, shape_, filled_, text_] := {marker[col, shape, filled], tex[text, 14]};
 pairKey[colF_, colO_, shape_, text_] := {Row[{marker[colF, shape, True], marker[colO, shape, False]}, Spacer[3]], tex[text, 14]};
 patchKey[col_, text_, opacity_: .2] := {Graphics[{col, Opacity[opacity], Rectangle[]}, ImageSize -> {36, 12}], tex[text, 14]};
 keyGrid[entries_, ncol_: 3] := Grid[Partition[PadRight[
   (Row[#, Spacer[6]] & /@ entries), ncol Ceiling[Length[entries]/ncol], ""], ncol],
   Alignment -> Left, Spacings -> {2, .6}];
 assemble[panels_, title_, keys_, notes_, clean_] := If[clean,
   Grid[{panels}, Spacings -> {1.5, 0}],
   Column[Join[{tex[title, 23], Grid[{panels}, Spacings -> {1.5, 0}], keyGrid[keys]},
      (tex[#, 13] & /@ notes)], Alignment -> Center, Spacings -> .8]];
 inp = Import[FileNameJoin[{inRoot, "fig05_K8_inputs.json"}], "RawJSON"];
 require[AssociationQ[inp], "JSON import"];
 curve = inp["curve"]; refs = inp["references"];
 require[Length[curve] == 1004 && Length[refs] == 49, {"Row counts", Length[curve], Length[refs]}];
 (* K=4 regression of the code that produced the K=8 baseline (kept although no K=4 curve is drawn) *)
 require[inp["regression"]["K4_PB8_vs_archived_dense_PB"] < 10^-11 &&
   inp["regression"]["K4_CB8_vs_archived_CB8"] < 10^-12, "K=4 regression against the archived tables"];
 gff = Import[FileNameJoin[{inRoot, "fig05_gff_only_inputs.json"}], "RawJSON"];
 require[If[newStyle, inp["C8_switch"]["C8"] === "8059766.723129955" && gff["C8_switch"]["C8"] === "8059766.723129955",
   gff["C8_switch"]["C8"] === "8066723.342964563"], "Figure 05 inputs do not match LRI_C8_1"];
 require[AssociationQ[gff] && Length[gff["curve"]] == 1004, "GFF-only input"];
 require[AllTrue[Transpose[{curve, gff["curve"]}], #[[1]]["Delta_sigma"] == #[[2]]["Delta_sigma"] &&
     Abs[#[[2]]["direct_CB8"] - #[[1]]["CB8_K8"] - #[[2]]["direct_CB8_minus_K8"]] < 10^-14 &],
   "GFF-only input: grid or K=8 baseline differs from fig05_K8_inputs.json"];
 require[gff["checks"]["gff_only_v_eps_vs_direct_L8_max_abs"] < 10^-12 &&
   gff["checks"]["fig05_CB8_K8_vs_curve_K_endpoint_v_K8_L8_max_abs"] < 10^-12 &&
   gff["checks"]["plot_data_direct_CB8_vs_curve_K_direct_L8_max_abs"] == 0, "GFF-only cross-checks"];
 gffRes = ({#["Delta_sigma"], 1000 #["direct_CB8_minus_K8"]} & /@ gff["curve"]);
 (* caption numbers (from the input since 2026-10-13): clipped below the frame for Delta_sigma < crossing; value at 0 *)
 gffCross = gff["frame_crossing_Delta_sigma_linear_interpolation"]; gff0 = Round[gffRes[[1, 2]]];
 require[Round[gffCross, 0.001] == 0.088 && gff0 == If[newStyle, -433, -431] && gffRes[[1, 1]] == 0 &&
   AllTrue[gffRes, If[#[[1]] < gffCross, #[[2]] < -35, -35 <= #[[2]] <= 10^-9] &], "GFF-only clipping differs from the caption"];
 purple = RGBColor[0.48, 0.24, 0.68]; orange = RGBColor[0.85, 0.39, 0.08];
 blue = RGBColor[0.122, 0.467, 0.706]; green = RGBColor[0.12, 0.52, 0.38];
 gray = RGBColor[0.40, 0.44, 0.49]; black = GrayLevel[0.12]; lightgray = GrayLevel[0.64]; envgray = GrayLevel[0.45];
 (* 2026-10-18: one color per published MC reference, as in Figures 01 and 06; none is a method color *)
 teal = RGBColor[0.00, 0.58, 0.60]; rose = RGBColor[0.84, 0.33, 0.58];
 require[teal =!= rose && ! IntersectingQ[{teal, rose}, {purple, orange, blue, green, black, lightgray, RGBColor[0.80, 0.12, 0.18]}],
   "published MC colors must differ from each other and from the method colors"];
 sc[key_] := ({#["Delta_sigma"], 1000 #[key]} & /@ curve);
 omitQ[r_] := r["method"] == "HT" && Abs[num[r, "x"] - .001] < 10^-12;
 shown = Select[refs, ! omitQ[#] &];
 require[Length[shown] == 48, "Expected 48 displayed points"];
 filledQ[r_] := Switch[r["method"],
   "HT", MemberQ[{"final", "one_sided"}, r["status"]],
   "NRG", ! MemberQ[{"flagged", "not_converged"}, r["status"]],
   "MC", StringStartsQ[r["status"], "ACCEPTED"],
   _, False];
 (* NRG rev 2 (2026-10-13): final points carry the linear error sum; the three not-converged points have no error *)
 require[With[{nrg = Select[refs, #["method"] == "NRG" &]}, Length[nrg] == 13 && If[newStyle,
     AllTrue[nrg, If[num[#, "x"] <= .2 + 10^-12, #["status"] == "final" && #["error"] =!= "", #["status"] == "not_converged" && #["error"] === ""] &],
     AllTrue[nrg, If[num[#, "x"] <= .2 + 10^-12, #["status"] == "reported", #["status"] == "flagged"] && #["error"] =!= "" &]]],
   "NRG statuses/errors differ from the caption (rev 2: final x<=0.2, not_converged x>=0.225 without error)"];
 refLayer := Flatten[Map[Function[r, Module[{x, y, col, shape, err, stat, extra},
   x = num[r, "x"]; y = 1000 r["method_minus_K8"];
   col = Switch[r["method"], "HT", green, "NRG", If[newStyle, orange, gray], "MC",
     If[StringStartsQ[r["status"], "ACCEPTED"], black, lightgray], "MC_literature", If[newStyle, If[StringStartsQ[r["source"], "Uzelac"], rose, teal], blue]];
   (* 2026-10-13 evening: published MC by source (shape), as in Figures 01 and 06; 2026-10-18: NRG orange, one color per reference *)
   shape = Switch[r["method"], "HT", "square", "NRG", "circle", "MC", "diamond", "MC_literature", If[newStyle && StringStartsQ[r["source"], "Uzelac"], "invtriangle", "triangle"]];
   err = If[r["error"] == "", {}, errorAt[x, y, 1000 num[r, "error"], col, .9, 3]];
   stat = If[r["stat"] == "", {}, errorAt[x, y, 1000 num[r, "stat"], col, 1.8, 1.5]];
   extra = If[r["status"] == "one_sided", {col, AbsoluteThickness[.9], AbsoluteDashing[{2, 2}],
       Line[{{x, y - 1000 num[r, "error"]}, {x, y - 1000 (num[r, "error"] + 5*^-4)}}]}, {}];
   {err, stat, extra, markAt[{x, y}, col, shape, filledQ[r]]}]], shown], 1];
 If[! newStyle, require[AllTrue[Join[sc["env_lo_minus_K8"], sc["env_hi_minus_K8"]], -35 <= #[[2]] <= 40 &], "Envelope outside displayed range"]];
 (* 2026-10-13: the K=5..8 envelope is not drawn in the new presentation; its width enters the caption *)
 envW = (#["env_hi_minus_K8"] - #["env_lo_minus_K8"]) & /@ curve; envI = First@Ordering[envW, -1];
 envAt[x_] := envW[[First@FirstPosition[#["Delta_sigma"] & /@ curve, _?(Abs[# - x] < 10^-12 &)]]];
 envWidth = <|"0.05" -> envAt[.05], "0.1" -> envAt[.1], "0.15" -> envAt[.15], "max" -> envW[[envI]], "max_at" -> curve[[envI, "Delta_sigma"]]|>;
 require[AllTrue[shown, Function[r, With[{y = 1000 r["method_minus_K8"],
     e = 1000 Max[If[r["error"] == "", 0, num[r, "error"]], If[r["stat"] == "", 0, num[r, "stat"]]]},
     -35 <= y - e && y + e <= 40]]], "Reference error bar outside displayed range"];
 makeDispersion[clean_] := Module[{p, keys},
   p = panel[{
       If[newStyle, {}, {envgray, Opacity[.28], EdgeForm[None], Polygon[Join[sc["env_lo_minus_K8"], Reverse[sc["env_hi_minus_K8"]]]]}],
       line[gffRes, blue, {7, 3, 1.5, 3}],
       line[{{0, 0}, {.25, 0}}, purple], refLayer},
     {-.005, .255}, {-35, 40}, "10^3(\\Delta_{\\mathcal E}-\\Delta_{\\mathcal E}^{{\\rm CB8},\\,K=8})",
     "\\text{1d long-range Ising: deviations from CB8 with the short-range series through }C^{\\rm SR}_8",
     {-30, -20, -10, 0, 10, 20, 30, 40}, clean];
   keys = {lineKey[purple, {}, "\\text{CB8, }K=8\\text{ (baseline)}"],
     If[newStyle, Nothing, patchKey[envgray, "\\text{sensitivity band (}K=5\\text{--}8\\text{ envelope)}", .28]],
     lineKey[blue, {7, 3, 1.5, 3}, "\\text{CB8: GFF only }(\\epsilon)"],
     Sequence @@ If[newStyle,
       (* 2026-10-13 evening: one entry per method with its filled and open marker; the caption says what each means *)
       {pairKey[green, green, "square", "\\text{HT}"], pairKey[orange, orange, "circle", "\\text{NRG}"], pairKey[black, lightgray, "diamond", "\\text{MC (this work)}"]},
       {pointKey[green, "square", True, "\\text{HT: final}"],
     pointKey[green, "square", False, "\\text{HT: no continuum value}"],
     pointKey[gray, "circle", True, "\\text{NRG}"], pointKey[gray, "circle", False, "\\text{NRG: flagged near }s=1/2"],
     pointKey[black, "diamond", True, "\\text{MC}"],
     pointKey[lightgray, "diamond", False, "\\text{MC}"]}],
     Sequence @@ If[newStyle, {pointKey[rose, "invtriangle", False, "\\text{MC: Uzelac et al. (2001)}"], pointKey[teal, "triangle", False, "\\text{MC: Angelini et al. (2014)}"]},
       {pointKey[blue, "triangle", False, "\\text{Literature MC (2001, 2014)}"]}]};
   If[clean, If[newStyle, Column[{p, keyGrid[keys]}, Alignment -> Center, Spacings -> .8], p], Column[{p, keyGrid[keys],
     Sequence @@ If[newStyle, {
      tex["\\text{Deviations from the baseline of Figure 01 (CB8, }K=8\\text{). Blue: GFF series alone (CB8), below the frame for }\\Delta_\\sigma<" <> fix[gffCross, 3] <> ".", 13],
      tex["\\text{Not drawn: dependence on prescription and on }K=5\\text{--}8\\text{, at most }" <> sci[envWidth["max"], 2] <> "\\text{. HT dashed bar: one-sided error.}", 13],
      tex["\\text{Filled: HT final values, NRG, accepted new MC.}", 13],
      tex["\\text{Open: HT without continuum value }(N=40)\\text{, new MC with other statuses, NRG not converged in chain depth}", 13],
      tex["(\\Delta_\\sigma\\geq0.225\\text{; settled value, no error bar, not used in the comparison).}", 13]},
     Join[If[newStyle,
      {tex["\\text{Baseline: endpoint-}v\\text{ CB8},\\ N=8,\\ b_{\\rm L}=3,\\ \\alpha=0,\\ v=1-2\\sqrt{\\Delta_\\sigma},\\ \\text{short-range series imposed through }C^{\\rm SR}_8\\ (K=8).", 13],
       tex["\\text{GFF coefficients }C_0,\\ldots,C_8\\text{ with the final }C_8(1)=(8.060\\pm0.017)\\times10^6.", 13],
       tex["\\text{Not drawn: the }K=5\\text{--}8\\text{ envelope of the core bands }(N=6\\text{--}8,\\ b_{\\rm L}=2\\text{--}4,\\ \\alpha=-1,0,1),", 13],
       tex["\\text{i.e. the sensitivity to the prescription and to the number }K\\text{ of imposed short-range coefficients (not a confidence interval);}", 13],
       tex["\\text{its width is }" <> sci[envWidth["0.05"], 2] <> ",\\ " <> sci[envWidth["0.1"], 2] <> ",\\ " <> sci[envWidth["0.15"], 2] <>
         "\\text{ at }\\Delta_\\sigma=0.05,\\ 0.1,\\ 0.15\\text{ and at most }" <> sci[envWidth["max"], 2] <> "\\ (\\Delta_\\sigma=" <> fix[envWidth["max_at"], 3] <> ").", 13]},
      {tex["\\text{Baseline: endpoint-}v\\text{ CB8},\\ N=8,\\ b_{\\rm L}=3,\\ \\alpha=0,\\ v=1-2\\sqrt{\\Delta_\\sigma},\\ \\text{short-range series imposed through }C^{\\rm SR}_8\\ (K=8).", 13],
       tex["\\text{Envelope: core prescription bands }(N=6\\text{--}8,\\ b_{\\rm L}=2\\text{--}4,\\ \\alpha=-1,0,1)\\text{ for }K=5\\text{--}8;\\ \\text{sensitivity, not a confidence interval.}", 13]}], {
     tex["\\text{Blue dash-dot: GFF-only CB8, directly in }\\epsilon\\text{ (no short-range input); below the frame for }\\Delta_\\sigma<" <> fix[gffCross, 3] <> "\\ ({" <> ToString[gff0] <> "}\\text{ at }\\Delta_\\sigma=0)\\text{, clipped there.}", 13],
     tex["\\text{The archived }K=4\\text{ construction and the PB comparisons are in Figures 02--04 and in history/.}", 13],
     tex["\\text{HT: density-basis final values (dashed: extra one-sided }{-5\\times10^{-4}}\\text{ at }\\Delta_\\sigma=0.075);\\ \\text{open: no continuum value }(N=40).", 13],
     tex["\\text{Open circles: NRG flagged at }\\Delta_\\sigma\\geq0.225.", 13],
     tex["\\text{MC: filled, accepted infinite-size values; open, other statuses (conditional, cross-check failed); separate statistical and systematic bars.}", 13],
     tex["\\text{Literature MC: Uzelac et al. (2001), Angelini et al. (2014), quoted errors. 48 points; HT at }\\Delta_\\sigma=0.001\\text{ omitted.}", 13]}]]},
     Alignment -> Center, Spacings -> .8]]];
 outdir = If[newStyle, FileNameJoin[{base, "figures"}], FileNameJoin[{inRoot, "figures"}]];
 csvdir = If[newStyle, FileNameJoin[{base, "dispersion"}], FileNameJoin[{inRoot, "dispersion"}]];
 If[! DirectoryQ[#], CreateDirectory[#, CreateIntermediateDirectories -> True]] & /@ {outdir, csvdir};
 exportPair[stem_, obj_] := Module[{pp, qq},
   pp = Export[FileNameJoin[{outdir, stem <> ".pdf"}], obj, "PDF"];
   qq = Export[FileNameJoin[{outdir, stem <> ".png"}], obj, "PNG", ImageResolution -> 160];
   require[AllTrue[{pp, qq}, StringQ[#] && FileExistsQ[#] && FileByteCount[#] > 0 &], {"Export", stem}];
   Print["EXPORTED ", stem]; {pp, qq}];
 Print["BUILDING SINGLE PANEL WITH K=8 BASELINE"];
 exportPair["05_method_dispersion", makeDispersion[False]];
 exportPair["05_method_dispersion_clean", makeDispersion[True]];
 Export[FileNameJoin[{csvdir, "reference_residuals_K8.csv"}],
   Prepend[Values /@ (KeyTake[#, {"method", "x", "y", "error", "stat", "status", "CB8_K8", "method_minus_K8"}] & /@ refs),
     {"method", "x", "y", "error", "stat", "status", "CB8_K8", "method_minus_K8"}], "CSV"];
 Print["DONE"];
 "ok"
], "LRIPlotFailure"];
If[FailureQ[result], Print[result]; End[]; result, End[]; result]
