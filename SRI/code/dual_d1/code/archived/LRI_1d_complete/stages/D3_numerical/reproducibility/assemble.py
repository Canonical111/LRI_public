"""Assemble the next thermal coefficient from independently evaluated raw moments."""
from pathlib import Path
import mpmath as m,json,math
m.mp.dps=45;ROOT=Path(__file__).resolve().parent;DATA=ROOT/'data'
z2=m.zeta(2);z3=m.zeta(3);z4=m.zeta(4);L=m.log(2);H=m.log(3);li=m.polylog(2,-m.mpf('.5'))
a=-4*z2;c=-16;p=8-2*z2-7*z3-8*L
b=-18-6*z2+m.mpf(28)/3*z3+32*L-12*H-4*L*L-8*li
f=32-m.mpf(136)/3*z3-64*L+48*H+16*L*L+32*li
P=4*z2+m.mpf(8)/3*z3-2+3*H+L*L+2*li
T2=2-2*z2-4*z3;D2=m.mpf(5)/2+2*z2

def moment(name):
 data=json.loads((DATA/name).read_text())
 return {j-1:(-1)**(j-1)*m.mpf(data['coeff'][str(-j)][0])/m.factorial(j-1) for j in range(1,9)}
def moment3(name,all3):
 return {j-1:(-1)**(j-1)*m.mpf(all3[name][str(-j)])/m.factorial(j-1) for j in range(1,9)}
def read(name,k):return moment(name)[k]

def assemble(N6=10,NE4=10,N5=12,NE3=12,N4=16):
 three=json.loads((DATA/'three_derivatives.json').read_text())
 A=-m.mpf(three['vv']['-2'])/2;E=4-m.mpf(three['vd']['-2']);C30vv=8+m.mpf(three['vv']['-1'])
 A3vplus1log=-m.mpf(three['v_at_minus1']['-2'])
 Q4=moment(f'm4_1_e0_base_N{N4}_c0.json')
 Q4v=moment(f'm4_1_e0_v2_N{N4}_c0.json')
 Q4plus1=moment(f'm4_1_e0_base_N{N4}_c-1.json')
 Z4=moment(f'm4_0_e0_base_N{N4}_c0.json')
 Z4v=moment(f'm4_0_e0_v2_N{N4}_c0.json')
 Z4minus1=moment(f'm4_0_e0_base_N{N4}_c1.json')
 A5v=moment(f'm5_0_e0_v_N{N5}_c0.json')
 Q6=moment(f'm6_1_e0_base_N{N6}_c0.json')
 E3=moment(f'm3_0_e1_e2_N{NE3}_c0.json' if (DATA/f'm3_0_e1_e2_N{NE3}_c0.json').exists() else f'm3_0_e1_analytice_N{NE3}_c0.json')
 E3v=moment(f'm3_0_e1_ve_N{NE3}_c0.json')
 EQ4=moment(f'm4_1_e1_e2_N{NE4}_c0.json' if (DATA/f'm4_1_e1_e2_N{NE4}_c0.json').exists() else f'm4_1_e1_analytice_N{NE4}_c0.json')
 delta={}
 for pair,weight in [('01',-m.mpf('.5')),('02',m.mpf('.5')),('03',-m.mpf('.25')),('12',-m.mpf('.25'))]:
  pol=moment(f'm4_1_e0_vv_N{N4}_c0_p{pair}.json')
  for j,val in pol.items():delta[j]=delta.get(j,0)+weight*val
 C30=3-2*z2;C30v=18-14*z2-15*z3-8*L
 C51v=A5v[1]-Z4v[1]-C30v-14-4*z2-A3vplus1log
 EC3=-26+8*z2;EC3v=E3v[0]+4*z2-4*z3
 J3=-2*C30v+EC3;J3v=-2*C30vv+EC3v
 K40=P+4*z2-10;K40v=Q4v[0]
 K61=Q6[1]+Z4[0]-P+7-6*z2-Q4plus1[1]-Z4minus1[1]
 L2=10-4*z2;L2d=-60+12*z2+12*z3+8*z4
 L4=-2*K40-4*K40v+2*(EQ4[0]-6)
 G=C51v-3*C30v-3*C30*a+16-f+2*J3+2*J3v
 q=-4*(delta[1]-4+2*p+L2d)
 k=-4*(K61+2*b-4*K40-4*L2+L4)
 D3=(16*A-32*E-8*G+8*b+c*c+4*f-4*k+32*p-8*q)/64
 C5=2*D3-T2/2+(D2-m.mpf(1)/16)**2/4
 out=dict(A=A,E=E,G=G,q=q,k=k,D3=D3,thermal_x5half=C5,C51v=C51v,EC3v=EC3v,J3v=J3v,K40v=K40v,K61=K61,L2d=L2d,L4=L4,Q4delta_log=delta[1],EQ4finite=EQ4[0],E3vfinite=E3v[0],Q6log=Q6[1],Z40=Z4[0],Q4plus1log=Q4plus1[1],Z4minus1log=Z4minus1[1],A3vplus1log=A3vplus1log)
 checks=dict(three_A=A-(-8-4*z2-2*z3+16*L),endpoint3=E3[0]-(-26+10*z2),Q40=Q4[0]-(P+4*z2-8),Q41=Q4[1]-(-8+4*z2),Q42=Q4[2]+7,Q43=Q4[3]+m.mpf(4)/3,Z41=Z4[1]-(4-6*z2),Z42=Z4[2]+m.mpf(9)/2,Z43=Z4[3]-2)
 result={'resolution':dict(N6=N6,NE4=NE4,N5=N5,NE3=NE3,N4=N4),'coefficients':{key:str(v) for key,v in out.items()},'baseline_checks':{key:str(v) for key,v in checks.items()}}
 return result
if __name__=='__main__':
 import argparse
 pa=argparse.ArgumentParser();pa.add_argument('--n6',type=int,default=10);pa.add_argument('--ne4',type=int,default=10);pa.add_argument('--n5',type=int,default=12);pa.add_argument('--ne3',type=int,default=12);pa.add_argument('--n4',type=int,default=16);ar=pa.parse_args()
 try:result=assemble(ar.n6,ar.ne4,ar.n5,ar.ne3,ar.n4)
 except (FileNotFoundError,KeyError) as e:print('Input not yet available:',e);raise SystemExit(1)
 print(json.dumps(result,indent=2));(DATA/f'assembled_{ar.n6}_{ar.ne4}_{ar.n5}_{ar.ne3}_{ar.n4}.json').write_text(json.dumps(result,indent=2))
