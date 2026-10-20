import json, mpmath as mp
from irel import lll_relation
from consts import build
mp.mp.dps=130
c=build(480)
K3=mp.mpf(json.load(open('K3_value.json'))['K3'])
r=json.load(open('../inputs/general_d3/period_values.json'))['runs'][-1]['values']
cv=lambda s: mp.mpf(str(s).strip('()').split(' ')[0])
Q3,P4,X0,Xh=cv(r['Q3']),cv(r['P4_3']),cv(r['Xi4_0']),cv(r['Xi4_1_8'])
am=r['amplitudes'];a4,b4=cv(am['a4']),cv(am['b4'])
pi,l2,G,z3,s2=c['pi'],c['l2'],c['G'],c['z3'],c['s2']
g=c['G14']
H30=(Q3+g**10/(48*pi**mp.mpf(3.5)))/(4*pi**2)
D=85
cl=[('1',1),('pi',pi),('l2',l2),('pi2',pi**2),('G',G),('pil2',pi*l2),('pi3',pi**3),('z3',z3),('piG',pi*G),('pi4',pi**4),('pi2G',pi**2*G),('G2',G**2),('pi z3',pi*z3),('l2 z3',l2*z3),('pi3l2',pi**3*l2)]
def run(tag,extra):
    B=cl+extra
    res=lll_relation([K3]+[v for _,v in B],D,['K3']+[n for n,_ in B])
    print('%-40s n=%d %s | bound %.3g | allowed %.3g'%(tag,res['n'],('HIT '+res['relation']) if res.get('admissible') else 'none',res['maxcoeff_bound'],res['allowed_maxcoeff']),flush=True)
run('Q3 x {1,pi,l2,pi2,G}',[('Q3',Q3),('piQ3',pi*Q3),('l2Q3',l2*Q3),('pi2Q3',pi**2*Q3),('GQ3',G*Q3)])
run('pi2H3(0), sqrtpi a3b3 x {1,pi,l2}',[('pi2H',pi**2*H30),('pi3H',pi**3*H30),('l2pi2H',l2*pi**2*H30),('g10',g**10/pi**mp.mpf(3.5)),('pig10',g**10/pi**mp.mpf(2.5)),('l2g10',l2*g**10/pi**mp.mpf(3.5))])
run('P4(3) pieces x {1}',[('P4',P4),('piX0',pi*X0),('piXh',pi*Xh),('pia4b4',pi*a4*b4),('s2pia4b4',s2*pi*a4*b4)])
