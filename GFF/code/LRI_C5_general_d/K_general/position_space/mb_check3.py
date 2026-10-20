import numpy as np
from scipy.special import loggamma as lg, gamma
from mb_check_np import J_d1

def Jreg_mb(d, t, c1, c2, h, Y=12.0):
    q = d / 4.0
    y = np.arange(-Y, Y + h / 2, h)
    tot = 0.0
    for chunk in np.array_split(y, 8):
        Y1, Y2 = np.meshgrid(chunk, y, indexing='ij')
        z1 = c1 + 1j * Y1; z2 = c2 + 1j * Y2
        L = (2 * lg(-z1) + 2 * lg(-z2) + 2 * lg(q + z1 + z2) + lg(q + z2) - lg(q - z2)
             + lg(t / 2 + z1) + lg(q - t / 2 - z1 - z2) - lg(2 * q - t / 2 - z1) - lg(q + t / 2 + z1 + z2))
        tot += np.exp(L).sum()
    return gamma(2 * q) ** 2 / gamma(q) ** 4 * tot * h * h / (4 * np.pi ** 2)

def Jpole(d, t):
    q = d / 4.0
    return gamma(2 * q) * gamma(t / 2) ** 2 * gamma(q - t / 2) ** 4 / (gamma(q) ** 4 * gamma(2 * q - t))

for (d, t, c1, c2, ex) in [(2.0, 0.6, -0.15, -0.25, 47.790785413226103671), (1.0, 0.3, -0.075, -0.125, J_d1(0.3))]:
    for h in (0.02, 0.012):
        print('d', d, 't', t, 'h', h, 'direct %.14g' % Jreg_mb(d, t, c1, c2, h).real, ' exact %.14g' % ex)
# pole-extracted: contour c1' left of -t/2
for (d, t, c1p, c2, ex) in [(2.0, 0.6, -0.45, -0.2, 47.790785413226103671), (1.0, 0.3, -0.19, -0.03, J_d1(0.3))]:
    for h in (0.05, 0.03, 0.02):
        jr = Jreg_mb(d, t, c1p, c2, h).real
        print('d', d, 't', t, 'h', h, 'pole+reg %.14g' % (Jpole(d, t) + jr), ' exact %.14g' % ex, ' Jpole %.10g Jreg %.10g' % (Jpole(d, t), jr))
