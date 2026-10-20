#!/bin/bash
# Install one release on Expanse (login node):  bash install.sh /path/to/<commit12>.tar <tar-sha256>
#  * copies the tarball (one file) to $HT3D_DATA/releases/ unless already there, never overwriting;
#  * unpacks a read-only reference copy to ~/ht3d/code/<commit12> and verifies RELEASE.sha256;
#  * creates the pinned venv once (python/3.11.9 module) and verifies its pins every time.
# No `set -u` (site module init is not nounset-safe).
set -eo pipefail
tar_in=${1:?usage: install.sh TAR SHA256}; want=${2:?usage: install.sh TAR SHA256}
module purge
module load cpu/0.21.2a gcc/13.3.0 python/3.11.9 slurm/expanse/23.02.7
HT3D_DATA=${HT3D_DATA:-/expanse/lustre/scratch/$USER/temp_project/ht3d}
HT3D_VENV=${HT3D_VENV:-$HT3D_DATA/venv-py3119-np235-sp1170-nb0651}
name=$(basename "$tar_in"); tag=${name%.tar}
got=$(sha256sum "$tar_in" | cut -d' ' -f1)
[ "$got" = "$want" ] || { echo "install: tarball sha256 $got != $want" >&2; exit 74; }
mkdir -p "$HT3D_DATA"/{releases,logs,validation,campaigns,probe}
rel=$HT3D_DATA/releases/$name
if [ -e "$rel" ]; then
  [ "$(sha256sum "$rel" | cut -d' ' -f1)" = "$want" ] || { echo "install: $rel exists with different content" >&2; exit 74; }
else
  cp "$tar_in" "$rel.tmp.$$" && mv -n "$rel.tmp.$$" "$rel"
  [ "$(sha256sum "$rel" | cut -d' ' -f1)" = "$want" ] || { echo "install: copy corrupted" >&2; exit 74; }
  chmod a-w "$rel"
fi
echo "$want  $name" > "$HT3D_DATA/releases/$name.sha256"
code=$HOME/ht3d/code/$tag
if [ ! -d "$code" ]; then
  mkdir -p "$code.tmp.$$" && tar -xf "$rel" -C "$code.tmp.$$" && mv -n "$code.tmp.$$" "$code"
fi
( cd "$code" && sha256sum -c --quiet --strict RELEASE.sha256 ) || { echo "install: reference copy $code does not verify" >&2; exit 74; }
chmod -R a-w "$code"
if [ ! -x "$HT3D_VENV/bin/python" ]; then
  python3 -m venv "$HT3D_VENV"
  "$HT3D_VENV/bin/python" -m pip install --upgrade --no-cache-dir pip
  "$HT3D_VENV/bin/python" -m pip install --no-cache-dir -r "$code/cluster/expanse/requirements-expanse.txt"
fi
"$HT3D_VENV/bin/python" -m pip freeze > "$HT3D_VENV/freeze.txt"
missing=0
while read -r pin; do
  case "$pin" in ''|\#*) continue;; esac
  grep -qixF "$pin" "$HT3D_VENV/freeze.txt" || { echo "install: venv lacks pin $pin" >&2; missing=1; }
done < "$code/cluster/expanse/requirements-expanse.txt"
[ "$missing" = 0 ] || exit 74
echo "installed release $tag"
echo "  tarball   $rel"
echo "  sha256    $want"
echo "  reference $code"
echo "  venv      $HT3D_VENV"
