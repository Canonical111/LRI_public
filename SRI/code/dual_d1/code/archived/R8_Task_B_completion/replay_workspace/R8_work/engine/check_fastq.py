from pathlib import Path
import time,json,random
st=time.time()
import install_fastq
Q=install_fastq.install_domain()
import scaled_b as sb
install_fastq.install_endpoint()
import factored_field as ff
from fractions import Fraction
from sympy.polys.domains import QQ
from sympy import Rational
random.seed(785563);K=sb.K
for i in range(200):
 a=Q(random.randrange(-2000,2000),random.randrange(1,1000));b=Q(random.randrange(1,2000),random.randrange(1,1000))
 assert QQ.to_sympy(a)==Rational(str(a));assert QQ.exquo(a,b)==a/b;assert QQ.convert(a)==a
 x=K(str(a)); y=K(str(b));assert x+y==K(str(a+b))
 r=(sb.GEN[3]-2*sb.GEN[4]+1);s=(sb.GEN[3]+sb.GEN[4]+2)
 expr=(x*r*s+x*s)/(r*s)
 assert expr==x+x/r
# Complete saved n=6 terminal block and one n=8 terminal sub-batch.
checks=[]
for name in ['n6_f1_b00']:
 folder=sb.OUT/name;n=int(name.split('_')[0][1:]);N=n-2
 items=sb.tb.br.rr.load(folder/f'stage{N-2}.jsonl');actual,count,neg=sb.last_two_scaled(items,n)
 ref=json.loads((folder/'result.json').read_text())
 assert str(actual)==ref['value'],(actual,ref)
 assert list(map(str,neg))==ref['dimensionless_negative_inverse_euler']
 checks.append({'block':name,'value':str(actual),'negative':list(map(str,neg)),'all_equal':True})
report={'status':'exact_fast_scalar_domain_regression_pass','random_domain_cases':200,'complete_terminal_comparisons':checks,'seconds':time.time()-st}
Path(sb.ROOT/'fastq_domain_checks.json').write_text(json.dumps(report,indent=2));print('PASS',report,flush=True)
