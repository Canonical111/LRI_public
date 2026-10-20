// Independent randomizations per graph. Uniform coordinate layouts and rate changes
// preserve the exact measure. Antithetic variants reflect only radial uniforms.
#include "kernel.hpp"
struct ArrayRng{const vector<ld>&u;int j=0;};
ld uniform(ArrayRng&r){if(r.j>=int(r.u.size()))throw runtime_error("uniform exhausted");return r.u[r.j++];}
vector<ld> sample_array(const Graph&g,const vector<ld>&uu,int K,const vector<ld>&logs,int&level,int layout,bool anti){
 int E=g.E, S=(1<<E)-1;vector<int>order(E);vector<ld>lt(E-1);ld fac=0;ld ou=uu[0];
 for(int pos=0;pos<E;pos++){
  ld tot=0;for(int j=0;j<E;j++)if(S>>j&1)tot+=g.dp[S^(1<<j)];
  ld u=(layout==2?ou:uu[layout==0?2*pos:E-1+pos])*tot;int pick=-1;
  for(int j=0;j<E;j++)if(S>>j&1){u-=g.dp[S^(1<<j)];if(u<=0){pick=j;break;}}
  if(pick<0)pick=31-__builtin_clz(S);
  if(layout==2){ld pr=g.dp[S^(1<<pick)];ou=(u+pr)/pr;ou=max(0.L,min(nextafterl(1.L,0.L),ou));}
  order[pos]=pick;S^=1<<pick;
  if(S){int ix=layout==0?2*pos+1:(layout==2?pos+1:pos);ld v=uu[ix];if(anti)v=1-v;
   ld l=logl(v)/g.alpha[S];lt[pos]=l;fac+=(D*__builtin_popcount((unsigned)S)/4.0L-g.alpha[S])*l;}
 }
 vector<ld>lx(E);ld cur=0;for(int j=0;j<E;j++){lx[order[j]]=cur;if(j<E-1)cur+=lt[j];}
 auto v=evaluate(g,lx,fac);level=v.level;
 ld sumlog=accumulate(lx.begin(),lx.end(),0.L),XX=0;for(ld x:lx)XX+=expl(x);ld ss=sumlog/4-g.L/2.L*logl(XX);
 vector<ld>ex(K+1);ex[0]=1;for(int n=1;n<=K;n++){ld val=0;for(int j=1;j<=n;j++)val+=j*(logs[j]+(j==1?ss:0))*ex[n-j];ex[n]=val/n;}
 for(auto&x:ex)x*=v.y;return ex;
}
int main(int argc,char**argv){try{
 if(argc!=12){cerr<<"kernel rates counts seed net output gamma method layout antithetic rate_factor\n";return 1;}
 auto gs=load(argv[1],argv[2]);int L=gs.at(0).L,K=6-L,dim=2*(K+1),layout=stoi(argv[9]);bool anti=stoi(argv[10]);ld rate=stold(argv[11]);string method=argv[8];
 if(rate<=0||rate>=2.5L)throw runtime_error("bad rate factor");
 if(rate!=1)for(auto&g:gs){int sz=1<<g.E;for(auto&x:g.alpha)x*=rate;g.dp.assign(sz,0);g.dp[0]=1;for(int s=1;s<sz;s++){ld sum=0;for(int j=0;j<g.E;j++)if(s>>j&1)sum+=g.dp[s^(1<<j)];g.dp[s]=sum/(s==sz-1?1:g.alpha[s]);}g.Z=g.dp.back();}
 uint64_t seed=stoull(argv[4]);ifstream dc(argv[5],ios::binary);uint32_t head[3];dc.read((char*)head,sizeof(head));int B=head[0],dd=head[1],bits=head[2];
 if(!dc||B<2||dd!=(layout==2?2*L:4*L-1)||bits<32||bits>60)throw runtime_error("net header");
 vector<uint64_t>dirs(size_t(B)*dd*bits);dc.read((char*)dirs.data(),dirs.size()*sizeof(uint64_t));if(!dc)throw runtime_error("net truncated");
 ifstream ci(argv[3]);int ng;ci>>ng;if(ng!=int(gs.size()))throw runtime_error("graph count mismatch");vector<uint64_t>counts(ng);uint64_t N=0;for(int k=0;k<ng;k++){int id;ci>>id>>counts[k];if(!ci||id!=gs[k].id||(counts[k]&&(counts[k]&(counts[k]-1))))throw runtime_error("allocation");N+=counts[k];}
 vector<ld>logs(K+1,0);ld norm=0;ifstream cf(argv[7]);for(int l=2;l<=6;l++){int kl;ld nl;cf>>kl>>nl;vector<ld>v(5);for(auto&x:v)cf>>x;if(l==L){norm=nl;for(int j=1;j<=K;j++)logs[j]=v[j];}}if(!cf||!norm)throw runtime_error("gamma config");
 vector<vector<ld>>res(B,vector<ld>(dim));vector<vector<vector<ld>>>per(B,vector<vector<ld>>(ng,vector<ld>(dim)));vector<uint64_t>qf(B),mf(B);vector<ld>maxv(B);vector<double>times(ng,0);
 const int NB=32;bool train=getenv("TRAIN_HIST")!=nullptr;string gp=getenv("GRID_FILE")?getenv("GRID_FILE"):"";
 vector<vector<vector<ld>>>grid(ng,vector<vector<ld>>(2*L-1,vector<ld>(NB+1)));
 for(auto&gr:grid)for(auto&axis:gr)for(int i=0;i<=NB;i++)axis[i]=ld(i)/NB;
 if(!gp.empty()){ifstream gf(gp);int nn,ee,nb;gf>>nn>>ee>>nb;if(nn!=ng||ee!=2*L-1||nb!=NB)throw runtime_error("grid dimensions");for(int k=0;k<ng;k++){int id;gf>>id;if(id!=gs[k].id)throw runtime_error("grid graph id");for(auto&ax:grid[k])for(auto&v:ax)gf>>v;}if(!gf)throw runtime_error("grid read");}
 vector<vector<vector<ld>>>hist;if(train)hist.assign(B,vector<vector<ld>>(ng,vector<ld>((2*L-1)*NB,0)));
 bool prefix=getenv("PREFIX_STRATA")!=nullptr;
 struct Branch{ld prob,lo;uint64_t n;};vector<vector<Branch>>branches(ng);
 vector<uint64_t>actual_counts(ng);N=0;
 for(int k=0;k<ng;k++)if(counts[k]){
  if(!prefix)branches[k].push_back({1,0,counts[k]});
  else{const auto&g=gs[k];int mask=(1<<g.E)-1;ld total=0,lo=0;for(int j=0;j<g.E;j++)total+=g.dp[mask^(1<<j)];
   for(int j=0;j<g.E;j++){ld p=g.dp[mask^(1<<j)]/total;ld want=max(ld(4),counts[k]*p);uint64_t n=uint64_t(1)<<int(roundl(log2l(want)));branches[k].push_back({p,lo,n});lo+=p;}}
  for(auto&br:branches[k])actual_counts[k]+=br.n;N+=actual_counts[k];
 }
 double start=omp_get_wtime();
 #pragma omp parallel for schedule(dynamic) num_threads(4)
 for(int b=0;b<B;b++){
  for(int k=0;k<ng;k++)if(counts[k]){double t0=omp_get_wtime();
   vector<ld>tot(K+1,0),u(dd);const auto&g=gs[k];
   for(int bb=0;bb<int(branches[k].size());bb++){const auto&br=branches[k][bb];
   mt19937_64 rng(seed+0x9e3779b97f4a7c15ULL*(b+1)+0xbf58476d1ce4e5b9ULL*(gs[k].id+1)+(prefix?0x94d049bb133111ebULL*(bb+1):0));
   DigitalNet net(dd,bits,dirs.data()+size_t(b)*dd*bits,rng);
   for(uint64_t i=0;i<br.n;i++){
    if(method=="rqmc"){net.point(i);for(int j=0;j<dd;j++)u[j]=uniform(net);}else if(method=="mc"){for(auto&v:u)v=uniform(rng);}else throw runtime_error("method");
    if(prefix){int ix=layout==0?0:(layout==2?0:g.E-1);if(layout==2)u[ix]=br.lo+br.prob*u[ix];else{for(int j=dd-1;j>ix;j--)u[j]=u[j-1];u[ix]=br.lo+br.prob/2;}}
    ld jac=1;
    if(!gp.empty())for(int j=0;j<g.E-1;j++){int ix=layout==0?2*j+1:(layout==2?j+1:j);ld yy=u[ix]*NB;int bin=min(NB-1,int(yy));ld width=grid[k][j][bin+1]-grid[k][j][bin];u[ix]=grid[k][j][bin]+width*(yy-bin);jac*=NB*width;}
    int lev=0;auto v=sample_array(g,u,K,logs,lev,layout,false);qf[b]+=lev>=1;mf[b]+=lev>=2;
    if(anti){int ll=0;auto w=sample_array(g,u,K,logs,ll,layout,true);for(int j=0;j<=K;j++)v[j]=(v[j]+w[j])/2;qf[b]+=ll>=1;mf[b]+=ll>=2;}
    for(auto&val:v)val*=jac;
    if(train)for(int j=0;j<g.E-1;j++){int ix=layout==0?2*j+1:(layout==2?j+1:j);int bin=min(NB-1,int(u[ix]*NB));hist[b][k][j*NB+bin]+=v[0]*v[0];}
    for(int j=0;j<=K;j++){if(!isfinite(v[j]))abort();tot[j]+=br.prob*v[j]/br.n;}maxv[b]=max(maxv[b],abs(norm*(3*g.wb-g.wa)*v[0]));
   }
   }
   for(int j=0;j<=K;j++){per[b][k][j]=norm*g.wa*tot[j];per[b][k][K+1+j]=norm*g.wb*tot[j];}
   for(int j=0;j<dim;j++)res[b][j]+=per[b][k][j];
   #pragma omp atomic
   times[k]+=omp_get_wtime()-t0;
  }
  #pragma omp critical
  cerr<<"replicate "<<b<<" completed\n";
 }
 double elapsed=omp_get_wtime()-start;
 if(train){ofstream hf(string(argv[6])+".hist.json");hf<<setprecision(20)<<"{\"bins\":"<<NB<<",\"rows\":[";for(int k=0;k<ng;k++){if(k)hf<<',';hf<<"{\"id\":"<<gs[k].id<<",\"squared\":[";for(int j=0;j<(2*L-1)*NB;j++){if(j)hf<<',';ld h=0;for(int b=0;b<B;b++)h+=hist[b][k][j];hf<<h;}hf<<"]}";}hf<<"]}";}

 ofstream f(argv[6]);f<<setprecision(20)<<"{\"dimension\":"<<D<<",\"L\":"<<L<<",\"N\":"<<N*B*(anti?2:1)<<",\"replicates\":"<<B<<",\"seed\":"<<seed<<",\"bits\":"<<bits<<",\"seconds\":"<<elapsed<<",\"method\":\""<<method<<"\",\"layout\":"<<layout<<",\"antithetic\":"<<(anti?"true":"false")<<",\"rate_factor\":"<<rate<<",\"prefix_stratification\":"<<(prefix?"true":"false")<<",\"graph_ids\":[";
 for(int k=0;k<ng;k++){if(k)f<<',';f<<gs[k].id;}f<<"],\"counts_per_replicate\":[";for(int k=0;k<ng;k++){if(k)f<<',';f<<actual_counts[k];}f<<"],\"graph_cpu_seconds\":[";for(int k=0;k<ng;k++){if(k)f<<',';f<<times[k];}
 f<<"],\"batches\":[";for(int b=0;b<B;b++){if(b)f<<',';f<<'[';for(int j=0;j<dim;j++){if(j)f<<',';f<<res[b][j];}f<<']';}
 f<<"],\"graph_batches\":[";for(int b=0;b<B;b++){if(b)f<<',';f<<'[';for(int k=0;k<ng;k++){if(k)f<<',';f<<'[';for(int j=0;j<dim;j++){if(j)f<<',';f<<per[b][k][j];}f<<']';}f<<']';}
 f<<"],\"quad_fallbacks\":"<<accumulate(qf.begin(),qf.end(),uint64_t(0))<<",\"mp_fallbacks\":"<<accumulate(mf.begin(),mf.end(),uint64_t(0))<<",\"max_abs_target_sample\":"<<*max_element(maxv.begin(),maxv.end())<<"}\n";
 }catch(exception&e){cerr<<e.what()<<'\n';return 2;} }
