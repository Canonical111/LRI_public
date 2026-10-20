"""Exact extraction of hard-cutoff coefficients from finite-cutoff hyperlogs.
Z(word) means the constant at infinity, not a numerical guess.
"""
import sympy as s
from read_expression import parse
from functools import lru_cache
from pathlib import Path
import json,math
E,L,ell=s.symbols('e L ell');Z2,Z3,Z4=s.symbols('Z2 Z3 Z4')
ZWORDS={}
def Z(word):
 word=tuple(word)
 if not word:return s.S(1)
 if len(set(word))==1 and word[0]<0:return (-s.log(-word[0]))**len(word)/s.factorial(len(word))
 if all(a==0 for a in word):return s.S(0)
 if word[-1]==0:
  from hyperlog_core import shuffle
  sh=shuffle((0,),word[:-1]).copy();mu=sh.pop(word)
  return -sum(co*Z(ww) for ww,co in sh.items())/mu
 if len(word)==2:
  a,b=word
  if a<0 and b<0:
   a=-a;b=-b
   return s.log(a)*s.log(b)-s.log(a)**2/2-s.polylog(2,1-s.Rational(b,a))
 if word[-1]<0 and all(a==0 for a in word[:-1]):
  m=len(word);ln=-s.log(-word[-1]);zz={2:Z2,4:Z4}
  return ln**m/s.factorial(m)+sum(2*(1-s.Rational(1,2)**(2*k-1))*zz.get(2*k,s.zeta(2*k))*ln**(m-2*k)/s.factorial(m-2*k) for k in range(1,m//2+1))
 name='R_'+'_'.join('m'+str(-a) if a<0 else str(a) for a in word)
 sym=s.Symbol(name);ZWORDS[sym]=word;return sym

@lru_cache(maxsize=None)
def big(word,n):
 if not word:return s.S(1) if n==0 else s.S(0)
 if n==0:return s.expand(sum(Z(word[k:])*L**k/s.factorial(k) for k in range(len(word)+1)))
 rhs=s.expand(sum(word[0]**k*big(word[1:],n-k) for k in range(n+1)))
 return s.expand(-sum(s.diff(rhs,L,j)/s.Integer(n)**(j+1) for j in range(s.degree(rhs,L)+1))) if rhs else s.S(0)

@lru_cache(maxsize=None)
def rseries(expr,pmax):
 ex=parse(expr)
 ser=s.series(ex,E,0,max(0,pmax+1)).removeO().expand()
 out={}
 for term in s.Add.make_args(ser):
  p=term.as_powers_dict().get(E,0);
  if p<=pmax:out[int(p)]=out.get(int(p),s.S(0))+term/E**p
 return out

@lru_cache(maxsize=None)
def shiftcoef(N,j,k,d):
 if j>d or k>d-j:return s.S(0)
 # [e^d] (e/(1-N e))^j log(1-N e)^k/k!
 h=sum(-s.Rational(N**r,r)*E**r for r in range(1,d+1))
 he=s.Poly(s.expand(h**k/s.factorial(k)),E)
 out=0
 for (p,),c in he.terms():
  r=d-j-p
  if r<0:continue
  q=s.binomial(j+r-1,r)*N**r if j else (1 if r==0 else 0)
  out+=c*q
 return out

def extract_rows(rows,N,p=0,logpower=None):
 contributions=[];terms={}
 def flush():
  for mon in s.Add.make_args(s.expand(s.Add(*contributions))):
   co,base=mon.as_coeff_Mul(rational=True)
   terms[base]=terms.get(base,s.S.Zero)+co
  contributions.clear()
 for row in rows:
  if len(row)==2:word,expr=row;scalars=[]
  else:word,scalars,expr=row
  word=tuple(word);rs=rseries(expr,p)
  scalar=s.prod(ell+s.log(k) for k in scalars)
  term=s.S(0)
  for pp,cc in rs.items():
   d=p-pp
   if d<0:continue
   for j in range(d+1):
    bj=big(word,j)
    if not bj:continue
    for k in range(min(s.degree(bj,L),d-j)+1):
     c=shiftcoef(N,j,k,d)
     if c:term+=cc*c*s.diff(bj,L,k).subs(L,-ell)
  contributions.append(scalar*term)
  if len(contributions)>=64:flush()
 if contributions:flush()
 out=s.Add(*(co*base for base,co in terms.items() if co))
 return out.coeff(ell,logpower) if logpower is not None else out

def moment(name,n,p=0,m=0):
 rows=json.loads((Path(__file__).resolve().parent / f'{name}{n}_negative.json').read_text())
 return extract_rows(rows,n-1,p,m)

def Q61():
 rows=json.loads((Path(__file__).resolve().parent / 'six_negative.json').read_text())
 h=extract_rows(rows,5,0,None)
 return s.expand(-sum(s.factorial(j)*h.coeff(ell,j) for j in range(s.degree(h,ell)+1)))

