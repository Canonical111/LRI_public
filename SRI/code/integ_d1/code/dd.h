// Double-double real and complex arithmetic (about 32 significant digits), after Hida, Li and Bailey (QD).
// Requires a correctly rounded fma (any IEEE platform with -ffp-contract=off for the rest of the code).
#pragma once
#include <cmath>
#include <cstdio>
#include <string>
#include <type_traits>

struct dd {
    double hi, lo;
    dd() : hi(0), lo(0) {}
    dd(double h) : hi(h), lo(0) {}
    dd(double h, double l) : hi(h), lo(l) {}
};

static inline dd quick_two_sum(double a, double b) { double s = a + b; return dd(s, b - (s - a)); }
static inline dd two_sum(double a, double b) {
    double s = a + b, bb = s - a;
    return dd(s, (a - (s - bb)) + (b - bb));
}
static inline dd two_prod(double a, double b) { double p = a * b; return dd(p, std::fma(a, b, -p)); }

static inline dd operator+(const dd &a, const dd &b) {
    dd s = two_sum(a.hi, b.hi), t = two_sum(a.lo, b.lo);
    s.lo += t.hi; s = quick_two_sum(s.hi, s.lo);
    s.lo += t.lo; return quick_two_sum(s.hi, s.lo);
}
static inline dd operator-(const dd &a) { return dd(-a.hi, -a.lo); }
static inline dd operator-(const dd &a, const dd &b) { return a + (-b); }
static inline dd operator*(const dd &a, const dd &b) {
    dd p = two_prod(a.hi, b.hi);
    p.lo += a.hi * b.lo + a.lo * b.hi;
    return quick_two_sum(p.hi, p.lo);
}
static inline dd operator*(const dd &a, double b) {
    dd p = two_prod(a.hi, b);
    p.lo += a.lo * b;
    return quick_two_sum(p.hi, p.lo);
}
static inline dd operator*(double b, const dd &a) { return a * b; }
static inline dd operator/(const dd &a, const dd &b) {
    double q1 = a.hi / b.hi;
    dd r = a - b * q1;
    double q2 = r.hi / b.hi;
    r = r - b * q2;
    double q3 = r.hi / b.hi;
    dd q = quick_two_sum(q1, q2);
    return q + dd(q3);
}
static inline dd operator/(const dd &a, double b) { return a / dd(b); }
static inline dd &operator+=(dd &a, const dd &b) { a = a + b; return a; }
static inline dd &operator-=(dd &a, const dd &b) { a = a - b; return a; }
static inline dd &operator*=(dd &a, const dd &b) { a = a * b; return a; }
static inline dd &operator/=(dd &a, const dd &b) { a = a / b; return a; }
static inline bool operator<(const dd &a, const dd &b) { return a.hi < b.hi || (a.hi == b.hi && a.lo < b.lo); }
static inline bool operator>(const dd &a, const dd &b) { return b < a; }
static inline dd ldexp(const dd &a, int e) { return dd(std::ldexp(a.hi, e), std::ldexp(a.lo, e)); }
static inline double to_double(const dd &a) { return a.hi + a.lo; }
static inline dd fabs(const dd &a) { return a.hi < 0 ? -a : a; }
static inline dd sqr(const dd &a) { return a * a; }

static const dd DD_LOG2(6.931471805599452862e-01, 2.319046813846299558e-17);
static const dd DD_PI(3.141592653589793116e+00, 1.224646799147353207e-16);
static const dd DD_PI2(1.570796326794896558e+00, 6.123233995736766036e-17);

static inline dd sqrt(const dd &a) {
    if (a.hi <= 0) return dd(0);
    double x = 1.0 / std::sqrt(a.hi);
    double ax = a.hi * x;
    dd t = a - two_prod(ax, ax);
    return two_sum(ax, t.hi * x * 0.5);
}

// e^x - 1 for |x| <= ~0.35 (Taylor of x/2^10, then squaring identity s -> s(2 + s))
static inline dd expm1_small(const dd &x) {
    const int SQ = 10;
    dd r = ldexp(x, -SQ);
    // Taylor for e^r - 1, |r| < 3.5e-4
    dd s = r, term = r;
    for (int k = 2; k <= 12; ++k) {
        term = term * r / double(k);
        s += term;
        if (std::fabs(term.hi) < 1e-36 * std::fabs(s.hi)) break;
    }
    for (int i = 0; i < SQ; ++i) s = s * (s + 2.0);
    return s;
}
struct DDExpTable {
    dd e[47];   // e^{j/64}, j = -23..23
    DDExpTable() { for (int j = -23; j <= 23; ++j) { dd x = dd(double(j)) / 64.0; e[j + 23] = expm1_small(x) + 1.0; } }
};
static const DDExpTable DDE;
static inline dd exp(const dd &x) {
    if (x.hi > 709.0) return dd(INFINITY);
    if (x.hi < -745.0) return dd(0);
    double k = std::nearbyint(x.hi / DD_LOG2.hi);
    dd r = x - DD_LOG2 * k;
    double j = std::nearbyint(r.hi * 64.0);
    r = r - dd(j / 64.0);
    // e^r - 1 for |r| <= 1/128 + tiny: Horner with 1/n!, n <= 12
    static const double ifd[13] = {1.0, 1.0, 0.5, 1.0 / 6, 1.0 / 24, 1.0 / 120, 1.0 / 720, 1.0 / 5040, 1.0 / 40320,
                                   1.0 / 362880, 1.0 / 3628800, 1.0 / 39916800, 1.0 / 479001600};
    // exact dd inverse factorials for the low orders that need full precision
    static const dd if2(0.5), if3(1.666666666666666574e-01, 9.251858538542970658e-18), if4(4.166666666666666435e-02, 2.312964634635742664e-18),
        if5(8.333333333333333218e-03, 1.156482317317871332e-19), if6(1.388888888888888942e-03, -5.300543954373577209e-20),
        if7(1.984126984126984125e-04, 1.720955829342070024e-22), if8(2.480158730158730157e-05, 2.151194786677587530e-23);
    dd p = dd(ifd[12]);
    p = dd(ifd[11]) + r * p; p = dd(ifd[10]) + r * p; p = dd(ifd[9]) + r * p;
    p = if8 + r * p; p = if7 + r * p; p = if6 + r * p; p = if5 + r * p; p = if4 + r * p; p = if3 + r * p; p = if2 + r * p;
    p = dd(1.0) + r * p;
    dd em1 = r * p;                       // e^r - 1
    int jj = int(j);
    if (jj < -23 || jj > 23) { dd s = expm1_small(x - DD_LOG2 * k) + 1.0; return ldexp(s, int(k)); }
    dd s = DDE.e[jj + 23] + DDE.e[jj + 23] * em1;
    return ldexp(s, int(k));
}
static inline dd expm1(const dd &x) {
    if (std::fabs(x.hi) < 0.3) return expm1_small(x);
    return exp(x) - 1.0;
}
static inline dd log(const dd &a) {
    // one Newton step on exp: y <- y + a e^{-y} - 1
    double y0 = std::log(a.hi);
    dd y(y0);
    y = y + a * exp(-y) - 1.0;
    return y;
}
// log(1+x): series in u = x/(2+x) for small |x|
static inline dd log1p(const dd &x) {
    if (std::fabs(x.hi) > 0.25) return log(x + 1.0);
    dd u = x / (x + 2.0), u2 = u * u, term = u, s = u;
    for (int k = 3; k < 80; k += 2) {
        term = term * u2;
        dd t = term / double(k);
        s += t;
        if (std::fabs(t.hi) < 1e-35 * std::fabs(s.hi)) break;
    }
    return s * 2.0;
}
// sin and cos for |r| <= pi/4 (Taylor), used to build the table
static inline void sincos_taylor(const dd &r, dd &s, dd &c) {
    dd r2 = r * r, term = r, sum = r;
    for (int k = 1; k < 30; ++k) {
        term = -term * r2 / double((2 * k) * (2 * k + 1));
        sum += term;
        if (std::fabs(term.hi) < 1e-36) break;
    }
    s = sum;
    term = dd(1.0); dd cs = term;
    for (int k = 1; k < 30; ++k) {
        term = -term * r2 / double((2 * k - 1) * (2 * k));
        cs += term;
        if (std::fabs(term.hi) < 1e-36) break;
    }
    c = cs;
}
// tables: inverse factorials, sin/cos(j pi/32), j = 0..8
struct DDTables {
    dd invfact[32]; dd sj[9], cj[9];
    DDTables() {
        invfact[0] = dd(1.0);
        for (int i = 1; i < 32; ++i) invfact[i] = invfact[i - 1] / double(i);
        const dd pi(3.141592653589793116e+00, 1.224646799147353207e-16);
        for (int j = 0; j <= 8; ++j) sincos_taylor(pi * double(j) / 32.0, sj[j], cj[j]);
    }
};
static const DDTables DDT;
// |r| <= pi/64 ~ 0.049: sin to r^17, cos to r^18 (error < 1e-36)
static inline void sincos_small(const dd &r, dd &s, dd &c) {
    dd r2 = r * r;
    // Horner for sin: r (1 - r2/3! + r2^2/5! - ...)
    dd hs = DDT.invfact[17];
    for (int k = 15; k >= 1; k -= 2) hs = DDT.invfact[k] - r2 * hs;
    // signs: the recursion above alternates correctly because each step multiplies by -r2
    s = r * hs;
    dd hc = DDT.invfact[18];
    for (int k = 16; k >= 0; k -= 2) hc = DDT.invfact[k] - r2 * hc;
    c = hc;
}
static inline void sincos(const dd &x, dd &s, dd &c) {
    // x = k pi/2 + j pi/32 + r
    double k = std::nearbyint(x.hi / DD_PI2.hi);
    dd r = x - DD_PI2 * k;
    const dd pi32 = ldexp(DD_PI, -5);
    double j = std::nearbyint(r.hi / pi32.hi);
    r = r - pi32 * j;
    dd ss, cc;
    sincos_small(r, ss, cc);
    int jj = int(j);
    dd sa, ca;
    if (jj >= 0) { sa = DDT.sj[jj]; ca = DDT.cj[jj]; } else { sa = -DDT.sj[-jj]; ca = DDT.cj[-jj]; }
    dd s1 = sa * cc + ca * ss, c1 = ca * cc - sa * ss;
    long kk = ((long)k % 4 + 4) % 4;
    if (kk == 0) { s = s1; c = c1; }
    else if (kk == 1) { s = c1; c = -s1; }
    else if (kk == 2) { s = -s1; c = -c1; }
    else { s = -c1; c = s1; }
}
static inline dd atan2(const dd &y, const dd &x) {
    double z0 = std::atan2(y.hi, x.hi);
    dd z(z0), s, c;
    sincos(z, s, c);
    // Newton: z <- z + (y c - x s)/(x c + y s)
    dd num = y * c - x * s, den = x * c + y * s;
    return z + num / den;
}
static inline std::string str(const dd &a) {
    char buf[96];
    // print hi + lo with enough digits: split into a decimal string via repeated extraction
    snprintf(buf, sizeof buf, "%.17e %.17e", a.hi, a.lo);
    return std::string(buf);
}

// ------------------------------------------------------------------ complex
template <typename T> struct cx {
    T re, im;
    cx() : re(0.0), im(0.0) {}
    cx(const T &r) : re(r), im(0.0) {}
    cx(const T &r, const T &i) : re(r), im(i) {}
    template <typename U = T, typename = std::enable_if_t<!std::is_same<U, double>::value>> cx(double r) : re(r), im(0.0) {}
};
template <typename T> static inline cx<T> operator+(const cx<T> &a, const cx<T> &b) { return cx<T>(a.re + b.re, a.im + b.im); }
template <typename T> static inline cx<T> operator-(const cx<T> &a, const cx<T> &b) { return cx<T>(a.re - b.re, a.im - b.im); }
template <typename T> static inline cx<T> operator-(const cx<T> &a) { return cx<T>(-a.re, -a.im); }
template <typename T> static inline cx<T> operator*(const cx<T> &a, const cx<T> &b) {
    return cx<T>(a.re * b.re - a.im * b.im, a.re * b.im + a.im * b.re);
}
template <typename T> static inline cx<T> operator*(const cx<T> &a, const T &b) { return cx<T>(a.re * b, a.im * b); }
template <typename T> static inline cx<T> operator*(const T &b, const cx<T> &a) { return cx<T>(a.re * b, a.im * b); }
template <typename T, typename = std::enable_if_t<!std::is_same<T, double>::value>> static inline cx<T> operator*(const cx<T> &a, double b) { return cx<T>(a.re * b, a.im * b); }
template <typename T> static inline cx<T> operator/(const cx<T> &a, const cx<T> &b) {
    T d = b.re * b.re + b.im * b.im;
    return cx<T>((a.re * b.re + a.im * b.im) / d, (a.im * b.re - a.re * b.im) / d);
}
template <typename T> static inline cx<T> operator/(const cx<T> &a, const T &b) { return cx<T>(a.re / b, a.im / b); }
template <typename T> static inline cx<T> &operator+=(cx<T> &a, const cx<T> &b) { a = a + b; return a; }
template <typename T> static inline cx<T> &operator-=(cx<T> &a, const cx<T> &b) { a = a - b; return a; }
template <typename T> static inline cx<T> &operator*=(cx<T> &a, const cx<T> &b) { a = a * b; return a; }
template <typename T> static inline cx<T> conj(const cx<T> &a) { return cx<T>(a.re, -a.im); }
template <typename T> static inline T abs2(const cx<T> &a) { return a.re * a.re + a.im * a.im; }

// real-type helpers for double
static inline double to_double(double a) { return a; }
static inline void sincos(double x, double &s, double &c) { s = std::sin(x); c = std::cos(x); }

template <typename T> static inline cx<T> cexp(const cx<T> &z) {
    T e = exp(z.re), s, c;
    sincos(z.im, s, c);
    return cx<T>(e * c, e * s);
}
template <typename T> static inline cx<T> cxlog(const cx<T> &z) {
    T r2 = z.re * z.re + z.im * z.im;
    return cx<T>(log(r2) * 0.5, atan2(z.im, z.re));
}
// log(1+z)/z, accurate for small |z|
template <typename T> static inline cx<T> clog1p_over(const cx<T> &z) {
    double az = std::sqrt(to_double(abs2(z)));
    if (az > 0.01) return cxlog(z + cx<T>(T(1.0))) / z;
    // 2 atanh(u)/z, u = z/(2+z): 2/(2+z) * sum u^{2k}/(2k+1)
    cx<T> u = z / (z + cx<T>(T(2.0))), u2 = u * u, term(T(1.0)), s(T(1.0));
    for (int k = 1; k < 80; ++k) {
        term = term * u2;
        cx<T> t = term / T(double(2 * k + 1));
        s += t;
        if (to_double(abs2(t)) < 1e-72 * to_double(abs2(s))) break;
    }
    return s * T(2.0) / (z + cx<T>(T(2.0)));
}
template <typename T> static inline cx<T> clog1p(const cx<T> &z) { return clog1p_over(z) * z; }
// (e^z - 1)/z, accurate for small |z|
template <typename T> static inline cx<T> cexpm1_over(const cx<T> &z) {
    double az = std::sqrt(to_double(abs2(z)));
    if (az > 0.01) return (cexp(z) - cx<T>(T(1.0))) / z;
    cx<T> term(T(1.0)), s(T(1.0));
    for (int k = 2; k < 60; ++k) {
        term = term * z / T(double(k));
        s += term;
        if (to_double(abs2(term)) < 1e-72 * to_double(abs2(s))) break;
    }
    return s;
}
