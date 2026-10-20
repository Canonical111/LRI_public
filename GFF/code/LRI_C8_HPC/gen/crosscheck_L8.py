"""Consistency checks of the L<=8 inventory produced by the gen/ programs.
1. forest_polynomials.json / .zero.json (Lmax=8): the L<=7 part is byte-identical to the reference.
2. articulation.json (networkx) agrees with the C++ articulation test of forest_audit (subset JSON)
   and its L<=7 part equals the reference articulation.json.
3. Power/primitive flags in L{L}_coord.txt agree with the subset JSON and summaries; the subset
   free_articulation_nonzero = {power-free} & {articulation} & not {exact zero} recomputed from files.
4. Prints the per-L table used in the report.
Usage: python crosscheck_L8.py <out8 dir> <reference/inputs> <reference/verification> [Lmax=8]"""
import json,sys
from pathlib import Path
O,RI,RV=map(Path,sys.argv[1:4]);Lmax=int(sys.argv[4]) if len(sys.argv)>4 else 8;bad=0
def check(ok,msg):
 global bad;bad+=not ok;print(('OK   ' if ok else 'FAIL ')+msg)
for f in ['forest_polynomials.json','forest_polynomials.json.zero.json']:
 a=(O/f).read_text();b=(RV/f).read_text()
 check(a.startswith(b[:-1]+',"8":') and a.endswith('}'),f'{f}: L<=7 part byte-identical to reference')
art=json.load(open(O/'articulation.json'));ref_art=json.load(open(RI/'articulation.json'))
check(all(art[L]==ref_art[L] for L in ref_art),'articulation.json L<=7 equals reference')
sub=json.load(open(O/'forest_subsets.json'));zero=json.load(open(O/'forest_polynomials.json.zero.json'))
def coordflags(L):
 rows=[]
 with open(O/f'L{L}_coord.txt') as f:
  _,ng=map(int,f.readline().split())
  for i in range(ng):
   h=f.readline().split();assert int(h[0])==i;rows.append((int(h[3]),int(h[4]),int(h[5])))
   for _ in range(int(h[5])):f.readline()
 return rows
print(f"{'L':>2} {'classes':>7} {'power':>6} {'prim':>5} {'free_prim':>9} {'artic':>6} {'free_art':>8} {'zeros':>6} {'S=free&art&nonzero':>18} {'S beta_mon':>10} {'S gamma_mon':>11}")
for L in range(1,Lmax+1):
 s=sub[str(L)];S=s['subsets'];fl=coordflags(L);summ=json.load(open(O/f'L{L}_summary.json'))
 power={i for i,r in enumerate(fl) if r[0]};prim={i for i,r in enumerate(fl) if r[0]==0 and r[1]==1}
 # coord 'primitive' column is subs.empty(); a primitive class in the summary sense also has no power subgraph
 a=set(art.get(str(L),[]));z=set(zero[str(L)])
 check(s['power_classes']==len(power)==summ['power_classes'],f'L{L} power classes C++ subset vs coord vs summary ({len(power)})')
 check(s['primitive_classes']==len(prim)==summ['primitive_classes'],f'L{L} primitive classes ({len(prim)})')
 if L>=2:check(s['articulation_classes']==len(a) and set(S['articulation']['ids'])==a,f'L{L} articulation C++ == networkx ({len(a)})')
 freeart={i for i in a if i not in power}
 check(set(S['free_articulation']['ids'])==freeart,f'L{L} free_articulation ids recomputed from files')
 check(set(S['free_articulation_nonzero']['ids'])==freeart-z,f'L{L} free_articulation_nonzero ids recomputed from files')
 check(set(S['free_primitive']['ids'])==prim,f'L{L} free_primitive ids')
 check(s['classes']==summ['classes']==len(fl),f'L{L} class count')
 X=S['free_articulation_nonzero']
 print(f"{L:>2} {s['classes']:>7} {len(power):>6} {len(prim):>5} {S['free_primitive']['size']:>9} {len(a):>6} {len(freeart):>8} {len(z):>6} {X['size']:>18} {X['beta_monomials']:>10} {X['gamma_monomials']:>11}")
print('CROSSCHECK','PASS' if not bad else f'FAIL ({bad})')
sys.exit(1 if bad else 0)
