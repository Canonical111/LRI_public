"""Fresh algebra, numerical-convergence, direct-kernel, and availability audit.
Raw reintegration and numerical certification are not implied by this check.
"""
from pathlib import Path
import json,subprocess,sys,time,hashlib
import sympy as s,mpmath as mp
from read_expression import load
ROOT=Path(__file__).resolve().parent;start=time.time();records=[]
for fn in ['derive_D4.py','check_Q8_toplogs_fresh.py','check_A7v_toplogs_fresh.py','check_one_pair.py']:
 st=time.time();r=subprocess.run([sys.executable,fn],cwd=ROOT,capture_output=True,text=True)
 (ROOT/(fn[:-3]+'_completion_check.log')).write_text(r.stdout+r.stderr)
 assert r.returncode==0,(fn,r.stdout[-1000:],r.stderr[-1000:])
 records.append({'check':fn,'returncode':r.returncode,'seconds':time.time()-st})
C=load(ROOT/'C7_symbolic.expr');D=load(ROOT/'D4_value_symbolic.expr');Om=load(ROOT/'Omega_symbolic.expr');Cp=load(ROOT/'C7_without_Omega_symbolic.expr');off=load(ROOT/'C7_known_additive_symbolic.expr')
assert s.expand(C-4*D-off)==0
assert s.expand(C-Cp+Om/8)==0
records.append({'check':'exact final expression assembly','C7_minus_4D4_minus_known':'0','C7_minus_partial_plus_Omega_over8':'0'})
mp.mp.dps=130
run1=json.loads((ROOT/'final_evaluation_C7_first.json').read_text());run2=json.loads((ROOT/'final_evaluation_C7_second.json').read_text())
differences={}
for name in run1['coefficients']:
 if name not in run2['coefficients']:continue
 diff=mp.mpf(run1['coefficients'][name])-mp.mpf(run2['coefficients'][name]);differences[name]=mp.nstr(diff,25)
 assert abs(diff)<mp.mpf('1e-70'),(name,diff)
records.append({'check':'two numerical runs','differences':differences,'qualification':'Agreement under settings changes; not a rigorous interval bound.'})
rawchecks=[]
for tag,dps in [('A7_v',90),('Q8_base',80),('Q4_dd',80)]:
 exact=json.loads((ROOT/f'{tag}_finite_raw_check_{dps}.json').read_text());num=json.loads((ROOT/f'{tag}_direct_gauss.json').read_text())[-1]
 diff=mp.mpf(str(num['value']))-mp.mpf(exact['value'])
 assert abs(diff)<mp.mpf('1e-10'),(tag,diff)
 rawchecks.append({'raw_moment':tag,'highest_cubature_order':num['order'],'absolute_difference':mp.nstr(abs(diff),12),'qualification':'Empirical cubature convergence, not an interval enclosure.'})
records.append({'check':'independent original-kernel finite-cutoff cubature','comparisons':rawchecks})
candidate=json.loads((ROOT/'C7_candidate_recognition.json').read_text());candidate_check={'status':candidate['status'],'analytic_proof':False}
if (ROOT/'C7_candidate.expr').exists():
 cn=load(ROOT/'C7_candidate.expr');dn=load(ROOT/'D4_candidate.expr');sub={s.Symbol(f'Z{k}'):s.zeta(k) for k in range(2,7)}
 for name,ex in [('C7',cn),('D4_value',dn)]:
  val=mp.mpf(str(s.N(ex.xreplace(sub),120)));diff=mp.mpf(run2['coefficients'][name])-val
  candidate_check[name+'_residual']=mp.nstr(diff,30)
  assert abs(diff)<mp.mpf('1e-75'),(name,diff)
records.append({'check':'candidate comparison after recognition',**candidate_check})
req=json.loads((ROOT/'C7_raw_requirements.json').read_text());needed=sorted(set(t for vals in req['all'].values() for t in vals));availability={}
for tag in needed:
 p=ROOT/(tag+'_negative.json');assert p.is_file(),p
 availability[tag]={'file':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
(ROOT/'C7_input_availability.json').write_text(json.dumps(availability,indent=2))
records.append({'check':'all raw inputs available','number_of_raw_moments':len(needed),'missing':[]})
result={'status':'completed_numerical_C7_with_internal_and_independent_integral_checks','C7':run2['coefficients']['C7'],'D4':run2['coefficients']['D4_value'],'Omega':run2['coefficients']['Omega'],'checks':records,'seconds':time.time()-start,'scope':'Matched perturbative construction; not an independent proof of the duality or all-orders renormalizability. Compact closed form, when present, remains numerically supported unless an analytic certificate is supplied.'}
(ROOT/'C7_completion_verification.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2),flush=True)
