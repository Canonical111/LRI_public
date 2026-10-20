from common import *
mp.dps = 25
s = mpc('0.25','11.0')
f = lambda w: (lambda v: GP([v,v+0.5,1-v,0.5-v],[v+0.25,v+0.75,0.25-v,0.75-v])/((0.5-v)*(0.5-s-v)))(mpc(1/mpf(16), w))
si = quad(f, [-inf,-40,-12,-11.5,-11,-10.5,-10,-5,-1,0,1,5,40,inf])/(2*pi)
print('seventhinner*(-pi s/Psi)-1 at s=1/4+11i with breakpoints:', si*(-pi*s)/(psi(0,1-2*s)+euler)-1)
