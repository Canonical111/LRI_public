import json
T=[]
def add(**kw):
    kw.setdefault('dps',60)
    kw['id']=kw.get('tag','b')+'_n{n}_{icpt}_{top}_lo{lo}_hi{hi}_J{J}_d{dps}'.format(**kw)
    T.append(kw)
# Part 1: fixed intercept, free top coefficient
for n,ks,Js in [(2,(0,1),range(2,8)),(3,(1,2),range(2,7)),(4,(2,3),range(2,7))]:
    for ksub in ks:
        for J in Js:
            for lo in (20,40,60,100,150,200,300,500):
                add(n=n,icpt='fixed',top='free',lo=lo,hi=2000,J=J,ksub=ksub)
            if n>2 and J<=5:
                for lo in (20,40,60,80,100,150):
                    add(n=n,icpt='fixed',top='free',lo=lo,hi=500,J=J,ksub=ksub)
# Calibration: free intercept on known orders, top fixed (deferred) or free
for n in (3,4):
    for top in ('fixed','free'):
        for hi in (500,2000):
            for J in range(2,6):
                for ksub in (n-2,n-1):
                    for lo in (40,60,80,100,120,150,200):
                        add(n=n,icpt='free',top=top,lo=lo,hi=hi,J=J,ksub=ksub)
# Part 2: C5, free intercept, top fixed (deferred) or free
for top in ('fixed','free'):
    for hi in (400,500):
        for J in range(2,6):
            for ksub in (3,4):
                for lo in (40,60,80,100,120,150,200):
                    add(n=5,icpt='free',top=top,lo=lo,hi=hi,J=J,ksub=ksub)
# precision duplicates at dps=120 for the most ill-conditioned configurations
dup=[t for t in T if (t['J']>=5 and t['ksub']==t['n']-1 and t['lo'] in (80,100,150) and t['hi'] in (500,2000))]
for t in dup[::2]:
    u=dict(t); u['dps']=120; u.pop('id'); add(**u)
for t in T:
    if t['top']=='fixed': t['top_cands']={'p199':'1.99','p200':'2.00'}
with open('tasks.jsonl','w') as f:
    for t in T: f.write(json.dumps(t)+'\n')
print(len(T), len(dup))
