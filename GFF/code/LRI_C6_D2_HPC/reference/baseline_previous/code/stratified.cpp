// Stratified randomized QMC; integral kernel retained from the supplied calculation.
#include "kernel.hpp"
int main(int argc,char**argv){
 try{
 if(argc!=9){cerr<<"kernel rates counts seed digital_matrices output gamma_config mode(rqmc/mc)\n";return 1;}
 auto gs=load(argv[1],argv[2]);int L=gs.at(0).L,K=6-L,dim=2*(K+1),udim=SINGLE_ORDER?2*L:4*L-1;uint64_t seed=stoull(argv[4]);string mode=argv[8];
 if(mode!="rqmc"&&mode!="mc")throw runtime_error("invalid mode");
 ifstream dc(argv[5],ios::binary);uint32_t head[3];dc.read((char*)head,sizeof(head));int B=head[0],dd=head[1],bits=head[2];if(!dc||B<2||dd!=udim||bits<32||bits>60)throw runtime_error("invalid digital matrix header");
 vector<uint64_t>dirs(size_t(B)*dd*bits);dc.read((char*)dirs.data(),dirs.size()*sizeof(uint64_t));if(!dc)throw runtime_error("truncated directions");
 ifstream ci(argv[3]);int ng;ci>>ng;if(ng!=int(gs.size()))throw runtime_error("graph count mismatch");vector<uint64_t>counts(ng);uint64_t N=0;for(int k=0;k<ng;k++){int id;ci>>id>>counts[k];if(!ci||id!=gs[k].id||!counts[k]||(counts[k]&(counts[k]-1)))throw runtime_error("invalid graph allocation");N+=counts[k];}
 vector<ld>logs(K+1,0);ld norm=0;ifstream cf(argv[7]);for(int l=2;l<=6;l++){int kl;ld nl;cf>>kl>>nl;vector<ld>v(5);for(auto&x:v)cf>>x;if(l==L){norm=nl;for(int j=1;j<=K;j++)logs[j]=v[j];}}if(!cf||!norm)throw runtime_error("invalid gamma config");
 vector<vector<ld>>res(B,vector<ld>(dim));vector<vector<vector<ld>>>per(B,vector<vector<ld>>(ng,vector<ld>(dim)));vector<uint64_t>qf(B),mf(B);vector<ld>maxv(B);
 #pragma omp parallel for schedule(dynamic) num_threads(4)
 for(int b=0;b<B;b++){
  for(int k=0;k<ng;k++){
   // Independent graph shifts and pseudo-random controls, reproducible under threading.
   mt19937_64 rng(seed+0x9e3779b97f4a7c15ULL*(b+1)+0xbf58476d1ce4e5b9ULL*(gs[k].id+1));
   DigitalNet net(udim,bits,dirs.data()+size_t(b)*udim*bits,rng);vector<ld>t(K+1,0);const auto&g=gs[k];
   for(uint64_t i=0;i<counts[k];i++){
    int level=0;vector<ld>v;
    if(mode=="rqmc"){net.point(i);v=sample(g,net,K,logs,level);}else v=sample(g,rng,K,logs,level);
    qf[b]+=level>=1;mf[b]+=level>=2;
    for(int j=0;j<=K;j++){if(!isfinite(v[j])){cerr<<"NONFINITE\n";abort();}t[j]+=v[j];}
    maxv[b]=max(maxv[b],abs(norm*(3*g.wb-g.wa)*v[0]));
   }
   for(int j=0;j<=K;j++){per[b][k][j]=norm*g.wa*t[j]/counts[k];per[b][k][K+1+j]=norm*g.wb*t[j]/counts[k];}
   for(int j=0;j<dim;j++)res[b][j]+=per[b][k][j];
  }
  #pragma omp critical
  cerr<<"replicate "<<b<<" completed\n";
 }
 ofstream f(argv[6]);f<<setprecision(20)<<"{\"dimension\":"<<D<<",\"L\":"<<L<<",\"N\":"<<N*B<<",\"replicates\":"<<B<<",\"seed\":"<<seed<<",\"bits\":"<<bits<<",\"method\":\""<<mode<<"\",\"graph_ids\":[";
 for(int k=0;k<ng;k++){if(k)f<<',';f<<gs[k].id;}f<<"],\"counts_per_replicate\":[";for(int k=0;k<ng;k++){if(k)f<<',';f<<counts[k];}
 f<<"],\"batches\":[";for(int b=0;b<B;b++){if(b)f<<',';f<<'[';for(int j=0;j<dim;j++){if(j)f<<',';f<<res[b][j];}f<<']';}
 f<<"],\"graph_batches\":[";for(int b=0;b<B;b++){if(b)f<<',';f<<'[';for(int k=0;k<ng;k++){if(k)f<<',';f<<'[';for(int j=0;j<dim;j++){if(j)f<<',';f<<per[b][k][j];}f<<']';}f<<']';}
 f<<"],\"quad_fallbacks\":"<<accumulate(qf.begin(),qf.end(),uint64_t(0))<<",\"mp_fallbacks\":"<<accumulate(mf.begin(),mf.end(),uint64_t(0))<<",\"max_abs_target_sample\":"<<*max_element(maxv.begin(),maxv.end())<<"}\n";
 return 0;
 }catch(exception&e){cerr<<e.what()<<'\n';return 2;}
}
