# prod1: independent C8(2) production on Expanse (2026-10-09/10)

**Result:** C8(2) = 46006.14 ± 13.42 (sampling SE; forecast 14.97). Ours (LRI_C8_D2_HPC aafa8a4): 45990.0 ± 8.2.
The difference is +16.1 against a combined SE of 15.7, a pull of +1.03.

- Code: LRI_C8_D2_HPC_optimized at a791a1f (site layer c8ind-B4; the last fix is not Codex-inspected).
- Campaign: manifest 13ea54c0840c…, seed 7522572997107493768, 342 indices, R = 64 replicates per campaign.
- Jobs: runners 54788180–54788190 (11 whole compute nodes, 16.3–20.1 h each, all COMPLETED) and merge 54788191
  (shared, 4:36, COMPLETED).
- Analysis: debug jobs 54820592 and 54820630 (scripts in ../pilot/scripts/analyse_prod.sbatch and util_prod.sbatch).
  54820592 failed after writing inspect and the cost model, because a utilization grep was empty under pipefail.
  compare.txt was then made locally from C8_result.json.
- Cost: 207.2 node-h = 26,526 core-h allocated. Kernel time is 25,585 core-h, so utilization is 0.965.

## Checks

- Lower orders: C3 −0.01, C4 +1.75, C5 +0.57, C6 −1.18, C7 +1.04 (pulls against the references; none flagged).
- Power-null pulls: C4 0.75, C5 0.05, C6 0.76.
- Campaigns: a 46012.5 ± 19.7, b 45999.7 ± 18.2, difference +0.48σ. Replicate halves 46008.2 / 46004.1.
- Bootstrap: SE / sampling SE 0.997, bias / SE −0.008.
- Variance:
  - by sector: free L8 78%, free L7 14%, power L8 6%, power L7 1.3%;
  - by graph: top-1 0.2%, top-10 1.2%, top-100 6.3%.
- Power correction: +1.29 ± 3.71. Power-free value 46004.84 ± 12.90.

## Files

- prod1/: C8_result.json (sha256 856595ff…), manifest, seed receipt, site identity, submissions, Slurm logs.
- prod1_analysis/: inspect.json and inspect.txt (inspect_result --top 25), cost_model.json, compare.txt,
  kernel_util.txt. kernel_sum.txt is the empty output of the failed step.

The full run directory stays on Expanse: <SCRATCH>/temp_project/c8-d2-indep/runs/prod1.
