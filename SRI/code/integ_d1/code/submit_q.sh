#!/bin/bash
# usage: submit_q.sh QUEUEFILE    (lines: CE TASKFILE, in priority order)
# Login-node helper: only polls sinfo/squeue and calls sbatch (no computation). Rules: submit only onto a partition
# with an idle node (amdq first, then defq); --exclude=cn112; never longq/preq/amdpreq. An amdq job takes the next two
# task files (one per socket, 32 threads each); a defq job takes one. A task file is never submitted twice: every
# submission is appended to logs/submitted_<queue>.txt and files listed there, or whose outputs all exist with
# fingerprints, are skipped. Exits when every file is submitted or skipped.
# MSC-025: state is appended only after sbatch returns a numeric job id (failures are retried after 60 s); missing,
# empty or unreadable task files stop the submitter with exit status 2.
export PATH=$PATH:/cm/shared/apps/slurm/current/bin
q=$1; state=../../logs/submitted_$(basename $q .txt).txt; touch $state
TIME=${TIME:-12:00:00}
idle() { sinfo -h -p $1 -N -o "%N %t" | awk '$2=="idle" && $1!="cn112"' | sort -u | wc -l; }
done_file() { local f=$1; [ -r "$f" ] && [ -s "$f" ] || return 2; while read -r out args; do [ -z "$out" ] && continue; [ -f ../../results/m4/$out.out ] && [ -f ../../results/m4/$out.out.fp ] || return 1; done < "$f"; return 0; }
# MSC-025: a task file that is missing, empty or unreadable is an error (never "complete")
checkfiles() { while read -r ce f; do [ -z "$f" ] && continue; [ -r "$f" ] && [ -s "$f" ] || { echo "$(date +%T) ERROR: task file $f missing or unreadable" >&2; exit 2; }; [ -x "$ce" ] || { echo "$(date +%T) ERROR: engine $ce not executable" >&2; exit 2; }; done < $q; }
# MSC-025: record a submission only after sbatch returned a numeric job id
submit() { local id; id=$(sbatch --parsable "$@" 2>&1); if [[ "$id" =~ ^[0-9]+(;.*)?$ ]]; then echo "${id%%;*}"; return 0; fi; echo "$(date +%T) sbatch failed: $id" >&2; return 1; }
pending() { while read -r ce f; do [ -z "$f" ] && continue; grep -qx "$f" $state && continue; done_file "$f"; r=$?; [ $r -eq 2 ] && { echo "$(date +%T) ERROR: task file $f unreadable" >&2; exit 2; }; [ $r -eq 0 ] && { echo "$(date +%T) skip $f: complete" >&2; echo "$f" >> $state; continue; }; echo "$ce $f"; done < $q; }
while true; do
  checkfiles      # in the main shell, so a missing or unreadable task file stops the submitter
  todo=(); while IFS= read -r l; do todo+=("$l"); done < <(pending)
  [ ${#todo[@]} -eq 0 ] && break
  if [ $(idle amdq) -ge 1 ]; then
    a=(${todo[0]}); b=(${todo[1]:-})
    if [ ${#b[@]} -eq 2 ]; then
      if id=$(submit --time=$TIME --job-name=integ-m4amd_$(basename ${a[1]} .tasks) m4_tasks_amd.sbatch ${a[0]} ${a[1]} ${b[0]} ${b[1]}); then
        echo "$(date +%T) amdq $id: ${a[1]} ${b[1]}"; echo "${a[1]}" >> $state; echo "${b[1]}" >> $state
      else sleep 60; fi
    else
      if id=$(submit --time=$TIME --job-name=integ-m4amd_$(basename ${a[1]} .tasks) m4_tasks_amd.sbatch ${a[0]} ${a[1]}); then
        echo "$(date +%T) amdq $id: ${a[1]}"; echo "${a[1]}" >> $state
      else sleep 60; fi
    fi
    sleep 15; continue
  fi
  if [ $(idle defq) -ge 1 ]; then
    a=(${todo[0]})
    if id=$(submit --time=$TIME --exclude=cn112 --job-name=integ-m4$(basename ${a[1]} .tasks) --export=ALL,CE=${a[0]} m4_tasks.sbatch ${a[1]}); then
      echo "$(date +%T) defq $id: ${a[1]}"; echo "${a[1]}" >> $state
    else sleep 60; fi
    sleep 15; continue
  fi
  sleep 30
done
echo "$(date +%T) submitter done"
