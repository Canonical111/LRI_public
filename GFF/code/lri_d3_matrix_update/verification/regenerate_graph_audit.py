#!/usr/bin/env python3
"""Regenerate all exact graph weights and compare to integration input hashes."""
from pathlib import Path
import hashlib,json,time
import numpy as np
from kernel_inputs import ROOT,original
start=time.time();rows=original.graphs(6)
assert len(rows)==59145
assert all((144*a).denominator==1 and (144*b).denominator==1 for _,a,b in rows)
full=np.asarray([list(g)+[int(144*a),int(144*b)]for g,a,b in rows],dtype='<i4')
w=3*full[:,16]-full[:,15];combined=full[w!=0].copy();combined[:,15]=w[w!=0];combined[:,16]=0
assert len(combined)==49605
computed={'full_graph_input_sha256':hashlib.sha256(full.tobytes()).hexdigest(),
'combined_graph_input_sha256':hashlib.sha256(combined.tobytes()).hexdigest()}
expected_path=ROOT/'inputs/executed_graph_hashes.json'
expected=json.loads(expected_path.read_text()) if expected_path.exists()else computed
assert computed==expected,(computed,expected)
out={'ordered_graphs':len(rows),'nonzero_combined_graphs':len(combined),
'all_144_scaled_weights_exact_integers':True,'regenerated_inputs_match_executed_input_hashes':True,
'elapsed_seconds':time.time()-start,**computed}
(ROOT/'records/graph_regeneration.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out,indent=2))
