"""Sequential per-node lanes; every item runs in a fresh process with its own lock.

No hard-coded account, expiry, partition, or automatic unbounded retries.
"""
from __future__ import annotations
import json,os,signal,subprocess,sys
from pathlib import Path
from .runtime import fingerprint,require_receipt


def lane(manifest,lane_id):
    obj=json.loads(Path(manifest).read_text())
    if obj.get('source_sha256')!=fingerprint():raise ValueError('Manifest source mismatch')
    receipt=require_receipt(obj['validation_receipt'])
    if receipt['payload_sha256']!=obj['validation_receipt_sha256']:raise ValueError('Validation receipt changed after manifest was frozen')
    lanes=obj['lanes']
    if not 0<=lane_id<len(lanes):raise ValueError('Invalid lane index')
    selected=lanes[lane_id];child=None;pending=[]
    def forward(sig,frame):
        pending.append(sig)
        if child is not None and child.poll() is None:
            try:os.killpg(child.pid,sig)
            except ProcessLookupError:pass
    old={s:signal.signal(s,forward) for s in (signal.SIGTERM,signal.SIGINT,signal.SIGUSR1)}
    try:
        for L in selected['cutoffs']:
            if pending:return 75
            cmd=[sys.executable,'-m','lri_eh','run','--cutoff',str(L),'--degree',str(obj['degree']),
                 '--threads',str(selected['threads']),'--memory-limit-gib',str(selected['memory_limit_gib']),
                 '--output-dir',str(Path(obj['output_dir']).resolve()),'--max-attempts',str(obj.get('max_attempts',3)),'--resume']
            child=subprocess.Popen(cmd,start_new_session=True)
            code=child.wait();child=None
            # A busy item belongs to another live solver: do not duplicate it.
            # Other failures stop the lane for operator/scheduler review.
            if code==73:continue
            if code:return code
        return 0
    finally:
        for s,h in old.items():signal.signal(s,h)
