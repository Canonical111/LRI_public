import scaled_b as sb,json,time
from pathlib import Path
st=time.time()
for f in [1,2,3,4]:
 sb.tb.sources(8,f)
 print('FACE_SOURCES_FINISHED',f,time.time()-st,flush=True)
