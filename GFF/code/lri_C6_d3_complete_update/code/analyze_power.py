from pathlib import Path
import json,mpmath as m,sys
W=Path(__file__).resolve().parents[1];m.mp.dps=70
p=W/'records'/(sys.argv[1]if len(sys.argv)>1 else 'power_ms_d3_complete.json');data=json.load(open(p));m.mp.dps=data['dps']+5;d=m.mpf(data['dimension']);q=d/4
A=m.digamma(2*q)+m.digamma(1)-2*m.digamma(q);R=m.polygamma(1,2*q)-m.polygamma(1,1);U=m.polygamma(2,q);V=m.polygamma(2,1)+m.polygamma(2,2*q)
Q=m.mpf(__import__('os').environ.get('POWER_Q','5.01710256455385536959085484569018369956'));P4=m.mpf(__import__('os').environ.get('POWER_P4','62.05832794340667246646338858409673691827'))
M=m.gamma(-q)*m.gamma(2*q)**2/m.gamma(3*q);N=m.digamma(-q)+m.digamma(3*q)-m.digamma(1)-m.digamma(2*q)
b3=6*Q+m.mpf(87)/4*A*A-m.mpf(9)/4*R+M;c3=m.mpf(7)/2*A*A-R/2+M/3
b4=-m.mpf(393)/4*A**3-m.mpf(11)/2*A*M-54*A*Q+m.mpf(117)/4*A*R-m.mpf(3)/2*M*N-6*P4-m.mpf(165)/8*U+m.mpf(9)/4*V
c4=-m.mpf(127)/8*A**3-m.mpf(7)/6*A*M-3*A*Q+m.mpf(51)/8*A*R-M*N/2-m.mpf(57)/16*U+m.mpf(3)/8*V
parts={}
for row in data['loops']:
 L=row['L'];gs=[g for g in row['done']if g['power']];parts[L]=(sum(m.mpf(g['b'])for g in gs),sum(m.mpf(g['c'])for g in gs))
 if any(g['power'] for g in row['failed']):raise RuntimeError(('unclosed power graphs',L,row['failed']))
if 6 not in parts:raise RuntimeError('incomplete run')
def lower(b3,c3,b4,c4):return 2016*A**5-448*A**3*b3+672*A**3*c3-84*A*A*b4+168*A*A*c4+m.mpf(49)/3*A*b3*b3-42*A*b3*c3+m.mpf(7)/3*b3*b4-4*b3*c4-3*b4*c3
b3p,c3p=parts[3];b4p,c4p=parts[4];b5p,c5p=parts[5];b6p,c6p=parts[6]
hi=(3*c6p-b6p-12*A*b5p+30*A*c5p)/2187
lo=(lower(b3,c3,b4,c4)-lower(b3-b3p,c3-c3p,b4-b4p,c4-c4p))/2187
out={'dimension':str(d),'source':p.name,'auxiliary_power_sums':{str(L):{'b':str(b),'c':str(c)}for L,(b,c)in parts.items()},'higher_contribution':str(hi),'lower_difference':str(lo),'power_correction_C6':str(hi+lo),'core_finite_jet':data['core_U0'],'core_linear_jet':data['core_U1'],'max_root_discrepancy':str(max(m.mpf(g['root_error'])for row in data['loops']for g in row['done'])),'individual_sums_are_physical':False,'individual_sums_note':'Finite core coefficients were retained symbolically and assigned trial values for this audit; only the assembled correction is independent of those choices.','scope':'Complete nonzero-weight power target; two core coefficients cancel algebraically and are not evaluated separately.'}
(W/'records'/('correction_'+p.name)).write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
