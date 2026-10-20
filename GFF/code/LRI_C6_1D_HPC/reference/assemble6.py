"""Exact-layout, high-precision minimal subtraction through six loops."""
import sys,json
from pathlib import Path
import mpmath as mp
mp.mp.dps=70
R=Path(__file__).resolve().parent
sys.path.insert(0,str(R/'lri_numerical_resolution/verification'))
from laurent_assembly import la_add,la_mul,gc,scalar_mul,serial

def coefficients(beta,gamma):
 L=len(beta);inv=[1/beta[0]]
 for n in range(1,L):inv.append(-mp.fsum(beta[j]*inv[n-j]for j in range(1,n+1))/beta[0])
 cs=[mp.mpf('.5')]
 for n in range(1,L+1):
  pw=[mp.mpf(1)]
  for _ in range(n):pw=scalar_mul(pw,inv,n-1)
  v=mp.fsum((i+1)*gamma[i]*pw[n-1-i]for i in range(n))/n
  if n==1:v-=mp.mpf('.5')
  cs.append(v)
 return cs

def assemble(data,Lmax=6):
 A={1:{-1:mp.mpf(3)}};B={1:{-1:mp.mpf(1)}}
 for L,pair in data.items():
  L=int(L);A[L]={int(k):mp.mpf(str(v))for k,v in pair[0].items()};B[L]={int(k):mp.mpf(str(v))for k,v in pair[1].items()}
 G=[{}, {0:mp.mpf(1)}]+[{}for _ in range(Lmax)]
 for n in range(2,Lmax+2):
  pw=G[:];v={}
  for L in range(1,n):
   pw=gc(pw,G,n);v=la_add(v,la_mul(A[L],pw[n]),(-1)**L)
  G[n]={k:-x for k,x in v.items()if k<0}
 H=[{0:mp.mpf(1)}]+[{}for _ in range(Lmax)]
 pw=[{0:mp.mpf(1)}]+[{}for _ in range(Lmax)]
 for L in range(1,Lmax+1):
  pw=gc(pw,G,Lmax)
  for i in range(Lmax+1):H[i]=la_add(H[i],la_mul(B[L],pw[i]),(-1)**L)
 Z=[{0:mp.mpf(1)}]
 for n in range(1,Lmax+1):
  v={}
  for i in range(n):v=la_add(v,la_mul(H[n-i],Z[i]))
  Z.append({k:-x for k,x in v.items()if k<0})
 beta=[L*G[L+1].get(-1,mp.mpf(0))for L in range(1,Lmax+1)];gamma=[L*Z[L].get(-1,mp.mpf(0))for L in range(1,Lmax+1)]
 return dict(beta=beta,gamma=gamma,C=coefficients(beta,gamma),G=G,Z=Z)

def inputs(cut,N=28):
 data=json.load(open(R/f'lower6_{cut}_{N}.json'))
 p=json.load(open(R/f'lri_numerical_resolution/verification/records/amplitude5_{cut}_18.json'),parse_float=str,parse_int=str)
 data['5']=[p['A'],p['B']];data['5'][0]['0']='0';data['5'][1]['0']='0';data['6']=[{},{}]
 return data

def baseline(cut,N=28):
 d=inputs(cut,N);ans=assemble(d);out={k:v for k,v in ans.items()if k in ('C','beta','gamma')}
 x=ans['C'][-1]
 d['6'][1]['-1']=str(mp.mpf(1)/3);deltaH=assemble(d)['C'][-1]-x;d['6'][1]={}
 d['5'][0]['0']=str(-mp.mpf(1)/3);deltaJ=assemble(d)['C'][-1]-x
 assert abs(deltaH+mp.mpf(2)/729)<mp.mpf('1e-60'),deltaH
 assert abs(deltaJ-mp.mpf(4)/243)<mp.mpf('1e-60'),deltaJ
 out.update(C6_lower=x,sensitivity_H6=deltaH,sensitivity_J5=deltaJ,definition_J5='[eps^0](8 B5 - 3 A5)',definition_H6='[eps^-1](3 B6 - A6)')
 return out
if __name__=='__main__':
 out={}
 for n in [16,22,28]:
  for cut in ['maxgap','span']:
   if not (R/f'lower6_{cut}_{n}.json').exists():continue
   out[f'{cut}_{n}']=baseline(cut,n)
 (R/'assembly_lower6.json').write_text(json.dumps(serial(out),indent=2))
 for k,v in out.items():print(k,'C5=',mp.nstr(v['C'][5],30),'C6lower=',mp.nstr(v['C6_lower'],30))
