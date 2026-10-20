#!/usr/bin/env python3
"""Write a standalone LaTeX report from the verified full-coverage pilot."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def number(value, digits=6):
    value = format(float(value), f".{digits}g")
    if "e" in value:
        mantissa, exponent = value.split("e")
        return mantissa + r"\times10^{" + str(int(exponent)) + "}"
    return value


def report(result):
    if result.get("purpose") != "pilot" or not result.get("complete_graph_coverage"):
        raise ValueError("This report template requires a verified complete-coverage pilot")
    se = result["sampling_standard_error"]
    rows = []
    for check in result["lower_order_checks"]:
        rows.append(
            f"{check['order']} & ${number(check['estimate'], 11)}$ & "
            f"${number(check['sampling_se'], 4)}$ & ${number(check['reference'], 11)}$ & "
            f"${check['pull']:+.2f}$ \\\\"
        )
    campaigns = []
    for tag in ("a", "b"):
        item = result["individual_campaigns"][tag]
        campaigns.append(f"Campaign {tag} & ${number(item['coefficients'][8], 9)}$ & ${number(item['standard_errors'][8], 5)}$ \\\\")
    campaigns.append(f"Combined & ${number(result['C8_estimate'], 10)}$ & ${number(se, 5)}$ \\\\")
    boot = result["bootstrap"]
    flags = [str(row["order"]) for row in result["lower_order_checks"] if row["flag_abs_pull_above_3"]]
    control_text = (
        "The lower-order comparisons with absolute pull above three occur at orders "
        + ", ".join(flags) + ". They are retained as failed pilot controls; the estimate is not adjusted to fit them."
        if flags else
        "No lower-order comparison has an absolute pull above three. These are consistency checks within the inherited framework, not a substitute for larger-net convergence."
    )
    return r"""
\section*{Numerical result and status}
This package implements the complete eighth-order extension of the supplied
three-dimensional calculation and runs a full-graph exploratory pilot.
The pilot estimator and its propagated sampling standard error are
\begin{equation}
 \widehat C_{8,\mathrm{pilot}}(3)=VALUE,\qquad
 \widehat\sigma_{\mathrm{sampling}}=ERROR.
\end{equation}
\textbf{This is a pilot estimate, not a converged production determination.}
No empirical reporting interval is assigned. In particular, the sampling
standard error does not establish the effect of rare contributions at the
small eight-loop net size, and it does not bound a shared error in the
graph/renormalization framework or the omitted orders of the epsilon series.
Extra displayed digits identify the estimator for reproduction.

Both sectors are included explicitly:
\begin{center}
\begin{tabular}{@{}lrr@{}}\toprule
Contribution & Estimate & Sampling SE\\\midrule
Power-free coefficient & $FREE$ & $FREESE$\\
Power correction & $POWER$ & $POWERSE$\\
Complete coefficient & $VALUE$ & $ERROR$\\\bottomrule
\end{tabular}
\end{center}
The power-free coefficient and correction are correlated; their covariance
is $CROSS$. Their individual standard errors must therefore not be added
in quadrature without that cross term.

\subsection*{Frozen design and complete coverage}
The pilot contains 24,173 active graph kernels and EVALS evaluations.
Every active class is present in each of the eight randomized replicates
of both independent campaigns. The point allocation was fixed before the
integrations, without fitting a physical coefficient:
\begin{center}
\begin{tabular}{@{}rrr@{}}\toprule
Loop & Active graphs & Points per graph and replicate\\\midrule
3&6&32,768\\
4&19&8,192\\
5&96&2,048\\
6&502&512\\
7&3,150&64\\
8&20,400&16\\\bottomrule
\end{tabular}
\end{center}
The two-loop input is analytic. Campaigns $a$ and $b$ use 52-bit and
60-bit scrambled Sobol matrices and importance-rate multipliers $0.8$
and $0.7$, respectively. Their preassigned final weights are $1/2$ each.
Only complete powers-of-two nets are used. Native point intervals are
merged before statistics, and all beta/mass and regulator-slot covariance
of each graph-summed replicate is retained.

\subsection*{Independent campaigns, bootstrap and lower-order checks}
\begin{center}
\begin{tabular}{@{}lrr@{}}\toprule
Estimate & $C_8$ & Sampling SE\\\midrule
CAMPAIGNS
\bottomrule
\end{tabular}
\end{center}
The campaign difference is $ABPULL$ combined standard errors. The two
half-stream estimates are $HALFA$ and $HALFB$. A bootstrap of BOOTN
whole-replicate resamples gives standard error $BOOTSE$ and diagnostic
plug-in bias $BOOTBIAS$. These diagnostics do not resolve tails that have
not been adequately sampled.

The same samples yield the following uncalibrated lower-order coefficients.
Reference sampling errors for $C_6$ and $C_7$ are included in each pull;
the references are never inputs to the estimated mean.
\begin{center}
\begin{tabular}{@{}rrrrr@{}}\toprule
Order & Estimate & Sampling SE & Reference & Pull\\\midrule
CONTROLS
\bottomrule
\end{tabular}
\end{center}
CONTROLTEXT

\subsection*{What is ready for a larger calculation}
The package contains the complete generated inputs, their exact graph and
subtraction audits, the C8 native worker, analytic regulator jets,
fixed-point assembly, complete-net coverage guards, pilot allocation
diagnostics, and restartable local/Slurm-array drivers. A production
allocation can be frozen from the pilot timing and variance data, with
fresh production seeds and the allocation-training pilot excluded from
the production mean. Larger independent complete nets and stability of
the resulting estimates are required before quoting production precision.

The complete machine-readable result is
\nolinkurl{results/pilot_20261008/C8_result.json}; every native checkpoint
and its frozen task/net description is retained in the same run directory.
Build and cluster instructions are in \nolinkurl{README.md} and
\nolinkurl{docs/HPC.md}. The following sections give the mathematical
extension and the exact input/coverage checks.
\clearpage
""".replace("VALUE", number(result["C8_estimate"], 10)).replace("ERROR", number(se, 5)).replace("FREESE", number(result["power_free_se"], 5)).replace("FREE", number(result["power_free_C8"], 10)).replace("POWERSE", number(result["power_correction_se"], 5)).replace("POWER", number(result["power_correction"], 9)).replace("CROSS", number(result["power_free_correction_covariance"], 6)).replace("EVALS", f"{result['evaluations']:,}").replace("CAMPAIGNS", "\n".join(campaigns)).replace("ABPULL", number(result["campaign_difference_pull"], 4)).replace("HALFA", number(result["half_streams"][0][8], 9)).replace("HALFB", number(result["half_streams"][1][8], 9)).replace("BOOTN", f"{boot['resamples']:,}").replace("BOOTSE", number(boot["standard_errors"][8], 5)).replace("BOOTBIAS", number(boot["estimated_plugin_bias"][8], 5)).replace("CONTROLS", "\n".join(rows)).replace("CONTROLTEXT", control_text)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = json.loads(args.result.read_text())
    source = (ROOT / "docs/DERIVATION.tex").read_text()
    start = source.index("\\title{")
    end = source.index("\\author", start)
    source = source[:start] + "\\title{$C_8$ in three dimensions:\\\\ complete implementation and pilot calculation}\n" + source[end:]
    source = source.replace("\\date{}", "\\date{8 October 2026}")
    source = source.replace("\\geometry{margin=1in}", "\\geometry{margin=1in}\n"
                            "\\hypersetup{pdftitle={C8 in three dimensions: complete implementation and pilot calculation},"
                            "pdfsubject={Eighth perturbative coefficient of the thermal scaling dimension in the long-range Ising model},"
                            "pdfkeywords={long-range Ising model, C8, epsilon expansion, three dimensions, pilot calculation}}")
    source = source.replace("\\maketitle", "\\maketitle\n" + report(result))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(source)
    print(args.output)


if __name__ == "__main__":
    main()
