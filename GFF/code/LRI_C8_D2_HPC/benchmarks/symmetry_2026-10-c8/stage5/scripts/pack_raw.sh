#!/bin/bash
# Pack the small, non-scientific campaign files of the Stage-5 symmetry campaigns into raw_evidence.tgz (run on the
# symmetry login node): manifest.json, submissions.jsonl, slurm_logs/, sweep_logs/, lanes/ (queue,
# done markers, invalidation log, claim/failure records, per-attempt index logs), every group's config.json and
# merged.json, C8_test_result.json, and the measurement-hook records (*-rchar/). Checkpoints, tasks.sqlite, per-index
# task files, nets and the graph tables stay on BeeGFS (their sha256 are in the merged.json files); each campaign's
# cost_model.json (a 5 MB copy of the model it was planned with) is listed by sha256 in campaign_cost_models.sha256.
#   bash pack_raw.sh OUT.tgz
set -euo pipefail
out=${1:?OUT.tgz}; cd <SCRATCH>/c8-d2
C="smoke1-20261005 smoke1-20261005-twin drills-5d7586e9f1ab/drA drills-5d7586e9f1ab/drB drl23-20261005 sweep2-5d7586e9f1ab sweep3-5d7586e9f1ab sweep3amd-5d7586e9f1ab desb1-20261005 desb2-20261005 desc1-20261005 desc2-20261005 smk4-20261005 pilot1-20261005 perf5-final-5d7586e9f1ab perf5-baseline-5d7586e9f1ab"
L=$(mktemp); for c in $C; do [ -d "$c" ] || continue
  for f in manifest.json submissions.jsonl C8_test_result.json; do [ -f "$c/$f" ] && echo "$c/$f"; done
  for d in slurm_logs sweep_logs lanes; do [ -d "$c/$d" ] && find "$c/$d" -type f; done
  find "$c/groups" -maxdepth 2 \( -name config.json -o -name merged.json \) -type f
done > "$L"; for d in smoke1-20261005-rchar smk4-20261005-rchar; do [ -d "$d" ] && find "$d" -type f >> "$L"; done
for c in $C; do [ -f "$c/cost_model.json" ] && sha256sum "$c/cost_model.json"; done > campaign_cost_models.sha256; echo campaign_cost_models.sha256 >> "$L"
tar czf "$out" -T "$L"; rm -f campaign_cost_models.sha256; echo "$(wc -l < "$L") files -> $out ($(du -h "$out" | cut -f1))"; rm -f "$L"
