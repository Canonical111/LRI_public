"""Byte-for-byte regression of the regenerated L<=Lmax inventory against reference/inputs and
reference/verification. Summary JSONs are compared on every field except "seconds", and their
text before ',"seconds":' must match byte-for-byte. Exit status 1 on any mismatch.
Usage: python compare_regression.py <regenerated dir> <reference/inputs> <reference/verification> [Lmax=7]"""
import json,sys,filecmp
from pathlib import Path
new,ref,ver=map(Path,sys.argv[1:4]);Lmax=int(sys.argv[4]) if len(sys.argv)>4 else 7;bad=0;rows=[]
def same(a,b):return a.exists() and b.exists() and a.read_bytes()==b.read_bytes()
files=[f'classes{L}.txt' for L in range(1,Lmax+1)]+[f'L{L}_{s}' for L in range(1,Lmax+1) for s in ('inventory.txt','coord.txt','coord.txt.idx')]+[f'exact_zero_L{L}.txt' for L in range(5,Lmax+1)]
for f in files:
 ok=same(new/f,ref/f);bad+=not ok;rows.append((f,'IDENTICAL' if ok else 'DIFFERENT'))
for L in range(1,Lmax+1):
 a=(new/f'L{L}_summary.json').read_text();b=(ref/f'L{L}_summary.json').read_text()
 ja,jb=json.loads(a),json.loads(b);ja.pop('seconds');jb.pop('seconds')
 ok=ja==jb and a.split(',"seconds":')[0]==b.split(',"seconds":')[0];bad+=not ok;rows.append((f'L{L}_summary.json','IDENTICAL except seconds' if ok else 'DIFFERENT'))
for f,g in [('forest_polynomials.json','forest_polynomials.json'),('forest_polynomials.json.zero.json','forest_polynomials.json.zero.json')]:
 ok=same(new/f,ver/g);bad+=not ok;rows.append((f,'IDENTICAL' if ok else 'DIFFERENT'))
ra=ref/'articulation.json'
if (new/'articulation.json').exists():
 ok=same(new/'articulation.json',ra);bad+=not ok;rows.append(('articulation.json (L2..7)','IDENTICAL' if ok else 'DIFFERENT'))
for f,s in rows:print(f'{f:40s} {s}')
print('REGRESSION','PASS' if not bad else f'FAIL ({bad} mismatches)')
sys.exit(1 if bad else 0)
