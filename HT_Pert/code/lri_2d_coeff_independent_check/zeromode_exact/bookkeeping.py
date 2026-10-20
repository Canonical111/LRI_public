#!/usr/bin/env python3
"""Order / zero-mode-number bookkeeping for the zeromode window through eps^ORD (ORD = 8).

Notation: channel (z, l) = branch connected to |z> in the corrected Hamiltonian at cutoff l; E_z^(n)(l) its
eps^n coefficient.  D_l(z_s, N)^(k) = E_{z_s}^(k)(l) - E_{z_s}^(k)(l - N) acts on states with z_s zero modes
and level N >= 2.

Cost counting (closed RS paths |z> -> ... -> |z>):
  * every off-diagonal hop carries >= eps^1 (g = O(eps), r = O(eps^2), D = O(eps^2)); V changes the
    particle number P by <= 4, M by <= 2;
  * D^(k) is diagonal and acts only on level >= 2 states, never on |z> (level 0), so it needs a hop in and a
    hop out: D^(k) enters E_z^(n) only for k <= n - 2;
  * degenerate partners B (z >= 5, P = z - 2N < z): each passage through B comes with one resolvent
    G_B = (E^(1) - W_1^BB)^{-1} = O(eps^-1), but B is never adjacent to |z> and a B-visit costs >= 1 net
    order (entry hop + exit hop - 1) and returns P to <= z; it can therefore neither raise the highest
    particle number reachable at given order nor lower the cost of a D insertion below k + 2;
  * a state s with level >= 2 reached in a path of total order n that still carries D^(k) satisfies
    P_s <= z + 4 floor((n - k)/2), hence z_s <= P_s - 1 <= z + 4 floor((n - k)/2) - 1;
  * the particle numbers visited by E_z^(n) satisfy P <= z + 4 floor(n/2)  (channel cap).

Starting from the primaries (z = p = 0..3, n = 8) the set of needed (z_s, k) is closed under
  (z, n) needed  =>  (z', k) needed for 2 <= k <= n - 2 and z' <= z + 4 floor((n - k)/2) - 1.
"""
import argparse, json

ORD = 8


def closure(pmax=3, order=ORD):
    need = {}                      # z -> highest order k at which E_z^(k)(l) is needed (for D)
    todo = [(p, order) for p in range(pmax + 1)]
    seen = set()
    while todo:
        z, n = todo.pop()
        if (z, n) in seen:
            continue
        seen.add((z, n))
        for k in range(2, n - 1):
            zmax = z + 4 * ((n - k) // 2) - 1
            for z2 in range(0, zmax + 1):
                if need.get(z2, 0) < k:
                    need[z2] = k
                todo.append((z2, k))
    return dict(sorted(need.items()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    need = closure()
    zmax_of_k = {k: max(z for z, kk in need.items() if kk >= k) for k in range(2, ORD - 1)}
    print("needed: z -> highest order k of E_z^(k)(l) that enters C_0..C_8 through D")
    for z, k in need.items():
        cap = z + 4 * (k // 2)
        print(f"  z = {z:2d}: k_max = {k}   (channel cap P <= {cap}; degenerate partners: "
              f"{'none' if z < 5 else 'levels ' + ','.join(str(N) for N in range(2, (z - 1) // 2 + 1, 2))})")
    print("largest z needed at order k:", zmax_of_k)
    print("primary channels p = 0..3 to order 8, cap P <= p + 16")
    if a.json:
        with open(a.json, "w") as f:
            json.dump({"kmax_of_z": need, "zmax_of_k": zmax_of_k}, f, indent=1)


if __name__ == "__main__":
    main()
