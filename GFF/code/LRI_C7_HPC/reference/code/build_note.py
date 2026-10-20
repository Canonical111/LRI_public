"""Build the C7 appendix from the accepted saved analysis; preserve earlier displays."""
from pathlib import Path
import json,re,shutil,sys
W=Path(__file__).resolve().parents[1]
basepath=Path(sys.argv[1]) if len(sys.argv)>1 else W/'retained/previous_note.tex'
out=Path(sys.argv[2]) if len(sys.argv)>2 else W/'note/final';out.mkdir(parents=True,exist_ok=True)
b=basepath.read_text();d=json.load(open(W/'verification/C7_assembled_result.json'))
s=(W/'note/C7_appendix_template.tex').read_text()
prod=r'''The two independent power-free campaigns each have 16 independent
randomizations at each loop order. The graph allocations were frozen
from separate pilot data; every positive per-graph count is a power of two.
\begin{center}\begin{tabular}{rrrr}
\toprule
Loops & Active strata & Points per replicate & Production replicates\\
\midrule
5 & 76 & 1,087,360 & 32\\
6 & 395 & 2,039,600 & 32\\
7 & 2254 & 3,867,568 & 32\\
\bottomrule
\end{tabular}\end{center}
The 44 seventh-order primitive classes are omitted from these new point
streams only because their independently evaluated contribution is added
exactly once. The continuous production count is 223,824,896. The paired
power-sector streams evaluate 7,043,120 sampled trees; a tree evaluation
at degree $N$ uses up to $(N+1)^{L-1}$ tensor nodes, so these counts are not
comparable unit costs. The complete raw-stream manifest records the
1,714,336,280 nominal tensor nodes as well as actual timings. Pilots,
training, precision replays and deterministic lower-loop calculations are
not included in these production counts.

The two independent power-free campaigns, projected using the same full
lower-loop data and retained primitive input, give $-325691.36$ and
$-326017.03$, with sampling errors $1906.74$ and $2254.84$. Their difference
is $0.11$ combined sampling standard errors. These intermediate numbers
are not full $C_7$: the power-containing higher-loop inputs have not yet
been added to them. The common power correction is accounted for separately,
not treated as an independent measurement in each campaign.
'''
level=r'''The telescoping resolution sequence for the \emph{complete} coefficient is
\begin{center}\begin{tabular}{rrr}
\toprule
Power-grid degree & Full $C_7$ estimate & Sampling standard error\\
\midrule
'''
for v in d['resolution_sequence']:
 level+=f"{v['degree']} & {v['mean'][7]:,.2f} & {v['sampling_se'][7]:,.2f}\\\\\n"
level+=r'''\bottomrule\end{tabular}\end{center}
The individual refinement corrections (in absolute units of $C_7$) are
\begin{center}\begin{tabular}{lrr}\toprule
Paired degrees & Correction & Sampling standard error\\\midrule
'''
for name,label in [('refine3',r'$1\to3$'),('refine5',r'$3\to5$'),('refine6',r'$5\to6$')]:
 v=d['power_levels'][name];level+=f"{label} & {v['mean'][7]:+,.2f} & {v['sampling_se'][7]:,.2f}\\\\\n"
level+=r'''\bottomrule\end{tabular}\end{center}
The last refinement is small compared with the total sampling error.
No limit has been replaced by a fitted extrapolation. The empirical
allowance is chosen as the next multiple of 1000 above the largest of
four sampling errors, twice the absolute last correction plus four errors
of that correction, and the observed half-split displacement. This gives
24000; it is an error policy supported by convergence tests, not a proved
upper bound on all remaining discretization or shared systematic errors.

A 4096-resample bootstrap of the independent randomized replicate totals,
with frozen controls and allocations, gives a seventh-order standard
error of 5677.90, compared with the covariance value 5861.76. Splitting
every production stream into its first and second halves gives
$-313955.46$ and $-332855.16$. Both shifts lie inside the stated allowance.
The largest absolute standardized residual among the monitored spurious
Laurent poles is 2.78. A direct fixed-point assembly of the raw positive
Taylor coefficients followed by the explicitly recorded zero-pole control
agrees with the affine calculation to $1.8\times10^{-10}$. The uncontrolled
central value is also retained in the record; the control coefficients
were fixed before production, not chosen to match any physical reference.
'''
low=r'''The same calculation gives the following uncalibrated lower-order checks:
\begin{center}\begin{tabular}{rrrr}\toprule
Coefficient & New value & Sampling error & Retained reference\\\midrule
'''
for v in d['lower_order_checks']:
 if v['n']>=5:low+=f"$C_{v['n']}(1)$ & {v['value']:,.6f} & {v['sampling_se']:,.6f} & {v['reference']:,.6f}\\\\\n"
low+=r'''\bottomrule\end{tabular}\end{center}
Their differences are respectively 1.45 and 0.71 sampling errors.
Deterministic low-loop assembly also gives
$C_3=-3.71985632290349$ and $C_4=45.4248801371166$; their discrepancies
from the retained higher-precision values are respectively
$1.5\times10^{-12}$ and $3.4\times10^{-8}$.
'''
power=r'''\begin{equation}\begin{aligned}
 C_7^{\rm power\mbox{-}free}&=-324276.5293,
 &\widehat\sigma_{\rm free}&=1476.7054,\\
 \Delta_p C_7&=+871.2185,
 &\widehat\sigma_{\Delta_p}&=5672.7349.
\end{aligned}\label{c7f:fullPowerSplit}\end{equation}
The two quantities have covariance $-173.7207$ in squared coefficient
units, which is included in the final variance'''
repl={'@@ROUNDED@@':'-323000','@@ALLOWANCE@@':r'$\pm24000$', '@@MEAN@@':f"{d['C7_full']:.10f}",'@@SE@@':f"{d['sampling_se']:.6f}",'@@PRODUCTION_TABLE@@':prod,'@@LEVEL_TABLE@@':level,'@@LOWER_CHECK_TABLE@@':low,'@@POWER_CORRECTION@@':power}
for a,c in repl.items():s=s.replace(a,c)
# Avoid nested math delimiters inside the boxed text field.
s=s.replace(r'\text{$\pm24000$}',r'\pm24000')
assert '@@' not in s
(out/'C7_full_appendix.tex').write_text(s)
# Preserve source in exact order; only front matter and bibliography are updated.
full=b.replace('\\begin{thebibliography}{99}',s+'\n\\begin{thebibliography}{99}')
full=re.sub(r'\\title\{.*?\}\n\\author',lambda m:r'''\title{The thermal dimension of the\\long-range Ising model\\[1mm]
\large Closed forms through fifth order; numerical sixth order at $d=1,2,3$\\and seventh order at $d=1$}
\author''',full,count=1,flags=re.S)
full=full.replace(r'\date{Numerical-method refinement:',r'\date{One-dimensional numerical seventh order: 15 September 2026\\Numerical-method refinement:',1)
paragraph=r'''\par\smallskip
Appendix~\ref{app:C7complete} now gives the full one-dimensional seventh-order
numerical estimate $C_7(1)=(-3.23\pm0.24)\times10^5$, with underlying
sampling standard error $5.862\times10^3$ and an empirical (not rigorous)
reported allowance. Both power-free and power-containing graphs are
included in one coordinate-space finite prescription. Binary vertex
clusters, pointwise forest subtraction and paired meromorphic quadrature
refinements complete the earlier missing numerical contribution. No
seventh-order power correction is set to zero or inferred from lower orders.
The inventory, full rational bare-series certificate, raw replicate data,
resolution checks and shared primitive-input covariance are supplied.
'''
full=full.replace(r'\end{abstract}',paragraph+'\n'+r'\end{abstract}',1)
giles=r'''\bibitem{C7Giles} M.~B.~Giles, \emph{Multilevel Monte Carlo methods},
arXiv:1304.5472 (2013), \url{https://arxiv.org/abs/1304.5472}.
'''
full=full.replace(r'\end{thebibliography}',giles+'\n'+r'\end{thebibliography}')
full=full.replace('pdftitle={Long-range Ising thermal dimension: sixth order in one, two and three dimensions}','pdftitle={Long-range Ising thermal dimension: numerical seventh order in one dimension}')
(out/'long_range_ising_complete.tex').write_text(full)
# Standalone has the same appendix text and equation labels, with local page numbering.
preamble=b[:b.index(r'\begin{document}')]
preamble=preamble[:preamble.index(r'\title{')]+preamble[preamble.index(r'\setcounter{tocdepth}'):]
preamble=preamble.replace('pdftitle={Long-range Ising thermal dimension: sixth order in one, two and three dimensions}','pdftitle={Full seventh order in one-dimensional long-range Ising}')
stand=preamble+r'''\title{Full seventh order in one-dimensional long-range Ising\\[2mm]
\large Coordinate forests, binary-cluster integration, and numerical evidence}
\author{Research calculation record}\date{15 September 2026}
\begin{document}\maketitle\appendix\setcounter{section}{24}
'''+s.replace('\\clearpage\n','',1)+r'''
\begin{thebibliography}{9}
\bibitem{BrownKreimerLocal} F.~Brown and D.~Kreimer,
\emph{Angles, scales and parametric renormalization}, arXiv:1112.1180 (2011).
\bibitem{PrecisionSobol} SciPy developers, \emph{scipy.stats.qmc.Sobol}.
LMS scrambling, digital shifts and powers-of-two balance. Documentation
accessed 15 September 2026; calculation runtime SciPy 1.17.0.
\url{https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.qmc.Sobol.html}.
'''+giles+r'\end{thebibliography}\end{document}'
(out/'C7_1d_full_calculation.tex').write_text(stand)
# Enumerate all display blocks, including unnumbered ones, as a subsequence check.
pat=r'\\begin\{(equation\*?|align\*?|gather\*?|multline\*?|eqnarray\*?)\}.*?\\end\{\1\}|(?<!\\)\\\[.*?(?<!\\)\\\]'
old=[m.group(0)for m in re.finditer(pat,b,re.S)];new=[m.group(0)for m in re.finditer(pat,full,re.S)];i=0
for t in new:
 if i<len(old) and t==old[i]:i+=1
assert i==len(old)
old_body=b[b.index('\\section{'):b.index('\\begin{thebibliography}')]; assert old_body in full
(W/'verification/source_preservation.json').write_text(json.dumps({'previous_display_blocks':len(old),'new_total_display_blocks':len(new),'retained_verbatim_in_original_order':i,'all_retained':i==len(old),'entire_previous_main_body_retained_verbatim':True,'front_matter_updated':True,'new_appendix':'Y'},indent=2))
print('built note',out,'preserved',i,'displays; total',len(new))
