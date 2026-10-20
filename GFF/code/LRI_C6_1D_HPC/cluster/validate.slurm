#!/bin/bash
#SBATCH -p defq -N 1 --exclusive --mem=180G -t 08:00:00
#SBATCH -o /mnt/beegfs/zzheng1/lri_c6_1d/logs/%x_%j.out
# Validation gates V3-V6, V8-V10 (PLAN.md rev 5, 4.6). PART=dbl | ld | l5; each part owns $ATTEMPT_DIR/$PART.json and
# stops at the first failed gate. All gate levels and runs live inside the attempt directory (never reused by, or
# taken from, production). The binaries and data must still match the identities recorded by prepare.
set -euo pipefail
source "$C6_CODE/cluster/env.sh"
: "${ATTEMPT_DIR:?}"
case "${PART:-}" in dbl|ld|l5|xarch) ;; *) echo "PART must be dbl, ld, l5 or xarch (got '${PART:-}')" >&2; exit 2 ;; esac
[[ "$(c6_identities)" == "$(cat "$ATTEMPT_DIR/identities.json")" ]] || { echo "binaries/data changed since prepare" >&2; exit 1; }
export C6_LEVELS=$ATTEMPT_DIR/levels C6_RUNS=$ATTEMPT_DIR/runs; mkdir -p "$C6_LEVELS" "$C6_RUNS"
cd "$C6_CODE"; V=$ATTEMPT_DIR/$PART.json; rm -f "$V"; R=$C6_CODE/reference; T=$(phys_alloc)
REC=/mnt/beegfs/zzheng1/lri_c6_1d/recon/work/full_H_L6_N6_comp40_0_10000.json
lvl(){ local L=$1 N=$2 MODE=$3 S=$4 K=$5 P=$6 M=$7 TH=${8:-$T}
  local stem=L${L}_${MODE}_${S}_N${N}.${K}; (( P )) && stem+=.pert$P; (( M == 10 )) && stem+=.mod10
  local sub=all; (( M == 10 )) && sub=mod10; local bin=bin/c6sum; [[ $K == ld ]] && bin=bin/c6sum_ld
  [[ -e $C6_LEVELS/$stem.json ]] && { echo "have $stem"; return 0; }
  mkdir -p "$C6_RUNS/$stem"; local nsect=$(( L == 6 ? 360 : 60 ))
  /usr/bin/time -f "$stem %e s %M KB" $bin $L $N $TH "$C6_DATA" $MODE --out "$C6_RUNS/$stem/part_000_$(printf %03d $nsect).jsonl" --first 0 --stop $nsect --mod $M --stratum $S --perturb $P 2> "$C6_RUNS/$stem/engine.err" || { tail -3 "$C6_RUNS/$stem/engine.err"; return 1; }
  tail -1 "$C6_RUNS/$stem/engine.err"
  python tools/merge.py --leveldir "$C6_LEVELS" "$C6_RUNS/$stem"/part_*.jsonl --subset $sub; }
lv(){ echo "$C6_LEVELS/$1.json"; }
P6='--pole-rel 1e-12 --poles 0,1,2,3,6,7,8,9'
# Saved original records carry their uncompensated-summation errors (measured up to 2.3e-9 relative against our long
# double, L5 J16 eps^0); reproduction tolerance 1e-8 (plan 9). Our double vs long double must agree to 1e-9.
RT=1e-8
case $PART in
dbl)
  lvl 6 6 H all dbl 0 1
  python tools/validate.py $V vector V3_all_N6_vs_reference $(lv L6_H_all_N6.dbl) $R/full_H_L6_N6_0_10000.json --rel 1e-9 $P6
  python tools/validate.py $V vector V3_all_N6_vs_recon_compensated $(lv L6_H_all_N6.dbl) $REC --rel 1e-12
  for N in 6 8 10; do lvl 6 $N H hard dbl 0 1; done
  python tools/validate.py $V vector V4_hard_dbl_N6 $(lv L6_H_hard_N6.dbl) $R/full_H_hard_L6_N6_0_10000.json --rel $RT $P6
  for N in 8 10; do python tools/validate.py $V vector V4_hard_dbl_N$N $(lv L6_H_hard_N$N.dbl) $R/full_H_hard_packed_L6_N${N}_0_10000.json --rel $RT $P6; done
  for N in 6 8; do lvl 6 $N H light dbl 0 1; lvl 6 $N H all dbl 0 1; done
  for N in 6 8; do python tools/validate.py $V partition V8_partition_N$N $(lv L6_H_all_N$N.dbl) $(lv L6_H_light_N$N.dbl) $(lv L6_H_hard_N$N.dbl) --rel 1e-12; done
  X=$C6_RUNS/validation_scratch_dbl; rm -rf $X; mkdir -p $X; PROD=$C6_RUNS/L6_H_light_N8.dbl/part_000_360.jsonl
  bin/c6sum 6 8 20 "$C6_DATA" H --out $X/t20.jsonl --stratum light 2> $X/t20.err
  python tools/validate.py $V same-sectors V5_light_dbl_N8_20_vs_40_threads --a $X/t20.jsonl --b $PROD
  for r in "0 97" "97 211" "211 360"; do set -- $r; bin/c6sum 6 8 $T "$C6_DATA" H --out $X/s_$1.jsonl --first $1 --stop $2 --stratum light 2>> $X/split.err; done
  python tools/validate.py $V same-sectors V5_light_dbl_N8_split --a $X/s_0.jsonl $X/s_97.jsonl $X/s_211.jsonl --b $PROD
  set +e; timeout 25 bin/c6sum 6 8 $T "$C6_DATA" H --out $X/r.jsonl --first 100 --stop 200 --stratum light 2> $X/r1.err; set -e
  n1=$(grep -c '"type":"sector"' $X/r.jsonl || true); echo "killed after $n1 sectors"
  bin/c6sum 6 8 $T "$C6_DATA" H --out $X/r.jsonl --first 100 --stop 200 --stratum light 2> $X/r2.err
  python tools/validate.py $V same-sectors V6_resume_light_dbl_N8 --a $X/r.jsonl --b $PROD
  set +e
  python - $X/r.jsonl $n1 <<'PY'
import sys, json
recs = [json.loads(l) for l in open(sys.argv[1])]
s = [r['sector'] for r in recs if r['type'] == 'sector']; a = [r for r in recs if r['type'] == 'attempt']
ok = sorted(s) == list(range(100, 200)) and len(set(s)) == 100 and len(a) == 2 and 0 < int(sys.argv[2]) < 100
print('resume file:', len(s), 'sectors,', len(a), 'attempts, killed after', sys.argv[2]); sys.exit(0 if ok else 1)
PY
  st=$?; set -e
  python tools/validate.py $V check V6_resume_structure $st "100 unique sectors, 2 attempts, interrupted after $n1"
  set +e; bin/c6sum 6 8 $T "$C6_DATA" H --out $X/r.jsonl --first 100 --stop 200 --stratum light --comp 2 2> $X/r3.err; rc=$?; set -e
  python tools/validate.py $V expect-fail V6_resume_refuses_changed_fingerprint $rc
  bin/c6sum 6 8 $T "$C6_DATA" H --out $X/comp2.jsonl --stratum light --comp 2 2> $X/comp2.err
  python tools/merge.py $X/comp2_level.json $X/comp2.jsonl
  python tools/validate.py $V c6diff V9_comp2_minus_comp1_light_N8 $X/comp2_level.json $(lv L6_H_light_N8.dbl)
  ;;
ld)
  for N in 6 8; do lvl 6 $N H hard ld 0 1; done
  python tools/validate.py $V vector V4_hard_ld_N6 $(lv L6_H_hard_N6.ld) $R/full_H_hard_L6_N6_0_10000.json --rel $RT $P6
  python tools/validate.py $V vector V4_hard_ld_N8 $(lv L6_H_hard_N8.ld) $R/full_H_hard_packed_L6_N8_0_10000.json --rel $RT $P6
  until [[ -e $(lv L6_H_hard_N8.dbl) ]]; do sleep 30; done
  for N in 6 8; do python tools/validate.py $V vector V4b_hard_N${N}_dbl_vs_ld $(lv L6_H_hard_N$N.dbl) $(lv L6_H_hard_N$N.ld) --rel 1e-9; done
  X=$C6_RUNS/validation_scratch_ld; rm -rf $X; mkdir -p $X; PROD=$C6_RUNS/L6_H_hard_N6.ld/part_000_360.jsonl
  bin/c6sum_ld 6 6 20 "$C6_DATA" H --out $X/t20.jsonl --stratum hard 2> $X/t20.err
  python tools/validate.py $V same-sectors V5_hard_ld_N6_20_vs_40_threads --a $X/t20.jsonl --b $PROD
  for r in "0 97" "97 211" "211 360"; do set -- $r; bin/c6sum_ld 6 6 $T "$C6_DATA" H --out $X/s_$1.jsonl --first $1 --stop $2 --stratum hard 2>> $X/split.err; done
  python tools/validate.py $V same-sectors V5_hard_ld_N6_split --a $X/s_0.jsonl $X/s_97.jsonl $X/s_211.jsonl --b $PROD
  lvl 6 6 H all ld 0 1
  until [[ -e $(lv L6_H_all_N6.dbl) ]]; do sleep 30; done
  python tools/validate.py $V c6diff V10_all_N6_ld_minus_dbl $(lv L6_H_all_N6.ld) $(lv L6_H_all_N6.dbl)
  ;;
l5)
  for K in dbl ld; do for M in 12 16; do lvl 5 $M H all $K 0 1; lvl 5 $M J all $K 0 1; done
    python tools/validate.py $V vector V4_L5_H16_$K $(lv L5_H_all_N16.$K) $R/full_H_L5_N16_0_10000.json --rel $RT --pole-rel 1e-12 --poles 0,1,2,5,6,7
    python tools/validate.py $V vector V4_L5_J16_$K $(lv L5_J_all_N16.$K) $R/full_J_L5_N16_0_10000.json --rel $RT --pole-rel 1e-12 --poles 0,1,2,6,7,8
    python tools/validate.py $V vector V4_L5_J12_$K $(lv L5_J_all_N12.$K) $R/full_J_L5_N12_0_10000.json --rel $RT --pole-rel 1e-12 --poles 0,1,2,6,7,8
  done
  for M in 12 16; do for X in H J; do python tools/validate.py $V vector V4b_L5_${X}${M}_dbl_vs_ld $(lv L5_${X}_all_N$M.dbl) $(lv L5_${X}_all_N$M.ld) --rel 1e-9; done; done
  ;;
xarch)
  # Cross-architecture check (V11): rerun on the other node type (defq, Intel) what dbl/ld/l5 computed on amdq (AMD).
  # Double: bitwise-identical sector values required. Long double: per-entry agreement <= 1e-14 (see below). Also
  # require that the two runs really used different CPU models.
  X=$ATTEMPT_DIR/runs/xarch; rm -rf $X; mkdir -p $X
  bin/c6sum 6 8 $T "$C6_DATA" H --out $X/light8.jsonl --stratum light 2> $X/light8.err
  python tools/validate.py $V same-sectors V11_xarch_light_dbl_N8 --a $X/light8.jsonl --b $C6_RUNS/L6_H_light_N8.dbl/part_000_360.jsonl
  bin/c6sum_ld 6 6 $T "$C6_DATA" H --out $X/hard6.jsonl --stratum hard 2> $X/hard6.err
  # Long double: glibc logl/cosl use x87 transcendental instructions whose last bits differ between CPU vendors
  # (measured: <= 1.0e-16 relative per entry, <= 5e-15 in C6). Gate: per-entry relative agreement <= 1e-14.
  python tools/validate.py $V close-sectors V11_xarch_hard_ld_N6 --rel 1e-14 --a $X/hard6.jsonl --b $C6_RUNS/L6_H_hard_N6.ld/part_000_360.jsonl
  bin/c6sum_ld 5 16 $T "$C6_DATA" J --out $X/j16.jsonl 2> $X/j16.err
  python tools/validate.py $V close-sectors V11_xarch_L5_J16_ld --rel 1e-14 --a $X/j16.jsonl --b $C6_RUNS/L5_J_all_N16.ld/part_000_060.jsonl
  set +e
  python - $X/light8.jsonl $C6_RUNS/L6_H_light_N8.dbl/part_000_360.jsonl <<'PY'
import sys, json
cpu = [{json.loads(l)['cpu'] for l in open(f) if '"type":"attempt"' in l} for f in sys.argv[1:]]
print('cpus:', cpu); sys.exit(0 if cpu[0] and cpu[1] and not (cpu[0] & cpu[1]) else 1)
PY
  st=$?; set -e
  python tools/validate.py $V check V11_xarch_cpus_differ $st "xarch node: $(lscpu | grep -m1 'Model name' | sed 's/ \+/ /g')"
  ;;
esac
echo "validate $PART done $(date)"
