"""Write one sbatch per (x, theta0) point. usage: python3 gen.py MODE   (MODE = smoke | prod)"""
import json, sys
R = "<HOME>/lri2d_window"
BASIS = {"0.125": (f"{R}/campaigns/prod1/inputs/x0.125/L6_z24.json", "6768fa34b6e1bfd4c4dde27ea4eb1edc526c49cf350c6f622dc91fd724c85bb5"),
         "0.126": (f"{R}/campaigns/prod1/inputs/x0.126/teacher_L6_x0.126.json", "a072ded2eba723e7089bf9a09d2eda98f34676c2f557e53bd2173f15c291ae72")}
# theta1 guesses: polynomial fit to the evaluated L=24 valley points; the exact best Newton point is reused at
# one theta0 per x so that its first evaluation reproduces the checkpointed residual norm.
PROD = {"0.125": [(12.5, -1.20530811798243), (13.25, -1.1751094405970028), (13.934717481590253, -1.1481209111073274),
                  (14.3, -1.1336042306113123), (14.8, -1.1141567905251517), (15.5, -1.0872739025618194)],
        "0.126": [(12.5, -1.2057853979964408), (13.25, -1.1767765721847092), (13.883939249339136, -1.1522301466696132),
                  (14.3, -1.1361642160482845), (14.8, -1.1168249988404635), (15.5, -1.089750094749514)]}
mode = sys.argv[1]
tmpl = open("valley.sbatch.in").read()
jobs = []
if mode == "smoke":
    pts = [("0.125", 8, json.loads(sys.argv[2]))]  # [theta0, theta1]
    res = dict(CPUS="8", MEM="16G", TIME="00:30:00")
else:
    pts = [(x, 24, list(p)) for x, ps in PROD.items() for p in ps]
    res = dict(CPUS="64", MEM="64G", TIME="16:00:00")
for x, L, (t0, t1) in pts:
    name = f"ht2d-valley-{mode}-x{x}-t{t0:.4f}"
    out = f"{R}/valley/out/{mode}_x{x}_L{L}_t{t0:.4f}.json"
    s = tmpl
    for k, v in dict(res, NAME=name, L=str(L), X=x, T0=repr(t0), T1=repr(t1), OUT=out, BASIS=BASIS[x][0], BASIS_SHA=BASIS[x][1]).items():
        s = s.replace(f"@{k}@", v)
    assert "@" not in s.replace("#SBATCH", "")
    fn = f"{name}.sbatch"; open(fn, "w").write(s); jobs.append(fn)
print("\n".join(jobs))
