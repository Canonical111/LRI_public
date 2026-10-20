# Quick (<1 min, 30 digit) checks of the elementary ingredients of the L2-elliptic route.
# f(k)=K(k), g(k)=K(k') (modulus convention), M=int f^2, N=int f g, l=log 2.
import mpmath as mp
mp.mp.dps = 30
pi, l = mp.pi, mp.log(2)
kp = lambda k: mp.sqrt((1-k)*(1+k))
f = lambda k: mp.pi/(2*mp.agm(1, kp(k)))   # K(k)
g = lambda k: mp.pi/(2*mp.agm(1, k))       # K(k')
Q = lambda F: mp.quad(F, [0, mp.mpf(1)/2, 1])
M = Q(lambda k: f(k)**2)
N = Q(lambda k: f(k)*g(k))
a = 8*N/pi**3; b = 8*M/pi**3
print('a', a); print('b', b)
# 70-digit reference values from confirm_dps70.json
a70 = mp.mpf('1.118636387164187068349619257525640916794857551529361191480618646924046')
b70 = mp.mpf('0.9027285783238348241903933987727629850304635036014195522559185553239932')
print('a-a70', a-a70, ' b-b70', b-b70)
Sy70 = mp.mpf('0.321311538544619606853604164437241038370829048911')
Sx1y70 = mp.mpf('-0.07096629825322418433412296948435087373037822033')
Sz1_70 = mp.mpf('5.009759040984015386070483995287017465707352402263')
Sxy70 = 4*Sx1y70 + Sz1_70

# 1. d/dx 2F1(x,x;1;z) at x=1/2 equals -log(1-z) 2F1(1/2,1/2;1;z)
z = mp.mpf('0.37')
d = mp.diff(lambda x: mp.hyp2f1(x, x, 1, z), mp.mpf(1)/2)
print('1. Euler-derivative identity:', d + mp.log(1-z)*mp.hyp2f1(0.5, 0.5, 1, z))

# 2. Sy = -(8/pi^3) int f g log k'  and  int f g log k' = l N/2 - pi M/4
Ilk1 = Q(lambda k: f(k)*g(k)*2*mp.log(kp(k))/2)
print('2a. Sy rep    :', -8/pi**3*Ilk1 - Sy70)
print('2b. log k\' mom:', Ilk1 - (l*N/2 - pi*M/4))
print('2c. (L-a)      :', Sy70 - (pi*b70 - 2*a70*l)/4)

# 3. sum c^4 x1 y = -(8/pi^3) int f g log k log k'
Ill = Q(lambda k: f(k)*g(k)*mp.log(k)*2*mp.log(kp(k))/2)
print('3. sum c^4 x1 y rep:', -8/pi**3*Ill - Sx1y70)

# 4. d/dalpha 2F1(al,al;2al;1-u) at al=1/2 = [4l - log(1-u)] (2/pi) K(sqrt(1-u)) - 2 K(sqrt u)
u = mp.mpf('0.23')
d4 = mp.diff(lambda al: mp.hyp2f1(al, al, 2*al, 1-u), mp.mpf(1)/2)
rhs4 = (4*l - mp.log(1-u))*2/pi*mp.ellipk(1-u) - 2*mp.ellipk(u)
print('4. d/dalpha 2F1(al,al;2al):', d4 - rhs4)

# 5. (*)  2X + pi Y = (pi^2/4) N + pi l M,  X = int f g w log k, Y = int f^2 log k
X = Q(lambda k: f(k)*g(k)*(mp.log(k) - 2*mp.log(kp(k)))*mp.log(k))
Y = Q(lambda k: f(k)**2*mp.log(k))
print('X', X, 'Y', Y)
print('5. (*) residual:', 2*X + pi*Y - (pi**2/4*N + pi*l*M))
# Sxy from the integral representation
Sz1 = 16/pi**3*Q(lambda k: f(k)*g(k)*mp.log(k)**2) + 8/pi**2*Y
print('6. sum c^4 psi1(k+1/2) rep:', Sz1 - Sz1_70)
print('7. (L-b):', Sxy70 - (pi**2*a70/4 + pi*b70*l))
