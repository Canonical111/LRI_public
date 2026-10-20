# Kernels: generic builder from Meijer/H parameter lists (note's convention eq:gkernel / eq:localH)
# and the simplified kernels written in the note.
import mpmath as mp

lg = mp.loggamma

def gkernel_log(s, a, b, m, n):
    """log of prod_{j<=m}G(b_j+s) prod_{j<=n}G(1-a_j-s) / (prod_{j>m}G(1-b_j-s) prod_{j>n}G(a_j+s))"""
    r = 0
    for j, bj in enumerate(b):
        r += lg(bj + s) if j < m else -lg(1 - bj - s)
    for j, aj in enumerate(a):
        r += lg(1 - aj - s) if j < n else -lg(aj + s)
    return r

def gkernel(s, a, b, m, n):
    return mp.exp(gkernel_log(s, a, b, m, n))

def Glists(P):
    h = mp.mpf(1)/2; q = mp.mpf(1)/4
    L = {}
    L['G4'] = ([h]*4 + [P['alpha4']], [0]*4 + [P['alpha4']], 2, 3)
    L['G6'] = ([h]*6 + [P['alpha6']], [0]*6 + [P['alpha6']], 4, 5)
    L['G8'] = ([-q] + [h]*8 + [P['a8p'], P['a8m']], [0]*8 + [3*q, P['a8p'], P['a8m']], 3, 8)
    L['G7'] = ([-q] + [h]*7 + [P['eta7p'], P['eta7m']], [0]*7 + [3*q, P['eta7p'], P['eta7m']], 3, 8)
    return L

G = mp.gamma
def N_alpha(s, al):
    return G(s)**2*G(0.5 - s)**3/(G(1 - s)**2*G(0.5 + s)*G(s + al)*G(1 - s - al))
def N_6(s, al):
    return G(s)**4*G(0.5 - s)**5/(G(1 - s)**2*G(0.5 + s)*G(s + al)*G(1 - s - al))
def N_8(s, ap, am):
    return (G(s)**3*G(0.5 - s)**7*G(1.25 - s)/(G(1 - s)**5*G(0.5 + s)*G(0.25 - s)
            *G(s + ap)*G(1 - s - ap)*G(s + am)*G(1 - s - am)))
def N_7(s, e1, e2):
    return (G(s)**3*G(0.5 - s)**7*G(1.25 - s)/(G(1 - s)**4*G(0.25 - s)
            *G(s + e1)*G(1 - s - e1)*G(s + e2)*G(1 - s - e2)))
def A_7(s, b):
    bb = mp.conj(b)
    return (G(s)**3*G(0.5 - s)**7*G(1.25 - s)/(G(1 - s)**3*G(-s)*G(0.25 - s)
            *G(s + b)*G(1 - s - b)*G(s + bb)*G(1 - s - bb)))
def N_p(s, b):
    return N_7(s, b, mp.conj(b))
def Psi_sig(s, b):
    bb = mp.conj(b)
    return G(s)**3*G(0.5 - s)**3/(G(0.5 + s)*G(s + b)*G(1 - s - b)*G(s + bb)*G(1 - s - bb))
def Pt(t):
    return G(t)*G(t + 0.5)*G(0.5 - t)*G(1 - t)
