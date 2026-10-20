"""Independent high-precision incomplete-beta evaluation of the three-vertex
residues, including the finite-delta insertion. This is optional: the stored
outputs are included in data/.
"""
from pathlib import Path
B=Path(__file__).resolve().parent/'data'
B.mkdir(exist_ok=True)
import mpmath as mp,json
mp.mp.dps=70
# a here = Mellin variable; p1,p2 = internal opposite-pair powers, Q=same-pair power
# All times measured in an interval of length 1, consecutive kink gaps >= cutoff.
def M(a,p1=1,p2=1,Q=1):
 k=2-2*p1-2*p2+2*Q
 I=mp.betainc(a+1-2*p1,1-2*p2,0,mp.mpf('.5'))+mp.betainc(a+1-2*p2,1-2*p1,0,mp.mpf('.5'))
 return I/(a*(a+k)*(a+k+1))
def Mv(a):return mp.diff(lambda z:M(a,1+z,1+z,1+z),0)
def Md(a):
 return (mp.diff(lambda t:M(a,1,1,t),1,2)-2*mp.diff(lambda t:M(a,t,1,1),1,2))/4
N=48; radius=mp.mpf('.17')
for name,F in [('base',M),('vderivative',Mv),('deltaderivative',Md)]:
 vals=[]
 for j in range(N):
  a=radius*mp.exp(2j*mp.pi*j/N); vals.append((a,F(a)))
 out={}
 for n in range(-6,2):
  coef=sum(v/a**n for a,v in vals)/N
  out[str(n)]=str(coef.real)
 print(name,out,flush=True)
 with open(B/('mellin3_'+name+'.json'),'w') as f:json.dump(out,f,indent=2)

base=json.loads((B/'mellin3_base.json').read_text())
charge=json.loads((B/'mellin3_vderivative.json').read_text())
delta=json.loads((B/'mellin3_deltaderivative.json').read_text())
p=8-2*mp.zeta(2)-7*mp.zeta(3)-8*mp.log(2)
checks=[
 ('base single pole',mp.mpf(base['-1']),2-2*mp.zeta(2)),
 ('charge double pole',mp.mpf(charge['-2']),-4+4*mp.zeta(2)),
 ('charge finite response',mp.mpf(charge['-1'])-2,18-14*mp.zeta(2)-15*mp.zeta(3)-8*mp.log(2)),
 ('finite-delta double pole',mp.mpf(delta['-2']),4-p),
]
for label,numerical,analytic in checks:
 error=abs(numerical-analytic)
 print(label,'absolute difference',mp.nstr(error,8))
 assert error<mp.mpf('1e-26')
print('Three-vertex residue checks passed.')
