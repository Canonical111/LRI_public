#!/bin/bash
# validate_all.sh: the single validation entry point (PLAN.md rev 5, 4.6 and 8).
# Creates a fresh attempt directory and withdraws the active approval. Submits prepare (V1, V2) -> dbl / ld / l5 gate
# jobs (afterok) -> a collector (afterany). The collector writes validation/APPROVED.json only if every required gate
# of this attempt passed and the binaries and data still match the identities recorded by prepare.
# Attempts are serialized with production: refused while any validation or production job is queued or running (or
# squeue fails), under the campaign lock (prepare rewrites the shared binaries and inputs). Each attempt owns validation/CURRENT_ATTEMPT; a collector publishes approval only if it still owns it.
set -euo pipefail
source "$(dirname "$0")/env.sh"
c6_lock campaign
n=$(c6_active_jobs '^c6(prep|val_|valsum|_|m_|prod|l5|rep)') || exit 1
(( n == 0 )) || { echo "$n validation or production jobs still queued or running; validation needs an idle campaign" >&2; exit 1; }
mkdir -p "$C6_HOME/validation/attempts" "$C6_LOGS"
AD=$(mktemp -d "$C6_HOME/validation/attempts/$(date +%Y%m%dT%H%M%S)_$(cat "$C6_CODE/GIT_SHA" 2>/dev/null || echo nogit)_XXXXXX")
ID=$(basename "$AD")
rm -f "$C6_HOME/validation/APPROVED.json"
echo "$ID" > "$C6_HOME/validation/CURRENT_ATTEMPT.tmp" && mv "$C6_HOME/validation/CURRENT_ATTEMPT.tmp" "$C6_HOME/validation/CURRENT_ATTEMPT"
# Routing (user: prioritize amdq): prepare on amddebugq (debugq fallback); the gate jobs on amdq (AMD); the
# cross-architecture job on defq (Intel) after them, so V11 compares AMD and Intel results bitwise.
P=$(sbatch --parsable -p amddebugq,debugq --export=ALL,C6_CODE=$C6_CODE,ATTEMPT_DIR=$AD "$C6_CODE/cluster/prepare.slurm")
ids=()
for part in dbl ld l5; do
  j=$(sbatch --parsable -J c6val_$part -p amdq --dependency=afterok:$P --kill-on-invalid-dep=yes --export=ALL,C6_CODE=$C6_CODE,PART=$part,ATTEMPT_DIR=$AD "$C6_CODE/cluster/validate.slurm")
  ids+=("$j")
done
x=$(sbatch --parsable -J c6val_xarch -p defq -t 02:00:00 --dependency=afterok:$(IFS=:; echo "${ids[*]}") --kill-on-invalid-dep=yes --export=ALL,C6_CODE=$C6_CODE,PART=xarch,ATTEMPT_DIR=$AD "$C6_CODE/cluster/validate.slurm")
ids+=("$x")
REQ=V1_enumeration_nv6,V1_enumeration_nv7,V1_refuse_graphs_truncated_by_4,V1_refuse_graphs_truncated_by_92
REQ+=,V2_weights_L6_vs_prepare80,V2_weights_L5_vs_prepare80,V2_weights_selfcheck_L5,V2_weights_selfcheck_L6
REQ+=,V3_all_N6_vs_reference,V3_all_N6_vs_recon_compensated,V4_hard_dbl_N6,V4_hard_dbl_N8,V4_hard_dbl_N10,V4_hard_ld_N6,V4_hard_ld_N8
REQ+=,V4_L5_H16_dbl,V4_L5_J16_dbl,V4_L5_J12_dbl,V4_L5_H16_ld,V4_L5_J16_ld,V4_L5_J12_ld
REQ+=,V4b_hard_N6_dbl_vs_ld,V4b_hard_N8_dbl_vs_ld,V4b_L5_H12_dbl_vs_ld,V4b_L5_J12_dbl_vs_ld,V4b_L5_H16_dbl_vs_ld,V4b_L5_J16_dbl_vs_ld
REQ+=,V5_light_dbl_N8_20_vs_40_threads,V5_light_dbl_N8_split,V5_hard_ld_N6_20_vs_40_threads,V5_hard_ld_N6_split
REQ+=,V6_resume_light_dbl_N8,V6_resume_structure,V6_resume_refuses_changed_fingerprint,V8_partition_N6,V8_partition_N8
REQ+=,V9_comp2_minus_comp1_light_N8,V10_all_N6_ld_minus_dbl
REQ+=,V11_xarch_light_dbl_N8,V11_xarch_hard_ld_N6,V11_xarch_L5_J16_ld,V11_xarch_cpus_differ
D=$(IFS=:; echo "${ids[*]}")
cat > "$AD/collect.sh" <<EOS
#!/bin/bash
source $C6_CODE/cluster/env.sh
python $C6_CODE/tools/validate.py $AD/summary.json collect - \$(ls $AD/{prepare,dbl,ld,l5,xarch}.json 2>/dev/null) --require $REQ || exit 1
cur=\$(c6_identities); [[ "\$cur" == "\$(cat $AD/identities.json)" ]] || { echo "identities changed during validation" >&2; exit 1; }
python - "$AD" "\$cur" "$C6_HOME/validation/APPROVED.json" "$C6_HOME/validation/CURRENT_ATTEMPT" <<'PY'
import sys, json, os
ad, cur, out, token = sys.argv[1], json.loads(sys.argv[2]), sys.argv[3], sys.argv[4]
if open(token).read().strip() != os.path.basename(ad):
    sys.exit(f'attempt {ad} is no longer current; not publishing approval')
s = json.load(open(f'{ad}/summary.json'))
rec = {'pass': s['pass'] is True, 'attempt': ad, 'identities': cur}
tmp = out + '.tmp'; json.dump(rec, open(tmp, 'w'), indent=1, sort_keys=True); os.replace(tmp, out)
print('APPROVED', ad)
PY
EOS
C=$(sbatch --parsable -J c6valsum -p sharedq -N 1 -n 1 -c 1 --mem=2G -t 00:10:00 --dependency=afterany:$D -o "$C6_LOGS/%x_%j.out" "$AD/collect.sh")
echo "$(date +%F_%T) validation attempt $ID: prepare=$P dbl/ld/l5=${ids[*]} collector=$C" | tee -a "$C6_HOME/SUBMITTED.txt"
