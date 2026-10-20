# Independent check: elliptic closed forms (M, N by AGM quadrature at 75 digits) against C62d's 70-digit single sums.
import mpmath as mp, json
mp.mp.dps=75
pi=mp.pi; l=mp.log(2)
K=lambda k,kp: pi/(2*mp.agm(1,kp))
def Q(F):
    G=lambda th: F(mp.sin(th),mp.cos(th),K(mp.sin(th),mp.cos(th)),K(mp.cos(th),mp.sin(th)))*mp.cos(th)
    return mp.quad(G,mp.linspace(0,pi/2,17))
M=Q(lambda k,kp,f,g:f**2); N=Q(lambda k,kp,f,g:f*g)
d=json.load(open('<PROJECT>/LRI_C5_d2_simplify/confirm_dps70.json'))
S=lambda e: mp.mpf(d['singles'][str(('L',e))])
a=S((0,)*7); b=-2*S((1,0,0,0,0,0,0))/pi; Sy=S((0,0,0,1,0,0,0)); Sxy=4*S((1,0,0,1,0,0,0))+S((0,0,0,0,1,0,0))
L2=mp.mpf(d['checks']['L2'])
res={'a-8N/pi^3':a-8*N/pi**3,'b-8M/pi^3':b-8*M/pi**3,'Sy-(2M/pi^2-4log2 N/pi^3)':Sy-(2*M/pi**2-4*l*N/pi**3),
     'Sxy-(8 log2 M/pi^2+2N/pi)':Sxy-(8*l*M/pi**2+2*N/pi),'L2(C62d 70 dig)+1024 log2 M N/pi^3':L2+1024*l*M*N/pi**3}
for k,v in res.items(): print('%-40s %s'%(k,mp.nstr(v,5)))
print('M =',mp.nstr(M,72)); print('N =',mp.nstr(N,72)); print('L2=-1024 log2 MN/pi^3 =',mp.nstr(-1024*l*M*N/pi**3,72))
json.dump({k:mp.nstr(v,6) for k,v in res.items()}|{'M':mp.nstr(M,72),'N':mp.nstr(N,72),'L2':mp.nstr(-1024*l*M*N/pi**3,72),'P4(2)':mp.nstr(512*M*N/pi**3,72)},
          open('check_vs_C62d_dps70.json','w'),indent=1)
