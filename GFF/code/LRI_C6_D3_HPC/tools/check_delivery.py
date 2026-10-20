#!/usr/bin/env python3
"""Verify every shipped payload against the distribution manifest (same check as `tools/checksums.py verify --strict`):
a missing or changed listed file, or a package file that the manifest does not list, fails."""
import json,sys
from checksums import check
r=check();bad=[{'file':f,'error':'missing'}for f in r['missing']]+[{'file':f,'error':'sha256 mismatch'}for f in r['changed']]
bad+=[{'file':f,'error':'not listed in SHA256SUMS_HPC.json'}for f in r['unlisted']]
print(json.dumps({'checked_files':r['listed'],'ok':not bad,'failures':bad},indent=2))
sys.exit(bool(bad))
