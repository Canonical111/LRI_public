"""Assemble 2187 C6(1) by eq:baseline from the independently computed inputs."""
import mpmath as mp, json, sympy as sp

mp.mp.dps = 80
pi = mp.pi; ell = mp.log(2); A = pi + 4*ell; Q = mp.gamma(mp.mpf(1)/4)**4/pi
G = mp.catalan; z3 = mp.zeta(3); z5 = mp.zeta(5); s2 = mp.sqrt(2)

o = {k: mp.mpf(v['EM']) for k, v in json.load(open('ordinary.json')).items()}
w = {k: mp.mpf(v) for k, v in json.load(open('wheel.json')).items()}
m7 = json.load(open('m7.json'))
pl = {k: mp.mpf(v) for k, v in json.load(open('polylog.json')).items()}
pr = {k: mp.mpf(v) for k, v in json.load(open('primitive_dps95.json')).items() if k != 'relation'}

# E (eq:E)
P = (mp.mpf(21)/640*A**5 + mp.mpf(7)/64*A**3*pi**2 + mp.mpf(1149)/64*A**2*pi**3
     + mp.mpf(7863)/16*A**2*z3 + 192*A*G*(16*G + 3*pi**2) + mp.mpf(14853)/640*A*pi**4
     - mp.mpf(544)/3*G*pi**3 + mp.mpf(37631)/128*pi**5 + mp.mpf(722279)/48*pi**2*z3
     - mp.mpf(805959)/8*z5)
E = Q/8*(63*A**3 + 120*A*G + 79*A*pi**2 + 2013*pi**3 + 54204*z3) + Q**2*(29*pi - 249*A) + P
Ereal = E - mp.mpf(476)/3*pi**3*(32*G + 9*pi**2)
D3, D5 = pl['D3'], pl['D5']
Bpol = 4352*((32*G + 9*pi**2)*D3 - 64*D5)
Cd = 96*Q - 42*A**2 - 18*A*pi - 1227*pi**2
Cs = 60*Q - mp.mpf(105)/4*A**2 - 9*A*pi - mp.mpf(2469)/4*pi**2
Blow = 4*pi**3*Cd*o['U4'] + 2*pi**4*Cs*o['U6']
Pb = 6*Q**3/pi*(2*o['Hm'] - 1) - 104*pi**5*o['H0'] + 2**18*pi**5/Q**3*o['Hp']
B6 = 24*Pb
B8 = pi**6*(4932 - 5004*s2)*o['U8'] + 556*pi**2*((17 + 12*s2)*o['Y1'] - (17 - 12*s2)*o['Y7'])
W0 = w['Wc_from0']
M7 = mp.mpf(m7['avg_4000_150'])
Pa = pr['Pa']
blocks = dict(E=E, Bpol=Bpol, Blow=Blow, B6=B6, B8=B8, wheel=-393*pi**3*W0,
              seventh=24*pi**3*M7, primitive=96*Pa)
r6 = mp.fsum(blocks.values())
C6 = r6/2187

claimed = json.load(open('<PROJECT>/GFF/C6_research_note/outputs/reassembly.json'))
cb = {k: mp.mpf(v) for k, v in claimed['blocks_r6'].items()}
cmp = [('E_real (known_real)', Ereal, cb['known_real']),
       ('Bpol-(Ereal-E) (log_sine_and_Clausen)', Bpol - (Ereal - E), cb['log_sine_and_Clausen']),
       ('B_low (lower)', Blow, cb['lower']), ('B6 (sixth)', B6, cb['sixth']),
       ('B8 (eighth)', B8, cb['eighth']), ('-393pi^3 W0 (wheel)', blocks['wheel'], cb['wheel']),
       ('24pi^3 M7 (seventh)', blocks['seventh'], cb['seventh']),
       ('96 P_a (primitive)', blocks['primitive'], cb['primitive'])]
def agree(a, b):
    d = abs(a - b)
    return 'exact' if d == 0 else '%.1f' % float(-mp.log10(d/abs(b)))
print('%-42s %-50s %s' % ('block (r6 units)', 'this computation', 'rel. agreement digits'))
for n, a, b in cmp:
    print('%-42s %-50s %s   diff %s' % (n, mp.nstr(a, 45), agree(a, b), mp.nstr(a - b, 3)))
print('E (unshifted) =', mp.nstr(E, 50), '  E+Bpol =', mp.nstr(E + Bpol, 50))
print('sum of blocks r6 =', mp.nstr(r6, 70))
print('C6(1) =', mp.nstr(C6, 70))
Cc = mp.mpf(claimed['C6_reassembled_from_series'])
print('claimed C6 (series) =', mp.nstr(Cc, 70))
print('C6 - claimed =', mp.nstr(C6 - Cc, 5), ' rel', mp.nstr((C6 - Cc)/Cc, 5))
print('C6 - note Crefval(58 digits shown) =', mp.nstr(C6 - mp.mpf('14331.6870327580543204454632552462171183173230619887904582'), 3))
gs = mp.mpf('14331.68703276838')
print('C6 - graph sum 14331.68703276838 =', mp.nstr(C6 - gs, 6), ' in units of 4.9e-7 allowance:', mp.nstr((C6 - gs)/mp.mpf('4.9e-7'), 4))
# repair
dr = (mp.mpf(1024)/25*A**5 - mp.mpf(1216)/15*A**3*pi**2 + mp.mpf(2672)/5*A**2*pi**3
      + mp.mpf(60864)/5*A**2*z3 - mp.mpf(2738)/75*A*pi**4 + mp.mpf(5963)/15*pi**5
      - mp.mpf(12046)/5*pi**2*z3 + mp.mpf(711576)/5*z5)
print('repair Delta r6 =', mp.nstr(dr, 30), '  in C6 units:', mp.nstr(dr/2187, 30))
print('C6 without repair =', mp.nstr(C6 - dr/2187, 30), '  minus graph sum:', mp.nstr(C6 - dr/2187 - gs, 8))
# table lines 1500-1522
print('W0 =', mp.nstr(W0, 45)); print('M7 =', mp.nstr(M7, 45)); print('P_a =', mp.nstr(Pa, 45))
c1 = -393*pi**3*W0/2187; c2 = 24*pi**3*M7/2187; c3 = 96*Pa/2187
for name, v, ref in [('-393pi^3W0/2187', c1, '-437.775914461168923635033332127009'),
                     ('24pi^3M7/2187', c2, '-5217.069054363479839305067485280987'),
                     ('96Pa/2187', c3, '14701.829146690890003104395116162537'),
                     ('sum', c1 + c2 + c3, '9046.984177866241240164294298754541')]:
    print('%-18s %s   vs note %s  diff %s' % (name, mp.nstr(v, 40), ref, mp.nstr(v - mp.mpf(ref), 3)))
# fixed values in json: G4 via B_low = -4 pi^2 rho4 G4 and G6, G8 normalizations
X4 = -Cd; Y4 = -Cs; rho4 = mp.sqrt(X4**2 + Y4**2)
print('G4 implied by B_low:', mp.nstr(-Blow/(4*pi**2*rho4), 40), ' claimed', claimed['fixed_values']['G4'][:42])
print('G6 implied by B6   :', mp.nstr(B6/(192*pi*mp.sqrt(290)), 40), ' claimed', claimed['fixed_values']['G6'][:42])
rho8 = mp.sqrt(2177203 - 1028322*s2)
print('G8 implied by B8   :', mp.nstr(B8/(16*pi**3*rho8), 40), ' claimed', claimed['fixed_values']['G8'][:42])
print('H_W implied by W0  :', mp.nstr(W0*pi**2/mp.sqrt(89), 40), ' claimed', claimed['fixed_values']['H_W'][:42])
print('H_* implied by P_a :', mp.nstr(Pa/(80*pi**3), 40), ' claimed', claimed['fixed_values']['H_star'][:42])
print('X4>0, Y4>0:', X4 > 0, Y4 > 0, ' X4 =', mp.nstr(X4, 10), ' Y4 =', mp.nstr(Y4, 10))
print('L3 vs claimed:', mp.nstr(pl['Ls3'] - mp.mpf(claimed['fixed_values']['Ls3_pi_over_2']), 3),
      '  C212 vs claimed:', mp.nstr(D5 - mp.mpf(claimed['fixed_values']['Cl212_pi_over_2']), 3))

# symbolic: monomial count of E and E_real, Eshift
Asym, Qs, Gs, pis, z3s, z5s = sp.symbols('A Q G pi z3 z5')
R = sp.Rational
Ps = (R(21,640)*Asym**5 + R(7,64)*Asym**3*pis**2 + R(1149,64)*Asym**2*pis**3 + R(7863,16)*Asym**2*z3s
      + 192*Asym*Gs*(16*Gs + 3*pis**2) + R(14853,640)*Asym*pis**4 - R(544,3)*Gs*pis**3
      + R(37631,128)*pis**5 + R(722279,48)*pis**2*z3s - R(805959,8)*z5s)
Es = sp.expand(Qs/8*(63*Asym**3 + 120*Asym*Gs + 79*Asym*pis**2 + 2013*pis**3 + 54204*z3s)
               + Qs**2*(29*pis - 249*Asym) + Ps)
Ereals = sp.expand(Es - R(476,3)*pis**3*(32*Gs + 9*pis**2))
print('monomials in E:', len(Es.as_ordered_terms()), '  in E_real:', len(Ereals.as_ordered_terms()))
js = sp.sympify(claimed['known_polynomial_real'].replace('z3', 'z3s').replace('z5', 'z5s'),
                locals={'A': Asym, 'Q': Qs, 'G': Gs, 'pi': pis, 'z3s': z3s, 'z5s': z5s})
print('json known_polynomial_real == E_real (eq:Ereal):', sp.simplify(js - Ereals) == 0)
json.dump({k: mp.nstr(v, 70) for k, v in dict(blocks, C6=C6, r6=r6, Ereal=Ereal, repair_r6=dr).items()},
          open('assembly.json', 'w'), indent=1)
