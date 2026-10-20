import argparse,json,math,struct,time
from pathlib import Path
from fractions import Fraction as Q
from c6_relations import relations
p=argparse.ArgumentParser();p.add_argument('weight',type=int);p.add_argument('--max-letter',type=int,default=10);p.add_argument('--no-zeros',action='store_true');args=p.parse_args()
n=args.weight;M=args.max_letter;root=Path(__file__).resolve().parent;start=time.time()
label=f'w{n}_M{M}'+('_positive' if args.no_zeros else '')
def code(w):
    out=0
    for a in w:out=out*(M+1)+a
    return out

def ints(row):
    den=math.lcm(*(c.denominator for c in row.values()))
    return den,{w:int(c*den) for w,c in row.items()}
v={tuple(w):Q(c) for w,c in json.loads((root/'C6_linear_words.json').read_text()) if len(w)==n}
assert max(max(w) for w in v)<=M
scale,tar=ints(v)
(root/(label+'.target.json')).write_text(json.dumps({'weight':n,'base':M+1,'scale':scale,'target':[[list(w),str(c)] for w,c in sorted(v.items())]},indent=2))
with (root/(label+'.target.txt')).open('w') as f:
    f.write(f'{(M+1)**n} {len(tar)}\n')
    for w,c in tar.items():f.write(f'{code(w)} {c}\n')
with (root/(label+'.rows.bin')).open('wb') as out,(root/(label+'.labels.jsonl')).open('w') as labels:
    count=0;nonzero=0
    for desc,row in relations(n,M,not args.no_zeros):
        den,raw=ints(row);labels.write(json.dumps({'scale':den,'relation':desc},separators=(',',':'))+'\n')
        out.write(struct.pack('<I',len(raw)))
        for w,c in raw.items():out.write(struct.pack('<Iq',code(w),c))
        count+=1;nonzero+=len(raw)
        if count%10000==0:print('GEN',n,count,'nonzeros',nonzero,'sec',time.time()-start,flush=True)
print('GENERATED',label,'rows',count,'nonzero',nonzero,'seconds',time.time()-start,flush=True)
(root/(label+'.generation.json')).write_text(json.dumps({'rows':count,'nonzero':nonzero,'seconds':time.time()-start},indent=2))
