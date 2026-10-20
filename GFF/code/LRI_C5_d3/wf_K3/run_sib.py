import json, mpmath as mp
from irel import lll_relation
from consts import build
mp.mp.dps=300
c=build(480)
K3=mp.mpf(json.load(open('K3_value.json'))['K3'])
z=json.load(open('../wf_Z3/Z3_values.json'))['values']; zz=json.load(open('../wf_Z3/pslq_z3_results.json'))
L=json.load(open('../wf_L3/L3_final_values.json'))['values']
pi,l2,G,z3,s2=c['pi'],c['l2'],c['G'],c['z3'],c['s2']
H=mp.mpf(zz['H30']); S2=mp.mpf(zz['S2']); g10=c['G14']**10/pi**mp.mpf(3.5)
cl=[('1',1),('pi',pi),('l2',l2),('pi2',pi**2),('G',G),('pil2',pi*l2),('pi3',pi**3),('z3',z3),('piG',pi*G),('pi4',pi**4),('pi2G',pi**2*G),('G2',G**2),('piz3',pi*z3),('l2z3',l2*z3),('pi3l2',pi**3*l2)]
def run(tag,extra,D):
    B=cl+extra
    r=lll_relation([K3]+[v for _,v in B],D,['K3']+[n for n,_ in B])
    print('%-46s n=%d D=%d %s | bound %.3g | allowed %.3g'%(tag,r['n'],D,('HIT '+r['relation']) if r.get('admissible') else 'none',r['maxcoeff_bound'],r['allowed_maxcoeff']),r.get('internal_relations',''),flush=True)
ZX=[('H',H),('piH',pi*H),('pi2H',pi**2*H),('pi3H',pi**3*H),('GH',G*H),('piGH',pi*G*H),('l2pi2H',l2*pi**2*H),('S2',S2),('piS2',pi*S2),('pi2S2',pi**2*S2),('GS2',G*S2),('g10',g10),('pig10',pi*g10),('pi2g10',pi**2*g10),('Gg10',G*g10),('l2pig10',l2*pi*g10)]
run('classical15 + Z3 constants (H3(0),S2,g10)',ZX,240)
v=lambda k: mp.mpf(L[k])
LX=[('X0',v('X0')),('Xh',v('Xh')),('a4b4',v('a4')*v('b4')),('s2a4b4',s2*v('a4')*v('b4')),('dH',v('dH')),('b4da',v('b4')*v('da')),('s2b4da',s2*v('b4')*v('da')),('m0',v('m0_mu1_weighted_h4_0'))]
LX=LX+[('pi*'+n,pi*x) for n,x in LX]
run('classical15 + L3/P4 constants x{1,pi}',LX,150)
