# Compare all independently computed values with the claims; reassemble M7, P_a, residual blocks and C6(1).
import mpmath as mp, json
from params import setup
P = setup(60); mp.mp.dps = 60
pi = mp.pi
claim = json.load(open('<PROJECT>/GFF/C6_research_note/outputs/reassembly.json'))['fixed_values']
claim = {k: mp.mpf(v) for k, v in claim.items()}
table = dict(W0='78.57031213654711716068274888671985244', M7='-15332.55419477457527697894653409303157',
             Pa='334926.04524805183788322200124007778661')
table = {k: mp.mpf(v) for k, v in table.items()}
pl = json.load(open('polylog_out.json')); gm = json.load(open('gvals_mb_50.json'))
r1 = json.load(open('reduced1d_40.json')); pr = json.load(open('primitive1d_40.json')); se = json.load(open('series_out.json'))
mine = dict(Ls3_pi_over_2=mp.mpf(pl['L3_quad']), Cl212_pi_over_2=mp.mpf(pl['C212_cvz']),
            G4=mp.mpf(gm['G4'][0]), G6=mp.mpf(gm['G6'][0]), G8=mp.mpf(gm['G8'][0]), G7=mp.mpf(gm['G7'][0]),
            H_W=mp.mpf(r1['H_W_1d']), H7_unit=mp.mpf(r1['H7_1d']), H_star=mp.mpf(pr['H_star_1d']))
def digits(a, b):
    d = abs(a - b)
    return 'all' if d == 0 else f"{float(-mp.log10(d/abs(b))):.1f}"
print("value            claimed (as given)                                     mine                                             agree(sig.digits)")
for k in mine:
    print(f"{k:16s} {mp.nstr(claim[k], 40):45s} {mp.nstr(mine[k], 40):45s} {digits(mine[k], claim[k])}")
M7_from = P['rho7']*mine['G7']/pi**mp.mpf(1.5) + 196*mp.sqrt(185)/mp.sqrt(pi)*mine['H7_unit']
M7_ser = mp.mpf(se['M7_series'])
print("M7 = rho7 G7/pi^1.5 + 196 sqrt185/sqrt(pi) H7 =", mp.nstr(M7_from, 40))
print("M7 series eq:M7                               =", mp.nstr(M7_ser, 40), " rel diff", mp.nstr(abs(M7_from - M7_ser)/abs(M7_ser), 3))
print("M7 note table                                 =", mp.nstr(table['M7'], 40), " digits vs mine", digits(M7_from, table['M7']))
W0 = mp.sqrt(89)/pi**2*mine['H_W']
print("W0 = sqrt89 H_W/pi^2 =", mp.nstr(W0, 40), " vs series", digits(W0, mp.mpf(se['W0_series'])), " vs table", digits(W0, table['W0']))
Pa = 80*pi**3*mine['H_star']
print("P_a = 80 pi^3 H*     =", mp.nstr(Pa, 40), " vs Gauss-input pairing", digits(Pa, mp.mpf(pr['Pa_gauss_input'])), " vs table", digits(Pa, table['Pa']))
# residual contributions (lines 1518-1522)
c1 = -393*pi**3*W0/2187; c2 = 24*pi**3*M7_from/2187; c3 = 96*Pa/2187
print("-393pi^3W0/2187 =", mp.nstr(c1, 34), "  claim -437.775914461168923635033332127009")
print("24pi^3M7/2187   =", mp.nstr(c2, 34), "  claim -5217.069054363479839305067485280987")
print("96Pa/2187       =", mp.nstr(c3, 34), "  claim 14701.829146690890003104395116162537")
print("sum             =", mp.nstr(c1 + c2 + c3, 34), "  claim 9046.984177866241240164294298754541")
# full boxed formula eq:preferred with my nine values
A, Q, G, z3, z5 = P['A'], P['Q'], P['G'], mp.zeta(3), mp.zeta(5)
Preal = (mp.mpf(21)/640*A**5 + mp.mpf(7)/64*A**3*pi**2 + mp.mpf(1149)/64*A**2*pi**3 + mp.mpf(7863)/16*A**2*z3
         + 192*A*G*(16*G + 3*pi**2) + mp.mpf(14853)/640*A*pi**4 - mp.mpf(15776)/3*G*pi**3
         - mp.mpf(145153)/128*pi**5 + mp.mpf(722279)/48*pi**2*z3 - mp.mpf(805959)/8*z5)
Ereal = Q/8*(63*A**3 + 120*A*G + 79*A*pi**2 + 2013*pi**3 + 54204*z3) + Q**2*(29*pi - 249*A) + Preal
v = mine
r6 = (Ereal - 2176*((32*G + 9*pi**2)*v['Ls3_pi_over_2'] + 128*v['Cl212_pi_over_2'])
      - 4*pi**2*P['rho4']*v['G4'] + 192*pi*mp.sqrt(290)*v['G6'] + 16*pi**3*P['rho8']*v['G8']
      - 393*pi*mp.sqrt(89)*v['H_W'] + 24*pi**mp.mpf(1.5)*(P['rho7']*v['G7'] + 196*pi*mp.sqrt(185)*v['H7_unit'])
      + 7680*pi**3*v['H_star'])
C6 = r6/2187
Cref = mp.mpf('14331.6870327580543204454632552462171183173230619887904582')
print("C6(1) from eq:preferred with my values =", mp.nstr(C6, 40))
print("note reference Crefval                 =", mp.nstr(Cref, 40), "  rel diff", mp.nstr(abs(C6 - Cref)/Cref, 3))
# E (non-real) + B_pol route as a check of eq:Eshift
E = Ereal + mp.mpf(476)/3*pi**3*(32*G + 9*pi**2)
D3 = -v['Ls3_pi_over_2']/2 - 7*pi**3/192; D5 = v['Cl212_pi_over_2']
Bpol = 4352*((32*G + 9*pi**2)*D3 - 64*D5)
print("E+B_pol - (E_real - 2176[...]) =", mp.nstr(E + Bpol - (Ereal - 2176*((32*G + 9*pi**2)*v['Ls3_pi_over_2'] + 128*v['Cl212_pi_over_2'])), 3))
print("D3 (ODE route) vs -L3/2-7pi^3/192:", mp.nstr(mp.mpf(pl['D3_ode']) - D3, 3))
