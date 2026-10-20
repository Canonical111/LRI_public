from pathlib import Path
from fractions import Fraction as Q
from math import gcd,isqrt
import sys
files=[Path(p) for p in sys.argv[2:]];out=Path(sys.argv[1]);M=1;values={}
for file in files:
 lines=file.read_text().splitlines();p=int(lines[0]);data={tuple(s.split()[1:]):int(s.split()[0]) for s in lines[1:]};inv=pow(M,-1,p)
 for label in set(values)|set(data):
  v=values.get(label,0);values[label]=v+M*((data.get(label,0)-v)*inv%p)
 M*=p
bound=isqrt(M//2)
def rr(x):
 a,b=M,x;c,d=0,1
 while abs(b)>bound:
  q=a//b;a,b=b,a-q*b;c,d=d,c-q*d
 if d and abs(d)<=bound and gcd(b,d)==1:return Q(b,d)
 raise ValueError('rational reconstruction failed')
try:
 r={l:rr(v) for l,v in values.items()}
except ValueError:
 print('INSUFFICIENT MODULUS',M.bit_length());sys.exit(1)
out.write_text(''.join(str(c)+' 0 '+' '.join(l)+'\n' for l,c in sorted(r.items()) if c))
print('RECONSTRUCTED',len(r),'bits',M.bit_length(),'max_num_bits',max(abs(c.numerator).bit_length() for c in r.values()),'max_den_bits',max(c.denominator.bit_length() for c in r.values()))
