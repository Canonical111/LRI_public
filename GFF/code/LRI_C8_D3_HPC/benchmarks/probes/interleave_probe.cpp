// P2 fallback probe (PLAN "Performance plan", P2; #6 go/no-go): is the long-double first pass latency-bound?
// Port to C8(3) of C62d's benchmarks/probes/interleave_probe.cpp (LRI_C8_D2_HPC@2083d84, sha256 0020e521...); the d=3
// change: each term's denominator is U*sqrtl(U) (kernel.hpp calculate_products), so the lock-step term loop computes
// den = U*sqrtl(U) per point, in the kernel's order. Not part of the worker: tools/benchmark.py --interleave-probe
// builds bin/diag/c8d3_interleave_probe from this file and the UNCHANGED src/kernel.hpp (only read) with the worker's gmp
// command. For one graph it draws NPOINTS uniform points, maps them to log-coordinates exactly as kernel.hpp's
// sample() does for layout 0, keeps the "moderate" ones (those evaluate() sends to calculate_products), and times
//   width 1: kernel.hpp's own calculate_products, point after point (the worker's first pass);
//   width W = 2, 4: products_lockstep<W> below, W independent points in lock-step, every loop of calculate_products
//            (exponentials, products, ordered-prefix sums, numerators, terms) advancing all W points per step, each
//            point's operation sequence and addition order unchanged (R6's construction).
// The lock-step results must equal the sequential ones bit for bit ("identical"); the speedup of width W is the
// sequential time over the lock-step time for the same points. Single thread; the caller pins it to one core.
//   c8d3_interleave_probe GRAPH_FILE RATE NPOINTS SEED REPEATS   -> one JSON object on stdout
#include "../../src/kernel.hpp"
#include <chrono>
#include <cstdio>
#include <cstring>
#include <iostream>
#include <random>
#include <string>
#include <vector>

using Point = std::array<ld, EMAX>;

// sample()'s map from uniforms to log-coordinates (layout 0): the same choice walk and logarithms.
static void log_coordinates(const Graph& g, const ld* uu, Point& lx) {
    std::array<int, EMAX> order{};
    std::array<ld, EMAX> lt{};
    int E = g.E, S = (1 << E) - 1;
    for (int pos = 0; pos < E; ++pos) {
        ld u = uu[2 * pos] * g.choice_total[S];
        int pick = -1;
        for (int j = 0; j < E; ++j)
            if (S >> j & 1) { u -= g.dp[S ^ (1 << j)]; if (u <= 0) { pick = j; break; } }
        if (pick < 0) pick = 31 - __builtin_clz(S);
        order[pos] = pick; S ^= 1 << pick;
        if (S) lt[pos] = logl(uu[2 * pos + 1]) / g.alpha[S];
    }
    ld cur = 0;
    for (int j = 0; j < E; ++j) { lx[order[j]] = cur; if (j < E - 1) cur += lt[j]; }
}

// evaluate()'s shift and "moderate" decision.
static bool moderate_shift(const Graph& g, const Point& lx, ld& shift) {
    shift = 0; bool direct = true;
    for (int j = 0; j < g.E; ++j) if (lx[j] < -600 || lx[j] > 0) direct = false;
    if (!direct) {
        shift = -std::numeric_limits<ld>::infinity();
        for (auto mask : g.masks) { ld v = 0; while (mask) { int j = __builtin_ctz(mask); mask &= mask - 1; v += lx[j]; } shift = std::max(shift, v); }
    }
    for (int j = 0; j < g.E; ++j) if (fabsl(lx[j] - shift / g.L) > 500) return false;
    return true;
}

// calculate_products for W points in lock-step; each point's operations in the original order.
template <int W>
static void products_lockstep(const Graph& g, const Point* const* lx, const ld* shift, Scratch* const* s, std::pair<ld, ld>* out) {
    for (int w = 0; w < W; ++w) { s[w]->S = 0; s[w]->products[0] = 1; s[w]->sums[0] = 0; }
    for (int j = 0; j < g.E; ++j)
        for (int w = 0; w < W; ++w) {
            Scratch& q = *s[w]; const ld* l = lx[w]->data();
            q.x[j] = expl(l[j]); q.S += q.x[j]; q.xs[j] = shift[w] == 0 ? q.x[j] : expl(l[j] - shift[w] / g.L);
        }
    for (size_t j = 0; j < g.products.size(); ++j) {
        auto o = g.products[j];
        for (int w = 0; w < W; ++w) s[w]->products[j + 1] = s[w]->products[o.first] * s[w]->xs[o.second];
    }
    for (size_t j = 0; j < g.segments.size(); ++j) {
        auto a = g.segments[j]; ld v[W];
        for (int w = 0; w < W; ++w) v[w] = s[w]->sums[a.parent];
        for (int k = a.begin; k < a.end; ++k) { int id = g.addends[k]; for (int w = 0; w < W; ++w) v[w] += s[w]->products[id]; }
        for (int w = 0; w < W; ++w) s[w]->sums[j + 1] = v[w];
    }
    for (size_t j = 0; j < g.numerators.size(); ++j) {
        ld n[W], ab[W];
        for (int w = 0; w < W; ++w) { n[w] = 0; ab[w] = 0; }
        for (auto [i, c] : g.numerators[j])
            for (int w = 0; w < W; ++w) { ld p = ld(c) * s[w]->x[i]; n[w] += p; ab[w] += absolute(p); }
        for (int w = 0; w < W; ++w) { s[w]->numerator[j] = n[w]; s[w]->abs_numerator[j] = ab[w]; }
    }
    ld val[W], err[W];
    for (int w = 0; w < W; ++w) { val[w] = 0; err[w] = 0; }
    for (const auto& t : g.terms)
        for (int w = 0; w < W; ++w) {
            ld U = s[w]->sums[t.denominator];
            ld den = U * sqrtl(U);
            val[w] += s[w]->numerator[t.numerator] / den; err[w] += s[w]->abs_numerator[t.numerator] / den;
        }
    for (int w = 0; w < W; ++w) out[w] = {val[w] / s[w]->S, err[w] / s[w]->S};
}

static bool same(const std::pair<ld, ld>& a, const std::pair<ld, ld>& b) {
    auto eq = [](ld x, ld y) { return (std::isnan(x) && std::isnan(y)) || (x == y && std::signbit(x) == std::signbit(y)); };
    return eq(a.first, b.first) && eq(a.second, b.second);
}

using Clock = std::chrono::steady_clock;

template <int W>
static double time_lockstep(const Graph& g, const std::vector<Point>& pts, const std::vector<ld>& sh, std::vector<std::pair<ld, ld>>& res,
                            std::vector<Scratch>& sc) {
    const size_t n = pts.size() / W * W;
    const Point* lp[W]; ld s[W]; Scratch* sp[W]; std::pair<ld, ld> out[W];
    for (int w = 0; w < W; ++w) sp[w] = &sc[w];
    auto t0 = Clock::now();
    for (size_t i = 0; i < n; i += W) {
        for (int w = 0; w < W; ++w) { lp[w] = &pts[i + w]; s[w] = sh[i + w]; }
        products_lockstep<W>(g, lp, s, sp, out);
        for (int w = 0; w < W; ++w) res[i + w] = out[w];
    }
    return std::chrono::duration<double>(Clock::now() - t0).count() / double(n ? n : 1);
}

static double median(std::vector<double> v) { std::sort(v.begin(), v.end()); return v.empty() ? 0 : v[v.size() / 2]; }

int main(int argc, char** argv) {
    try {
        if (argc != 6) { std::cerr << "usage: c8d3_interleave_probe GRAPH_FILE RATE NPOINTS SEED REPEATS\n"; return 1; }
        const std::string path = argv[1];
        const ld rate = std::stold(argv[2]);
        const long npoints = std::stol(argv[3]);
        const unsigned long long seed = std::stoull(argv[4]);
        const int repeats = std::stoi(argv[5]);
        if (!(rate > 0 && rate <= 1) || npoints < 8 || npoints > 10000000 || repeats < 1 || repeats > 100) throw std::runtime_error("bad arguments");
        Graph g = load_graph(path, rate);
        std::mt19937_64 rng(seed);
        std::vector<Point> pts; std::vector<ld> sh; long drawn = 0;
        std::array<ld, 2 * EMAX> uu{};
        while (long(pts.size()) < npoints && drawn < 100 * npoints) {
            for (auto& u : uu) u = (ld(rng() >> 11) + .5L) / ld(uint64_t(1) << 53);
            Point lx{}; log_coordinates(g, uu.data(), lx); ++drawn;
            ld shift = 0;
            if (moderate_shift(g, lx, shift)) { pts.push_back(lx); sh.push_back(shift); }
        }
        if (pts.size() < 8) throw std::runtime_error("fewer than 8 moderate points");
        const size_t n = pts.size();
        std::vector<Scratch> sc(4); for (auto& s : sc) s.resize(g);
        std::vector<std::pair<ld, ld>> ref(n), r2(n), r4(n);
        std::vector<double> t1, t2, t4;
        volatile ld sink = 0;
        for (int r = 0; r < repeats; ++r) {
            auto t0 = Clock::now();
            for (size_t i = 0; i < n; ++i) ref[i] = calculate_products(g, pts[i].data(), sh[i], sc[0]);
            t1.push_back(std::chrono::duration<double>(Clock::now() - t0).count() / double(n));
            t2.push_back(time_lockstep<2>(g, pts, sh, r2, sc));
            t4.push_back(time_lockstep<4>(g, pts, sh, r4, sc));
            sink = sink + ref[0].first + r2[0].first + r4[0].first;
        }
        size_t bad2 = 0, bad4 = 0;
        for (size_t i = 0; i < n / 2 * 2; ++i) bad2 += !same(ref[i], r2[i]);
        for (size_t i = 0; i < n / 4 * 4; ++i) bad4 += !same(ref[i], r4[i]);
        const double m1 = median(t1), m2 = median(t2), m4 = median(t4);
        std::printf("{\"schema\":\"c8-d3-interleave-probe-1\",\"graph\":%d,\"L\":%d,\"E\":%d,\"products\":%zu,\"segments\":%zu,\"addends\":%zu,"
                    "\"numerators\":%zu,\"terms\":%zu,\"points\":%zu,\"drawn\":%ld,\"moderate_fraction\":%.6f,\"repeats\":%d,"
                    "\"seconds_per_point\":{\"1\":%.6e,\"2\":%.6e,\"4\":%.6e},\"speedup\":{\"2\":%.4f,\"4\":%.4f},"
                    "\"identical\":{\"2\":%s,\"4\":%s},\"mismatches\":{\"2\":%zu,\"4\":%zu},\"all_seconds\":{\"1\":[",
                    g.id, g.L, g.E, g.products.size(), g.segments.size(), g.addends.size(), g.numerators.size(), g.terms.size(), n, drawn,
                    double(n) / double(drawn), repeats, m1, m2, m4, m1 / m2, m1 / m4, bad2 ? "false" : "true", bad4 ? "false" : "true", bad2, bad4);
        auto list = [](const std::vector<double>& v) { for (size_t i = 0; i < v.size(); ++i) std::printf("%s%.6e", i ? "," : "", v[i]); };
        list(t1); std::printf("],\"2\":["); list(t2); std::printf("],\"4\":["); list(t4);
        std::printf("]},\"compiler\":\"%s\",\"long_double_bits\":%d,\"sink_finite\":%s}\n", __VERSION__, std::numeric_limits<ld>::digits,
                    std::isfinite(ld(sink)) ? "true" : "false");
        return (bad2 || bad4) ? 3 : 0;
    } catch (const std::exception& e) { std::cerr << e.what() << '\n'; return 2; }
}
