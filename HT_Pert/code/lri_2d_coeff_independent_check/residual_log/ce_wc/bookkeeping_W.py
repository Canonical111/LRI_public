#!/usr/bin/env python3
"""
Bookkeeping for scheme W / W+V (WINDOW_SPEC.md): which auxiliary channels (z, order, particle cap), which entries
h^(k)_{z'z} of the zero-mode window and which orders of c_1, c_2 can enter the main channels through eps^8.

Model: an RS term is a path of insertions separated by resolvents.  States are coarse-grained to nodes (P, N)
(particle number, level; N = 0 <=> pure zero-mode state |P>).  One insertion of order 1 (V) moves
    P -> P + dP, dP in {0, +-2, +-4},  with dP = -4 => N' <= N (four annihilations) and dP = +4 => N' >= N;
insertions of order k >= 2 move at most as far as k order-1 hops (r M, D^M, D^V, D^zm,(k) with |dz| <= 4k).
Degenerate nodes (partner blocks, and the reference block of the even descendants) carry the resolvent
G = O(1/eps): each visit refunds one order (-1); an insertion between two degenerate nodes costs >= 2 (W_1 does
not couple different blocks, and inside a block it is part of G).  Partner nodes:
    zero-mode channel z >= 5:   (z - 2N, N), N = 2, 4, ...;
    descendant chi_aa (odd):    (1 + 4j, 2a - 2j), j = 1..a;   descendant (L Lbar)^a phi^2:  (2, 2a) [reference
    block], (2 + 4j, 2a - 2j).
Minimal effective orders d(u -> v) by Bellman-Ford (no negative cycles: every refund needs >= 2 orders).
D^zm,(k) acts on s = (P_s, N_s >= 2) with z_s in [P_s - N_s, P_s - 1] and lands on s' = (P_s + dz, N_s); it is
needed iff d(start -> s) + k + d(s' -> end) <= order (d(start -> s) = 0 only for s = reference of a level >= 2
channel, with z_s one of the reference zero-mode numbers).
h recursion: h^(k)_{z'z} needs X^(k)_{z'z}, E_z^(j) X^(k-j)_{z'z}, and h^(m)_{z'z''} X^(k-m)_{z''z} for
|z'' - z| <= 4(k - m), |z' - z''| <= 4m (same parity); h^(1) = W_1 on P0 from the order-1 channels.
Requests are closed under these rules; each request holds at every cutoff l.  Verified by the garbage and
extension tests of ce_run.py (--garbage, --bookext).
usage: python3 bookkeeping_W.py [--V] [--desc] [--Lmax 18] [--out results/book_W.json]
"""
import argparse, json

PMAX = 48
NMAX = 20


def graph_dist(start, dnodes, refund_nodes, reverse=False, pmax=PMAX, nmax=NMAX):
    """effective-order distances from `start` (or to `start` if reverse) over nodes (P, N), P <= pmax.
    A refund is applied on arriving at a node of refund_nodes (except the start); the end node's refund is
    removed by the caller when it is the projection target."""
    INF = 10 ** 9
    nodes = [(P, N) for P in range(0, pmax + 1) for N in range(0, nmax + 1, 2)
             if (N == 0 or P >= 1) and (P - start[0]) % 2 == 0]
    dist = {u: INF for u in nodes}
    dist[start] = 0

    def edges(u):
        P, N = u
        for dP in (-4, -2, 0, 2, 4):
            P2 = P + dP
            if P2 < 0 or P2 > pmax:
                continue
            for N2 in range(0, nmax + 1, 2):
                if N2 >= 1 and P2 < 1:
                    continue
                # forward hop u -> (P2, N2); in reverse mode we enumerate predecessors (hop (P2,N2) -> u)
                a, b = ((P, N), (P2, N2)) if not reverse else ((P2, N2), (P, N))
                d = b[0] - a[0]
                if d == -4 and b[1] > a[1]:
                    continue
                if d == 4 and b[1] < a[1]:
                    continue
                if (P2, N2) == u and not (u in dnodes):
                    pass
                w = 2 if (a in dnodes and b in dnodes) else 1
                yield (P2, N2), w

    for _ in range(len(nodes)):
        changed = False
        for u in nodes:
            du = dist[u]
            if du >= INF:
                continue
            for v, w in edges(u):
                if v not in dist:
                    continue
                nd = du + w - (1 if (v in refund_nodes and v != start) else 0)
                if nd < dist[v]:
                    dist[v] = nd
                    changed = True
        if not changed:
            break
    return dist


class Channel:
    """distance tables of one channel type (start node, end node, degenerate nodes)."""
    cache = {}

    @classmethod
    def get(cls, start, end, dnodes):
        key = (start, end, tuple(sorted(dnodes)))
        c = cls.cache.get(key)
        if c is None:
            c = cls(start, end, dnodes)
            cls.cache[key] = c
        return c

    dcache = {}

    def __init__(self, start, end, dnodes):
        self.start, self.end, self.dnodes = start, end, set(dnodes)
        kf = (start, tuple(sorted(dnodes)), False)
        kb = (end, tuple(sorted(dnodes)), True)
        if kf not in Channel.dcache:
            Channel.dcache[kf] = graph_dist(start, self.dnodes, self.dnodes)
        if kb not in Channel.dcache:
            Channel.dcache[kb] = graph_dist(end, self.dnodes, self.dnodes, reverse=True)
        self.dfw = Channel.dcache[kf]
        # backward distances: refund at intermediate nodes and at the node itself (s'), not at the end
        dbw = Channel.dcache[kb]
        # graph_dist applies the refund on arrival at v (= the predecessor s' in reverse mode): that is the
        # refund of s' itself (resolvent acting on s'), correct; the end node gets none (it is the start there).
        self.dbw = dbw


def bset_zero_mode(z, nmax=NMAX):
    return {(z - 2 * N, N) for N in range(2, nmax + 1, 2) if z - 2 * N >= 1}


class Book:
    def __init__(self, withV):
        self.withV = withV
        self.h = set()
        self.c1 = set()
        self.c2 = set()
        self.chE = {}
        self.chX = {}
        self.cap = {}
        self.kmax = {}
        self.todo = []
        self.seen = set()

    def push(self, item):
        if item not in self.seen:
            self.seen.add(item)
            self.todo.append(item)

    def path(self, ch, j, zref=None):
        INF = 10 ** 8
        start, end = ch.start, ch.end
        for (Ps, Ns), d1 in ch.dfw.items():
            if Ns < 2 or d1 >= INF:
                continue
            for k in range(2, j + 1):
                for dz in range(-4 * k, 4 * k + 1, 2):
                    s2 = (Ps + dz, Ns)
                    d2 = ch.dbw.get(s2, INF)
                    if s2[0] < 1 or d2 >= INF:
                        continue
                    for zs in range(max(0, Ps - Ns), Ps):
                        zs2 = zs + dz
                        if zs2 < 0 or zs2 < s2[0] - Ns or zs2 > s2[0] - 1:
                            continue
                        c1 = d1
                        if (Ps, Ns) == start:
                            c1 = 0 if (zref is not None and zs in zref) else max(1, d1)
                        c2 = d2
                        if s2 == end:
                            c2 = 0 if (zref is not None and zs2 in zref) else max(1, d2)
                        if c1 + k + c2 <= j:
                            self.push(("h", k, zs2, zs))
        for k in range(2, j + 1):
            if k <= j - 1 or zref is not None:
                for i in range(2, k + 1):
                    self.push(("c1", i))
                    if self.withV:
                        self.push(("c2", i))

    def chan_cap(self, ch, j):
        best = max(ch.start[0], ch.end[0])
        for u, d1 in ch.dfw.items():
            d2 = ch.dbw.get(u, 10 ** 9)
            refund_double = 1 if u in ch.dnodes and u not in (ch.start, ch.end) else 0
            if d1 + d2 + refund_double <= j:
                best = max(best, u[0])
        return best

    def need_channel(self, z, j, cap):
        self.kmax[z] = max(self.kmax.get(z, 0), j)
        self.cap[z] = max(self.cap.get(z, z), cap)

    def run(self):
        while self.todo:
            it = self.todo.pop()
            t = it[0]
            if t == "main":
                _, start, j, dnodes, zref = it
                ch = Channel.get(start, start, frozenset(dnodes))
                self.path(ch, j, zref)
                self.maincap = getattr(self, "maincap", {})
                self.maincap[start] = max(self.maincap.get(start, 0), self.chan_cap(ch, j))
            elif t in ("E", "X"):
                if t == "E":
                    _, z, j = it
                    zb = z
                    self.chE[z] = max(self.chE.get(z, 0), j)
                else:
                    _, z, j, zb = it
                    self.chX.setdefault((z, j), set()).add(zb)
                ch = Channel.get((z, 0), (zb, 0), frozenset(bset_zero_mode(z)))
                self.need_channel(z, j, self.chan_cap(ch, j))
                self.path(ch, j)
            elif t == "c1":
                _, k = it
                self.c1.add(k)
                for z in (0, 1):
                    self.push(("E", z, k))
            elif t == "c2":
                _, k = it
                self.c2.add(k)
                for z in (0, 1, 2):
                    self.push(("E", z, k))
            elif t == "h":
                _, k, zp, z = it
                self.h.add((k, zp, z))
                if zp != z:
                    self.push(("X", z, k, zp))
                    for jj in range(1, k):
                        self.push(("E", z, jj))
                        self.push(("X", z, k - jj, zp))
                else:
                    self.push(("E", z, k))
                for m in range(1, k):
                    for zpp in range(max(0, z - 4 * (k - m)), z + 4 * (k - m) + 1, 2):
                        if zpp == z or abs(zp - zpp) > 4 * m:
                            continue
                        self.push(("X", z, k - m, zpp))
                        if m >= 2:
                            self.push(("h", m, zp, zpp))
                        else:
                            self.push(("h1", zp, zpp))
            elif t == "h1":
                _, zp, z = it
                self.h.add((1, zp, z))
                self.push(("E", z, 1))
                if zp != z:
                    self.push(("X", z, 1, zp))


def analyse(withV, desc, nmax=8, Lmax=18):
    b = Book(withV)
    for p in range(4):
        b.push(("main", (p, 0), nmax, frozenset(), None))
    if desc:
        for a in range(1, Lmax // 2 + 1):
            dn = {(1 + 4 * j, 2 * a - 2 * j) for j in range(1, a + 1)}
            b.push(("main", (1, 2 * a), nmax, frozenset(dn), (0,)))
        for a in (1, 2):
            dn = {(2, 2 * a)} | {(2 + 4 * j, 2 * a - 2 * j) for j in range(1, a + 1)}
            b.push(("main", (2, 2 * a), nmax, frozenset(dn), (0, 1)))
    b.run()
    return b


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--V", action="store_true")
    ap.add_argument("--desc", action="store_true")
    ap.add_argument("--nmax", type=int, default=8)
    ap.add_argument("--Lmax", type=int, default=18)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    b = analyse(a.V, a.desc, a.nmax, a.Lmax)
    zs = sorted(b.kmax)
    print(f"scheme {'W+V' if a.V else 'W'}, descendants {a.desc}, through eps^{a.nmax}")
    print(f"main-channel particle reach: {dict(sorted(b.maincap.items()))}")
    print(f"channels: {len(zs)} zero-mode numbers z = {zs[0]}..{zs[-1]} (at every cutoff l)")
    print(" z : kmax  cap  E-order  #X-rows")
    for z in zs:
        nx = sum(len(v) for (zz, j), v in b.chX.items() if zz == z)
        print(f"{z:3d}: {b.kmax[z]:3d} {b.cap[z]:4d} {b.chE.get(z, '-')!s:>6} {nx:6d}")
    byk = {}
    for (k, zp, z) in b.h:
        byk.setdefault(k, []).append((zp, z))
    for k in sorted(byk):
        zmx = max(z for _, z in byk[k]); zpmx = max(zp for zp, _ in byk[k])
        print(f"h^({k}): {len(byk[k])} entries, z <= {zmx}, z' <= {zpmx}")
    print(f"c1 orders {sorted(b.c1)}, c2 orders {sorted(b.c2)}")
    if a.out:
        out = {"withV": a.V, "desc": a.desc, "nmax": a.nmax,
               "main_reach": {str(k): v for k, v in b.maincap.items()},
               "channels": {str(z): {"kmax": b.kmax[z], "cap": b.cap[z]} for z in zs},
               "h": sorted(b.h), "c1": sorted(b.c1), "c2": sorted(b.c2),
               "X": {f"{z},{j}": sorted(v) for (z, j), v in sorted(b.chX.items())},
               "E": {str(z): j for z, j in sorted(b.chE.items())}}
        with open(a.out, "w") as f:
            json.dump(out, f)


if __name__ == "__main__":
    main()


# ============================================================================ diagonal windows (zeromode, consistent)
def analyse_diag(desc, nmax=8, Lmax=18, consistent=False):
    """tiers {z: (kmax, cap)} of E_z(l) needed by the diagonal schemes (zeromode: D(s) = E_{z_s}(l) - E_{z_s}(l - N);
    consistent: z_s -> 0) through eps^nmax, with the same path model (refunds included)."""
    need = {}
    todo, seen = [], set()

    def push(it):
        if it not in seen:
            seen.add(it); todo.append(it)

    def path(ch, j, zref=None):
        INF = 10 ** 8
        for (Ps, Ns), d1 in ch.dfw.items():
            if Ns < 2 or d1 >= INF:
                continue
            d2 = ch.dbw.get((Ps, Ns), INF)
            if d2 >= INF:
                continue
            for zs in range(max(0, Ps - Ns), Ps):
                c1, c2 = d1, d2
                if (Ps, Ns) == ch.start:
                    c1 = 0 if (zref is not None and zs in zref) else max(1, d1)
                if (Ps, Ns) == ch.end:
                    c2 = 0 if (zref is not None and zs in zref) else max(1, d2)
                for k in range(2, j + 1):
                    if c1 + k + c2 <= j:
                        push(("E", 0 if consistent else zs, k))

    for p in range(4):
        path(Channel.get((p, 0), (p, 0), frozenset()), nmax)
    if desc:
        for a in range(1, Lmax // 2 + 1):
            dn = {(1 + 4 * j, 2 * a - 2 * j) for j in range(1, a + 1)}
            path(Channel.get((1, 2 * a), (1, 2 * a), frozenset(dn)), nmax, (0,))
        for a in (1, 2):
            dn = {(2, 2 * a)} | {(2 + 4 * j, 2 * a - 2 * j) for j in range(1, a + 1)}
            path(Channel.get((2, 2 * a), (2, 2 * a), frozenset(dn)), nmax, (0, 1))
    b = Book(False)
    while todo:
        _, z, k = todo.pop()
        ch = Channel.get((z, 0), (z, 0), frozenset(bset_zero_mode(z)))
        cap = b.chan_cap(ch, k)
        km, cp = need.get(z, (0, 0))
        need[z] = (max(km, k), max(cp, cap))
        path(ch, k)
    return dict(sorted(need.items()))


def main_diag():
    ap = argparse.ArgumentParser()
    ap.add_argument("--desc", action="store_true")
    ap.add_argument("--consistent", action="store_true")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    t = analyse_diag(a.desc, consistent=a.consistent)
    print(("consistent" if a.consistent else "zeromode"), "desc" if a.desc else "", t)
    if a.out:
        json.dump({str(z): {"kmax": k, "cap": c} for z, (k, c) in t.items()}, open(a.out, "w"))
