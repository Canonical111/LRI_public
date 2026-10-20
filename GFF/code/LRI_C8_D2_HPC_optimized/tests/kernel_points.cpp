#include "../src/kernel.hpp"
#include <iostream>

using Ref = boost::multiprecision::number<boost::multiprecision::cpp_dec_float<450>>;

// Independent evaluation: exponentiate each complete monomial's logarithm.
// This bypasses the production product DAG and ordered-sum trie.
std::pair<Ref, Ref> independent(const Graph& g, const ld* lx, ld shift) {
    std::vector<Ref> x(g.E), monomials(g.masks.size());
    Ref S = 0;
    for (int j = 0; j < g.E; ++j) { x[j] = exp(Ref(lx[j])); S += x[j]; }
    for (size_t k = 0; k < g.masks.size(); ++k) {
        Ref z = -Ref(shift);
        for (int j = 0; j < g.E; ++j) if (g.masks[k] >> j & 1) z += Ref(lx[j]);
        monomials[k] = exp(z);
    }
    Ref value = 0, absolute_terms = 0;
    for (const auto& term : g.terms) {
        Ref U = 0, numerator = 0, absolute_numerator = 0;
        for (int index : term.ids) U += monomials[index];
        for (int j = 0; j < g.E; ++j) {
            Ref z = Ref(term.co[j]) * x[j];
            numerator += z;
            absolute_numerator += abs(z);
        }
        value += numerator / U;
        absolute_terms += absolute_numerator / U;
    }
    return {value / S, absolute_terms / S};
}

Graph toy(int L, bool cancellation = false) {
    // Algebra/memory fixture, deliberately not labelled as a physical graph.
    Graph g;
    g.L = L; g.E = 2 * L;
    unsigned half = (1u << L) - 1;
    g.masks = {half, half << L};
    Term a; a.ids = {0, 1}; a.co.assign(g.E, 1);
    if (cancellation) {
        a.co.assign(g.E, 0); a.co[0] = 1;
        Term b; b.ids = {0}; b.co = a.co; b.co[0] = -1;
        g.terms = {a, b};
    } else g.terms = {a};
    g.alpha.assign(1u << g.E, 1);
    g.alpha.front() = g.alpha.back() = 0;
    rates(g, .8L); prepare(g);
    return g;
}

void check_point(const Graph& g, const ld* lx, int& count, ld& largest) {
    ld shift = -std::numeric_limits<ld>::infinity();
    for (unsigned mask : g.masks) {
        ld z = 0;
        for (int j = 0; j < g.E; ++j) if (mask >> j & 1) z += lx[j];
        shift = std::max(shift, z);
    }
    auto q = calculate_shared<Q>(g, lx, shift);
    auto oldq = calculate_reference<Q>(g, lx, shift);
    if (q.first != oldq.first || q.second != oldq.second)
        throw std::runtime_error("Quad sharing changed arithmetic");
    auto m = calculate_shared<MP, false>(g, lx, shift);
    auto ref = independent(g, lx, shift);
    Ref observed(m.first.str(430, std::ios_base::scientific));
    Ref error = abs(Ref(observed - ref.first)) / (1 + ref.second);
    if (error > Ref("1e-280")) throw std::runtime_error("450-digit point comparison failed");
    largest = std::max(largest, error.convert_to<ld>());
    ++count;
}

void check_sampling() {
    for (int layout = 0; layout < 3; ++layout) for (int L : {2, 8}) {
        auto g = toy(L);
        Scratch scratch; scratch.resize(g);
        std::array<ld, 32> u{};
        for (int j = 0; j < 32; ++j) u[j] = .03L + (j + 1) * .027L;
        std::array<ld, 7> logs{};
        for (int j = 1; j < 7; ++j) logs[j] = .001L / j;
        int level = 0, K = 8 - L;
        auto values = sample(g, u.data(), K, logs, level, layout, scratch);
        if (!std::isfinite(values[0]) || values[0] == 0)
            throw std::runtime_error("Invalid synthetic sample");
        // Independent truncated polynomial exponential, including the z^6 term.
        Ref S = 0, sumlog = 0;
        for (int j = 0; j < g.E; ++j) { S += exp(Ref(scratch.lx[j])); sumlog += Ref(scratch.lx[j]); }
        Ref h = sumlog / 4 - Ref(g.L) / 2 * log(S);
        std::array<Ref, 7> polynomial{}; polynomial[0] = 1;
        for (int j = 1; j <= K; ++j) {
            Ref a = Ref(logs[j]) + (j == 1 ? h : Ref(0));
            std::array<Ref, 7> factor{}; factor[0] = 1;
            Ref current = 1;
            for (int k = 1; k * j <= K; ++k) { current *= a / k; factor[k * j] = current; }
            std::array<Ref, 7> next{};
            for (int r = 0; r <= K; ++r) for (int q = 0; q <= K - r; ++q)
                next[r + q] += polynomial[r] * factor[q];
            polynomial = next;
        }
        for (int j = 0; j <= K; ++j) {
            Ref observed = Ref(values[j]) / Ref(values[0]);
            if (abs(Ref(observed - polynomial[j])) / (1 + abs(polynomial[j])) > Ref("1e-16"))
                throw std::runtime_error("Regulator Taylor recurrence failed");
        }
    }
}

int main(int argc, char** argv) {
    try {
        int count = 0, physical_graphs = 0;
        ld largest = 0;
        auto g = toy(8);
        for (int k = 0; k < 4; ++k) {
            std::array<ld, 16> lx{};
            for (int j = 0; j < 16; ++j) lx[j] = -(j + 1) / 17.L - (j < 8 ? k * 180.L : 0);
            check_point(g, lx.data(), count, largest);
        }
        auto cancelled = toy(8, true); cancelled.Z = 1;
        std::array<ld, 16> lx{};
        for (int j = 8; j < 16; ++j) lx[j] = -50;
        Scratch scratch; scratch.resize(cancelled);
        auto value = evaluate(cancelled, lx.data(), 0, scratch);
        auto reference = independent(cancelled, lx.data(), 0);
        if (value.level != 2 || value.y == 0 ||
            abs(Ref(Ref(value.y) - reference.first)) / abs(reference.first) > Ref("1e-17"))
            throw std::runtime_error("Severe cancellation promotion failed");
        check_point(cancelled, lx.data(), count, largest);
        check_sampling();
        if (argc == 2) {
            std::ifstream list(argv[1]);
            if (!list) throw std::runtime_error("Cannot read graph list");
            std::string path;
            while (list >> path) {
                auto graph = load_graph(path, .8L);
                for (int k = 0; k < 4; ++k) {
                    std::array<ld, 16> point{};
                    for (int j = 0; j < graph.E; ++j)
                        point[j] = logl((3 + (j * 11 + graph.id) % 29) / 32.L) - (j < graph.L ? k * 180.L : 0);
                    check_point(graph, point.data(), count, largest);
                }
                ++physical_graphs;
            }
        } else if (argc != 1) throw std::runtime_error("Usage: kernel_points [graph_list]");
        std::cout << "{\"status\":\"passed\",\"point_checks\":" << count
                  << ",\"physical_graphs\":" << physical_graphs
                  << ",\"synthetic_sampling_checks\":6,\"cancellation_promotion\":2,\"backend\":\""
                  << mp_backend << "\",\"reference_digits\":450,\"max_scaled_error\":\""
                  << std::setprecision(21) << largest << "\"}\n";
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n'; return 2;
    }
}
