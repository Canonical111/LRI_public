from common import *
import json
R1=[r for r in load('results_574286.jsonl') if r['dps']==60 and r['n']==5]
R3=[r for r in load('results_574295.jsonl') if r['dps']==60 and r['n']==5]
c5fit=-(mp.mpf(3.5)/3)*mp.mpf('-1.7112'); c5H=(mp.mpf(3.5)**3/6)*mp.mpf('0.278612140024')
NZ=(3.6e-12,2.6e-12)
rows=[]
def one(r_fx,r_fr,label,hi,lo):
    A=mp.mpf(r_fx['coef_y']['I'])-c5fit*mp.mpf(r_fx['coef_f']['I'])
    AH=mp.mpf(r_fx['coef_y']['I'])-c5H*mp.mpf(r_fx['coef_f']['I'])
    rr=np.array(r_fx['res_y'])-float(c5fit)*np.array(r_fx['res_f'])
    sA=sig_corr(r_fx,*NZ) if 'p' in r_fx else float(r_fx['sig_unit']['I'])*6e-12
    sU=sig_corr(r_fr,*NZ) if 'p' in r_fr else float(r_fr['sig_unit']['I'])*6e-12
    d=dict(basis=label,hi=hi,lo=lo,ncols=r_fx['ncols'],A=float(A),A_Hchain=float(AH),sigma_noise=sA,rms=float(np.sqrt(np.mean(rr**2))),maxres=float(np.max(abs(rr))),
           dA_dc5top=-float(mp.mpf(r_fx['coef_f']['I'])),A_uncon=float(mp.mpf(r_fr['coef_y']['I'])),top_uncon=float(mp.mpf(r_fr['coef_y']['j1k3'])),sigma_uncon=sU,rms_uncon=r_fr['rms'])
    rows.append(d); return d
for hi in (500,400):
  for lo in (40,50,60,70,80,100,120,150,200):
    for lab,base in (('A[3,2,3]','A'),('B[3,2,3,0]','B'),('C[3,2,3,1]','C'),('L[3,3,3]','L'),('I[3,1,3,0]','I'),('O[3,1,2]','O')):
        fx=[r for r in R3 if r['base']==base and r['hi']==hi and r['lo']==lo and r['top']=='fixed']
        fr=[r for r in R3 if r['base']==base and r['hi']==hi and r['lo']==lo and r['top']=='free']
        if fx: one(fx[0],fr[0],lab,hi,lo)
    for lab,ks in (('U2[3,3]',3),('U2b[3,4]',4)):
        fx=[r for r in R1 if r['J']==2 and r['ksub']==ks and r['hi']==hi and r['lo']==lo and r['top']=='fixed']
        fr=[r for r in R1 if r['J']==2 and r['ksub']==ks and r['hi']==hi and r['lo']==lo and r['top']=='free']
        if fx: one(fx[0],fr[0],lab,hi,lo)
json.dump(dict(c5top_fit=float(c5fit),c5top_Hchain=float(c5H),noise_model=dict(white=NZ[0],rw_inc=NZ[1]),rows=rows),open('summary_c5.json','w'),indent=1)
for d in rows:
    if d['hi']==500 and d['lo']>=80:
        print('%-11s lo%3d nc%2d A=%10.4f (H-chain %10.4f) sn=%.0e rms=%.1e max=%.1e dA/dt=%+.3f | uncon A=%10.3f top=%8.3f sn=%.0e'%(d['basis'],d['lo'],d['ncols'],d['A'],d['A_Hchain'],d['sigma_noise'],d['rms'],d['maxres'],d['dA_dc5top'],d['A_uncon'],d['top_uncon'],d['sigma_uncon']))
