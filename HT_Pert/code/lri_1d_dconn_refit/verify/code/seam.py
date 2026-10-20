import numpy as np, json, csv
from myload import *
DO=SCR+'/delta/out/'
my=json.load(open('../out/mycont_dC678.json'))
Lp=list(range(74,119,2))
tab={}
for r in csv.DictReader(open(DO+'delta_v1_hi72_smooth_table.csv')):
    tab[(int(r['k']),int(r['L']))]=r
V=json.load(open(DO+'variants_full_hi72.json'))
D=load(); dC=D['dC678']
print('central(L) - my weighted-family median(L);  in units of my member std at that L')
for k in (6,7,8):
    s=my[str(k)]['summary']
    for L in (74,76,80,92,118):
        i=Lp.index(L); m=s['median'][i]; sd=s['std'][i]
        row=tab[(k,L)]
        print(' dC%d L=%3d my %.11f std %.1e | '%(k,L,m,sd)+'  '.join('%s %+.2e (%+.1f)'%(c[:6],float(row[c])-m,(float(row[c])-m)/sd) for c in ('median','medoid','floormean','floormedoid'))+'  env %.1e typ %.1e'%(float(row['unc_envelope']),float(row['unc_typ'])))
# floor-level member spread vs my spread; kept member misfit at 72
print()
for k in (6,7,8):
    b=V['dC%d'%k]; P=np.array(b['pred']); mr=np.array(b['maxres']); Lv=b['L']
    lo=np.array([int(s.split('lo=')[1].split('|')[0]) for s in b['labels']])
    best={l:mr[lo==l].min() for l in set(lo)}
    fl=np.array([mr[i]<=3*best[lo[i]] for i in range(len(mr))])
    i72=Lv.index(72); ex72=dC[72][k]
    mis=P[:,i72]-ex72
    # misfit relative to my smooth value at 72 (fit through all exact points), not the noisy point
    # my smooth at 72: refit quickly = median member prediction from weighted family at 72 -> use the exact-L residual of best fit instead; approximate by my median at 74 extrapolated? use exact value
    s=my[str(k)]['summary']
    for L in (74,92,118):
        if L not in Lv: continue
        j=Lv.index(L); i=Lp.index(L)
        print(' dC%d L=%d all-kept std %.1e halfrange %.1e | floor n=%d std %.1e halfrange %.1e mean-my %+.1e | my std %.1e'%(k,L,P[:,j].std(),(P[:,j].max()-P[:,j].min())/2,fl.sum(),P[fl,j].std(),(P[fl,j].max()-P[fl,j].min())/2,P[fl,j].mean()-s['median'][i],s['std'][i]))
    print('   kept-member misfit at 72 (curve - exact): all median|.| %.1e max %.1e ; floor median %.1e max %.1e'%(np.median(abs(mis)),abs(mis).max(),np.median(abs(mis[fl])),abs(mis[fl]).max()))
