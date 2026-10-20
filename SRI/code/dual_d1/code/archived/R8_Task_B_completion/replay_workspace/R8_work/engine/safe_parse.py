"""Non-recursive parser for archived expanded rational-function numerators.
The denominator grammar is still checked by the original restricted parser.
"""
import re
from factored_field import Frac
from sympy.polys.domains import QQ

def install(K):
 old=K.from_expr
 ix={n:i for i,n in enumerate(K.names)}
 def poly(s):
  s=s.strip()
  if s.startswith('(') and s.endswith(')'):s=s[1:-1]
  s=s.replace('**','^').replace(' ','')
  if '(' in s or ')' in s:raise ValueError('nonexpanded numerator')
  out={}
  for term in re.findall(r'[+-]?[^+-]+',s):
   c=QQ.one;m=[0]*K.ngens
   for factor in term.split('*'):
    sign=1
    if factor.startswith('-'):sign=-1;factor=factor[1:]
    elif factor.startswith('+'):factor=factor[1:]
    c*=sign
    if not factor:continue
    if factor[0].isalpha():
     name,*powers=factor.split('^');m[ix[name]]+=int(powers[0]) if powers else 1
    else:
     nums=factor.split('/');c*=QQ(int(nums[0]),int(nums[1]) if len(nums)>1 else 1)
   mm=tuple(m);out[mm]=out.get(mm,QQ.zero)+c
  return K.ring.from_dict({m:c for m,c in out.items() if c})
 def parse(s):
  s=str(s)
  if len(s)<15000:return old(s)
  if not s.startswith('('):return K(poly(s))
  d=0;end=None
  for j,c in enumerate(s):
   if c=='(':d+=1
   elif c==')':
    d-=1
    if d==0:end=j;break
  if end is None:raise ValueError('unbalanced rational expression')
  num=poly(s[1:end]);rest=s[end+1:]
  if not rest:return K(num)
  if not rest.startswith('/'):raise ValueError('unexpected rational suffix')
  inv=old('1/'+rest[1:])
  # The serialized fraction is already in the archive's normalized form.
  n=num.mul_ground(inv.numer.get((0,)*K.ngens,QQ.zero))
  assert inv.numer.is_ground
  return Frac(K,n,dict(inv.denf))
 K.from_expr=parse
 return old,parse
