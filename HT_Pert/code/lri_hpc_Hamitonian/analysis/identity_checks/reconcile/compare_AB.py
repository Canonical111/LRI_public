import json, math, collections
base='<TMP>/scratchpad/identity/'
A=json.load(open(base+'A/analysis_table.json'))
B=json.load(open(base+'B/results_table.json'))
Bd={(r['L'],r['variant']):r for r in B}
vmap={'raw':'raw','g2D':'g2D','Dfull':'Dfull_raw','Dconn':'Dfull_c'}
worst=collections.defaultdict(lambda:(0,None))
rows=[]
for Ls,av in A.items():
    L=int(Ls)
    for va,vb in vmap.items():
        if va not in av or (L,vb) not in Bd: continue
        a=av[va]; b=Bd[(L,vb)]
        pairs=[('r4',a.get('r4'),b.get('r4')),('g4',a.get('g4'),b.get('g4'))]
        for k in (2,3,4):
            pairs.append((f'C{k}',a['C'][k],b.get(f'C{k}')))
        for s in ('dphi1','dphi2','dphi3'):
            if s in a:
                for k in (2,3,4):
                    pairs.append((f'{s}_e{k}',a[s][k],b.get(f'{s}_e{k}')))
        for name,x,y in pairs:
            if x is None or y is None: continue
            if isinstance(y,float) and math.isnan(y): continue
            dd=abs(x-y); rel=dd/max(1,abs(y))
            key=(va,name)
            rows.append((L,va,name,x,y,dd,rel))
            if rel>worst[key][0]: worst[key]=(rel,L)
print('worst |A-B|/max(1,|B|) per (variant, quantity) [L at worst]:')
for k in sorted(worst): print(f'  {k[0]:6s} {k[1]:10s} {worst[k][0]:.2e}  L={worst[k][1]}')
print('n comparisons', len(rows))
bad=[r for r in rows if r[6]>1e-9]
print('n > 1e-9:', len(bad))
for r in bad[:40]: print(r)
# L coverage
print('common L:', sorted({r[0] for r in rows}))
