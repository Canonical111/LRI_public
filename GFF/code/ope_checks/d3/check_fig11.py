#!/usr/bin/env python3
"""C63d, OPE review 2026-10-16: the 3d comparison points against the vector data of BLNV Figure 11.

Input: an SVG made with `pdftocairo -svg fig/plot_kinks_3d.pdf` from the arXiv source of arXiv:2311.02742v6.
The axis frame (x from -0.08 to 0, Delta from 1.40 to 1.50) is the plotted rectangle; the four region boundaries are
the stroked polylines drawn with transform matrix(1,0,0,-1,-2,311); the perturbative dot is the small circle.
Reports, for each boundary, the kink (largest turning angle inside the frame) and the boundary abscissa at the
package's [4/2] thermal value; and the dot's centre.  Usage: python3 check_fig11.py FIG.svg OUT.json"""
import json, math, re, sys

s = open(sys.argv[1]).read()
X0, X1, Y0, Y1 = 71.726562, 412.71875, 6.871094, 259.160156   # frame: a=-0.08..0, Delta=1.5 (top)..1.4 (bottom)
def data(px, py):
    return -0.08 + (px - X0) / (X1 - X0) * 0.08, 1.5 - (py - Y0) / (Y1 - Y0) * 0.1
polys, dot = [], None
for m in re.finditer(r'<path[^>]*>', s):
    t = m.group(0)
    d = re.search(r' d="([^"]*)"', t).group(1)
    tr = re.search(r'transform="matrix\(1, 0, 0, -1, -2, 311\)"', t)
    if not tr:
        continue
    nums = [float(v) for v in re.findall(r'-?\d+\.?\d*', d)]
    pts = [(nums[i] - 2, 311 - nums[i + 1]) for i in range(0, len(nums) - 1, 2)]
    if d.startswith('M') and ' C ' in d and len(d) < 700:
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        dot = data((max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2)
    elif ' C ' not in d and d.split()[2] == '-1':
        polys.append([data(*p) for p in pts if X0 - 1 <= p[0] <= X1 + 1 and Y0 - 1 <= p[1] <= Y1 + 1])
# order the four boundaries by Delta_phi: the region reaching furthest right at the top belongs to 0.70363
polys.sort(key=lambda P: -max(p[1] for p in P))
labels = ['0.70363', '0.65726', '0.61089', '0.56452']
pkg = json.load(open(sys.argv[3])) if len(sys.argv) > 3 else None
out = {'dot_centre': dot, 'boundaries': {}}
print('dot centre (cubic perturbative point of BLNV):', dot)
for lab, P in zip(labels, sorted(polys, key=lambda P: -max(p[0] for p in P if p[1] > 1.405))):
    # turning angle in axis-normalized coordinates
    Q = [((x + 0.08) / 0.08, (y - 1.4) / 0.1) for x, y in P]
    best = None
    for i in range(1, len(Q) - 1):
        a = math.atan2(Q[i][1] - Q[i - 1][1], Q[i][0] - Q[i - 1][0]); b = math.atan2(Q[i + 1][1] - Q[i][1], Q[i + 1][0] - Q[i][0])
        turn = abs((b - a + math.pi) % (2 * math.pi) - math.pi)
        if best is None or turn > best[0]:
            best = (turn, P[i])
    out['boundaries'][lab] = {'kink': best[1], 'turn_deg': math.degrees(best[0]), 'npoints': len(P), 'points': P}
    print(f'Delta_phi={lab}: kink at a={best[1][0]:.6f}, Delta={best[1][1]:.5f} (turn {math.degrees(best[0]):.0f} deg, {len(P)} pts)')
json.dump(out, open(sys.argv[2], 'w'), indent=1)
