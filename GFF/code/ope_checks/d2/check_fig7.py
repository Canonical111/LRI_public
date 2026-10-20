#!/usr/bin/env python3
"""C62d, OPE review 2026-10-16: the 2d comparison points against the vector data of BLNV Figure 7.

Input: an SVG made with `pdftocairo -svg fig/plot_pade_comparison.pdf` from the arXiv source of arXiv:2311.02742v6
(Figure 7: Pade estimates (lines, dots) and bootstrap kinks (crosses: black/red/blue = 3000/6000/12000 grid points)
at the eight external dimensions Delta_phi = 0.13333 ... 0.425, left to right).
Axis calibration from the tick marks, drawn with transform matrix(1,0,0,-1,-6,305): x ticks at X = 119.839844 ...
399.429688 for a_phi2 = -0.8 ... 0.0, y ticks at Y = 77.015625 ... 292.660156 for Delta = 0.96 ... 1.00. Markers are
paths around the origin placed by transform matrix(1,0,0,-1,tx,ty), device (tx,ty) = (X-6, 305-Y).
Usage: python3 -I check_fig7.py FIG.svg OUT.json"""
import json, re, sys

DPHI = ['0.13333', '0.14166', '0.15', '0.175', '0.2', '0.275', '0.35', '0.425']   # BLNV caption and Sec. 4, left to right
XT = (119.839844, 399.429688, -0.8, 0.0)
YT = (77.015625, 292.660156, 0.96, 1.00)


def data(tx, ty):
    X, Y = tx + 6, 305 - ty
    a = XT[2] + (X - XT[0]) / (XT[1] - XT[0]) * (XT[3] - XT[2])
    D = YT[2] + (Y - YT[0]) / (YT[1] - YT[0]) * (YT[3] - YT[2])
    return a, D


def main():
    s = open(sys.argv[1]).read()
    # sanity: the tick marks are where the calibration says
    ticks_x = sorted(float(m) for m in re.findall(r'd="M ([0-9.]+) 51\.839844 L \1 48\.339844', s))
    ticks_y = sorted(float(m) for m in re.findall(r'd="M 78\.335938 ([0-9.]+) L 74\.835938 \1', s))
    assert abs(ticks_x[0] - XT[0]) < 1e-6 and abs(ticks_x[-1] - XT[1]) < 1e-6 and len(ticks_x) == 5, ticks_x
    assert abs(ticks_y[0] - YT[0]) < 1e-6 and abs(ticks_y[-1] - YT[1]) < 1e-6 and len(ticks_y) == 5, ticks_y
    out = {'source': 'arXiv:2311.02742v6, fig/plot_pade_comparison.pdf (Figure 7), via pdftocairo -svg',
           'ticks_x': ticks_x, 'ticks_y': ticks_y, 'markers': {}}
    colours = {'rgb(0%, 0%, 0%)': 'black', 'rgb(100%, 0%, 0%)': 'red', 'rgb(0%, 0%, 100%)': 'blue'}
    groups = {}
    for t in re.findall(r'<path[^>]*>', s):
        tr = re.search(r'transform="matrix\(1, 0, 0, -1, ([-0-9.]+), ([-0-9.]+)\)"', t)
        st = re.search(r'stroke="([^"]*)"', t)
        d = re.search(r' d="([^"]*)"', t).group(1)
        if not tr or not st or st.group(1) not in colours:
            continue
        if (float(tr.group(1)), float(tr.group(2))) == (-6.0, 305.0):   # axes, ticks and curves, not markers
            continue
        kind = 'cross' if ' L ' in d and ' C ' not in d else ('dot' if ' C ' in d else None)
        if kind is None or len(d) > 1200:
            continue
        groups.setdefault((kind, colours[st.group(1)]), []).append(data(float(tr.group(1)), float(tr.group(2))))
    for (kind, col), pts in sorted(groups.items()):
        pts.sort()
        assert len(pts) == 8, (kind, col, len(pts))
        out['markers'][f'{kind}_{col}'] = {dp: {'a': round(a, 6), 'Delta': round(D, 6)} for dp, (a, D) in zip(DPHI, pts)}
    json.dump(out, open(sys.argv[2], 'w'), indent=1)
    for k, v in out['markers'].items():
        print(k, {dp: (v[dp]['a'], v[dp]['Delta']) for dp in ('0.425', '0.35', '0.275', '0.2')})


if __name__ == '__main__':
    main()
