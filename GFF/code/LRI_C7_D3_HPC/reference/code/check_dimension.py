from pathlib import Path
import json,hashlib,numpy as np,mpmath as m,time
W=Path(__file__).resolve().parents[1];m.mp.dps=65;q=m.mpf(3)/4
iv=json.load(open(W/'inputs/inventory.json'));checks=[];hs=json.load(open(W/'reference/d2_graph_structure_hashes.json'))
for sector,loops in iv.items():
 for L,rows in loops.items():
  for g in rows:
   key=f'{sector}/L{L}/G{g["id"]}.txt';lines=(W/'inputs'/key).read_text().splitlines();T=int(lines[0].split()[-1])
   text=' '.join(lines[0].split()[1:])+'\n'+'\n'.join(lines[1:T+2])+'\n'
   assert hashlib.sha256(text.encode()).hexdigest()==hs[key]
   checks.append(dict(sector=sector,L=int(L),id=g['id'],unchanged_polynomials_and_weights=True))
old=json.load(open(W/'reference/d3_C6_two_loop.json'))['B2_decimal'];new=json.load(open(W/'inputs/two_loop.json'))['B2'];err=max(abs(m.mpf(x)-m.mpf(y))for x,y in zip(old,new));assert err<m.mpf('1e-46')
js=json.load(open(W/'verification/gamma_jets.json'))['rows'];gammaerrors=[]
for row in js:
 L=row['L'];r=m.mpf('.041');n=64
 def logG(z):return L*(m.loggamma(2*q+z/2)-m.loggamma(1+z/2)-m.loggamma(2*q))+m.loggamma(1+L*z/2)-2*L*(m.loggamma(q+z/4)-m.loggamma(q))
 vals=[logG(r*m.exp(2j*m.pi*k/n))for k in range(n)]
 for j in range(1,6):
  value=m.fsum(vals[k]*m.exp(-2j*m.pi*k*j/n)for k in range(n))/(n*r**j);diff=abs(value-m.mpf(row['log_jets'][j]));assert diff<m.mpf('1e-46');gammaerrors.append(str(diff))
M=m.gamma(-q)*m.gamma(2*q)**2/m.gamma(3*q);assert abs(M+16*m.pi/15)<m.mpf('1e-60')
(W/'verification/dimension_checks.json').write_text(json.dumps(dict(status='passed',graph_structure_checks=len(checks),graphs=checks,two_loop_overlap_max_difference=str(err),gamma_cauchy_checks=len(gammaerrors),gamma_cauchy_max_difference=str(max(map(m.mpf,gammaerrors))),power_three_loop_b3_exact='-16*pi/15',power_three_loop_b3_value=str(M)),indent=2));print(len(checks),'graphs; gamma checks',len(gammaerrors),'max',max(map(m.mpf,gammaerrors)))
