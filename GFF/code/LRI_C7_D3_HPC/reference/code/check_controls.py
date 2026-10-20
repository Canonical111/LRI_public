from pathlib import Path
import json,numpy as np,mpmath as m,sys
from analyze import load_campaign
W=Path(__file__).resolve().parents[1]
m.mp.dps=65
ar,_,_,_=load_campaign('control_L2');v=ar['free'][2];mu=v.mean(0);se=v.std(0,ddof=1)/len(v)**.5;b2=np.array(json.load(open(W/'inputs/two_loop.json'))['B2'],float);target=np.r_[b2,b2/6]
two=[dict(channel='b'if j<6 else'c',order=j%6,mean=float(x),reference=float(y),sampling_se=float(e),pull=float((x-y)/e))for j,(x,y,e)in enumerate(zip(mu,target,se))]
outs={'two_loop':two,'sampled_points':len(v)*32768}
for tag in sys.argv[1:]:
 ar,_,_,_=load_campaign(tag);v=ar['power'][3][:,0];ex=float(-16*m.pi/15);mean=float(v.mean());err=float(v.std(ddof=1)/len(v)**.5)
 outs[tag]=dict(b3_power_mean=mean,b3_power_reference=ex,b3_power_sampling_se=err,pull=(mean-ex)/err,exact='-16*pi/15')
(W/'verification/sampling_controls.json').write_text(json.dumps(outs,indent=2));print(json.dumps(outs,indent=2))
