# C6 compact bivariate-H representation

`FORMULA.md` is self-contained: all coefficients and parameters of the new 18-value formula are present. `DERIVATION.md` proves the new primitive compression and states the inherited inputs. `results/expression.json` is the full machine-readable expression, not just a patch.

Dependencies: Python 3, SymPy, mpmath.

Run:

```
python build_verify.py
python write_formula.py
python numerical.py --dps 40 --meijer
python numerical.py --dps 70 --meijer
```

The first command performs finite exact algebra. The numerical runs are floating-point checks, not rigorous interval certificates. They check the new local Meijer G functions directly, and evaluate the bivariate H through the proved beta-product identity. Independent two-dimensional Barnes integration, Wolfram kernel execution, and full-C6 reevaluation were not performed.

The reduction replaces the primitive's four fixed bivariate values by one higher-order value, using four new explicitly fixed conjugate parameters. It also selects the already established one-value sixth-sector alternative. This is shorter in number of function calls, not necessarily in parameter complexity or numerical cost. No arithmetic independence, elementary evaluation, or new graph/RG proof is claimed.
