"""Build the precision appendix and preserve every prior displayed formula."""
import json,math,re,hashlib,difflib,os
from pathlib import Path
from final_analysis import summarize,W
from extra_checks import coefficient_blocks
OUT=Path(os.environ.get('C6_OUTPUT_DIR',str(W)))

def fl(x,n=6):return f'{x:.{n}f}'
def table(rows,columns,header):
 return '\\begin{center}\\begin{tabular}{'+columns+'}\n\\toprule\n'+header+'\\\\\\midrule\n'+'\n'.join(' & '.join(map(str,r))+'\\\\'for r in rows)+'\n\\bottomrule\n\\end{tabular}\\end{center}\n'

if __name__=='__main__':
 OUT.mkdir(exist_ok=True);(OUT/'verification').mkdir(exist_ok=True)
 results={d:summarize(d) for d in (2,3)}
 report={}
 for d,j in results.items():
  # The empirical allowance is a transparent convention, not a confidence guarantee.
  unit=.1 if d==2 else .05
  allowance=unit*math.ceil(4*j['sampling_standard_error']/unit)
  report[d]={'estimate':j['C6'],'sampling_standard_error':j['sampling_standard_error'],'empirical_allowance':allowance,'rounding_digits':1 if d==2 else 2,'reported_estimate':round(j['C6'],1 if d==2 else 2),'allowance_rule':'Round four estimated sampling standard errors upward to 0.1 (d=2) or 0.05 (d=3); empirical allowance only.'}
 old={}
 for d in (2,3):
  previous=json.load(open(W/f'baseline/lri_C6_d{d}_complete_update/verification/C6_d{d}_result.json'))
  old[d]=(previous[f'full_C6_{d}'],previous['sampling_standard_error'])
 rt=table([[f'$d={d}$',fl(old[d][0],8),fl(old[d][1],6),fl(results[d]['C6'],8),fl(results[d]['sampling_standard_error'],6)]for d in (2,3)],'crrrr','Dimension & Previous center & Previous SE & New center & New SE')
 rt+='\\begin{equation}\\boxed{C_6(2)='+fl(report[2]['reported_estimate'],1)+'\\pm'+fl(report[2]['empirical_allowance'],1)+',\\qquad C_6(3)='+fl(report[3]['reported_estimate'],2)+'\\pm'+fl(report[3]['empirical_allowance'],2)+'.}\\label{prec:reported}\\end{equation}\n'
 rt+='The estimated sampling standard errors decrease by factors '+fl(old[2][1]/results[2]['sampling_standard_error'],2)+' and '+fl(old[3][1]/results[3]['sampling_standard_error'],2)+', respectively.  For transparency, the reporting convention is four sampling standard errors rounded upward to 0.1 at $d=2$ and to 0.05 at $d=3$; it is not a probabilistic coverage theorem.\n'
 prod=[]
 for d in (2,3):
  for tag in ('prod_a','prod_b'):
   r=results[d]['runs'][tag]
   prod.append([f'{d}',tag[-1].upper(),*[f'{results[d]["samples"][tag][str(L)]:,}'for L in range(3,7)],fl(r['coefficients'][6],6),fl(r['sampling_se'][6],6)])
 pt=table(prod,'ccrrrrrr','$d$ & Run & $L=3$ & $L=4$ & $L=5$ & $L=6$ & $C_6$ & SE')
 pt='{\\footnotesize\n\\setlength{\\tabcolsep}{3.2pt}\n'+pt+'}\n'
 pt+='In total the new production uses '+f'{sum(sum(sum(z.values())for z in j["samples"].values())for j in results.values()):,}'+' kernel samples across both dimensions, campaigns and all four loop orders. Pilot and validation samples are additional and are excluded from the result.\n'
 diag=table([[d,*[fl(results[d]['error_by_loop'][str(L)],6)for L in range(3,7)],fl(results[d]['known76_common_uncertainty'],6),fl(results[d]['sampling_standard_error'],6)]for d in (2,3)],'crrrrrr','$d$ & Three-loop & Four-loop & Five-loop & Six-loop & Shared input & Total SE')
 diag+='Each row lists standard-error contributions; independent contributions combine in quadrature, not by addition.\n'
 diag+=table([[d,c['order'],fl(c['estimate'],10),fl(c['se'],7),fl(c['reference'],10),fl(c['pull'],2)]for d in (2,3)for c in results[d]['lower_order_checks']],'ccrrrr','$d$ & Order & New estimate & SE & Retained value & Pull')
 diag+=table([[d,fl(j['campaign_difference_pulls'][0],3),fl(j['half_run_coefficients'][0][6],6),fl(j['half_run_coefficients'][1][6],6),f'{j["nonlinear_jackknife_bias_estimate"][6]:.3g}']for d,j in results.items()],'crrrr','$d$ & Campaign difference pull & First half & Second half & Bias estimate')
 diag+='The campaign-difference pull uses the variance of the difference; the common two-dimensional input cancels from that difference.\n'
 appendix=(W/'code/precision_appendix_template.tex').read_text()
 for name,text in [('result',rt),('production',pt),('diagnostics',diag)]:
  appendix=appendix.replace('\\input{precision_'+name+'_table.tex}',text)
 (OUT/'C6_precision_appendix.tex').write_text(appendix)
 original_path=W/'baseline/lri_C6_d3_complete_update/long_range_ising_complete.tex'
 if not original_path.exists():original_path=W/'provenance/previous_note.tex'
 original=original_path.read_text()
 addition='\n\\par\\smallskip\nThe current precision update in Appendix~\\ref{app:C6Precision} supersedes the earlier numerical error bars with $C_6(2)='+fl(report[2]['reported_estimate'],1)+'\\pm'+fl(report[2]['empirical_allowance'],1)+'$ and $C_6(3)='+fl(report[3]['reported_estimate'],2)+'\\pm'+fl(report[3]['empirical_allowance'],2)+'$. These are empirical numerical allowances, not rigorous bounds. Graph-stratified randomized integration, independent campaigns, full regulator-jet covariance and the common two-dimensional finite-kernel uncertainty are documented; previous analytic formulas are unchanged.\n'
 full=original.replace('\\end{abstract}',addition+'\\end{abstract}',1)
 full=full.replace('\\begin{thebibliography}',appendix+'\n\\begin{thebibliography}',1)
 bib=r'''
\bibitem{PrecisionSobol} SciPy developers, \emph{scipy.stats.qmc.Sobol}: LMS scrambling, digital shifts, powers-of-two balance and bit resolution. Documentation accessed 14 September 2026. \url{https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.qmc.Sobol.html}.
\bibitem{PrecisionQMC} SciPy developers, \emph{Quasi-Monte Carlo submodule}: independent randomizations, approximate error estimation and limits of convergence claims. Documentation accessed 14 September 2026. \url{https://docs.scipy.org/doc/scipy/reference/stats.qmc.html}.
'''
 full=full.replace('\\end{thebibliography}',bib+'\\end{thebibliography}')
 full=full.replace('\\date{Three-dimensional numerical sixth order:', '\\date{Precision refinement: 14 September 2026\\\\Three-dimensional numerical sixth order:',1)
 (OUT/'long_range_ising_complete.tex').write_text(full)
 (OUT/'source.diff').write_text(''.join(difflib.unified_diff(original.splitlines(True),full.splitlines(True),fromfile='previous_note.tex',tofile='long_range_ising_complete.tex')))
 pre=original.split('\\begin{document}')[0]
 pre=re.sub(r'\\title\{[\s\S]*?\\author\{',r'\\title{Precision refinement of the\\\\sixth-order long-range Ising coefficients\\\\in two and three dimensions}\n\\author{',pre,count=1)
 pre=re.sub(r'\\date\{[\s\S]*?\}\n',r'\\date{14 September 2026}\n',pre,count=1)
 stand=pre+'\\begin{document}\n\\maketitle\n\\appendix\\setcounter{section}{22}\n'+appendix.replace('\\clearpage\n','',1)+'\n\\begin{thebibliography}{9}\n'+bib+'\\end{thebibliography}\n\\end{document}\n'
 (OUT/'C6_d2_d3_precision.tex').write_text(stand)
 restored=full.replace(addition,'',1).replace(appendix+'\n','',1).replace(bib,'',1).replace('\\date{Precision refinement: 14 September 2026\\\\Three-dimensional numerical sixth order:', '\\date{Three-dimensional numerical sixth order:',1)
 assert restored==original
 before=coefficient_blocks(original);after=coefficient_blocks(full);it=iter(after);assert all(any(x==y for y in it)for x in before)
 audit={'previous_displayed_blocks':len(before),'new_displayed_blocks':len(after),'previous_preserved_in_original_order':True,'full_previous_text_restored_after_removing_explicit_additions_and_date_prefix':True,'previous_sha256':hashlib.sha256(original.encode()).hexdigest(),'new_sha256':hashlib.sha256(full.encode()).hexdigest()}
 (OUT/'verification/source_preservation.json').write_text(json.dumps(audit,indent=2))
 (OUT/'verification/reported_values.json').write_text(json.dumps(report,indent=2))
 print(report,audit)
