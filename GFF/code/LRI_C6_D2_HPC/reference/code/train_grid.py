"""A pilot-frozen separable importance map; production never adapts."""
from driver import *
for d in [2,3]:
    h=json.load(open(W/f'records/grid_train_d{d}_L6.json.hist.json'))
    for top in [3,11]:
        grids=[];choices=[]
        for row in h['rows']:
            arr=np.array(row['squared']).reshape(11,32)
            arr=np.array([np.convolve(np.pad(a,(2,2),mode='reflect'),[1,2,3,2,1],mode='valid')/9 for a in arr])
            score=np.sqrt(arr+np.max(arr)*1e-12)
            score/=np.maximum(score.mean(1,keepdims=True),1e-300)
            rank=np.argsort(score.std(1))[::-1][:top]
            axes=[]
            for j in range(11):
                if j in rank:
                    density=.5+.5*np.clip(score[j],.15,4)
                    density/=density.mean()
                    cdf=np.r_[0,np.cumsum(density)/32]
                    xx=np.interp(np.linspace(0,1,33),cdf,np.linspace(0,1,33))
                else:xx=np.linspace(0,1,33)
                assert np.all(np.diff(xx)>0)
                axes.append(xx.tolist())
            grids.append((row['id'],axes));choices.append({'id':row['id'],'axes':rank.tolist()})
        path=W/f'inputs/grid_d{d}_top{top}.txt'
        path.write_text(f'{len(grids)} 11 32\n'+'\n'.join(str(idx)+'\n'+'\n'.join(' '.join(format(x,'.18g') for x in ax) for ax in axes) for idx,axes in grids)+'\n')
        (W/f'inputs/grid_d{d}_top{top}_metadata.json').write_text(json.dumps({'training':'grid_train','density_blend':.5,'bins':32,'choices':choices,'adaptive_production':False},indent=2))
