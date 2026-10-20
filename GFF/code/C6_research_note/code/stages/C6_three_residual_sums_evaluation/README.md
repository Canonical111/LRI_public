# Evaluate the three current C6 residual sums

Run `python evaluate.py` and then `python make_report.py` with Python 3,
SymPy and mpmath installed. The `work/` directory preserves the supplied
evaluation packages. `evaluate.py` recomputes the residuals using those packages;
prior values are read only afterward for overlap checks and the labelled
inherited full-C6 record. All comparison certificates are included locally.
The report and result archive are written alongside this directory.

The numerical values are not new symbolic finite summations. The primitive
spectral bracket is evaluated through its exact normalization with the faster
retained primitive recurrence. See `report.txt` for definitions and scope.
