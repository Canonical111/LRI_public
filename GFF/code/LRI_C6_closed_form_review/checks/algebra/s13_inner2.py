from common import *
mp.dps = 25
for s in [mpc('0.25','-3.1'), mpc('0.25','11.0')]:
    ds = psi(1,0.5-s)-psi(1,1-s)
    wi = B(lambda t: GP([t,t+0.5,0.5-t,1-t],[])/(0.5-s-t)**2, 0.125)
    si = B(lambda v: GP([v,v+0.5,1-v,0.5-v],[v+0.25,v+0.75,0.25-v,0.75-v])/((0.5-v)*(0.5-s-v)), 1/mpf(16))
    print('s',s,' wheelinner/(pi d)-1', wi/(pi*ds)-1, '  seventhinner*(-pi s/Psi)-1', si*(-pi*s)/(psi(0,1-2*s)+euler)-1)
