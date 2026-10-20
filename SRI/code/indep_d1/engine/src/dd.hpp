// Minimal double-double arithmetic (Dekker/Knuth error-free transforms).
// Written for the LRI independent engine; ~32 significant digits.
#pragma once
#include <cmath>

struct dd {
  double hi, lo;
};
static inline dd mkdd(double h) { return dd{h, 0.0}; }
static inline dd two_sum(double a, double b) {
  double s = a + b;
  double bb = s - a;
  double e = (a - (s - bb)) + (b - bb);
  return dd{s, e};
}
static inline dd quick_two_sum(double a, double b) {
  double s = a + b;
  double e = b - (s - a);
  return dd{s, e};
}
static inline dd two_prod(double a, double b) {
  double p = a * b;
  double e = std::fma(a, b, -p);
  return dd{p, e};
}
static inline dd operator+(const dd &a, const dd &b) {
  dd s = two_sum(a.hi, b.hi);
  dd t = two_sum(a.lo, b.lo);
  s.lo += t.hi;
  s = quick_two_sum(s.hi, s.lo);
  s.lo += t.lo;
  return quick_two_sum(s.hi, s.lo);
}
static inline dd operator+(const dd &a, double b) {
  dd s = two_sum(a.hi, b);
  s.lo += a.lo;
  return quick_two_sum(s.hi, s.lo);
}
static inline dd operator-(const dd &a) { return dd{-a.hi, -a.lo}; }
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
static inline dd operator/(const dd &a, const dd &b) {
  double q1 = a.hi / b.hi;
  dd r = a - b * q1;
  double q2 = r.hi / b.hi;
  r = r - b * q2;
  double q3 = r.hi / b.hi;
  dd q = quick_two_sum(q1, q2);
  return q + q3;
}
static inline dd operator/(const dd &a, double b) { return a / mkdd(b); }
static inline dd &operator+=(dd &a, const dd &b) { a = a + b; return a; }
static inline dd &operator-=(dd &a, const dd &b) { a = a - b; return a; }
static inline dd &operator*=(dd &a, const dd &b) { a = a * b; return a; }
static inline bool operator==(const dd &a, double b) { return a.hi == b && a.lo == 0.0; }
static inline bool operator!=(const dd &a, double b) { return !(a == b); }

// inverse factorials 1/k! in double-double (k=0..12), computed once
static inline const dd *dd_inv_fact() {
  static dd tab[13];
  static bool init = false;
  if (!init) {
    dd f = mkdd(1.0);
    tab[0] = f;
    for (int k = 1; k < 13; k++) {
      f = f / (double)k;
      tab[k] = f;
    }
    init = true;
  }
  return tab;
}
static inline dd dd_exp(const dd &a) {
  const dd ln2{6.931471805599452862e-01, 2.319046813846299558e-17};
  const dd *ifa = dd_inv_fact();
  double m = std::floor(a.hi / ln2.hi + 0.5);
  dd r = a - ln2 * m;
  r.hi = std::ldexp(r.hi, -9);
  r.lo = std::ldexp(r.lo, -9);
  // expm1(r) by Taylor (|r| < 7e-4): 9 terms give < 1e-33 relative
  dd p = r, s = r;
  for (int i = 2; i <= 9; i++) {
    p = p * r;
    s = s + p * ifa[i];
  }
  for (int i = 0; i < 9; i++) s = s * 2.0 + s * s;  // (1+s)^2-1
  s = s + 1.0;
  return dd{std::ldexp(s.hi, (int)m), std::ldexp(s.lo, (int)m)};
}
static inline dd dd_log(const dd &a) {
  // one Newton step from the double log (quadratic convergence: 1e-16 -> 1e-32)
  dd y = mkdd(std::log(a.hi));
  y = y + a * dd_exp(-y) - mkdd(1.0);
  return y;
}

template <class T> struct NT;
template <> struct NT<double> {
  static inline double c(double x) { return x; }
  static inline double d(double x) { return x; }
  static inline double lg(double x) { return std::log(x); }
};
template <> struct NT<dd> {
  static inline dd c(double x) { return mkdd(x); }
  static inline double d(const dd &x) { return x.hi + x.lo; }
  static inline dd lg(const dd &x) { return dd_log(x); }
};
