"""Level-local window algebra INCLUDING the r4/g4 retune, checked against A's exact Dconn-g2D eps^4
differences at L=48 (per-level values from A/vac_density_L48.json).  Zero-mode M0 = 2*sum n_i u_i^2,
V0 = (1/2)<C^2B^2>; u0^2=1, u1^2=1/2, u2^2=3/8, u3^2=5/16."""
import json, math
A='<TMP>/scratchpad/identity/A/'
d=json.load(open(A+'analysis_table.json'))['48']; dc={r[0]:r[2] for r in json.load(open(A+'vac_density_L48.json'))}
st=lambda E0: dc[math.ceil(2*E0-1e-9)/2]
dr4=-st(.25)/2; dg4=(-st(.75)-6*dr4)/3
u2=[1,.5,3/8,5/16]
pred={'dphi1':st(1.25)-st(.25)+dr4*(2*u2[1]-2),
      'dphi2':st(1.5)-st(.5)+dr4*(3-4)+dg4*(1-1),
      'dphi3':st(1.75)-st(.75)+dr4*(5-6)+dg4*(3-3),
      'd2phi':st(2.25)-st(.25)+dr4*(2*u2[2]-2),
      'd3phi':st(3.25)-st(.25)+dr4*(2*u2[3]-2)}
for k,v in pred.items():
    act=d['Dconn'][k][4]-d['g2D'][k][4]
    print(f'{k:6s} predicted {v:+.12f} actual {act:+.12f} diff {v-act:+.1e}')
print('retune dr4,dg4 pred', dr4, dg4, ' actual', d['Dconn']['r4']-d['g2D']['r4'], d['Dconn']['g4']-d['g2D']['g4'])
