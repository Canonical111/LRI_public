import json,math,glob
base='<TMP>/scratchpad/identity/'
mine={}
for l in open('top_a.jsonl'):
    r=json.loads(l); mine[r['L']]=r
d=json.load(open(base+'B/shift_all.json'))
mx=0
for l,s in zip(d['L'],d['shift']):
    l=int(l)
    if l in mine: mx=max(mx,abs(mine[l]['shift']-s)/abs(s))
print('B shift: max rel diff',mx,'over',sum(int(l) in mine for l in d['L']),'L')
mx=0;n=0
for f in glob.glob(base+'A/c4shift_*.json'):
    for k,v in json.load(open(f)).items():
        l=int(k)
        if l in mine: mx=max(mx,abs(mine[l]['shift_raw']-v['dC4'])/abs(v['dC4']));n+=1
print('A raw dC4 (-B/3): max rel diff',mx,'over',n)
print(json.load(open(base+'A/c4shift_96_96.json')))
