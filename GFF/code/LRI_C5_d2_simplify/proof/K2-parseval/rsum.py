# Generalized Richardson extrapolation for sum_{m>=0} f(m) when f(m) ~ m^{-1-p} * (power series in 1/m):
# the tail sum_{m>=N} f(m) has the asymptotic expansion sum_j c_j N^{-p-j}.  We compute partial sums
# P(N_i), N_i = N0*2^i (i=0..J), and solve P(N_i) = S - sum_{j<J} c_j N_i^{-p-j} for S (a (J+1)x(J+1) linear system).
import mpmath as mp

def rsum(f, p, N0=48, J=12, start=0):
    Ns = [N0*2**i for i in range(J+1)]
    P = []
    acc = mp.mpf(0)
    m = start
    for N in Ns:
        while m < N:
            acc += f(m)
            m += 1
        P.append(acc)
    A = mp.matrix(J+1, J+1)
    b = mp.matrix(J+1, 1)
    for i, N in enumerate(Ns):
        A[i, 0] = 1
        for j in range(J):
            A[i, j+1] = -mp.mpf(N)**(-p-j)
        b[i] = P[i]
    x = mp.lu_solve(A, b)
    return x[0]

if __name__ == '__main__':
    mp.mp.dps = 50
    tau = mp.mpf('0.13')
    al2 = (1-tau)/2
    f = lambda x: mp.exp(2*mp.loggamma(x+al2)-2*mp.loggamma(x+1))
    gauss = mp.gamma(al2)**2*mp.gamma(tau)/mp.gamma(1-al2)**2
    for J in (8, 10, 12):
        print(J, mp.nstr(rsum(f, tau, 48, J)-gauss, 5))
