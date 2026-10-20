import json,mpmath as m
from fractions import Fraction as F
from pathlib import Path
W=Path(__file__).parent;B=W/'lri_C6_d2_two_forest_update';m.mp.dps=50
import argparse
ap=argparse.ArgumentParser();ap.add_argument('--high',action='store_true');args=ap.parse_args()
raw=json.load(open(W/('position_kite_leaf_ms_48_55_.016.json' if args.high else 'position_kite_leaf_ms_32_45_.02.json')));inv=json.load(open(B/'classified_inventory.json'))
refs=json.load(open(B/'verification/reference_periods.json'));A=4*m.log(2);Q=m.mpf(refs['Q2']);P4=m.mpf(refs['P4_2']);M=-4;N=4-A;U=-14*m.zeta(3);V=-4*m.zeta(3)
b3=6*Q+m.mpf(87)/4*A*A+M;c3=m.mpf(7)/2*A*A+m.mpf(M)/3
b4=-m.mpf(393)/4*A**3-m.mpf(11)/2*A*M-54*A*Q-m.mpf(3)/2*M*N-6*P4-m.mpf(165)/8*U+m.mpf(9)/4*V
c4=-m.mpf(127)/8*A**3-m.mpf(7)/6*A*M-3*A*Q-m.mpf(1)/2*M*N-m.mpf(57)/16*U+m.mpf(3)/8*V
parts={}
for L in[3,4,5,6]:
 tab={g['id']:g for g in inv['loops'][L-1]['graphs']};gs=[g for g in raw['loops'][L-1]['solved']if tab[g['id']]['power_subgraphs']]
 b=sum(m.mpf(g['b'])for g in gs);c=sum(m.mpf(g['c'])for g in gs)
 pending=[g['id']for g in inv['loops'][L-1]['graphs']if g['power_subgraphs']and g['id']not in{a['id']for a in gs}]
 if L==6:
  
  print('pending6',[(i,tab[i]['weight4'],tab[i]['weight2'])for i in pending]);
  assert all(i in ['L6G106','L6G117'] or 3*F(tab[i]['weight2'])==F(tab[i]['weight4']) for i in pending);b+=32*P4;pending=[]
 assert not pending,(L,pending)
 parts[L]=(b,c)

def lower(b3,c3,b4,c4):
 return 2016*A**5-448*A**3*b3+672*A**3*c3-84*A*A*b4+168*A*A*c4+m.mpf(49)/3*A*b3*b3-42*A*b3*c3+m.mpf(7)/3*b3*b4-4*b3*c4-3*b4*c3
b3p,c3p=parts[3];b4p,c4p=parts[4];b5p,c5p=parts[5];b6p,c6p=parts[6]
pow6=3*c6p-b6p-12*A*b5p+30*A*c5p
lowdiff=lower(b3,c3,b4,c4)-lower(b3-b3p,c3-c3p,b4-b4p,c4-c4p)
res=(pow6+lowdiff)/2187
out={'power_sector_sums':{str(L):{'b':str(b),'c':str(c)}for L,(b,c)in parts.items()},'sunset_on_wheel_contribution':'32*P4 to b6, zero to c6','power_contribution_C6':str(res),'higher_piece':str(pow6/2187),'lower_difference':str(lowdiff/2187),'C6_power_cancellation_asserted':False,'scope':'Explicit computed correction; sixth-order b and c entries are partial-channel sums, only 3c-b is complete; see power_sector_audit.json'}
W.joinpath('power_cancellation_high.json' if args.high else 'power_cancellation.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
