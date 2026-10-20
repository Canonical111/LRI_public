# Check the generating-function identities and the elliptic-moment identities used in the proof.
# Elliptic integrals via AGM with k=sin(th), k'=cos(th) (no rounding of 1-k^2).
import mpmath as mp, json, sys
mp.mp.dps=int(sys.argv[1]) if len(sys.argv)>1 else 30
pi=mp.pi; l=mp.log(2); h=mp.mpf(1)/2
c2=lambda n: mp.exp(2*(mp.loggamma(n+h)-mp.loggamma(n+1)))/pi
x1=lambda n: mp.psi(0,n+h)-mp.psi(0,n+1)
y=lambda n: mp.psi(0,n+h)-mp.psi(0,h)
z1=lambda n: mp.psi(1,n+h)
K=lambda k,kp: pi/(2*mp.agm(1,kp))     # K(k) given k and k'
# --- generating functions at sample moduli
for k in [mp.mpf('0.3'),mp.mpf('0.77')]:
    z=k**2; kp=mp.sqrt(1-z); f=K(k,kp); g=K(kp,k)
    S=lambda wt: mp.nsum(lambda n: c2(n)*wt(n)*z**n,[0,mp.inf])
    Ptx=4*g*mp.log(kp)+2*pi*f+8/pi*f*mp.log(k)*mp.log(kp)
    r={'P  ':S(lambda n:1)-2/pi*f,'Pt ':S(x1)+g+2/pi*f*mp.log(k),'Px ':S(y)+2/pi*f*mp.log(kp),
       'Ptx':S(lambda n:4*x1(n)*y(n)+2*z1(n))-Ptx}
    for key,v in r.items(): print('k=%s gen.fn residual %s: %s'%(k,key,mp.nstr(v,5)))
# --- elliptic moments: int_0^1 F(k) dk = int_0^{pi/2} F(sin th) cos th dth
def Q(F):
    def G(th):
        k=mp.sin(th); kp=mp.cos(th); return F(k,kp,K(k,kp),K(kp,k))*kp
    return mp.quad(G,[0,pi/8,pi/4,3*pi/8,pi/2])
w=lambda k,kp: mp.log(k)-2*mp.log(kp)
M=Q(lambda k,kp,f,g:f**2); Nn=Q(lambda k,kp,f,g:f*g)
v={}
v['G2[1]-2M']=Q(lambda k,kp,f,g:g**2)-2*M
v['U0-2N']=Q(lambda k,kp,f,g:f**2/kp)-2*Nn
v['FG[log k]+pi M/2']=Q(lambda k,kp,f,g:f*g*mp.log(k))+pi*M/2
v['FG[log(1+k)]-l N/2']=Q(lambda k,kp,f,g:f*g*mp.log(1+k))-l*Nn/2
v['FG[w]+l N']=Q(lambda k,kp,f,g:f*g*w(k,kp))+l*Nn
FGlkp=Q(lambda k,kp,f,g:f*g*mp.log(kp))
v["FG[log k']-(-pi M/4+l N/2)"]=FGlkp-(-pi*M/4+l*Nn/2)
R=Q(lambda k,kp,f,g:f**2*w(k,kp))
v['R-(pi N/4-l M)']=R-(pi*Nn/4-l*M)
v['G2[w]-(-2R-4lM)']=Q(lambda k,kp,f,g:g**2*w(k,kp))-(-2*R-4*l*M)
v['G2[log k]+pi N']=Q(lambda k,kp,f,g:g**2*mp.log(k))+pi*Nn
G2lkp=Q(lambda k,kp,f,g:g**2*mp.log(kp))
v["G2[log k']-(l M-pi N/4)"]=G2lkp-(l*M-pi*Nn/4)
v['FG[logk logk\'] finite']=Q(lambda k,kp,f,g:f*g*mp.log(k)*mp.log(kp))
for key,val in v.items(): print('%-30s %s'%(key,mp.nstr(val,5)))
try:
    s=json.load(open(f'singles_dps{mp.mp.dps}.json'))
    a=mp.mpf(s['a']); b=mp.mpf(s['b']); Sy=mp.mpf(s['Sy']); Sxy=mp.mpf(s['Sxy'])
    print('a-8N/pi^3                     :',mp.nstr(a-8*Nn/pi**3,5)); print('b-8M/pi^3                     :',mp.nstr(b-8*M/pi**3,5))
    print('Sy-(-8/pi^3)FG[log k\']        :',mp.nstr(Sy+8/pi**3*FGlkp,5))
    print('Sxy-(8/pi^2 G2[logk\']+4N/pi)  :',mp.nstr(Sxy-(8/pi**2*G2lkp+4*Nn/pi),5))
except FileNotFoundError: pass
print('M =',M,' N =',Nn)
