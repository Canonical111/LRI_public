import gzip, json, sys, time, numpy as np, pickle
R='<TMP>/scratchpad/dconn_refit72/joint/out/r72/'
f=sys.argv[1]
t=time.time()
cols={k:[] for k in ('kind','ds','hi','low','lo','base','mode','sh','gap')}
num={}
for line in gzip.open(R+f,'rt'):
    r=json.loads(line)
    if 'err' in r: continue
    for k in cols: cols[k].append(r[k])
    for n,v in r['lim'].items(): num.setdefault('C'+n,[]).append(v)
    for n,o in r['o'].items():
        for j,name in enumerate(('rms','maxres','cond','gain','stat','npts','ncol','erms','emax','stat_x')):
            num.setdefault(name+n,[]).append(o[j] if o[j] is not None else np.nan)
    num.setdefault('om6',[]).append(r['om'].get('6',np.nan))
    # floor-member spliced delta response for C8 (std) if present
    for key in ('splF6_8','splF7_8','splF8_8','splF6_7','splF7_7','splF6_6','spl6_6','spl7_7','spl8_8'):
        num.setdefault('v_'+key,[]).append(r['v'][key][5] if ('v' in r and key in r['v']) else np.nan)
T={k:np.array(v) for k,v in cols.items()}
T.update({k:np.array(v,float) for k,v in num.items()})
pickle.dump(T,open('../out/'+f.replace('.jsonl.gz','.pkl'),'wb'))
print(f,len(T['kind']),'%.1fs'%(time.time()-t))
