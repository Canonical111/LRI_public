from mpmath import mp, mpf, gamma, pi, matrix, lu_solve
mp.dps=20
G14=gamma(mpf(1)/4); Ag=3*pi**2/G14**4; a=1/(3*Ag); KI=mpf('0.006246637286122373941927734')
C={3:-3.719856322901833,4:45.42488010356,5:-731.13947662454,6:14331.6870327684,7:-322549.888813,8:8066723.342964563}
print("b_eff(n) = -C_{n+1}/(a C_n) - n - 1 +4  [=4 if Gamma(n+4)]:")
for n in range(3,8): print(n, -C[n+1]/(a*C[n])-n)
r={n:C[n]/(KI*(-a)**n*gamma(n+4)) for n in C}
# fit r_n = r_inf (1 + b1/(n+3) + b2/((n+3)(n+2)) ) using last 3 points
for pts in [(6,7,8),(5,6,7)]:
    M=matrix([[1,1/mpf(n+3),1/mpf((n+3)*(n+2))] for n in pts]); y=matrix([r[n] for n in pts])
    s=lu_solve(M,y); print(pts,"r_inf",s[0],"b1/r_inf",s[1]/s[0],"b2/r_inf",s[2]/s[0])
