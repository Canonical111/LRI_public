#!/bin/bash
# Kept for old instructions: the analysis is run by `make replay` from NRG/, which works in the hidden workspace .work/
# and never writes into the released folders. This script only calls it.
set -euo pipefail
exec make -C "$(cd "$(dirname "$0")/../.." && pwd)" replay "$@"
