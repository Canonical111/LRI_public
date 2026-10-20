# Slurm templates for the NRG study

These templates run the study on any Slurm cluster. They are written for this release. The production itself used the
site-specific lane tools kept unchanged in `code/lri_spin_boson_hpc/cluster/symmetry/` and
`code/lri_spin_boson_hpc/scripts/symmetry_*.py`, described in `code/lri_spin_boson_hpc/docs/SYMMETRY.md` and
REPRODUCE.md §5.

Replace these placeholders before use:

| placeholder | meaning |
|---|---|
| `<ACCOUNT>` | Slurm account (`--account`) |
| `<PARTITION>` | partition. Use nodes with one CPU type, because records are bound to the runtime of the validation node |
| `<SCRATCH>` | a scratch root; validation receipts, runs and logs go below `<SCRATCH>/nrg/` |
| `<LOAD_MODULES>` | the site's commands for Python ≥ 3.10 with NumPy, SciPy and threadpoolctl (plus pytest and mpmath for validation and the independent check), e.g. `module load python; source <venv>/bin/activate` |
| `<CODE_DIR>` | a read-only copy of `NRG/code/lri_spin_boson_hpc` |
| `<MANIFEST>` | a frozen manifest from `scripts/make_manifest.py --items inputs/items/<list>.json --receipt <receipt> --output <manifest>` |
| `<VALIDATION_JOB_ID>` | the job id of `validate.sbatch` that issued the receipt |
| `<CAMPAIGN>` | a name for the output folder of one item list (`ds13`, `lambda_pilot`, ...) |

Order:
1. `validate.sbatch` (minutes) gives `receipt.json` on a compute node.
2. `make_manifest.py` freezes each item list against that receipt. Run it on the login node.
3. `items_array.sbatch` takes `--array=0-<n-1>` with n the number of items. Resubmitting the same array resumes from
   checkpoints. An item that is already complete exits at once.
4. Collect the records as described in REPRODUCE.md §5.4. Then run `make replay`.

`independent_check.sbatch` reruns the second implementation (note §8.1) on one node.

The templates use `--no-requeue` on purpose. A silent requeue after a node failure would restart an item without the
ownership checks of the lane tools. Resubmit by hand instead.

The array route runs one item per task. On whole-node partitions this wastes most of each node, because the items are
small (1–4 threads). There, either use a shared partition or pack items as the lane tools do.
