#!/bin/sh
# c8d3 exec guard (plan D.11 step 5): runs inside `timeout -s KILL 120`; execs its command (sbatch) only while the wall
# clock is still within the intent's utc + 60 s (argument 1, Unix seconds), else exits 86 with the marker below.
d=$1; shift; case "$d" in ''|*[!0-9]*) echo 'c8d3-exec-guard: bad deadline' >&2; exit 64;; esac; [ "$(date +%s)" -le "$d" ] && exec "$@"; echo 'c8d3-exec-guard: late' >&2; exit 86
