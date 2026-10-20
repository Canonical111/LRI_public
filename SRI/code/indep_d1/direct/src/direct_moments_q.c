/*
 * direct_moments_q.c -- quad-precision (__float128) version of the direct
 * finite-cutoff integrator, no-source moments only (A, Z, Q), form 0:
 * nested gaps r_1..r_m, logistic maps on middle gaps, exponential map on the
 * last gap, translation integral analytic (weight 1-R).  Same definitions as
 * direct_moments.c; used to produce ~30-digit data for the finite-part fits.
 *
 * Build (x86-64, gcc): gcc -O3 -march=x86-64-v3 -fopenmp -o direct_moments_q direct_moments_q.c -lquadmath -lm
 * Output: JSON line, coefficients [z^a delta^b] as 36-digit strings.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <quadmath.h>
#ifdef _OPENMP
#include <omp.h>
#endif

typedef __float128 R;
#define MAXN 10
#define MAXORD 4
#define MAXGL 2048

static int P_n = 3, P_m = 2, P_ord = 3, P_N = 100, P_NL = 0;
static char P_kind = 'A';
static R P_eps;
static R GLx[MAXGL], GLw[MAXGL], GLxL[MAXGL], GLwL[MAXGL];

static void gauleg(int N, R *x, R *w)
{
    const R pi = M_PIq;
    for (int i = 0; i < (N + 1) / 2; i++) {
        R z = cosq(pi * (i + 0.75Q) / (N + 0.5Q)), z1, p1, p2, p3, pp;
        for (int it = 0; it < 200; it++) {
            p1 = 1; p2 = 0;
            for (int j = 1; j <= N; j++) { p3 = p2; p2 = p1; p1 = ((2 * j - 1) * z * p2 - (j - 1) * p3) / j; }
            pp = N * (z * p1 - p2) / (z * z - 1);
            z1 = z; z = z1 - p1 / pp;
            if (fabsq(z - z1) < 1e-33Q) break;
        }
        p1 = 1; p2 = 0;
        for (int j = 1; j <= N; j++) { p3 = p2; p2 = p1; p1 = ((2 * j - 1) * z * p2 - (j - 1) * p3) / j; }
        pp = N * (z * p1 - p2) / (z * z - 1);
        x[i] = -z; x[N - 1 - i] = z;
        w[i] = w[N - 1 - i] = 2 / ((1 - z * z) * pp * pp);
    }
}

typedef R Ser[MAXORD + 1][MAXORD + 1];

typedef struct {
    R c[MAXN + 2];
    R W, S[MAXORD + 2], D, wt, Lam, used;
} State;

typedef struct { Ser acc; long long npts; } Acc;

static inline void place_kink(State *s, int j, R pos)
{
    s->c[j] = pos;
    for (int i = 1; i < j; i++) {
        R d = pos - s->c[i];
        int sg = ((i + j) & 1) ? -1 : 1;
        R d2 = d * d;
        if (sg < 0) s->W /= d2; else s->W *= d2;
        if (P_ord == 0) continue;
        R L = logq(d), Lp = L;
        for (int k = 1; k <= P_ord + 1; k++) { if (sg < 0) s->S[k] -= Lp; else s->S[k] += Lp; Lp *= L; }
    }
}

static inline void exp_struct(Ser r, R s1, const R *d, int ord)
{
    R G[MAXORD + 1], H[MAXORD + 1][MAXORD + 1], sp[MAXORD + 1];
    G[0] = 1;
    for (int b = 1; b <= ord; b++) { R acc = 0; for (int k = 1; k <= b; k++) acc += k * d[k] * G[b - k]; G[b] = acc / b; }
    for (int b = 0; b <= ord; b++) H[0][b] = G[b];
    for (int j = 1; j <= ord; j++) for (int b = 0; b <= ord; b++) {
        R acc = 0; for (int k = 1; k <= b; k++) acc += d[k] * H[j - 1][b - k]; H[j][b] = acc / j;
    }
    sp[0] = 1;
    for (int a = 1; a <= ord; a++) sp[a] = sp[a - 1] * s1 / a;
    for (int a = 0; a <= ord; a++) for (int b = 0; a + b <= ord; b++) {
        R acc = 0; for (int j = 0; j <= a; j++) acc += sp[a - j] * H[j][b]; r[a][b] = acc;
    }
}

static void leaf(State *s, Acc *A)
{
    int ord = P_ord;
    R d[MAXORD + 1]; d[0] = 0;
    R fact = 1;
    for (int k = 1; k <= ord; k++) { fact *= (k + 1); d[k] = 2 * s->S[k + 1] / fact; }
    Ser EX; exp_struct(EX, 2 * s->S[1], d, ord);
    R base = s->W * s->wt * s->Lam;
    if (P_kind == 'Q') base *= s->D;
    for (int a = 0; a <= ord; a++) for (int b = 0; a + b <= ord; b++) A->acc[a][b] += base * EX[a][b];
    A->npts++;
}

static inline void logistic_map(R lo, R hi, R e, R xi, R *x, R *jac)
{
    R L = hi - lo, c = L + 2 * e;
    R ta = logq(e / (L + e)), tb = logq((L + e) / e);
    R h = (tb - ta) / 2, t = (ta + tb) / 2 + h * xi, sg, om;
    if (t >= 0) { R ex = expq(-t); sg = 1 / (1 + ex); om = ex / (1 + ex); }
    else { R ex = expq(t); sg = ex / (1 + ex); om = 1 / (1 + ex); }
    *x = lo - e + c * sg;
    *jac = h * c * sg * om;
}

static inline void exp_map(R lo, R hi, R e, R xi, R *x, R *jac)
{
    R L = hi - lo, sb = logq((L + e) / e), h = sb / 2, sv = h + h * xi, u = e * expq(sv);
    *x = lo - e + u; *jac = h * u;
}

static void rec(State *s, int k, Acc *A)
{
    int m = P_m;
    R eps = P_eps;
    R B = 1 - s->used - (m - k) * eps;
    if (B < eps) return;
    if (k < m) {
        for (int i = 0; i < P_N; i++) {
            R r, jac; logistic_map(eps, B, eps, GLx[i], &r, &jac);
            State t = *s; t.wt *= GLw[i] * jac; t.used += r; if (k & 1) t.D += r;
            place_kink(&t, k + 1, s->c[k] + r);
            rec(&t, k + 1, A);
        }
    } else {
        for (int i = 0; i < P_NL; i++) {
            R r, jac; exp_map(eps, B, eps, GLxL[i], &r, &jac);
            State t = *s; t.wt *= GLwL[i] * jac; t.used += r; if (k & 1) t.D += r;
            t.Lam = B - r;
            place_kink(&t, k + 1, s->c[k] + r);
            leaf(&t, A);
        }
    }
}

int main(int argc, char **argv)
{
    char *epsstr = "0.1";
    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "-n")) P_n = atoi(argv[++i]);
        else if (!strcmp(argv[i], "-k")) P_kind = argv[++i][0];
        else if (!strcmp(argv[i], "-e")) epsstr = argv[++i];
        else if (!strcmp(argv[i], "-o")) P_ord = atoi(argv[++i]);
        else if (!strcmp(argv[i], "-N")) P_N = atoi(argv[++i]);
        else if (!strcmp(argv[i], "-NL")) P_NL = atoi(argv[++i]);
        else { fprintf(stderr, "usage: -n n -k A|Z|Q -e eps -o ord -N N [-NL NL]\n"); return 2; }
    }
    P_eps = strtoflt128(epsstr, NULL);
    P_m = P_n - 1;
    if (P_NL <= 0) P_NL = P_N;
    if (P_N > MAXGL || P_NL > MAXGL || P_ord > MAXORD) return 2;
    gauleg(P_N, GLx, GLw); gauleg(P_NL, GLxL, GLwL);
    int ord = P_ord;
    Acc tot; memset(&tot, 0, sizeof(tot));
    double t0 = 0;
#ifdef _OPENMP
    t0 = omp_get_wtime();
#endif
    if (P_m == 1) {
        State s; memset(&s, 0, sizeof(s)); s.W = 1; s.wt = 1;
        rec(&s, 1, &tot);
    } else {
        #pragma omp parallel
        {
            Acc loc; memset(&loc, 0, sizeof(loc));
            #pragma omp for schedule(dynamic,1)
            for (int i1 = 0; i1 < P_N; i1++) {
                State s; memset(&s, 0, sizeof(s)); s.W = 1; s.wt = 1;
                R B1 = 1 - (P_m - 1) * P_eps, r1, j1;
                logistic_map(P_eps, B1, P_eps, GLx[i1], &r1, &j1);
                s.wt *= GLw[i1] * j1; s.used += r1; s.D += r1;
                place_kink(&s, 2, r1);
                rec(&s, 2, &loc);
            }
            #pragma omp critical
            {
                for (int a = 0; a <= ord; a++) for (int b = 0; a + b <= ord; b++) tot.acc[a][b] += loc.acc[a][b];
                tot.npts += loc.npts;
            }
        }
    }
    double t1 = 0;
#ifdef _OPENMP
    t1 = omp_get_wtime();
#endif
    char buf[128];
    printf("{\"n\": %d, \"kind\": \"%c\", \"eps\": \"%s\", \"ord\": %d, \"N\": %d, \"NL\": %d, \"npts\": %lld, \"seconds\": %.2f, \"precision\": \"binary128\", \"coef\": {",
           P_n, P_kind, epsstr, ord, P_N, P_NL, tot.npts, t1 - t0);
    int first = 1;
    for (int a = 0; a <= ord; a++) for (int b = 0; a + b <= ord; b++) {
        quadmath_snprintf(buf, sizeof buf, "%.36Qe", tot.acc[a][b]);
        printf("%s\"%d,%d\": \"%s\"", first ? "" : ", ", a, b, buf);
        first = 0;
    }
    printf("}}\n");
    return 0;
}
