/*
 * direct_moments.c -- direct finite-cutoff evaluation of the hard-core ordered
 * kink moments of the d=1 long-range Ising wall gas (no eps expansion).
 *
 * Written from the definitions in note/LRI_perturbation_compendium.tex
 * (Secs. 3-6).  No archive code is used.
 *
 *   W_n(v,delta;X) = exp[ 2v sum_{i<j} q_i q_j f_delta(X_j-X_i) ],
 *   f_delta(r) = (r^delta-1)/delta,   q_i = (-1)^{i+1},
 *   Omega_n(eps) = {0<X_1<...<X_n<1, X_{i+1}-X_i >= eps},
 *   A_n (n odd), Z_n (n even): int W_n,  Q_n (n even): int D_n W_n,
 *   D_n = sum_j (X_{2j}-X_{2j-1}),
 *   endpoint source (first eta derivative at eta=0):
 *   E I = int W * sum_i q_i [f_delta(X_i) +- f_delta(1-X_i)]
 *       = 2 int W * sum_i q_i f_delta(X_i)        (reflection; first eta-derivative only)
 *
 * Output: Taylor coefficients [z^a delta^b] (v = 1+z) of the integral for
 * a+b <= ord, at v=1, delta=0, for the requested kind.  Derivatives are
 * d_v^a d_delta^b I = a! b! [z^a delta^b] I.
 *
 * Integration: nested Gauss-Legendre rules in transformed coordinates.
 *  form 0 ("NE"):  gaps r_1..r_m (m=n-1) as nested variables, translation
 *     integral done analytically (weight Lambda = 1-R).  Middle gaps use the
 *     two-sided logistic map t = log((r)/(B+eps-r)), r in [eps,B], which sends
 *     the poles at r=0 and at the squeeze point r=B+eps to t=-+infinity; the last
 *     gap uses the one-sided exponential map r = eps*exp(s).
 *  form 1 ("LO", Lambda outer): total free length Lambda = 1-R is the outermost
 *     variable (map with lower end at Lambda=0, truncated at t=-tcut, upper
 *     squeeze offset eps), gaps r_1..r_{m-1} nested inside with logistic maps,
 *     r_m fixed by sum r = 1-Lambda.  The translation integral of the source
 *     term is done analytically: int_0^Lambda log^k(x+c) dx.
 *  Endpoint-source moments require form 1 (Lambda log Lambda at Lambda=0).
 *
 * Build:  cc -O3 -march=x86-64-v3 -fopenmp -o direct_moments direct_moments.c -lm
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#ifdef _OPENMP
#include <omp.h>
#endif

#define MAXN 10
#define MAXORD 4
#define MAXGL 512

/* ---------------- parameters ---------------- */
static int    P_n = 3, P_m = 2;
static char   P_kind = 'A';
static int    P_E = 0;
static int    P_form = 0;
static double P_eps = 0.1;
static int    P_ord = 3;
static int    P_N = 20, P_N0 = 0, P_Nlast = 0;
static double P_tcut = 20.0;
static int    P_generic = 0;

/* Gauss-Legendre tables on [-1,1] */
static double GLx_N[MAXGL], GLw_N[MAXGL];
static double GLx_0[MAXGL], GLw_0[MAXGL];
static double GLx_L[MAXGL], GLw_L[MAXGL];

static void gauleg(int N, double *x, double *w)
{
    for (int i = 0; i < (N + 1) / 2; i++) {
        long double z = cosl(3.14159265358979323846264338327950288L * (i + 0.75L) / (N + 0.5L));
        long double pp = 0, z1;
        for (int it = 0; it < 100; it++) {
            long double p1 = 1, p2 = 0, p3;
            for (int j = 1; j <= N; j++) { p3 = p2; p2 = p1; p1 = ((2.0L * j - 1) * z * p2 - (j - 1.0L) * p3) / j; }
            pp = N * (z * p1 - p2) / (z * z - 1);
            z1 = z; z = z1 - p1 / pp;
            if (fabsl(z - z1) < 1e-19L) break;
        }
        /* recompute derivative at converged z */
        long double p1 = 1, p2 = 0, p3;
        for (int j = 1; j <= N; j++) { p3 = p2; p2 = p1; p1 = ((2.0L * j - 1) * z * p2 - (j - 1.0L) * p3) / j; }
        pp = N * (z * p1 - p2) / (z * z - 1);
        x[i] = (double)(-z); x[N - 1 - i] = (double)z;
        w[i] = w[N - 1 - i] = (double)(2.0L / ((1 - z * z) * pp * pp));
    }
}

/* ---------------- truncated bivariate series in (z, delta) ---------------- */
/* index: c[a][b], a+b <= ord */
typedef double Ser[MAXORD + 1][MAXORD + 1];

static inline void ser_zero(Ser s) { memset(s, 0, sizeof(Ser)); }

static inline void ser_mul(Ser r, Ser x, Ser y, int ord)
{
    Ser t; ser_zero(t);
    for (int a1 = 0; a1 <= ord; a1++) for (int b1 = 0; a1 + b1 <= ord; b1++) {
        double xv = x[a1][b1]; if (xv == 0.0) continue;
        for (int a2 = 0; a1 + a2 <= ord; a2++) for (int b2 = 0; a1 + a2 + b1 + b2 <= ord; b2++)
            t[a1 + a2][b1 + b2] += xv * y[a2][b2];
    }
    memcpy(r, t, sizeof(Ser));
}

/* exp(X) with X[0][0]=0 */
static inline void ser_exp(Ser r, Ser X, int ord)
{
    Ser term, acc;
    ser_zero(acc); acc[0][0] = 1.0;
    ser_zero(term); term[0][0] = 1.0;
    for (int k = 1; k <= ord; k++) {
        ser_mul(term, term, X, ord);
        for (int a = 0; a <= ord; a++) for (int b = 0; a + b <= ord; b++) term[a][b] /= (double)k;
        for (int a = 0; a <= ord; a++) for (int b = 0; a + b <= ord; b++) acc[a][b] += term[a][b];
    }
    memcpy(r, acc, sizeof(Ser));
}

/* ---------------- recursion state ---------------- */
typedef struct {
    double c[MAXN + 2];   /* positions relative to X_1 (c[1]=0) */
    double W;             /* partial product of r_ij^{2 q_i q_j} */
    double S[MAXORD + 2]; /* partial S_j, j=1..ord+1 */
    double D;             /* partial current insertion */
    double wt;            /* product of quadrature weights and Jacobians */
    double Lam;           /* Lambda (form 1) */
    double used;          /* sum of gaps fixed so far */
} State;

typedef struct {
    Ser acc, cmp, abs;   /* Neumaier-compensated sums: value = acc + cmp */
    long long npts;
} Acc;

static inline void nadd(double *s, double *c, double x)
{
    double t = *s + x;
    if (fabs(*s) >= fabs(x)) *c += (*s - t) + x; else *c += (x - t) + *s;
    *s = t;
}

static inline void place_kink(State *s, int j, double pos)
{
    /* place kink j (1-based) at relative position pos; pairs (i,j), i<j */
    s->c[j] = pos;
    int nS = P_ord + 1;
    for (int i = 1; i < j; i++) {
        double d = pos - s->c[i];
        double sg = ((i + j) & 1) ? -1.0 : 1.0;   /* q_i q_j = (-1)^{i+j} */
        double d2 = d * d;
        if (sg < 0) s->W /= d2; else s->W *= d2;
        if (P_ord == 0) continue;            /* no log insertions needed */
        double L = log(d), Lp = L;
        for (int k = 1; k <= nS; k++) { s->S[k] += sg * Lp; Lp *= L; }
    }
}

/* P_j(y) = int_0^y log^j u du = y * sum_{i=0}^j (-1)^{j-i} j!/i! log^i y */
static inline double Pint(int j, double y)
{
    if (y <= 0.0) return 0.0;
    double L = log(y);
    double sum = 0.0, fac = 1.0; /* j!/i! for i=j down */
    /* Horner-like: sum_{i=0}^{j} (-1)^{j-i} (j!/i!) L^i */
    double Li[MAXORD + 3]; Li[0] = 1.0;
    for (int i = 1; i <= j; i++) Li[i] = Li[i - 1] * L;
    for (int i = j; i >= 0; i--) {
        sum += (((j - i) & 1) ? -1.0 : 1.0) * fac * Li[i];
        fac *= (double)i; /* next: j!/(i-1)! = (j!/i!)*i */
    }
    return y * sum;
}

/* exp(s1 z + (1+z) D(delta)), D(delta) = sum_{k>=1} d[k] delta^k, truncated at a+b<=ord.
   = sum_j z^j/j! ... : [z^a delta^b] = sum_{j<=a} s1^{a-j}/(a-j)! [delta^b] (G D^j/j!),  G = e^D */
static inline void exp_struct(Ser r, double s1, const double *d, int ord)
{
    double G[MAXORD + 1], H[MAXORD + 1][MAXORD + 1], sp[MAXORD + 1];
    G[0] = 1.0;
    for (int b = 1; b <= ord; b++) {
        double acc = 0.0;
        for (int k = 1; k <= b; k++) acc += (double)k * d[k] * G[b - k];
        G[b] = acc / (double)b;
    }
    /* H[j] = G * D^j / j! */
    for (int b = 0; b <= ord; b++) H[0][b] = G[b];
    for (int j = 1; j <= ord; j++) {
        for (int b = 0; b <= ord; b++) {
            double acc = 0.0;
            for (int k = 1; k <= b; k++) acc += d[k] * H[j - 1][b - k];
            H[j][b] = acc / (double)j;
        }
    }
    sp[0] = 1.0;
    for (int a = 1; a <= ord; a++) sp[a] = sp[a - 1] * s1 / (double)a;
    for (int a = 0; a <= ord; a++) for (int b = 0; a + b <= ord; b++) {
        double acc = 0.0;
        for (int j = 0; j <= a; j++) acc += sp[a - j] * H[j][b];
        r[a][b] = acc;
    }
}

static void leaf(State *s, Acc *A)
{
    int ord = P_ord;
    Ser X; ser_zero(X);
    /* log W = 2(1+z) sum_k delta^k S_{k+1}/(k+1)!  minus the delta=0,z=0 part */
    X[1][0] = 2.0 * s->S[1];
    double fact = 1.0;
    for (int k = 1; k <= ord; k++) {
        fact *= (double)(k + 1);
        double coef = 2.0 * s->S[k + 1] / fact;
        X[0][k] = coef;
        if (1 + k <= ord) X[1][k] = coef;
    }
    Ser EX;
    if (P_generic) ser_exp(EX, X, ord);
    else exp_struct(EX, X[1][0], X[0], ord);
    double base = s->W * s->wt;
    if (P_kind == 'Q') base *= s->D;
    if (!P_E) {
        base *= s->Lam;
        for (int a = 0; a <= ord; a++) for (int b = 0; a + b <= ord; b++) {
            double v = base * EX[a][b];
            nadd(&A->acc[a][b], &A->cmp[a][b], v); A->abs[a][b] += fabs(v);
        }
    } else {
        /* T_E(delta) = 2 sum_i q_i sum_k delta^k [P_{k+1}(Lam+c_i)-P_{k+1}(c_i)]/(k+1)! */
        double TE[MAXORD + 1];
        for (int k = 0; k <= ord; k++) TE[k] = 0.0;
        for (int i = 1; i <= P_n; i++) {
            double qi = (i & 1) ? 1.0 : -1.0;
            double ci = s->c[i];
            double y1 = s->Lam + ci;
            double f = 1.0;
            for (int k = 0; k <= ord; k++) {
                f *= (double)(k + 1);
                TE[k] += 2.0 * qi * (Pint(k + 1, y1) - Pint(k + 1, ci)) / f;
            }
        }
        for (int a = 0; a <= ord; a++) for (int b = 0; a + b <= ord; b++) {
            double sum = 0.0;
            for (int bb = 0; bb <= b; bb++) sum += EX[a][b - bb] * TE[bb];
            double v = base * sum;
            nadd(&A->acc[a][b], &A->cmp[a][b], v); A->abs[a][b] += fabs(v);
        }
    }
    A->npts++;
}

/* logistic map: x in [lo,hi], offsets elo,ehi (>=0); node xi in [-1,1].
   returns x and dx (=Jacobian*halfwidth); if elo==0 the lower t-end is -tcut,
   if ehi==0 the upper t-end is +tcut. */
static inline void logistic_map(double lo, double hi, double elo, double ehi, double xi,
                                double *x, double *jac)
{
    double L = hi - lo;
    double c = L + elo + ehi;
    double ta = (elo > 0) ? log(elo / (L + ehi)) : -P_tcut;
    double tb = (ehi > 0) ? log((L + elo) / ehi) : P_tcut;
    double h = 0.5 * (tb - ta);
    double t = 0.5 * (ta + tb) + h * xi;
    double sg, om; /* sigma, 1-sigma */
    if (t >= 0) { double e = exp(-t); sg = 1.0 / (1.0 + e); om = e / (1.0 + e); }
    else { double e = exp(t); sg = e / (1.0 + e); om = 1.0 / (1.0 + e); }
    *x = lo - elo + c * sg;
    *jac = h * c * sg * om;
}

/* exponential map: x in [lo,hi], lower offset elo>0: x = lo-elo + elo*exp(s), s in [0, log((L+elo)/elo)] */
static inline void exp_map(double lo, double hi, double elo, double xi, double *x, double *jac)
{
    double L = hi - lo;
    double sb = log((L + elo) / elo);
    double h = 0.5 * sb;
    double sv = h + h * xi;
    double u = elo * exp(sv);
    *x = lo - elo + u;
    *jac = h * u;
}

/* ---------- form 0 recursion: level k chooses gap r_k (k=1..m) ---------- */
static void rec_form0(State *s, int k, Acc *A)
{
    int m = P_m;
    double eps = P_eps;
    double B = 1.0 - s->used - (double)(m - k) * eps;   /* max of r_k */
    if (B < eps) return;
    if (k < m) {
        for (int i = 0; i < P_N; i++) {
            double r, jac;
            logistic_map(eps, B, eps, eps, GLx_N[i], &r, &jac);
            State t = *s;
            t.wt *= GLw_N[i] * jac;
            t.used += r;
            if (k & 1) t.D += r;
            place_kink(&t, k + 1, s->c[k] + r);
            rec_form0(&t, k + 1, A);
        }
    } else {
        int NL = P_Nlast;
        for (int i = 0; i < NL; i++) {
            double r, jac;
            exp_map(eps, B, eps, GLx_L[i], &r, &jac);
            State t = *s;
            t.wt *= GLw_L[i] * jac;
            t.used += r;
            if (k & 1) t.D += r;
            t.Lam = B - r;        /* = 1 - R */
            place_kink(&t, k + 1, s->c[k] + r);
            leaf(&t, A);
        }
    }
}

/* ---------- form 1 recursion: level 0 = Lambda, levels 1..m-1 gaps, r_m fixed ---------- */
static void rec_form1(State *s, int k, Acc *A)
{
    int m = P_m;
    double eps = P_eps;
    double tot = 1.0 - s->Lam;    /* sum of all gaps */
    if (k == m) {
        double r = tot - s->used;  /* last gap */
        if (r < eps * (1 - 1e-12)) return;
        State t = *s;
        if (k & 1) t.D += r;
        place_kink(&t, k + 1, s->c[k] + r);
        leaf(&t, A);
        return;
    }
    double B = tot - s->used - (double)(m - k) * eps;
    if (B < eps) return;
    for (int i = 0; i < P_N; i++) {
        double r, jac;
        logistic_map(eps, B, eps, eps, GLx_N[i], &r, &jac);
        State t = *s;
        t.wt *= GLw_N[i] * jac;
        t.used += r;
        if (k & 1) t.D += r;
        place_kink(&t, k + 1, s->c[k] + r);
        rec_form1(&t, k + 1, A);
    }
}

static void init_state(State *s)
{
    memset(s, 0, sizeof(State));
    s->W = 1.0; s->wt = 1.0; s->c[1] = 0.0;
}

static void usage(void)
{
    fprintf(stderr,
        "usage: direct_moments -n N -k A|Z|Q [-E] -e eps [-f 0|1] [-o ord] [-N npts] [-N0 n0] [-NL nlast] [-t tcut]\n");
    exit(2);
}

int main(int argc, char **argv)
{
    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "-n") && i + 1 < argc) P_n = atoi(argv[++i]);
        else if (!strcmp(argv[i], "-k") && i + 1 < argc) P_kind = argv[++i][0];
        else if (!strcmp(argv[i], "-E")) P_E = 1;
        else if (!strcmp(argv[i], "-e") && i + 1 < argc) P_eps = atof(argv[++i]);
        else if (!strcmp(argv[i], "-f") && i + 1 < argc) P_form = atoi(argv[++i]);
        else if (!strcmp(argv[i], "-o") && i + 1 < argc) P_ord = atoi(argv[++i]);
        else if (!strcmp(argv[i], "-N") && i + 1 < argc) P_N = atoi(argv[++i]);
        else if (!strcmp(argv[i], "-N0") && i + 1 < argc) P_N0 = atoi(argv[++i]);
        else if (!strcmp(argv[i], "-NL") && i + 1 < argc) P_Nlast = atoi(argv[++i]);
        else if (!strcmp(argv[i], "-t") && i + 1 < argc) P_tcut = atof(argv[++i]);
        else if (!strcmp(argv[i], "-G")) P_generic = 1;
        else usage();
    }
    if (P_n < 2 || P_n > MAXN) usage();
    if (P_ord < 0 || P_ord > MAXORD) usage();
    if (P_kind == 'A' && !(P_n & 1)) { fprintf(stderr, "A needs odd n\n"); return 2; }
    if ((P_kind == 'Z' || P_kind == 'Q') && (P_n & 1)) { fprintf(stderr, "Z/Q need even n\n"); return 2; }
    if (P_E && P_form == 0) { fprintf(stderr, "source moments need -f 1\n"); return 2; }
    P_m = P_n - 1;
    if (P_N0 <= 0) P_N0 = 2 * P_N;
    if (P_Nlast <= 0) P_Nlast = P_N;
    if (P_N > MAXGL || P_N0 > MAXGL || P_Nlast > MAXGL) usage();
    if (1.0 - (P_m) * P_eps <= 0) { fprintf(stderr, "empty domain\n"); return 2; }
    gauleg(P_N, GLx_N, GLw_N);
    gauleg(P_N0, GLx_0, GLw_0);
    gauleg(P_Nlast, GLx_L, GLw_L);

    int ord = P_ord;
    Acc tot; memset(&tot, 0, sizeof(Acc));
    double t0 = 0;
#ifdef _OPENMP
    t0 = omp_get_wtime();
#endif

    if (P_form == 0) {
        /* parallelize over first one or two levels */
        int m = P_m;
        double eps = P_eps;
        if (m == 1) {
            State s; init_state(&s);
            rec_form0(&s, 1, &tot);
        } else {
            int n1 = P_N;
            int n2 = (m >= 3) ? P_N : P_Nlast;  /* level-2 rule */
            long ntask = (long)n1 * n2;
            #pragma omp parallel
            {
                Acc loc; memset(&loc, 0, sizeof(Acc));
                #pragma omp for schedule(dynamic,1)
                for (long task = 0; task < ntask; task++) {
                    int i1 = (int)(task / n2), i2 = (int)(task % n2);
                    State s; init_state(&s);
                    double B1 = 1.0 - (double)(m - 1) * eps;
                    double r1, j1;
                    logistic_map(eps, B1, eps, eps, GLx_N[i1], &r1, &j1);
                    s.wt *= GLw_N[i1] * j1; s.used += r1; s.D += r1;
                    place_kink(&s, 2, r1);
                    /* level 2 */
                    double B2 = 1.0 - s.used - (double)(m - 2) * eps;
                    if (B2 < eps) continue;
                    double r2, j2;
                    if (m >= 3) { logistic_map(eps, B2, eps, eps, GLx_N[i2], &r2, &j2); s.wt *= GLw_N[i2] * j2; }
                    else { exp_map(eps, B2, eps, GLx_L[i2], &r2, &j2); s.wt *= GLw_L[i2] * j2; }
                    s.used += r2;
                    place_kink(&s, 3, s.c[2] + r2);
                    if (m == 2) { s.Lam = B2 - r2; leaf(&s, &loc); }
                    else rec_form0(&s, 3, &loc);
                }
                #pragma omp critical
                {
                    for (int a = 0; a <= ord; a++) for (int b = 0; a + b <= ord; b++) {
                        nadd(&tot.acc[a][b], &tot.cmp[a][b], loc.acc[a][b]);
                        nadd(&tot.acc[a][b], &tot.cmp[a][b], loc.cmp[a][b]);
                        tot.abs[a][b] += loc.abs[a][b];
                    }
                    tot.npts += loc.npts;
                }
            }
        }
    } else {
        int m = P_m;
        double eps = P_eps;
        double S = 1.0 - m * eps;   /* max Lambda */
        int n2 = (m >= 2) ? P_N : 1;
        long ntask = (long)P_N0 * n2;
        #pragma omp parallel
        {
            Acc loc; memset(&loc, 0, sizeof(Acc));
            #pragma omp for schedule(dynamic,1)
            for (long task = 0; task < ntask; task++) {
                int i0 = (int)(task / n2), i1 = (int)(task % n2);
                State s; init_state(&s);
                double Lam, jl;
                logistic_map(0.0, S, 0.0, eps, GLx_0[i0], &Lam, &jl);
                s.Lam = Lam; s.wt *= GLw_0[i0] * jl;
                if (m == 1) { rec_form1(&s, 1, &loc); continue; }
                double tot1 = 1.0 - Lam;
                double B1 = tot1 - (double)(m - 1) * eps;
                if (B1 < eps) continue;
                double r1, j1;
                logistic_map(eps, B1, eps, eps, GLx_N[i1], &r1, &j1);
                s.wt *= GLw_N[i1] * j1; s.used += r1; s.D += r1;
                place_kink(&s, 2, r1);
                rec_form1(&s, 2, &loc);
            }
            #pragma omp critical
            {
                for (int a = 0; a <= ord; a++) for (int b = 0; a + b <= ord; b++) {
                    nadd(&tot.acc[a][b], &tot.cmp[a][b], loc.acc[a][b]);
                    nadd(&tot.acc[a][b], &tot.cmp[a][b], loc.cmp[a][b]);
                    tot.abs[a][b] += loc.abs[a][b];
                }
                tot.npts += loc.npts;
            }
        }
    }
    double t1 = 0;
#ifdef _OPENMP
    t1 = omp_get_wtime();
#endif
    int nthr = 1;
#ifdef _OPENMP
    nthr = omp_get_max_threads();
#endif
    /* JSON output */
    printf("{\"n\": %d, \"kind\": \"%c\", \"E\": %d, \"form\": %d, \"eps\": %.17g, \"ord\": %d, "
           "\"N\": %d, \"N0\": %d, \"NL\": %d, \"tcut\": %.6g, \"npts\": %lld, \"seconds\": %.3f, \"threads\": %d, \"coef\": {",
           P_n, P_kind, P_E, P_form, P_eps, ord, P_N, P_N0, P_Nlast, P_tcut, tot.npts, t1 - t0, nthr);
    int first = 1;
    for (int a = 0; a <= ord; a++) for (int b = 0; a + b <= ord; b++) {
        printf("%s\"%d,%d\": [%.17e, %.17e]", first ? "" : ", ", a, b, tot.acc[a][b] + tot.cmp[a][b], tot.abs[a][b]);
        first = 0;
    }
    printf("}}\n");
    return 0;
}
