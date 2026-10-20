#!/bin/bash
# Build the package as ONE tarball plus a sha256 file, optionally upload it to a
# site's shared filesystem and unpack a verified code copy in $HOME there (for
# submit.py). Site wrappers: cluster/expanse/make_tarball.sh, cluster/symmetry/make_tarball.sh.
#
#   cluster/sitekit/make_tarball.sh [--commit REV] [--allow-dirty] [--out DIR]
#                                   [--upload SITE] [--remote-root PATH]
#
# The tarball contains `git archive REV` under lri_c2/ plus
#   lri_c2/STAGE_INFO.json        commit, tree, dirty flag, creation time
#   lri_c2/STAGE_MANIFEST.sha256  sha256 of every other file in the tarball
# Jobs copy the tarball to node-local scratch, check <name>.tar.sha256, extract,
# and check STAGE_MANIFEST.sha256 before running anything (fail closed).
# Name: lri_c2_<12-hex commit>.tar; with --allow-dirty and uncommitted changes to
# tracked files: lri_c2_<commit>_dirty<UTC time>.tar (testing only).
#
# --upload SITE (expanse or symmetry) reads cluster/SITE/profile.json: it copies
#   <name>.tar(.sha256) over ssh to <persistent_root>/pkg/ on the site's host
#   (Expanse: /expanse/lustre/scratch/$USER/temp_project/lri_c2, symmetry:
#   /mnt/beegfs/$USER/lri_c2; --remote-root overrides), verifies it there, then
#   unpacks a verified code copy into <code_root>/<name>/ (~/lri_c2/pkgs/<name>/).
#   Existing uploads with the same name and checksum are reused; a different
#   checksum is refused.
set -eo pipefail
umask 022
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
REV=HEAD; ALLOW_DIRTY=0; OUT="$ROOT/outputs/site_pkg"; SITE=""; REMOTE_ROOT=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --commit) REV=$2; shift 2 ;;
        --allow-dirty) ALLOW_DIRTY=1; shift ;;
        --out) OUT=$2; shift 2 ;;
        --upload) SITE=$2; shift 2 ;;
        --remote-root|--lustre-root) REMOTE_ROOT=$2; shift 2 ;;
        -h|--help) sed -n '2,24p' "$0"; exit 0 ;;
        *) echo "unknown option $1" >&2; exit 64 ;;
    esac
done
if [[ -n "$SITE" ]]; then
    [[ -f "$ROOT/cluster/$SITE/profile.json" ]] || { echo "no site profile cluster/$SITE/profile.json" >&2; exit 64; }
    # Host, shared root and code root from the profile; {user}/{home} are expanded on the host.
    read -r HOST PROFILE_ROOT CODE_ROOT < <(python3 -c '
import json, sys
p = json.load(open(sys.argv[1]))
fmt = lambda s: s.replace("{user}", "$USER").replace("{home}", "$HOME")
print(p["ssh_host"], fmt(p["paths"]["persistent_root"]), fmt(p["paths"]["code_root"]))' "$ROOT/cluster/$SITE/profile.json")
    remote_root=${REMOTE_ROOT:-$PROFILE_ROOT}
fi
if command -v sha256sum > /dev/null; then SHA=(sha256sum); else SHA=(shasum -a 256); fi

cd "$ROOT"
git rev-parse --is-inside-work-tree > /dev/null 2>&1 || { echo "not a git checkout: $ROOT" >&2; exit 64; }
commit=$(git rev-parse --verify "$REV^{commit}")
tree_ref=$commit; dirty=false
if [[ "$REV" == HEAD && -n "$(git status --porcelain --untracked-files=no)" ]]; then
    [[ $ALLOW_DIRTY == 1 ]] || { echo "uncommitted changes to tracked files; commit them or pass --allow-dirty (testing only)" >&2; exit 65; }
    tree_ref=$(git stash create)   # commit object of the working tree (tracked files), index untouched
    dirty=true
fi
name="lri_c2_${commit:0:12}"
# Clean builds are reproducible byte for byte (same commit -> same sha256): the
# archive entries carry the commit time (git archive), STAGE_INFO.json records
# the commit time, and the two added files get that mtime. Dirty builds are
# unique by construction (their name and STAGE_INFO carry the build time).
epoch=$(git show -s --format=%ct "$commit")
stamp=$(python3 -c 'import datetime,sys; print(datetime.datetime.fromtimestamp(int(sys.argv[1]), datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))' "$epoch")
if [[ $dirty == true ]]; then
    epoch=$(date +%s)
    stamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    name="${name}_dirty$(date -u +%Y%m%dT%H%M%SZ)"
fi

mkdir -p "$OUT"
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
git archive --format=tar --prefix=lri_c2/ "$tree_ref" | tar -x -C "$work"
nfiles=$(cd "$work/lri_c2" && find . -type f | wc -l | tr -d ' ')
cat > "$work/STAGE_INFO.json" <<EOF
{
  "name": "$name",
  "commit": "$commit",
  "archived_tree": "$(git rev-parse "$tree_ref^{tree}")",
  "dirty": $dirty,
  "created_utc": "$stamp",
  "created_utc_is": "$([[ $dirty == true ]] && echo build time || echo commit time)",
  "git_files": $nfiles,
  "scope": "Code and data snapshot staged by the cluster jobs; see cluster/sitekit/README.md."
}
EOF
cp "$work/STAGE_INFO.json" "$work/lri_c2/STAGE_INFO.json"
( cd "$work/lri_c2" && find . -type f ! -name STAGE_MANIFEST.sha256 -print0 | LC_ALL=C sort -z \
    | xargs -0 "${SHA[@]}" | sed 's#  \./#  #' ) > "$work/STAGE_MANIFEST.sha256"
python3 -c 'import os, sys; t = int(sys.argv[1]); [os.utime(f, (t, t)) for f in sys.argv[2:]]' "$epoch" \
    "$work/STAGE_INFO.json" "$work/STAGE_MANIFEST.sha256"
MTIME=()   # git >= 2.42; older git already stamps the entries of a commit with its time
git archive -h 2>&1 | grep -q -- '--mtime' && MTIME=(--mtime="@$epoch")
git archive --format=tar "${MTIME[@]}" --prefix=lri_c2/ --add-file="$work/STAGE_INFO.json" \
    --add-file="$work/STAGE_MANIFEST.sha256" "$tree_ref" > "$OUT/$name.tar"
( cd "$OUT" && "${SHA[@]}" "$name.tar" > "$name.tar.sha256" )
# Self-check: the tarball extracts and its manifest verifies.
mkdir "$work/check"
tar -xf "$OUT/$name.tar" -C "$work/check"
( cd "$work/check/lri_c2" && "${SHA[@]}" -c --quiet STAGE_MANIFEST.sha256 ) || { echo "manifest self-check failed" >&2; exit 74; }
echo "BUILT $OUT/$name.tar ($(du -h "$OUT/$name.tar" | cut -f1), $nfiles files + 2; dirty=$dirty)"
cat "$OUT/$name.tar.sha256"

[[ -n "$SITE" ]] || exit 0
ssh -T -o BatchMode=yes "$HOST" "mkdir -p $remote_root/pkg"
if ssh -T -o BatchMode=yes "$HOST" "test -e $remote_root/pkg/$name.tar"; then
    echo "already on $HOST: $remote_root/pkg/$name.tar (checking it)"
else
    scp -q -o BatchMode=yes "$OUT/$name.tar" "$HOST:$(ssh -T -o BatchMode=yes "$HOST" "echo $remote_root")/pkg/.$name.tar.part"
    ssh -T -o BatchMode=yes "$HOST" "mv $remote_root/pkg/.$name.tar.part $remote_root/pkg/$name.tar"
    scp -q -o BatchMode=yes "$OUT/$name.tar.sha256" "$HOST:$(ssh -T -o BatchMode=yes "$HOST" "echo $remote_root")/pkg/$name.tar.sha256"
fi
# Verify on the host (fails if an older upload of the same name has another checksum).
ssh -T -o BatchMode=yes "$HOST" "cd $remote_root/pkg && cmp -s $name.tar.sha256 - && sha256sum -c $name.tar.sha256" \
    < "$OUT/$name.tar.sha256" || { echo "remote tarball or checksum differs from the local build: $name" >&2; exit 74; }
ssh -T -o BatchMode=yes "$HOST" "set -e
dest=$CODE_ROOT/$name
if [ -d \"\$dest\" ]; then
    (cd \"\$dest\" && sha256sum -c --quiet STAGE_MANIFEST.sha256) || { echo \"existing code copy \$dest does not verify; inspect or remove it\" >&2; exit 74; }
    echo \"code copy verified: \$dest\"; exit 0
fi
mkdir -p $CODE_ROOT; tmp=$CODE_ROOT/.$name.tmp.\$\$; mkdir -p \"\$tmp\"
tar -xf $remote_root/pkg/$name.tar -C \"\$tmp\"
(cd \"\$tmp/lri_c2\" && sha256sum -c --quiet STAGE_MANIFEST.sha256)
mv \"\$tmp/lri_c2\" \"\$dest\"; rmdir \"\$tmp\"
echo \"code copy: \$dest\"" || { echo "the code copy on $HOST could not be created or verified" >&2; exit 74; }
echo "UPLOADED $name to $HOST:$remote_root/pkg/ ; submit from $CODE_ROOT/$name on $HOST ($SITE)"
