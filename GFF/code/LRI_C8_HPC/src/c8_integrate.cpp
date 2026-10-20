#include "point.hpp"
#include "power.hpp"
int main(int argc,char**argv){try{
 double start=omp_get_wtime();Options o=parse_args(argc,argv);int ng;auto work=read_work(o.tasks,ng);vector<int>slot;auto graphs=load_graphs(o,work,ng,slot);
 bool exact=o.mode=="exact",wide=o.quad_bits==113;
 vector<TP>props(exact?0:graphs.size());
 for(size_t i=0;i<props.size();i++)props[i]=prep_tree(graphs[i],o.L,o.rate,o.mode=="power");
 unique_ptr<Net>net;unique_ptr<SmallGrid>grid;unique_ptr<TreeCatalog>cat;array<LD,NW>gamma{};
 if(o.mode=="qmc"){net=make_unique<Net>(o.net,work,o.L);ifstream f(o.inputs+"/cgamma_L"+to_string(o.L)+".txt");for(auto&v:gamma)f>>v;require(bool(f),"missing Gamma coefficients");string extra;require(!(f>>extra),"Gamma file must hold exactly NW coefficients");}
 else grid=make_unique<SmallGrid>(o.L,o.degree,o.inputs);
 if(exact)cat=make_unique<TreeCatalog>(o.L+1);
 vector<size_t> order(work.size());iota(order.begin(),order.end(),0);
 stable_sort(order.begin(),order.end(),[&](size_t a,size_t b){
  LD ca=LD(work[a].end-work[a].begin)*max(size_t(8),graphs[slot[work[a].graph]].terms.size());
  LD cb=LD(work[b].end-work[b].begin)*max(size_t(8),graphs[slot[work[b].graph]].terms.size());return ca>cb;
 });
 double prep=omp_get_wtime()-start;vector<Row>rows(work.size());vector<Profile>prof(omp_get_max_threads());exception_ptr error;atomic<bool>failed(false);double integration=omp_get_wtime();
 #pragma omp parallel
 {
  PointScratch<LD>sl;PointScratch<__float128>sq;PointScratch<MP>sm;unique_ptr<PowerScratch>ps;unique_ptr<PowerScratchT<__float128>>pq;auto&p=prof[omp_get_thread_num()];
  try{if(o.mode!="qmc"){if(wide)pq=make_unique<PowerScratchT<__float128>>(o.scratch_mib);else ps=make_unique<PowerScratch>(o.scratch_mib);}}catch(...){failed=true;
   #pragma omp critical(c8_error)
   {if(!error)error=current_exception();}
  }
  // Graph x replicate x sample-block tasks, independent of thread count and task placement.
  #pragma omp for schedule(dynamic,1)
  for(size_t job=0;job<work.size();job++){
   size_t i=order[job];
   if(failed.load(memory_order_relaxed))continue;
   try{auto&w=work[i];int gi=slot[w.graph];require(gi>=0,"missing graph");
    if(o.mode=="qmc")rows[i]=run_qmc(o,w,graphs[gi],props[gi],*net,gamma,p,sl,sq,sm);
    else if(exact)rows[i]=wide?run_exact(o,w,graphs[gi],*cat,*grid,*pq,p):run_exact(o,w,graphs[gi],*cat,*grid,*ps,p);
    else rows[i]=wide?run_power(o,w,graphs[gi],props[gi],*grid,*pq,p):run_power(o,w,graphs[gi],props[gi],*grid,*ps,p);
   }catch(...){failed=true;
    #pragma omp critical(c8_error)
    {if(!error)error=current_exception();}
   }
  }
 }
 if(error)rethrow_exception(error);integration=omp_get_wtime()-integration;write_results(o,ng,work,rows,prof,prep,integration);
 cerr<<"completed "<<work.size()<<" tasks; prep "<<prep<<" s, integration "<<integration<<" s, threads "<<omp_get_max_threads()<<"\n";return 0;
}catch(const exception&e){cerr<<"C8 failed: "<<e.what()<<'\n';return 2;}}
