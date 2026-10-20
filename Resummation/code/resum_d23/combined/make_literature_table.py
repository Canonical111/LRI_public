"""Build resummation/combined/literature_mc_2d3d.csv from the 2026-10-12 full-text extraction.

Selection: Monte Carlo rows whose sigma lies inside the window
  2d: 1 < sigma <= 7/4      3d: 3/2 < sigma < 1.9637 (= 2 - eta_SR)
Values: Delta_epsilon and its error are copied from the source CSV (DeltaE, DeltaE_err);
Delta_sigma = (d - sigma)/2 is recomputed and checked against the source column.
Display: literature markers sharing a Delta_sigma are dodged horizontally (2d: step 0.009,
centred; 3d: +0.006 so the project MC/HT markers at the same Delta_sigma stay visible).
Offsets are computed over plotted rows only.
Not plotted (rows kept, plotted = no, reason in exclusion_reason): the superseded preliminary 3d
sigma = 1.6 value, and (since 2026-10-13, author's request) Angelini et al. 2014 at sigma = 7/4,
Delta_epsilon = 1.02(10): window boundary, error too wide for the frame. Without it the sigma = 7/4
pair (Luijten Q fit, Xiao et al.) sits at -/+0.0045 instead of 0 / +0.009.
Since 2026-10-13 (evening) the group at the short-range Ising end, Delta_sigma = 1/8, is dodged with the doubled
step (-/+0.009) so that the star marking the SRI point (1/8, 1) in Figure 06 stays clear of both markers.
"""
import csv, hashlib, sys
from fractions import Fraction
from pathlib import Path

ROOT = Path("<PROJECT>")
SRC = ROOT / "<PAPER>/notes/comparison_data"
OUT = ROOT / "resummation/combined/literature_mc_2d3d.csv"
EXTRACTED = "2026-10-12"

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def read(name):
    p = SRC / name
    with p.open(newline="") as f:
        r = csv.DictReader(f)
        rows = []
        for row in r:
            rows.append((r.line_num, row))
    return p, rows

MC_PAPERS = ("Luijten", "Picco", "Angelini", "Xiao")
NON_MC = ("Behan", "Defenu")

def classify(paper, method):
    if paper.startswith(NON_MC):
        return "non-MC"
    if paper.startswith(MC_PAPERS):
        return "Monte Carlo"
    raise SystemExit(f"unclassified source: {paper}")

def source_key(d, paper, location, method):
    if paper.startswith("Angelini"):
        return "angelini2014"
    if paper.startswith("Picco"):
        return "picco2012"
    if paper.startswith("Xiao"):
        return "xiao2025"
    if paper.startswith("Luijten PhD") or paper.startswith("Luijten PhD thesis"):
        if d == 3:
            return "luijten1997_3d"
        if "Table 5.7" in location:
            return "luijten1997_chi"
        if "Table 5.8" in location or "Table 5.9" in location:
            return "luijten1997_Q"
    if paper.startswith("Luijten & Bloete"):
        return "luijten_bloete1997"
    raise SystemExit(f"no key for {paper} / {location}")

INFO = {
    "angelini2014": dict(label="Angelini, Parisi, Ricci-Tersenghi (2014)", status="journal (PRE 89, 062120); arXiv:1401.6805v2",
                         marker="blue open triangle (as in the previous figure)", estimator="quotient of Binder-cumulant derivatives, L -> 2L, extrapolated linearly in L^-omega"),
    "luijten1997_chi": dict(label="Luijten PhD thesis (1997), chi fit", status="PhD thesis, TU Delft 1997; not published in a journal",
                            marker="red open circle", estimator="FSS fit of the susceptibility chi(K,L), y_t free (Table 5.7)"),
    "luijten1997_Q": dict(label="Luijten PhD thesis (1997), Q fit", status="PhD thesis, TU Delft 1997; not published in a journal",
                          marker="red filled circle", estimator="FSS fit of the amplitude ratio Q (Table 5.8: Kc fixed; Table 5.9: regime-B fit with log + power corrections)"),
    "luijten1997_3d": dict(label="Luijten PhD thesis (1997), 3d Table 5.12", status="PhD thesis, TU Delft 1997; never published in a journal",
                           marker="red open circle with central dot", estimator="final FSS estimate with the correction exponent y_i fixed by hand"),
    "picco2012": dict(label="Picco (2012)", status="arXiv:1207.1018v1, unpublished",
                      marker="brown open inverted triangle", estimator="Binder-cumulant FSS fit, triangular lattice"),
    "xiao2025": dict(label="Xiao, Liu, Fan, Deng (2025)", status="arXiv:2512.04805v2 preprint",
                     marker="magenta open star", estimator="FSS fit of the covariance g_ER with one correction term"),
}

# Within-group display order (left to right) in 2d. Chosen so that, for groups with an odd
# count, the central (undodged) marker's bar does not cross the HT square at the same x.
ORDER_2D = ["angelini2014", "luijten1997_chi", "luijten1997_Q", "picco2012", "xiao2025"]
STEP_2D = Fraction(9, 1000)
OFFSET_3D = Fraction(6, 1000)

def conversion(d, quantity):
    q = quantity.strip()
    if q.startswith("nu"):
        return f"Delta_epsilon = {d} - 1/nu; error propagated linearly (source CSV)"
    return f"Delta_epsilon = {d} - y_t (y_t = 1/nu); error unchanged"

def inside(d, s):
    if d == 2:
        return 1 < s <= Fraction(7, 4)
    return Fraction(3, 2) < s < Fraction("1.9637")

out = []
exclusions = []
for d, name in [(2, "lit_2d.csv"), (3, "lit_3d.csv")]:
    path, rows = read(name)
    h = sha(path)
    for line, r in rows:
        cls = classify(r["paper"], r["method"])
        s = Fraction(r["sigma"])
        if cls != "Monte Carlo":
            exclusions.append((d, line, r["paper"][:40], r["sigma"], "not Monte Carlo (figure-read bootstrap/FRG context)"))
            continue
        if not inside(d, s):
            exclusions.append((d, line, r["paper"][:40], r["sigma"], "sigma outside window"))
            continue
        x = (d - s) / 2
        x_src = Fraction(r["Delta_sigma"])
        if abs(x - x_src) > Fraction(1, 10**9):
            raise SystemExit(f"Delta_sigma mismatch line {line}: {x} vs {x_src}")
        # Delta_epsilon consistency with the printed exponent
        val, err = Fraction(r["value"]), Fraction(r["error"])
        dE, dEerr = Fraction(r["DeltaE"]), Fraction(r["DeltaE_err"])
        q = r["quantity"].strip()
        if q.startswith("nu"):
            exact = d - 1 / val
            lin = err / val**2
            assert abs(exact - dE) <= Fraction(1, 1000) and abs(lin - dEerr) <= Fraction(1, 1000), line
        else:
            assert d - val == dE and err == dEerr, (line, d - val, dE)
        key = source_key(d, r["paper"], r["location"], r["method"])
        plotted, reason = "yes", ""
        if "superseded" in r["caveat"].lower():
            plotted, reason = "no", "preliminary value superseded in the same thesis by the final Table 5.12 estimate (1.523(16)); not an independent estimate"
        if key == "angelini2014" and s == Fraction(7, 4):   # author's request, 2026-10-13
            plotted, reason = "no", "window boundary, error too wide for the frame (Delta_epsilon = 1.02(10)); omitted from Figure 06 for readability (2026-10-13)"
        out.append(dict(
            id=f"{d}d-{key}-s{r['sigma']}", dimension=d, source_key=key, source_label=INFO[key]["label"],
            publication_status=INFO[key]["status"], paper=r["paper"], reference=r["arxiv"], location=r["location"],
            method_class=cls, estimator=INFO[key]["estimator"], sigma=r["sigma"], quantity=q,
            printed_value=r["value"], printed_error=r["error"],
            Delta_sigma=format(float(x), ".6g"), Delta_epsilon=r["DeltaE"], Delta_epsilon_err=r["DeltaE_err"],
            conversion=conversion(d, q), Lmax=r["Lmax"], extrapolated=r["extrapolated"],
            plotted=plotted, exclusion_reason=reason, plot_marker=INFO[key]["marker"],
            plot_offset="", plot_Delta_sigma="",
            source_file=str(path.relative_to(ROOT)), source_line=line, source_sha256=h,
            extracted=EXTRACTED, source_caveat=r["caveat"], _x=x))

# display offsets
for d in (2, 3):
    pts = [o for o in out if o["dimension"] == d and o["plotted"] == "yes"]
    groups = {}
    for o in pts:
        groups.setdefault(o["_x"], []).append(o)
    for x, g in groups.items():
        if d == 2:
            g.sort(key=lambda o: ORDER_2D.index(o["source_key"]))
            n = len(g)
            for i, o in enumerate(g):
                step = 2 * STEP_2D if x == Fraction(1, 8) else STEP_2D  # SRI end: keep (1/8, 1) free for the star
                off = (i - Fraction(n - 1, 2)) * step
                o["_off"] = off
        else:
            for o in g:
                o["_off"] = OFFSET_3D
    for o in pts:
        o["plot_offset"] = format(float(o["_off"]), ".4f")
        o["plot_Delta_sigma"] = format(float(o["_x"] + o["_off"]), ".6g")

# sanity: no duplicates (same source, sigma, estimator)
seen = set()
for o in out:
    k = (o["dimension"], o["source_key"], o["sigma"], o["location"])
    assert k not in seen, k
    seen.add(k)

fields = [k for k in out[0] if not k.startswith("_")]
out.sort(key=lambda o: (o["dimension"], -float(o["_x"]), ORDER_2D.index(o["source_key"]) if o["source_key"] in ORDER_2D else 9))
with OUT.open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields, quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
    w.writeheader()
    for o in out:
        w.writerow({k: o[k] for k in fields})

print("wrote", OUT, len(out), "rows;", sum(o["plotted"] == "yes" for o in out), "plotted")
for o in out:
    print(o["dimension"], o["source_key"], o["sigma"], o["Delta_sigma"], o["Delta_epsilon"], o["Delta_epsilon_err"],
          o["plotted"], o["plot_offset"], o["plot_Delta_sigma"], "line", o["source_line"])
print("excluded rows:")
for e in exclusions:
    print("  ", e)
