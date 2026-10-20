import json
T=[]; ids=set()
def kc(n,base,J):
    out=[]
    for j in range(1,J+1):
        if j%2==1: out.append(n-2)
        elif base=='oe1' or j==2: out.append(n-3)
        else: out.append(n-4)
    return out
def add(**kw):
    kw.setdefault('dps',60)
    kw['kcaps']=kc(kw['n'],kw['base'],kw['J'])
    kw['ksub']=-9
    kw['id']='{base}_n{n}_{icpt}_{top}_lo{lo}_hi{hi}_J{J}_d{dps}'.format(**kw)
    key=(kw['n'],kw['icpt'],kw['top'],kw['lo'],kw['hi'],tuple(kw['kcaps']),kw['dps'])
    if key in ids: return
    ids.add(key)
    if kw['top']=='fixed': kw['top_cands']={}
    T.append(kw)
for n in (2,3,4):
    for base in ('oe1','oe2'):
        for J in range(3,8):
            for hi in (2000,500):
                for lo in (20,40,60,100,150,200,300):
                    add(n=n,base=base,J=J,hi=hi,lo=lo,icpt='fixed',top='free')
for n in (3,4,5):
    for top in ('fixed','free'):
        for base in ('oe1','oe2'):
            for J in range(3,8):
                for hi in ((500,2000) if n<5 else (400,500)):
                    for lo in (20,40,60,80,100,120,150,200):
                        add(n=n,base=base,J=J,hi=hi,lo=lo,icpt='free',top=top)
extra=[]
for t in T:
    if t['n']==5 and t['J'] in (5,6) and t['lo'] in (40,80) and t['hi']==500:
        u={k:v for k,v in t.items() if k not in ('id','kcaps','ksub','top_cands')}; u['dps']=120; extra.append(u)
    if t['n']==4 and t['J']==6 and t['lo']==60 and t['icpt']=='fixed':
        u={k:v for k,v in t.items() if k not in ('id','kcaps','ksub','top_cands')}; u['dps']=120; extra.append(u)
for u in extra: add(**u)
open('tasks2.jsonl','w').write(''.join(json.dumps(t)+'\n' for t in T))
print(len(T), len(extra))
