from mpmath import mp, mpf, pi, log, zeta
mp.dps=30
A=pi+4*log(2); z3=zeta(3); z5=zeta(5)
dr6=(mpf(1024)/25*A**5-mpf(1216)/15*A**3*pi**2+mpf(2672)/5*A**2*pi**3+mpf(60864)/5*A**2*z3
     -mpf(2738)/75*A*pi**4+mpf(5963)/15*pi**5-mpf(12046)/5*pi**2*z3+mpf(711576)/5*z5)
print('Delta r6 repair =',dr6,' Delta C6 =',dr6/2187)
cf=mpf('14331.6870327580543204454632552462171183173')
num=mpf('14331.68703276838')
print('closed form - graph sum =',cf-num, ' in allowance units:',(cf-num)/mpf('4.9e-7'))
print('closed form without repair =',cf-dr6/2187)
