"""Fill the note from the audited numerical record; no integrations run."""
from pathlib import Path
import json,re
W=Path(__file__).resolve().parents[1]
r=json.load(open(W/'verification/C7_full_result.json'))
def f(x,n=6):
 if x!=0 and (abs(x)<.001 or abs(x)>1e7):
  a,b=f'{x:.{n}e}'.split('e');return a+r'\times10^{'+str(int(b))+'}'
 return f'{x:.{n}f}'
v={'FULL':f(r['C7_full']), 'SE':f(r['sampling_se']), 'ROUNDED':'-3950', 'ALLOW':str(int(r['empirical_allowance'])), 'PF':f(r['power_free_C7']), 'PFSE':f(r['power_free_se']), 'DELTA':f(r['power_correction']), 'DSE':f(r['power_correction_se']), 'BOOT':f(r['bootstrap']['full_se'][7]), 'HALF0':f(r['half_streams'][0]['full'][7]), 'HALF1':f(r['half_streams'][1]['full'][7])}
for i,c in enumerate(r['campaigns']):
 a='AB'[i];v['D'+a]=f(c['power_correction'][7]);v['S'+a]=f(c['independent_power_sampling_errors'][7])
for j in (4,5,6):v['D'+str(j)]=f(r['power_differences'][j]);v['S'+str(j)]=f(r['power_difference_errors'][j])
v['LOWERROWS']='\n'.join(f"{c['order']}&${f(c['estimate'])}$&${f(c['sampling_se'])}$&${f(c['reference'])}$\\\\"for c in r['lower_order_checks'])
s=(W/'notes/C7_d2_complete_template.tex').read_text()
for k,z in v.items():s=s.replace('@@'+k+'@@',z)
assert not re.findall(r'@@\w+@@',s)
(W/'notes/C7_d2_complete.tex').write_text(s)
