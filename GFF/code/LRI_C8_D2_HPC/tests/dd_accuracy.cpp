// R3b `dd` (PLAN A-FLAG-4): accuracy of the double-double arithmetic of src/numerics/dd.hpp against an independent
// 120-digit reference (boost cpp_dec_float<120>; every double and long double converts to it exactly up to 1e-119).
// Compiled with the dd profile's own options (NX_FLAGS_dd = -mavx2 -mfma, the required flags with -ffp-contract=off);
// tests/dd_accuracy.py builds and runs it on a cluster node (never the Mac: x86-64 long double and the fma of the build).
//
//   dd_accuracy N SEED THREADS     one JSON object on stdout; exit 1 when a measured error exceeds its bound
//
// Errors are relative, in units of u^2 = 2^-106 (about 1.23e-32), maximum over the set (and the 0.999 quantile):
//   exp_*         exp_dd(a) against exp(a) of the exact dd argument: uniform |a| <= 300 (the tier's range), -650..700,
//                 small |a| (1e-30 .. 1e-3, log-uniform), a next to (k + 1/2) ln2 and k ln2 (the reduction's edges),
//                 and special values. Bound 40 u^2 (docs/NUMERICS.md, "R3b").
//   arg_direct    the tier's xs_j with shift = 0: exp_dd(from_ld(lx)) against exp(lx), lx a long double in [-300, 0]:
//                 the argument is exact, bound 40 u^2.
//   arg_shifted   the tier's xs_j with shift != 0: c = div_d(from_ld(shift), L), a = add(from_ld(lx), -c), against
//                 exp(lx - shift/L) of the exact long doubles (shift a long-double sum of L of them, |lx - shift/L| <=
//                 300). Bound 40 + 3|a| + 5|c| (u^2 units): the argument's own rounding; the part from c is common to
//                 every j of a point and cancels in the tier's value up to a relative L x 4|c| u^2 (doc).
//   add, add_d, mul, mul_d, div, div_d   random operands (both signs; add with cancellations down to 2^-100): bounds
//                 3, 2, 6, 2, 11, 4 u^2.
//   exact_ops     two_sum, fast_two_sum, two_prod, from_ld: exact (error 0 up to the 120-digit reference's own conversion
//                 of doubles with longer exact expansions: bound 1e-60 u^2), to_ld: <= 2^-64 relative.
//   sum_positive  the kernel's compensated segment sum on n positive dd addends (n = 1 .. 4099, three magnitude
//                 profiles, start value 0 or a positive dd): bound (7.5 n + 1) u^2 for n < 8, (7.5 n + 29) u^2 from n = 8
//                 (the 4-lane path).
#define C8_NUMERICS
#define C8_NUMERICS_DD
#define C8_NX_STAGE 1
#include "../src/numerics/dd.hpp"
#undef C8_NX_STAGE
#include <algorithm>
#include <cstdio>
#include <iostream>
#include <random>
#include <sstream>
#include <vector>
#include <boost/multiprecision/cpp_dec_float.hpp>
#include <omp.h>
using R = boost::multiprecision::number<boost::multiprecision::cpp_dec_float<120>>;
using nx::dd::DW;
namespace D = nx::dd;
static const R U2 = boost::multiprecision::ldexp(R(1), -106);
static R val(DW x) { return R(x.h) + R(x.l); }
static double rel_u2(DW got, const R& ref) {
    if (ref == 0) return val(got) == 0 ? 0.0 : 1e300;
    return double(abs(val(got) - ref) / abs(ref) / U2);
}
struct Acc {
    std::vector<double> e; double bound_max = 0; long long over = 0;   // over: points above their own bound
    void add(double x, double bound) { e.push_back(x); if (x > bound) ++over; bound_max = std::max(bound_max, bound); }
};
struct Gen {
    std::mt19937_64 r;
    explicit Gen(uint64_t s) : r(s) {}
    double uni(double a, double b) { return a + (b - a) * (double(r() >> 11) * 0x1p-53); }
    // a normalized dd near x: x plus a random tail of up to half an ulp
    DW tail(double h) { if (h == 0) return {0, 0}; const double ulp = std::nextafter(std::fabs(h), INFINITY) - std::fabs(h); return D::fast_two_sum(h, ulp * uni(-0.5, 0.5)); }
    double logu(double lo10, double hi10) { return std::pow(10.0, uni(lo10, hi10)); }
    double sign() { return (r() & 1) ? 1.0 : -1.0; }
    long double ld_uniform(long double a, long double b) { return a + (b - a) * ((long double)(r()) * 0x1p-64L); }
};
static void report(std::ostream& o, const char* name, Acc& a, bool& ok, bool& first) {
    auto& e = a.e; std::sort(e.begin(), e.end());
    const double mx = e.empty() ? 0 : e.back(), q = e.empty() ? 0 : e[size_t(0.999 * (e.size() - 1))];
    const bool pass = a.over == 0; ok = ok && pass;
    char buf[400]; std::snprintf(buf, sizeof buf, "%s\"%s\":{\"n\":%zu,\"max_u2\":%.4g,\"q999_u2\":%.4g,\"bound_u2_max\":%.4g,\"over_bound\":%lld,\"passed\":%s}",
                                 first ? "" : ",", name, e.size(), mx, q, a.bound_max, a.over, pass ? "true" : "false");
    o << buf; first = false;
}
int main(int argc, char** argv) {
    if (argc != 4) { std::cerr << "dd_accuracy N SEED THREADS\n"; return 2; }
    const long long N = std::stoll(argv[1]); const uint64_t seed = std::stoull(argv[2]); const int threads = std::stoi(argv[3]);
    const char* names[] = {"exp_uniform_300", "exp_wide_m650_700", "exp_small", "exp_edges", "exp_special", "arg_direct", "arg_shifted",
                           "add", "add_d", "mul", "mul_d", "div", "div_d", "exact_ops", "sum_positive"};
    constexpr int NT = sizeof names / sizeof *names;
    std::vector<Acc> all(NT);
    const double LN2 = 0.6931471805599453;
    #pragma omp parallel num_threads(threads)
    {
        std::vector<Acc> acc(NT);
        #pragma omp for schedule(dynamic, 256)
        for (long long i = 0; i < N; ++i) {
            Gen G(seed * 0x9e3779b97f4a7c15ULL + uint64_t(i) * 0xbf58476d1ce4e5b9ULL + 1);
            auto ex = [&](int k, DW a, double bound) { acc[k].add(rel_u2(D::exp_dd(a), exp(val(a))), bound); };
            ex(0, G.tail(G.uni(-300, 300)), 40);
            ex(1, G.tail(G.uni(-650, 700)), 40);
            ex(2, G.tail(G.sign() * G.logu(-30, -3)), 40);
            {   const double k = std::floor(G.uni(-433, 433)); const double off = G.sign() * G.logu(-17, -9);
                ex(3, G.tail((k + 0.5) * LN2 + off), 40); ex(3, G.tail(k * LN2 + off), 40); }
            if (i == 0) {
                for (double s : {0.0, 0x1p-1074, -0x1p-1074, 1e-300, -1e-300, 300.0, -300.0, 700.0, -650.0, LN2 / 2, -LN2 / 2, LN2, -LN2})
                    ex(4, DW{s, 0}, 40);
            }
            {   const long double lx = G.ld_uniform(-300, 0);   // shift = 0: the argument is exact
                acc[5].add(rel_u2(D::exp_dd(D::from_ld(lx)), exp(R(lx))), 40); }
            {   const int L = 2 + int(G.r() % 7); long double lx[8], shift = 0;
                for (int j = 0; j < L; ++j) { lx[j] = G.ld_uniform(-900, 0); shift += lx[j]; }
                const long double x = G.ld_uniform(-900, 0);
                if (std::fabs((double)(x - shift / L)) <= 300) {
                    const DW c = D::div_d(D::from_ld(shift), double(L)), a = D::add(D::from_ld(x), D::neg(c));
                    const R ar = R(x) - R(shift) / L;
                    acc[6].add(rel_u2(D::exp_dd(a), exp(ar)), 40 + 3 * double(abs(ar)) + 5 * std::fabs(double(shift / L)));
                }
            }
            {   const DW x = G.tail(G.sign() * G.logu(-30, 30));
                DW y = G.tail(G.sign() * G.logu(-30, 30));
                if (G.r() % 4 == 0) y = G.tail(-x.h * (1 + G.sign() * G.logu(-16, -1)));      // cancellation
                if (G.r() % 8 == 0) y = D::fast_two_sum(-x.h, -x.l * G.uni(0, 2));               // massive cancellation
                acc[7].add(rel_u2(D::add(x, y), val(x) + val(y)), 3);
                const double d = G.sign() * G.logu(-30, 30);
                acc[8].add(rel_u2(D::add_d(x, d), val(x) + R(d)), 2);
                acc[9].add(rel_u2(D::mul(x, y), val(x) * val(y)), 6);
                acc[10].add(rel_u2(D::mul_d(x, d), val(x) * R(d)), 2);
                if (val(y) != 0) acc[11].add(rel_u2(D::div(x, y), val(x) / val(y)), 11);
                acc[12].add(rel_u2(D::div_d(x, d), val(x) / R(d)), 4);
                const double a = G.sign() * G.logu(-30, 30), b = G.sign() * G.logu(-30, 30);
                const double big = std::fabs(a) >= std::fabs(b) ? a : b, sml = std::fabs(a) >= std::fabs(b) ? b : a;
                double e = rel_u2(D::two_sum(a, b), R(a) + R(b)) + rel_u2(D::fast_two_sum(big, sml), R(big) + R(sml)) + rel_u2(D::two_prod(a, b), R(a) * R(b));
                const long double l = G.ld_uniform(-1e4L, 1e4L); e += rel_u2(D::from_ld(l), R(l));
                const R tl = R(D::to_ld(x)), xr = val(x);
                if (xr != 0 && double(abs(tl - xr) / abs(xr)) > std::ldexp(1.0, -64)) e += 1;
                acc[13].add(e, 1e-60);   // 0 up to the reference's own conversion floor (1e-119 relative = 1e-87 u^2)
            }
            if (i % 64 == 0) {
                static const int sizes[] = {1, 2, 7, 8, 9, 15, 64, 513, 4096, 4099};
                const int n = sizes[(i / 64) % 10]; const int prof = int((i / 64 / 10) % 3);
                std::vector<DW> P(n); std::vector<int> idx(n);
                R exact = 0;
                for (int k = 0; k < n; ++k) {
                    const double h = prof == 0 ? G.uni(0, 1) : (prof == 1 ? G.logu(-10, 0) : std::ldexp(G.uni(1, 2), -k % 60));
                    P[k] = G.tail(h); idx[k] = n - 1 - k; exact += val(P[k]);
                }
                double hi = 0, lo = 0;
                if (G.r() & 1) { const DW s0 = G.tail(G.uni(0, 10)); hi = s0.h; lo = s0.l; exact += val(s0); }
                D::sum_positive(hi, lo, P.data(), idx.data(), 0, n);
                acc[14].add(rel_u2(DW{hi, lo}, exact), 7.5 * n + (n < 8 ? 1 : 29));
            }
        }
        #pragma omp critical
        for (int k = 0; k < NT; ++k) { all[k].e.insert(all[k].e.end(), acc[k].e.begin(), acc[k].e.end()); all[k].over += acc[k].over; all[k].bound_max = std::max(all[k].bound_max, acc[k].bound_max); }
    }
    bool ok = true, first = true; std::ostringstream o;
    o << "{\"schema\":\"c8-d2-dd-accuracy-1\",\"N\":" << N << ",\"seed\":" << seed << ",\"u2\":\"2^-106\",\"tests\":{";
    for (int k = 0; k < NT; ++k) report(o, names[k], all[k], ok, first);
    o << "},\"params\":{"; nx::dd::params(o); o << "},\"passed\":" << (ok ? "true" : "false") << "}\n";
    std::cout << o.str();
    return ok ? 0 : 1;
}
