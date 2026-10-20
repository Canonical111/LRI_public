import json
N=None
BASES={'A':(0,1,0),'B':(0,1,0,3),'C':(0,1,0,2),'D':(0,1,0,1),'E':(0,2,0),'F':(0,1,1),'G':(0,N,0),
       'H':(0,1,0,N,0),'I':(0,2,0,3),'K':(0,1,1,2),'L':(0,0,0),'M':(0,1,0,2,1),'Nb':(0,2,1,3),'O':(0,2,1),'P':(0,1,0,3,1)}
TESTS={'T1':(0,0,0,1),'T2':(0,1,0,0),'T3':(0,0,0,0),'T4':(0,1,0,1),'T5':(0,1,0,1,0),'T6':(0,0,0,1,0),'T7':(0,1,0,0,0),'T8':(0,0,0,0,0),'T9':(0,1,0,1,0,1)}
T=[]; seen=set()
def caps(n,off):
    return [(-1 if d is None else n-2-d) for d in off]
def add(n,bname,off,lo,hi,icpt,top,dps=60):
    kc=caps(n,off)
    while kc and kc[-1]<0: kc.pop()
    key=(n,tuple(kc),lo,hi,icpt,top,dps)
    if key in seen: return
    seen.add(key)
    t=dict(n=n,base=bname,kcaps=kc,J=len(kc),ksub=-9,lo=lo,hi=hi,icpt=icpt,top=top,dps=dps)
    t['id']='%s_n%d_%s_%s_lo%d_hi%d_d%d'%(bname,n,icpt,top,lo,hi,dps)
    if top=='fixed': t['top_cands']={}
    T.append(t)
LOS=(20,30,40,50,60,70,80,100,120,150,200)
for b,off in BASES.items():
    for lo in LOS:
        for top in ('fixed','free'):
            for hi in (400,500): add(5,b,off,lo,hi,'free',top)
            for hi in (500,2000): add(4,b,off,lo,hi,'free',top)
        add(3,b,off,lo,500,'free','fixed')
for b,off in TESTS.items():
    for lo in (20,40,60,100,150,200,300):
        add(4,b,off,lo,2000,'fixed','free')
        add(4,b,off,lo,500,'fixed','free')
# precision duplicates
for t in list(T):
    if t['n']==5 and t['base'] in ('A','D','M') and t['lo'] in (40,80) and t['hi']==500:
        add(5,t['base'],BASES[t['base']],t['lo'],500,'free',t['top'],dps=120)
open('tasks3.jsonl','w').write(''.join(json.dumps(t)+'\n' for t in T))
print(len(T))
