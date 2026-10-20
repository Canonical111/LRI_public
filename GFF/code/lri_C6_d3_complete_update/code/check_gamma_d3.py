"""Check logarithmic Gamma jets by independent Cauchy sampling of their product."""
from pathlib import Path
import json,mpmath as m
W=Path(__file__).resolve().parents[1];m.mp.dps=65;q=m.mpf(3)/4
rows=json.load(open(W/'records/gamma_jets.json'));checks=[]
for row in rows:
 L=row['L'];rad=m.mpf('.037');n=64
 def logG(z):
  # A continuous local log defined by loggamma, rather than numerical phases.
  return L*(m.loggamma(2*q+z/2)-m.loggamma(1+z/2)-m.loggamma(2*q))+m.loggamma(1+L*z/2)-2*L*(m.loggamma(q+z/4)-m.loggamma(q))
 values=[logG(rad*m.exp(2j*m.pi*k/n))for k in range(n)]
 for j in range(1,5):
  v=m.fsum(values[k]*m.exp(-2j*m.pi*k*j/n)for k in range(n))/(n*rad**j)
  e=v-m.mpf(row['log_jets'][j]);assert abs(e)<m.mpf('1e-57'),(L,j,e)
  checks.append({'L':L,'order':j,'error':str(e),'absolute_error':str(abs(e))})
 nn=2*(-1)**(L+1)*m.gamma(2*q)**L/m.gamma(q)**(2*L)
 assert abs(nn-m.mpf(row['norm']))<m.mpf('1e-57')
 checks.append({'L':L,'order':'normalization','error':str(nn-m.mpf(row['norm'])),'absolute_error':str(abs(nn-m.mpf(row['norm'])))})
(W/'records/gamma_checks.json').write_text(json.dumps({'working_dps':65,'nodes':64,'radius':str(rad),'checks':checks,'max_error':str(max(m.mpf(x['absolute_error']) for x in checks))},indent=2))
print('Gamma checks:',len(checks),'passed')
