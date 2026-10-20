#!/usr/bin/env python3
"""Generate publication tables and separate plots from reproduced C1 data.
No reference result is silently substituted. The LaTeX embeds its tables and does not require these separate figures.
"""
from __future__ import annotations
import argparse,csv,hashlib,json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[2]
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--results',type=Path,default=ROOT/'outputs/reproduced');args=p.parse_args();res=args.results.resolve()
 td=ROOT/'outputs/tables';fd=ROOT/'outputs/figures';td.mkdir(exist_ok=True);fd.mkdir(exist_ok=True);sources={};products=[]
 def load(path):
  if not path.exists():raise FileNotFoundError(f'{path}: run reproduce.py full --from-scratch first')
  sources[str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)]=hashlib.sha256(path.read_bytes()).hexdigest();return json.loads(path.read_text())
 def js(name,data):
  path=td/name;path.write_text(json.dumps(data,indent=2,allow_nan=False)+'\n');products.append(str(path.relative_to(ROOT)))
 def table(name,rows):
  if not rows:raise ValueError(name+' is empty')
  fields=list(dict.fromkeys(k for row in rows for k in row));path=td/name
  with path.open('w',newline='') as f:
   w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows([{k:json.dumps(v) if isinstance(v,(list,dict)) else v for k,v in row.items()} for row in rows])
  products.append(str(path.relative_to(ROOT)))
 def plot(fig,name):
  fig.tight_layout()
  for ext in ['pdf','png']:
   path=fd/(name+'.'+ext);fig.savefig(path,dpi=180,bbox_inches='tight');products.append(str(path.relative_to(ROOT)))
  plt.close(fig)
 d=load(res/'precision/diagnostics_results.json');a=load(res/'precision/analysis_results.json');low=load(ROOT/'data/inputs/low_inputs.json');spectrum=load(ROOT/'data/inputs/retained_spectrum.json');ass=load(ROOT/'data/inputs/assumptions.json');receipt=load(res/'run_receipt.json')
 cases=[load(res/'refinement'/f'final_{name}_summary.json') for name in ['8_7_pad1','8_7_pad2','6_6_pad1']];n,pad,weaker=cases;cap=load(res/'refinement/alternative_domain_tail_checks.json');central=d['central'];C=central['C1'];b=central['b']
 if receipt['status']!='passed':raise RuntimeError('The computation receipt is not successful')
 if not all(.269 <= c['interval'][0] <= c['interval'][1] <= .276 for c in [n,pad]):
  raise RuntimeError('The nominal working range no longer contains the computed nominal/padding intervals')
 js('current_summary.json',dict(convention=ass['convention'],retained={k:central[k] for k in ['a','b','C1']},nominal_conditional_interval=n['interval'],doubled_nonlinear_padding_interval=pad['interval'],weaker_gap_sensitivity_interval=weaker['interval'],recommended_working_summary=dict(interval=[.269,.276],midpoint=.2725,halfwidth=.0035,midpoint_meaning='Rounded interval midpoint, NOT a best-fit CFT evaluation',status='Scenario-specific conditional envelope; not robust to input-box or gap changes'),physical_certified_interval=None,statistical_confidence_level=None,assumptions=ass,reproduction_profile=receipt['profile'],reproduction_from_scratch=receipt['from_scratch'],recorded_steps=len(receipt['steps']),warning='Retained digits are regression targets. The central input vector is infeasible under the nominal LP; the working range is scenario-specific and not robust to modest box/gap changes. See note and review/RESPONSE_TO_REVIEW.md.'))
 table('retained_spectrum.csv',spectrum);table('low_inputs.csv',[dict(parameter=k,**v,source=low['source']) for k,v in low['values'].items()]);table('family_contributions.csv',central['parts'])
 old=d['ward_updated_baseline'];t=d['Tprime'];table('central_progress.csv',[dict(stage='Original Ward-consistent selection',a=old['a'],b=old['b'],C1=old['C1']),dict(stage='Original selection plus Tprime',a=old['a']+t['contribution_a'],b=old['b']+t['contribution_b'],C1=d['baseline_plus_Tprime_C1']),dict(stage='Expanded 60-primary selection',a=central['a'],b=b,C1=C)])
 table('cutoff_convergence.csv',[dict(**row,absolute_difference_from_retained=abs(row['C1']-C)) for row in d['cutoff']]);cross=d['crossing_comparison'];table('crossing_comparison.csv',[dict(real_z=z[0],imag_z=z[1],old_relative=o,expanded_relative=e) for z,o,e in zip(cross['z'],cross['old_relative'],cross['expanded_relative'])]);table('known_input_sensitivities.csv',a['input_error_linearization']);table('numerical_stability.csv',d['numerical_stability']);table('alternative_domain_sensitivity.csv',cap)
 labels=['Nominal conditional','Doubled nonlinear allowances','Weaker gaps (6,6)'];ints=[dict(scenario=label,lower=c['interval'][0],upper=c['interval'][1],midpoint=c['midpoint'],halfwidth=c['halfwidth'],even_gap=c['even_gap'],odd_gap=c['odd_gap'],iterations=c['iterations'],status=c['status']) for label,c in zip(labels,cases)];ints.append(dict(scenario='Scenario-specific working range',lower=.269,upper=.276,midpoint=.2725,halfwidth=.0035,even_gap=8,odd_gap=7,status='Conditional; not a confidence interval'));table('conditional_intervals.csv',ints)
 table('error_budget.csv',[dict(source='Crossing-constrained retained linear input',lower=n['input_linear_shift'][0],upper=n['input_linear_shift'][1]),dict(source='Integrated nonlinear allowance',lower=-n['objective_nonlinear_allowance'],upper=n['objective_nonlinear_allowance']),dict(source='Omitted even a',lower=-n['tail_a_even']/b,upper=n['tail_a_even']/b),dict(source='Omitted odd a',lower=n['tail_a_odd'][0]/b,upper=n['tail_a_odd'][1]/b),dict(source='Omitted b in numerator combination',lower=-C*n['tail_b']/b,upper=C*n['tail_b']/b)])
 rows=[q for q in d['cutoff'] if q['cut']<24];fig,ax=plt.subplots(figsize=(7.4,4.8));ax.semilogy([q['cut'] for q in rows],[abs(q['C1']-C) for q in rows],'o-');ax.set(xlabel='Dimension cutoff on the selected primary list',ylabel=r'$|C_{1,\mathrm{cut}}-C_{1,\mathrm{retained}}|$',title='Selected-list convergence (not a physical error bound)');ax.grid(True,which='both',alpha=.3);plot(fig,'cutoff_convergence')
 fig,ax=plt.subplots(figsize=(8.7,4.8));order=[ints[0],ints[1],ints[3],ints[2]]
 for y,q in enumerate(order):
  m=(q['lower']+q['upper'])/2;ax.errorbar(m,y,xerr=[[m-q['lower']],[q['upper']-m]],fmt='o',capsize=5)
 ax.axvline(C,linestyle='--',label=f'Retained value: {C:.8f}');ax.set_yticks(range(4),[q['scenario'] for q in order]);ax.invert_yaxis();ax.set(xlabel=r'$C_1^{(3)}$, with $\delta=(s_*-s)/2$',title='Conditional envelopes, not confidence intervals');ax.legend(fontsize=8,loc='center right');ax.grid(True,axis='x',alpha=.3);plot(fig,'conditional_intervals')
 rows=sorted(a['input_error_linearization'],key=lambda q:q['quadrature'],reverse=True)[:8][::-1];fig,ax=plt.subplots(figsize=(8.7,4.9));ax.barh([f"{q['sector']}, spin {q['ell']}, dimension {q['Delta']:.5g}" for q in rows],[q['quadrature'] for q in rows]);ax.set(xlabel='Per-family RSS sensitivity to quoted input errors',title='Known-input sensitivities before joint crossing constraints');ax.ticklabel_format(axis='x',style='sci',scilimits=(0,0));ax.grid(True,axis='x',alpha=.3);plot(fig,'known_input_sensitivity')
 fig,ax=plt.subplots(figsize=(7.6,4.8));ax.errorbar([q['h'] for q in cap],[q['retained_C1'] for q in cap],yerr=[q['remainder_C1_scale'] for q in cap],fmt='o',capsize=5,label='Retained value and tail-only sensitivity');ax.axhline(C,linestyle='--',label='Main retained value');ax.set(xlabel='Alternative channel-boundary parameter h',ylabel=r'$C_1^{(3)}$',title='Domain sensitivity (known-input error not included)');ax.legend(fontsize=8);ax.grid(True,alpha=.3);plot(fig,'alternative_domain_sensitivity')
 (ROOT/'outputs/verification/assets_manifest.json').write_text(json.dumps(dict(generator='code/workflow/make_assets.py',input_sha256=sources,generated_files=products),indent=2)+'\n');print('Generated',len(products),'table/figure assets from reproduced data.')
if __name__=='__main__':main()
