"""Add the method appendix; all earlier displayed mathematical blocks retained."""
from pathlib import Path
import re,json,math,difflib
W=Path(__file__).resolve().parents[1]
J=json.load(open(W/'verification/method_precision_results.json'))
E=json.load(open(W/'verification/extra_checks.json'))
M=json.load(open(W/'verification/method_benchmarks.json'))
rows={};rpt={}
for d in [2,3]:
 j=J[str(d)];step=.1 if d==2 else .05
 allowance=math.ceil(4*j['sampling_standard_error']/step-1e-12)*step
 rpt[str(d)]={'underlying_mean':j['C6'],'sampling_standard_error':j['sampling_standard_error'],'reported_centre':f"{j['C6']:.{1 if d==2 else 2}f}",'empirical_allowance':round(allowance,8),'rule':'Four sampling standard errors rounded up in steps of 0.1 (d2) or 0.05 (d3). Not an interval enclosure.'}
rows['RESULT_ROWS']='\n'.join(f"{d} & {J[str(d)]['C6']:.8f} & {J[str(d)]['previous']['sampling_standard_error']:.6f} & {J[str(d)]['sampling_standard_error']:.6f} & {J[str(d)]['precision_improvement']:.2f} \\\\"for d in [2,3])
rows['PILOT_ROWS']='\n'.join(label+f" & {M['rows']['2'][key]['variance_ratio']:.3f} & {M['rows']['3'][key]['variance_ratio']:.3f} \\\\"for key,label in [('base','Original randomized Sobol'),('mc','Independent pseudo-random Monte Carlo'),('radial','Radial coordinates placed first'),('single','One-coordinate edge-order encoding'),('smooth6','Nominal endpoint rate $0.6p$'),('smooth5','Nominal endpoint rate $0.5p$'),('rate1','Nominal endpoint rate $1.0p$'),('anti','Radial antithetic pairs')])
rows['CAMPAIGN_ROWS']='\n'.join(label+' & '+' & '.join(f"{J[str(d)][source][tag]['C6']:.8f} & {J[str(d)][source][tag]['sampling_standard_error']:.6f}"for d in [2,3])+r' \\'for label,source,tag in [('Fresh A','fresh_campaigns','new_a'),('Fresh B','fresh_campaigns','new_b')])
rows['CAMPAIGN_ROWS']+='\nFresh only combined & '+' & '.join(f"{J[str(d)]['fresh_only']['C6']:.8f} & {J[str(d)]['fresh_only']['sampling_standard_error']:.6f}"for d in [2,3])+r' \\'
rows['ERROR_ROWS']='\n'.join(str(d)+' & '+' & '.join(f"{J[str(d)]['error_by_loop'][str(L)]:.6f}"for L in range(3,7))+f" & {J[str(d)]['shared_input_standard_error']:.6f} & {J[str(d)]['sampling_standard_error']:.6f}"+r' \\'for d in [2,3])
rows['LOWER_ROWS']='\n'.join(str(d)+' & '+' & '.join(f"{q['pull']:+.2f}"for q in J[str(d)]['lower_order_checks'])+r' \\'for d in [2,3])
for d in [2,3]:rows['CENTRE'+str(d)]=rpt[str(d)]['reported_centre'];rows['ALLOW'+str(d)]=f"{rpt[str(d)]['empirical_allowance']:.{1 if d==2 else 2}f}";rows['BOOT'+str(d)]=f"{E[str(d)]['bootstrap_se']:.8f}"
rows['SAMPLES']='782,893,056';rows['LAGRANGE']=r'$7\times10^{-13}$';rows['BIAS']=r'$3.4\times10^{-7}$'
appendix=(W/'code/method_appendix_template.tex').read_text()
for k,v in rows.items():appendix=appendix.replace('@@'+k+'@@',v)
assert not re.search(r'@@\w+@@',appendix)
(W/'C6_numerical_methods_appendix.tex').write_text(appendix)
base=(W/'provenance/previous_note.tex').read_text()
addition=r'''\par\smallskip
Appendix~\ref{app:C6Methods} adds an equal-budget numerical-method study
and further independent integrations. The updated estimates are
$C_6(2)=@@C2@@\pm@@A2@@$ and $C_6(3)=@@C3@@\pm@@A3@@$, with sampling
standard errors @@S2@@ and @@S3@@. Shared-product arithmetic accelerates
the unchanged forest kernels. The reported estimator retains full
covariance and shared-input uncertainty. Alternative maps and a paired
dimension control are benchmarked, including methods which did not
improve the complete coefficient. No independent field-theoretic
validation or rigorous numerical enclosure is claimed.
'''
for d in [2,3]:addition=addition.replace('@@C'+str(d)+'@@',rows['CENTRE'+str(d)]).replace('@@A'+str(d)+'@@',rows['ALLOW'+str(d)]).replace('@@S'+str(d)+'@@',f"{J[str(d)]['sampling_standard_error']:.6f}")
new=base.replace('\\end{abstract}',addition+'\\end{abstract}',1).replace('\\begin{thebibliography}',appendix+'\n\\begin{thebibliography}',1)
bibs=r'''\bibitem{MethodVegas}G. P. Lepage,
\emph{Adaptive Multidimensional Integration: VEGAS Enhanced},
J. Comput. Phys. \textbf{439} (2021) 110386,
\href{https://arxiv.org/abs/2009.05112}{arXiv:2009.05112}.
\bibitem{MethodLattice}S. Borowka, G. Heinrich, S. Jahn, S. P. Jones,
M. Kerner and J. Schlenk,
\emph{A GPU compatible quasi-Monte Carlo integrator interfaced to pySecDec},
Comput. Phys. Commun. \textbf{240} (2019) 120,
\href{https://arxiv.org/abs/1811.11720}{arXiv:1811.11720}.
\bibitem{MethodGlobal}M. Borinsky,
\emph{Tropicalized quantum field theory and global tropical sampling},
\href{https://arxiv.org/abs/2508.14263v2}{arXiv:2508.14263v2} (2026).
'''
new=new.replace('\\end{thebibliography}',bibs+'\\end{thebibliography}',1)
new=new.replace('Precision refinement: 14 September 2026','Numerical-method refinement: 14 September 2026',1)
(W/'long_range_ising_complete.tex').write_text(new)
# A standalone excerpt with its own compact bibliography.
preamble=base.split('\\begin{document}')[0]
preamble=re.sub(r'\\title\{[\s\S]*?\}\n\\author',lambda _:r'\title{Numerical-method benchmarks and precision refinement\\of $C_6(2)$ and $C_6(3)$}'+'\n'+r'\author',preamble,count=1)
preamble=re.sub(r'\\date\{[^}]*\}',lambda _:r'\date{14 September 2026}',preamble,count=1)
extra_refs=r'''\bibitem{BorinskyD2Focus}M. Borinsky,
\emph{Tropical Monte Carlo quadrature for Feynman integrals},
\href{https://arxiv.org/abs/2008.12310}{arXiv:2008.12310}.
\bibitem{PrecisionSobol}SciPy developers, \emph{Sobol engine reference},
\url{https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.qmc.Sobol.html}.
\bibitem{PrecisionQMC}SciPy developers, \emph{Quasi-Monte Carlo introduction},
\url{https://docs.scipy.org/doc/scipy/reference/stats.qmc.html}.
'''
stand=preamble+'\\begin{document}\n\\maketitle\n'+appendix.replace('\\clearpage\n','',1)+'\n\\begin{thebibliography}{9}\n'+extra_refs+bibs+'\\end{thebibliography}\n\\end{document}\n'
(W/'C6_numerical_methods.tex').write_text(stand)
pat=r'(?<!\\)\\begin\{(equation\*?|align\*?|gather\*?|multline\*?|eqnarray\*?|displaymath)\}[\s\S]*?\\end\{\1\}|(?<!\\)\\\[[\s\S]*?(?<!\\)\\\]'
a=[m.group()for m in re.finditer(pat,base)];b=[m.group()for m in re.finditer(pat,new)]
assert b[:len(a)]==a
(W/'verification/source_preservation.json').write_text(json.dumps({'previous_displays':len(a),'current_displays':len(b),'all_previous_displays_unchanged_and_in_order':True},indent=2))
(W/'verification/reported_values.json').write_text(json.dumps(rpt,indent=2))
(W/'source.diff').write_text(''.join(difflib.unified_diff(base.splitlines(True),new.splitlines(True),fromfile='previous_note.tex',tofile='long_range_ising_complete.tex')))
print(rpt,'displays',len(a),len(b))
