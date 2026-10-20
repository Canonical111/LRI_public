(* 2d and 3d LRI dimension curves, combined in one two-panel figure.
   Uses unchanged 2026-10-12 C8-updated inputs; no residual panels.
   Simplified 2026-10-13: the only resummation curves are the baseline CB8 with the SRI endpoint
   imposed (2d curvature-constrained, 3d slope-constrained; purple) with its CB prescription band,
   and the GFF-only CB8 (blue dash-dot). Green squares: finite-cutoff HT.
   Removed on 2026-10-13 (previous version: history/clean_curves_before_20261013/): the PB controls
   (2d PB8 [5/3], 3d PB7) and the thin gray 2d value-only / value + zero-slope CB8 endpoint lines.
   The 2d endpoint-construction spread is not drawn but is stated in the caption with its size
   (value-only up to 7.5e-3, value + zero slope up to 5.7e-3 from the curvature baseline, more than
   the core band at every stored point with 0.15 <= Delta_sigma <= 0.30); checked below. In 3d the
   value-only curve stays within 1.2e-4 of the slope baseline.
   Literature MC (update of 2026-10-12): every published Monte Carlo thermal exponent inside
   the windows, from combined/literature_mc_2d3d.csv (rows with plotted = yes). Sources:
   Angelini et al. 2014 (blue open triangles, as before), Luijten PhD thesis 1997 (red circles;
   2d chi fit open, 2d Q fit filled, 3d Table 5.12 dotted), Picco 2012 (brown inverted
   triangle), Xiao et al. 2025 (magenta star). Full quoted errors. Literature markers sharing a
   Delta_sigma are dodged horizontally by the plot_offset column (2d step 0.009, 3d +0.006);
   project HT and MC markers stay at their true coordinates.
   Since 2026-10-13 (author's request) the Angelini et al. 2014 point at sigma = 7/4 (Delta_epsilon
   = 1.02(10)) is not plotted (plotted = no in the CSV; window boundary, error too wide for the
   frame); the caption says so. The sigma = 7/4 pair (Luijten Q fit, Xiao et al.) is now at
   -/+0.0045 and the 2d frame starts at Delta_sigma = 0.115 (was 0.108). The 2d vertical range (was 0.913-1.128,
   set by that point's +-0.10 bar) is now computed from the data: the extremes of every plotted 2d error bar,
   HT marker (half-height 0.003) and drawn curve/band, padded by 0.005 and rounded to 0.001 (0.925-1.055);
   ticks 0.94, 0.97, 1.00, 1.03.
   Black diamond: the sole accepted new 3d MC point under amendment P1.
   Its statistical and systematic bars are separate, using full source precision.
   Inputs (unchanged): {2d,3d}/inputs/plot_data.json, 3d/inputs/mc_accepted.json,
   combined/literature_mc_2d3d.csv; output: figures/06_curves_2d3d{,_clean}.{pdf,png}.
   Run: wolframscript -file run_plot.wls /absolute/path/plot_lri_2d3d.wl
   Reusable source returns normally; shutdown belongs to run_plot.wls.
   Changes of 2026-10-13 (afternoon, author's requests; previous version history/C8_1_before_ext_20261013/):
   (i) the _clean variant now carries the legend (key) below the panels, still without panel titles and caption lines;
   (ii) the shaded CB prescription band is no longer drawn (full and _clean) and has no legend entry; its size is
   stated in one caption sentence computed here from the stored core-band columns (identical to {2d,3d}/results/
   curves.csv): curvature_core_low/high (2d) and slope_core_low/high (3d) minus the baseline. The vertical ranges are
   unchanged (the 2d rule still includes the band extremes);
   (iii) the two 2d L=22 HT points (the crossover benchmark at Delta_sigma = 1/8 and Delta_sigma = 0.126) share one
   marker (green open square) and one legend entry; the caption says that the exact value at 1/8 is 1 and that no
   L=24 solution exists at these two couplings;
   (iv) the legend says "MC: Picco (2012)" (publication status kept in combined/literature_mc_2d3d.csv only);
   (vi) legend "New MC: 3d" (was "New MC: 3d, accepted (P1)"); its status is one caption phrase;
   (viii) 2026-10-13 late evening (author's request; previous version history/captions_before_20261013/): caption cut to
   three lines (curves, markers, what is not drawn with its size); details live in note_combined/.
   (vii) 2026-10-13 evening (author's request; previous version history/sri_star_before_20261013/): a small filled black
   star marks the short-range Ising (SRI) point where each window ends and the baseline is pinned, with its coordinates
   beside it: 2d (1/8, 1) exact, 3d (0.518149, 1.412625) from 3d/inputs/protocol.json (S, E_SR; conformal bootstrap,
   Chang et al. 2024); one legend entry and one caption line. To keep (1/8, 1) clear, the sigma = 7/4 literature pair is
   dodged by -/+0.009 (combined/make_literature_table.py) and the 2d frame starts at 0.11 (was 0.115); the 3d frame
   starts at 1.400 (was 1.408) to leave room for the 3d label below the star;
   (v) a third curve in both panels, CB3 GFF only (blue dotted, thinner): the release's direct CB truncated at n=3 (only
   C_0..C_3, the published three-loop order), same prescription as the GFF-only CB8 (2d b_L=3.5, 3d b_L=4, alpha=0),
   read from combined/cb3_gff_only.csv (written by combined/make_cb3_gff_only.py with the release code, which is not
   modified). It reaches 0.9135 at Delta_sigma = 1/8, so the 2d frame now starts at 0.905 (the extremes rule below, with
   the lower edge rounded down to a multiple of 0.005; tick 0.91 added); the top (1.055) and the 3d frame are unchanged.
   Data, the CB8 curves, markers of all other points and the C8 inputs are unchanged. 
   2026-10-15 (paper notation): the HT cutoff is written N in the legend (was L); data and layout unchanged.
   Previous version: history/HT_N_legend_before_20261015/. 
   2026-10-15 (author request): legend label of the project MC points 'MC (this work)' (was 'New MC'); data and layout unchanged.
   Previous version: history/MC_this_work_legend_before_20261015/.
   2026-10-18 (author request, after a reader's comment): one color per method across the paper's Figs. 1-3. The short-range
   Ising star is red and filled (was black: red = short-range expansion/end); every published MC marker is one neutral
   gray, RGB(0.40,0.44,0.49), keeping its shape and fill (Angelini triangle, was blue; Picco inverted triangle, was brown;
   Xiao open star, was magenta; Luijten circles, filled circle and dotcircle, were red). The color words above describe
   the earlier versions. Legend and caption follow; data, layout and line styles unchanged.
   Previous version: history/palette_before_20261018/.
   2026-10-18, later (author request): the published MC get one color per reference besides their shapes, never a method
   color, and the same color and shape as in Figures 01/05: Angelini et al. teal RGB(0.00,0.58,0.60) (triangle), Luijten's
   thesis brown RGB(0.55,0.34,0.16) (circles), Picco slate RGB(0.36,0.40,0.56) (inverted triangle), Xiao et al. ochre
   RGB(0.78,0.60,0.05) (open star). Xiao's star sits on the blue GFF-only line next to the red SRI star, so it takes the hue
   farthest from both; Picco's single point is clear of the blue curves. This replaces the one neutral gray above; caption
   line 2 now says 'one color and shape per reference (legend)'. Previous version: history/pubcolors_before_20261018/. *)
Begin["LRICombinedPlot`"];
$HistoryLength=0;
base=Quiet@Check[If[$InputFileName=!="",DirectoryName[ExpandFileName[$InputFileName]],NotebookDirectory[]],Directory[]];
Needs["MaTeX`",FileNameJoin[{base,"vendor","MaTeX","MaTeX.m"}]];
result=Catch[Module[{raw2,raw3,rows2,rows3,ht2,ht3,mc2,mc3,litPath,litRaw,litHeader,litAll,lit,lit2,lit3,
   litCounts,litOmitted,figures,diagnostics},
 require[t_,message_]:=If[!TrueQ[t],Throw[Failure["PlotValidation",<|"Detail"->message|>],"Failure"]];
 raw2=Import[FileNameJoin[{base,"2d","inputs","plot_data.json"}],"RawJSON"];
 raw3=Import[FileNameJoin[{base,"3d","inputs","plot_data.json"}],"RawJSON"];
 protocol3=Import[FileNameJoin[{base,"3d","inputs","protocol.json"}],"RawJSON"]; (* S, E_SR: the 3d SRI point (star) *)
 {rows2,ht2,mc2}=Lookup[raw2,{"curves","ht_latest","references"}];
 {rows3,ht3}=Lookup[raw3,{"curves","ht_l20"}];
 (* 2026-10-13: CB3 GFF-only (C_0..C_3) from combined/cb3_gff_only.csv, on the stored grids *)
 cb3Raw=Import[FileNameJoin[{base,"combined","cb3_gff_only.csv"}],"CSV","Numeric"->False];
 require[ListQ[cb3Raw] && First[cb3Raw]=={"d","Delta_sigma","CB3_direct"},"CB3 CSV header"];
 cb3[d_]:=cb3[d]=({ToExpression[#[[2]]],ToExpression[#[[3]]]}& /@ Select[Rest[cb3Raw],#[[1]]==ToString[d]&]);
 require[Length[cb3[2]]==Length[rows2] && Length[cb3[3]]==Length[rows3] &&
   Max[Abs[cb3[2][[All,1]]-Lookup[rows2,"Delta_sigma"]]]<10^-12 && Max[Abs[cb3[3][[All,1]]-Lookup[rows3,"Delta_sigma"]]]<10^-12,"CB3 grid differs from the stored curves"];
 cb3At[d_,x_]:=First@SelectFirst[cb3[d],Abs[#[[1]]-x]<10^-9&][[{2}]];
 require[And@@(Abs[cb3At[2,#[[1]]]-#[[2]]]<6*^-6&/@{{.13,.91398},{.2,.92192},{.3,.93659},{.4,.95842},{.49,.99378}}) &&
   And@@(Abs[cb3At[3,#[[1]]]-#[[2]]]<6*^-5&/@{{.52,1.4111},{.55,1.41892},{.6,1.43356},{.65,1.45084},{.7,1.47204}}),"CB3 check values"];
 mc3=Import[FileNameJoin[{base,"3d","inputs","mc_accepted.json"}],"RawJSON"];
 require[Length[mc3]==1 && AllTrue[mc3,StringStartsQ[#["decision"],"ACCEPTED"] && TrueQ[#["p1_calibrated"]]&],"3d MC selection"];
 require[Length /@ {rows2,ht2,mc2,ht3}=={754,13,4,15},"Unexpected source counts"];
 require[Length[rows3]==raw3["metadata"]["curve_rows"],"3d curve count"];
 require[AllTrue[ht3,TrueQ[#["accepted"]]&],"Unaccepted HT in 3d snapshot"];
 require[And@@(Min[Differences[Lookup[#,"Delta_sigma"]]]>=-10^-14& /@ {rows2,rows3}),"Grid order"];
 require[AllTrue[rows2,AllTrue[Lookup[#,{"curvature_CB8","value_CB8","tangent_CB8"}],NumberQ]&],"2d endpoint-construction columns"];

 (* ---- literature MC table: read every field as a string, convert numeric fields explicitly ---- *)
 litPath=FileNameJoin[{base,"combined","literature_mc_2d3d.csv"}];
 litRaw=Import[litPath,"CSV","Numeric"->False];
 require[ListQ[litRaw] && Length[litRaw]>1,"Literature CSV import"];
 litHeader=First[litRaw];
 require[SubsetQ[litHeader,{"dimension","source_key","sigma","Delta_sigma","Delta_epsilon","Delta_epsilon_err",
   "plotted","plot_offset","plot_Delta_sigma","source_file","source_line"}],"Literature CSV header"];
 require[AllTrue[Rest[litRaw],Length[#]==Length[litHeader]&],"Literature CSV row length"];
 num[v_]:=Which[NumberQ[v],N[v],StringQ[v]&&StringMatchQ[StringTrim[v],NumberString],N[ToExpression[StringTrim[v]]],
   True,Throw[Failure["PlotValidation",<|"Detail"->{"Non-numeric literature field",v}|>],"Failure"]];
 str[v_]:=If[StringQ[v],v,ToString[v]];
 litAll=AssociationThread[litHeader->#]& /@ Rest[litRaw];
 lit=Map[<|"d"->Round[num[#["dimension"]]],"key"->str[#["source_key"]],"s"->num[#["sigma"]],"x"->num[#["Delta_sigma"]],
   "y"->num[#["Delta_epsilon"]],"e"->num[#["Delta_epsilon_err"]],"off"->num[#["plot_offset"]],"px"->num[#["plot_Delta_sigma"]],
   "line"->str[#["source_line"]],"file"->str[#["source_file"]]|>&,Select[litAll,str[#["plotted"]]=="yes"&]];
 litOmitted=Select[litAll,str[#["plotted"]]=!="yes"&];
 require[Sort[{Round[num[#["dimension"]]],str[#["source_key"]],str[#["sigma"]]}& /@ litOmitted]===
   Sort[{{2,"angelini2014","1.75"},{3,"luijten1997_3d","1.6"}}] &&
   AllTrue[litOmitted,StringLength[str[#["exclusion_reason"]]]>0&],{"Unplotted literature rows",litOmitted}];
 require[StringStartsQ[str[First[Select[litOmitted,str[#["source_key"]]=="angelini2014"&]]["exclusion_reason"]],
   "window boundary, error too wide for the frame"],"Angelini sigma=7/4 omission reason"];
 lit2=Select[lit,#["d"]==2&];lit3=Select[lit,#["d"]==3&];
 litCounts=Counts[Lookup[lit,"key"]];
 require[{Length[lit2],Length[lit3]}=={12,2},{"Literature counts",Length[lit2],Length[lit3]}];
 require[Sort[Normal[litCounts]]===Sort[{"angelini2014"->3,"luijten1997_chi"->3,"luijten1997_Q"->4,
   "picco2012"->1,"xiao2025"->1,"luijten1997_3d"->2}],{"Literature source counts",litCounts}];
 require[AllTrue[lit,Abs[#["x"]-(#["d"]-#["s"])/2]<10^-12&],"Literature Delta_sigma = (d - sigma)/2"];
 require[AllTrue[lit2,1<#["s"]<=7/4&] && AllTrue[lit3,3/2<#["s"]<1.9637&],"Literature sigma outside window"];
 require[AllTrue[lit,Abs[#["px"]-#["x"]-#["off"]]<10^-12 && #["e"]>0&],"Literature display offset"];
 require[AllTrue[lit2,Abs[#["off"]]<=0.0135+10^-12&] && AllTrue[lit3,Abs[#["off"]-0.006]<10^-12&],"Literature offset rule"];
 require[DuplicateFreeQ[{#["d"],#["key"],#["s"],#["line"]}& /@ lit],"Duplicated literature row"];
 (* the four Angelini rows (three plotted, sigma = 7/4 omitted) must be exactly the previous 2d references *)
 angAll=Map[<|"x"->num[#["Delta_sigma"]],"y"->num[#["Delta_epsilon"]],"e"->num[#["Delta_epsilon_err"]],"plotted"->str[#["plotted"]]|>&,
   Select[litAll,str[#["source_key"]]=="angelini2014"&]];
 require[Length[angAll]==4 && AllTrue[mc2,Function[r,Count[angAll,
   p_/;Abs[p["x"]-r["x"]]<10^-9 && Abs[p["y"]-r["y"]]<10^-12 && Abs[p["e"]-r["error"]]<10^-12]==1]],
   "Angelini rows differ from 2d/inputs/plot_data.json references"];
 require[With[{om=Select[angAll,#["plotted"]=!="yes"&]},Length[om]==1 && om[[1,"plotted"]]=="no" &&
   Abs[om[[1,"x"]]-0.125]<10^-12 && Abs[om[[1,"y"]]-1.02]<10^-12 && Abs[om[[1,"e"]]-0.1]<10^-12],"Omitted Angelini row"];

 purple=RGBColor[.48,.24,.68];orange=RGBColor[.85,.39,.08];blue=RGBColor[.122,.467,.706];
 green=RGBColor[.12,.52,.38];black=GrayLevel[.12];gray=GrayLevel[.42];
 red=RGBColor[.80,.12,.18];
 (* 2026-10-18: one color per published MC reference (and per-reference shapes); Angelini as in Figures 01/05 *)
 teal=RGBColor[0.00,0.58,0.60];brown=RGBColor[0.55,0.34,0.16];slate=RGBColor[0.36,0.40,0.56];ochre=RGBColor[0.78,0.60,0.05];
 litStyle=<|"angelini2014"->{teal,"triangle",False},"luijten1997_chi"->{brown,"circle",False},
   "luijten1997_Q"->{brown,"circle",True},"luijten1997_3d"->{brown,"dotcircle",False},
   "picco2012"->{slate,"invtriangle",False},"xiao2025"->{ochre,"star",False}|>;
 require[Length[Union[First/@Values[litStyle]]]==4 && !IntersectingQ[First/@Values[litStyle],{purple,orange,blue,green,black,red,GrayLevel[.64]}] &&
   litStyle["angelini2014"][[1]]===RGBColor[0.00,0.58,0.60],"published MC: one color per reference (Luijten keys share one), none a method color, Angelini teal as in Figure 01"];
 require[SubsetQ[Keys[litStyle],Union[Lookup[lit,"key"]]],"Literature style table"];
 tex[s_,sz_:16]:=tex[s,sz]=Module[{g=MaTeX`MaTeX[s,FontSize->sz,"Preamble"->{"\\usepackage{color,txfonts}"}]},
  require[Head[g]===Graphics,{"MaTeX",s}];g];
 ticks[v_]:=({N[#],tex[#,14]}& /@ v);
 xy[rs_,key_]:=({#["Delta_sigma"],#[key]}& /@ rs);
 stroke[col_,dash_:{}]:=Directive[col,AbsoluteThickness[2.1],AbsoluteDashing[dash]];
 line[pts_,col_,dash_:{}]:={stroke[col,dash],Line[pts]};
 lineThin[pts_,col_,dash_]:={Directive[col,AbsoluteThickness[1.4],AbsoluteDashing[dash]],Line[pts]};
 band[rs_,prefix_]:={purple,Opacity[.14],EdgeForm[None],
  Polygon[Join[xy[rs,prefix<>"_core_low"],Reverse[xy[rs,prefix<>"_core_high"]]]]};
 marker[col_,shape_,filled_:True]:=Graphics[{
  EdgeForm[Directive[col,AbsoluteThickness[1.2]]],FaceForm[If[filled,col,White]],
  Switch[shape,"triangle",Polygon[{{0,1},{-.9,-.7},{.9,-.7}}],
    "invtriangle",Polygon[{{0,-1},{-.9,.7},{.9,.7}}],
    "square",Rectangle[{-.75,-.75},{.75,.75}],
    "diamond",Polygon[{{0,1},{1,0},{0,-1},{-1,0}}],
    "star",Polygon[Table[If[EvenQ[k],1.05,.47]{Sin[k Pi/5],Cos[k Pi/5]},{k,0,9}]],
    "dotcircle",{Disk[{0,0},.8],EdgeForm[None],FaceForm[col],Disk[{0,0},.3]},
    _,Disk[{0,0},.8]]},
  PlotRange->{{-1.1,1.1},{-1.1,1.1}},ImagePadding->0,ImageSize->11];
 markAt[pos_,col_,shape_,filled_:True]:=Inset[marker[col,shape,filled],pos,Center,Scaled[.017]];
 litPoint[r_]:=With[{st=litStyle[r["key"]],x=r["px"],y=r["y"],e=r["e"]},
  {st[[1]],AbsoluteThickness[1.1],Line[{{x,y-e},{x,y+e}}],
   Line[{Offset[{-4,0},{x,y-e}],Offset[{4,0},{x,y-e}]}],
   Line[{Offset[{-4,0},{x,y+e}],Offset[{4,0},{x,y+e}]}],markAt[{x,y},st[[1]],st[[2]],st[[3]]]}];
 mcBar[x_,y_,e_,thick_,cap_]:={black,AbsoluteThickness[thick],Line[{{x,y-e},{x,y+e}}],
  Line[{Offset[{-cap,0},{x,y-e}],Offset[{cap,0},{x,y-e}]}],
  Line[{Offset[{-cap,0},{x,y+e}],Offset[{cap,0},{x,y+e}]}]};
 newMCLayer:=Map[Function[r,With[{x=r["Delta_sigma"],y=r["Delta_epsilon"]},
  {mcBar[x,y,r["sigma_sys"],.9,4],mcBar[x,y,r["sigma_stat"],1.8,2],markAt[{x,y},black,"diamond"]}]],mc3];
 panel[prims_,xr_,yr_,xt_,yt_,title_,clean_]:=Graphics[prims,
  Frame->True,Axes->False,FrameStyle->Directive[black,AbsoluteThickness[1]],
  FrameLabel->{{tex["\\Delta_{\\mathcal E}",21],None},{tex["\\Delta_\\sigma",21],None}},
  FrameTicks->{{ticks[yt],None},{ticks[xt],None}},PlotLabel->If[clean,None,tex[title,19]],
  PlotRange->{xr,yr},PlotRangePadding->None,PlotRangeClipping->True,
  GridLines->{None,yt},GridLinesStyle->Directive[GrayLevel[.93],AbsoluteThickness[.5]],
  ImageSize->565,AspectRatio->.74,ImagePadding->{{73,16},{62,If[clean,12,38]}},Background->White];
 lineKey[col_,dash_,s_]:=Row[{Graphics[{stroke[col,dash],Line[{{0,0},{1,0}}]},
  ImageSize->{35,13},ImagePadding->1,PlotRange->{{0,1},{-.2,.2}}],Spacer[6],tex[s,14]}];
 pointKey[col_,shape_,filled_,s_]:=Row[{marker[col,shape,filled],Spacer[6],tex[s,14]}];
 patchKey[s_]:=Row[{Graphics[{purple,Opacity[.14],Rectangle[]},ImageSize->{35,12}],Spacer[6],tex[s,14]}];
 (* 2d vertical range (2026-10-13): enclose every plotted 2d error bar, HT marker and drawn curve/band, padded by 0.005 *)
 markerHalf2=0.003;
 yExt2=Join[(#["y"]-#["e"])& /@ lit2,(#["y"]+#["e"])& /@ lit2,
   Flatten[{#["Delta_thermal"]-markerHalf2,#["Delta_thermal"]+markerHalf2}& /@ ht2],
   Flatten[Lookup[rows2,{"curvature_CB8","curvature_core_low","curvature_core_high","direct_CB8"}]],cb3[2][[All,2]]];
 (* 2026-10-13: CB3 (0.9135 at 1/8) sets the lower edge, rounded down to a multiple of 0.005; the top keeps its rule *)
 yr2={Floor[Min[yExt2]-0.005,0.005],Round[Max[yExt2]+0.005,0.001]};
 yt2={.91,.94,.97,1,1.03};
 require[yr2[[1]]<First[yt2] && Last[yt2]<yr2[[2]] && Abs[yr2[[1]]-0.905]<10^-9 && Abs[yr2[[2]]-1.055]<10^-9,{"2d vertical range",yr2}];
 xr2={.11,.51};xr3={.513,.755};yr3={1.400,1.505};
 (* 2026-10-13 evening: SRI points (end of each window), where the baseline is pinned; checked against the curves *)
 sri2={1/8,1};sri3=ToExpression/@{protocol3["S"],protocol3["E_SR"]};
 require[With[{r=First@MinimalBy[rows2,#["Delta_sigma"]&]},Abs[r["Delta_sigma"]-0.125]<10^-12 && Abs[r["curvature_CB8"]-1]<10^-12],"2d baseline does not start at the SRI point"];
 require[With[{r=First@MinimalBy[rows3,#["Delta_sigma"]&]},Abs[r["Delta_sigma"]-sri3[[1]]]<10^-12 && Abs[r["slope_CB8"]-sri3[[2]]]<10^-10],"3d baseline does not start at the SRI point"];
 sriStar[pos_]:=Inset[marker[red,"star",True],pos,Center,Scaled[.019]];
 sriLayer[2]:={sriStar[sri2],Inset[tex["(1/8,\\ 1)",13],Offset[{-6,22},sri2],{Left,Bottom}]};
 sriLayer[3]:={sriStar[sri3],Inset[tex["(0.518149,\\ 1.412625)",13],Offset[{-6,-14},sri3],{Left,Top}]};
 (* 2026-10-13: CB prescription spread (core band, not drawn) relative to the baseline, for the caption *)
 spreadOf[rs_,pre_,basekey_]:=Module[{lo=Lookup[rs,pre<>"_core_low"],hi=Lookup[rs,pre<>"_core_high"],b=Lookup[rs,basekey],i},
   i=First@Ordering[hi-lo,-1];
   <|"below"->Max[b-lo],"above"->Max[hi-b],"width"->Max[hi-lo],"at"->rs[[i,"Delta_sigma"]]|>];
 spread=<|2->spreadOf[rows2,"curvature","curvature_CB8"],3->spreadOf[rows3,"slope","slope_CB8"]|>;
 sci[v_,d_]:=Module[{e=Floor[Log10[Abs[v]]],m},m=v/10^e;If[Round[m,10^-d]>=10,e=e+1;m=m/10];
   ToString[NumberForm[N[Round[m,10^-d]],{d+1,d}]]<>"\\times10^{"<>ToString[e]<>"}"];
 fix[v_,d_]:=ToString[NumberForm[N[Round[v,10^-d]],{d+1,d}]];
 spreadTeX[d_]:="{-}"<>sci[spread[d]["below"],2]<>"\\text{ and }{+}"<>sci[spread[d]["above"],2];
 require[Abs[spread[2]["width"]-0.005237337]<10^-8 && Abs[spread[3]["width"]-0.0001528401]<10^-9 &&
   Abs[spread[2]["below"]-0.004066646]<10^-8 && Abs[spread[3]["above"]-0.00008089098]<10^-10,{"2d/3d prescription spread differs from results/curves.csv",spread}];
 make[clean_]:=Module[{p2,p3,keys,keyGrid},
  p2=panel[{
   line[xy[rows2,"direct_CB8"],blue,{7,3,1,3}],
   lineThin[cb3[2],blue,{2,2.5}],
   line[xy[rows2,"curvature_CB8"],purple],
   litPoint /@ lit2,
   (markAt[{#["x"],#["Delta_thermal"]},green,"square",#["L"]==24]& /@ ht2),sriLayer[2]},
   xr2,yr2,{.125,.2,.3,.4,.5},yt2,"\\text{(a) 2d long-range Ising}",clean];
  p3=panel[{
   line[xy[rows3,"direct_CB8"],blue,{7,3,1,3}],
   lineThin[cb3[3],blue,{2,2.5}],
   line[xy[rows3,"slope_CB8"],purple],
   litPoint /@ lit3,
   (markAt[{#["Delta_sigma"],#["HT_L20"]},green,"square"]& /@ ht3),newMCLayer,sriLayer[3]},
   xr3,yr3,{.52,.55,.6,.65,.7,.75},{1.42,1.44,1.46,1.48,1.5},"\\text{(b) 3d long-range Ising}",clean];
  keys={lineKey[purple,{},"\\text{CB8 + SRI endpoint (baseline)}"],
   lineKey[blue,{7,3,1,3},"\\text{CB8: GFF only}"],
   Row[{Graphics[{Directive[blue,AbsoluteThickness[1.4],AbsoluteDashing[{2,2.5}]],Line[{{0,0},{1,0}}]},
     ImageSize->{35,13},ImagePadding->1,PlotRange->{{0,1},{-.2,.2}}],Spacer[6],tex["\\text{CB3: GFF only (three loops)}",14]}],
   pointKey[red,"star",True,"\\text{Short-range Ising point (end of window)}"],
   pointKey[green,"square",True,"\\text{HT: 2d }N=24\\text{; 3d }N=20"],
   pointKey[green,"square",False,"\\text{2d HT: }N=22\\ (\\Delta_\\sigma=0.125,\\ 0.126)"],
   pointKey[black,"diamond",True,"\\text{MC (this work): 3d}"],
   pointKey[teal,"triangle",False,"\\text{MC: Angelini et al. (2014)}"],
   pointKey[slate,"invtriangle",False,"\\text{MC: Picco (2012)}"],
   pointKey[ochre,"star",False,"\\text{MC: Xiao et al. (2025)}"],
   pointKey[brown,"circle",False,"\\text{MC: Luijten thesis (1997), 2d }\\chi\\text{ fit}"],
   pointKey[brown,"circle",True,"\\text{MC: Luijten thesis (1997), 2d }Q\\text{ fit}"],
   pointKey[brown,"dotcircle",False,"\\text{MC: Luijten thesis (1997), 3d Table 5.12}"]};
  keyGrid=Grid[Partition[PadRight[keys,3 Ceiling[Length[keys]/3],""],3],Alignment->Left,Spacings->{1.6,.65}];
  If[clean,Column[{Grid[{{p2,p3}},Spacings->{1.3,0}],keyGrid},Alignment->Center,Spacings->.8],
   Column[{Grid[{{p2,p3}},Spacings->{1.3,0}],
    keyGrid,
    tex["\\text{Purple: CB8 matched to the short-range Ising expansion at the star (2d to second order, 3d to first order). Blue: GFF series alone, CB8 (dash-dot) and CB3 (dotted).}",13],
    tex["\\text{Red star: short-range Ising point (2d exact, 3d bootstrap). HT: finite cutoff, not continuum values. Published MC: one color and shape per reference (legend), quoted errors; coincident markers shifted slightly.}",13],
    tex["\\text{Not drawn: prescription dependence, at most }"<>sci[spread[2]["width"],1]<>"\\text{ (2d) and }"<>sci[spread[3]["width"],1]<>"\\text{ (3d); 2d endpoint construction, up to }7.5\\times10^{-3}\\text{. Angelini et al. (2014) at }\\sigma=7/4\\text{ omitted.}",13]},
    Alignment->Center,Spacings->.8]]];
 require[AllTrue[mc3,yr3[[1]]<=#["Delta_epsilon"]-Max[#["sigma_stat"],#["sigma_sys"]] && #["Delta_epsilon"]+Max[#["sigma_stat"],#["sigma_sys"]]<=yr3[[2]]&],"3d MC errors outside range"];
 require[AllTrue[Select[mc2,#["s"]!=1.75&],yr2[[1]]<=#["y"]-#["error"] && #["y"]+#["error"]<=yr2[[2]]&],"MC errors outside range"];
 (* bars, caps (4 px) and markers of every literature point inside the frames; 0.0045 exceeds the half-width in both panels *)
 require[AllTrue[lit2,xr2[[1]]<=#["px"]-0.0045 && #["px"]+0.0045<=xr2[[2]] && yr2[[1]]<=#["y"]-#["e"] && #["y"]+#["e"]<=yr2[[2]]&],"2d literature outside frame"];
 require[AllTrue[ht2,xr2[[1]]<=#["x"]-0.0045 && #["x"]+0.0045<=xr2[[2]] &&
   yr2[[1]]<=#["Delta_thermal"]-markerHalf2 && #["Delta_thermal"]+markerHalf2<=yr2[[2]]&],"2d HT markers outside frame"];
 require[AllTrue[lit3,xr3[[1]]<=#["px"]-0.0045 && #["px"]+0.0045<=xr3[[2]] && yr3[[1]]<=#["y"]-#["e"] && #["y"]+#["e"]<=yr3[[2]]&],"3d literature outside frame"];
 (* drawn curves and bands inside the frames (no clipping) *)
 require[AllTrue[Join@@(xy[rows2,#]&/@{"curvature_CB8","curvature_core_low","curvature_core_high","direct_CB8"}),
   xr2[[1]]<=#[[1]]<=xr2[[2]] && yr2[[1]]<=#[[2]]<=yr2[[2]]&],"2d curves or band outside frame"];
 require[AllTrue[cb3[2],xr2[[1]]<=#[[1]]<=xr2[[2]] && yr2[[1]]<=#[[2]]<=yr2[[2]]&] && AllTrue[cb3[3],xr3[[1]]<=#[[1]]<=xr3[[2]] && yr3[[1]]<=#[[2]]<=yr3[[2]]&],"CB3 outside a frame"];
 require[AllTrue[Join@@(xy[rows3,#]&/@{"slope_CB8","slope_core_low","slope_core_high","direct_CB8"}),
   xr3[[1]]<=#[[1]]<=xr3[[2]] && yr3[[1]]<=#[[2]]<=yr3[[2]]&],"3d curves or band outside frame"];
 (* caption numbers for the 2d endpoint-construction spread (not drawn) *)
 endpointDev=<|"value"->Max[Abs[Lookup[rows2,"value_CB8"]-Lookup[rows2,"curvature_CB8"]]],
   "tangent"->Max[Abs[Lookup[rows2,"tangent_CB8"]-Lookup[rows2,"curvature_CB8"]]],
   "value3d"->Max[Abs[Lookup[rows3,"value_CB8"]-Lookup[rows3,"slope_CB8"]]]|>;
 require[Round[10^3 endpointDev["value"],0.1]==7.5 && Round[10^3 endpointDev["tangent"],0.1]==5.7 &&
   Round[10^4 endpointDev["value3d"],0.1]==1.2,{"Endpoint-construction sizes differ from the caption",endpointDev}];
 require[AllTrue[Select[rows2,0.15<=#["Delta_sigma"]<=0.30&],
   Max[#["value_CB8"],#["tangent_CB8"],#["curvature_CB8"]]-Min[#["value_CB8"],#["tangent_CB8"],#["curvature_CB8"]]>
     #["curvature_core_high"]-#["curvature_core_low"]&],"2d endpoint spread no longer exceeds the core band on [0.15,0.30]"];
 If[!DirectoryQ[FileNameJoin[{base,"figures"}]],CreateDirectory[FileNameJoin[{base,"figures"}]]];
 export[stem_,g_]:=Module[{p,q},
  p=Export[FileNameJoin[{base,"figures",stem<>".pdf"}],g,"PDF"];
  q=Export[FileNameJoin[{base,"figures",stem<>".png"}],g,"PNG",ImageResolution->160];
  require[AllTrue[{p,q},StringQ[#]&&FileExistsQ[#]&&FileByteCount[#]>0&],{"Export",stem}];
  Print["EXPORTED ",stem];];
 export["06_curves_2d3d",make[False]];export["06_curves_2d3d_clean",make[True]];
 diagnostics=<|"WolframVersion"->$Version,"Panels"->2,"Axes"->"Delta_sigma versus Delta_epsilon",
  "CurveCounts"-><|"2d"->Length[rows2],"3d"->Length[rows3]|>,"HTCounts"-><|"2d"->Length[ht2],"3d"->Length[ht3]|>,
  "MCCounts"-><|"2d literature"->Length[lit2],"2d new"->0,"3d new"->Length[mc3],"3d literature"->Length[lit3]|>,
  "LiteratureSourceCounts"->litCounts,
  "LiteratureTable"->"combined/literature_mc_2d3d.csv",
  "LiteratureTableSHA256"->IntegerString[FileHash[litPath,"SHA256"],16,64],
  "LiteratureSelection"->"Monte Carlo rows of <PAPER>/notes/comparison_data/lit_{2d,3d}.csv (extracted 2026-10-12) with 1<sigma<=7/4 (2d) or 3/2<sigma<1.9637 (3d); superseded preliminary 3d value not plotted; Angelini 2014 sigma=7/4 not plotted since 2026-10-13 (window boundary, error too wide for the frame)",
  "LiteratureNotPlotted"->(<|"d"->Round[num[#["dimension"]]],"key"->str[#["source_key"]],"sigma"->str[#["sigma"]],
     "Delta_epsilon"->str[#["Delta_epsilon"]],"err"->str[#["Delta_epsilon_err"]],"reason"->str[#["exclusion_reason"]]|>& /@ litOmitted),
  "LiteratureDisplayOffsets"->"2d: centred dodge over plotted rows, step 0.009, max |offset| 0.0135 (sigma=7/4 pair at -/+0.0045 since 2026-10-13, -/+0.009 since the SRI star of 2026-10-13 evening); 3d: +0.006; project HT/MC at true Delta_sigma",
  "LiteraturePoints"->(KeyTake[#,{"d","key","s","x","px","y","e","line"}]& /@ lit),
  "CurvesDrawn"->{"baseline CB8 + SRI endpoint (2d curvature_CB8, 3d slope_CB8); its core band is not drawn since 2026-10-13 (size in the caption)","direct_CB8 (GFF only)",
    "CB3 GFF only (C_0..C_3; combined/cb3_gff_only.csv, since 2026-10-13)"},
  "CB3GFFOnly"-><|"File"->"combined/cb3_gff_only.csv","Generator"->"combined/make_cb3_gff_only.py (release cb('direct',3,...))",
    "SHA256"->IntegerString[FileHash[FileNameJoin[{base,"combined","cb3_gff_only.csv"}],"SHA256"],16,64],
    "Min2d"->MinimalBy[cb3[2],Last][[1]],"Min3d"->MinimalBy[cb3[3],Last][[1]]|>,
  "PrescriptionSpreadNotDrawn"->KeyMap[ToString[#]<>"d"&,spread],
  "HTL22"->"2d L=22 points at Delta_sigma = 0.125 (crossover benchmark, exact value 1) and 0.126 drawn alike (green open square), one legend entry; no L=24 solution there",
  "CleanVariant"->"panels + legend (key); no panel titles, no caption lines (since 2026-10-13)",
  "EndpointConstructions2d"->"value_CB8 (value only) and tangent_CB8 (value + zero slope) not drawn since 2026-10-13; size stated in the caption; baseline curvature_CB8",
  "EndpointConstructionMaxDeviation"-><|"2d value"->Max[Abs[Lookup[rows2,"value_CB8"]-Lookup[rows2,"curvature_CB8"]]],
    "2d tangent"->Max[Abs[Lookup[rows2,"tangent_CB8"]-Lookup[rows2,"curvature_CB8"]]],
    "2d curvature core width"->Max[Lookup[rows2,"curvature_core_high"]-Lookup[rows2,"curvature_core_low"]],
    "3d value"->Max[Abs[Lookup[rows3,"value_CB8"]-Lookup[rows3,"slope_CB8"]]],
    "3d slope core width"->Max[Lookup[rows3,"slope_core_high"]-Lookup[rows3,"slope_core_low"]]|>,
  "NewMC3d"->mc3,"NewMCErrorBars"->"Statistical and systematic shown separately, not combined",
  "FullMCErrorBars"->True,"NoSmoothing"->True,"NoFitting"->True,"ResidualPanels"->False,
  "PBControls"->"not drawn since 2026-10-13 (previously 2d PB8 [5/3], b=3.5; 3d PB7, b=4); see history/clean_curves_before_20261013/",
  "PanelWindows"->{{xr2,yr2},{xr3,yr3}},
  "SRIStar"-><|"2d"->N[sri2],"3d"->sri3,"Source3d"->"3d/inputs/protocol.json S, E_SR (conformal bootstrap, Chang et al. 2024)",
    "Marker"->"filled red star with coordinate label (black before 2026-10-18); drawn on top; baseline curves start there (checked)"|>,
  "Palette"->"2026-10-18: SRI star red; published MC one color and shape per reference (Angelini teal, Luijten brown, Picco slate, Xiao ochre), no method color; purple, blue, green, black unchanged",
  "YRange2dRule"->"2026-10-13: extremes of the plotted 2d literature bars, HT markers (half-height 0.003), curves, core band (not drawn) and CB3, padded by 0.005; top rounded to 0.001, bottom rounded down to a multiple of 0.005 (0.905, set by CB3 since the afternoon of 2026-10-13); ticks 0.91, 0.94, 0.97, 1.00, 1.03",
  "YExtremes2d"->{Min[yExt2],Max[yExt2]}|>;
 require[StringQ[Export[FileNameJoin[{base,"combined","diagnostics.json"}],diagnostics,"RawJSON"]],"Diagnostics export"];
 Print["FINISHED COMBINED CURVES ",diagnostics];diagnostics
],"Failure"];
With[{finalResult=result},End[];finalResult]
