// c8d3_inspect (PLAN.md C.7, HD7): kernel sizes from the worker's own reader and prepare(), one point regenerated
// exactly as the worker computes it, and the G-file entry point of the sanitizer parser corpus (A-KER-4).
//   c8d3_inspect --describe
//   c8d3_inspect sizes PACK INDEX [THREADS]
//       INDEX holds one line "id L offset length" per graph (its bytes in PACK). For every line, in INDEX order, one
//       JSON line {"id","L","masks","terms","products","segments","addends","numerators","kernel_bytes"} is printed.
//       Each member is read by kernel.hpp's read_graph (the reader load_graph uses) from its bytes, at rate scale 1,
//       which runs rates() and prepare() exactly as the worker does. kernel_bytes is the size of the graph's heap
//       tables after prepare(): masks, terms (struct and both vectors), the three 2^E long-double tables (alpha, dp,
//       choice_total), products, mon_ids, segments, addends and numerators (vector and pairs). addends.size() is the
//       worker's in-block ordering key. (fmax, the maximal forest size, is a property of the class, not of the
//       payload; `make inputs-inspect` takes it from gen3's size probe.)
//   c8d3_inspect files GFILE...
//       Loads each G-file with load_graph (the worker's path reader) at rate scale 1 and prints the same JSON line;
//       the first error exits 2 with "<path>: <reason>".
//   c8d3_inspect --point GRAPH REP INDEX... -- GRAPHS_ROOT L NET SEED LAYOUT RATE GRID_OR_DASH
//       Regenerates the worker's point INDEX of (GRAPH, REP): the net state at INDEX (random access, the worker's
//       Gray-code stream), the stream seed of src/stream.hpp, the grid, then sample() at K = 0 (the jet slots above 0
//       do not change v[0]). One JSON line per index: the log-coordinates lx, the Jacobian, y = v_0 and
//       t = v_0*jac (the class-B tail quantity, C.3), its absolute value, the tier level, direct and moderate. Built
//       with the worker's MP backend, so |t| at a row's tail_argmax equals that row's tail_top[0] bit for bit
//       (A-KER-6 (c)).
#include "kernel.hpp"
#include "stream.hpp"
#include "identity.hpp"
#include <iostream>
#include <sstream>
#include <omp.h>
static size_t kernel_bytes(const Graph&g){
    size_t b=g.masks.size()*sizeof(unsigned)+(g.alpha.size()+g.dp.size()+g.choice_total.size())*sizeof(ld)
        +g.products.size()*sizeof(std::pair<int,int>)+g.mon_ids.size()*sizeof(int)+g.segments.size()*sizeof(Segment)
        +g.addends.size()*sizeof(int);
    for(const auto&t:g.terms)b+=sizeof(Term)+(t.ids.size()+t.co.size())*sizeof(int);
    for(const auto&n:g.numerators)b+=sizeof(n)+n.size()*sizeof(std::pair<int,int>);
    return b;
}
static std::string sizes_json(const Graph&g){
    std::ostringstream o;
    o<<"{\"id\":"<<g.id<<",\"L\":"<<g.L<<",\"masks\":"<<g.masks.size()<<",\"terms\":"<<g.terms.size()<<",\"products\":"<<g.products.size()
     <<",\"segments\":"<<g.segments.size()<<",\"addends\":"<<g.addends.size()<<",\"numerators\":"<<g.numerators.size()<<",\"kernel_bytes\":"<<kernel_bytes(g)<<"}";
    return o.str();
}
struct Item{long id;int L;unsigned long long offset,length;};
static int sizes(int argc,char**argv){
    if(argc<4||argc>5){std::cerr<<"usage: c8d3_inspect sizes PACK INDEX [THREADS]\n";return 1;}
    const std::string pack=argv[2],index=argv[3];int threads=argc>4?std::stoi(argv[4]):omp_get_max_threads();
    if(threads<1||threads>4096)throw std::runtime_error("bad thread count");
    std::ifstream idx(index);if(!idx)throw std::runtime_error(index+": cannot open the index");
    // S1-07: one complete record "id L offset length" per non-blank line (a missing, malformed or trailing field is an
    // error, also in the last line, so a clean end of file comes only between records); an empty index is refused
    // (every caller, tools/inspect_inputs.py and tests/sanitize.py, has members to inspect).
    std::vector<Item>items;std::string line;
    while(std::getline(idx,line)){if(line.find_first_not_of(" \t\r")==std::string::npos)continue;
        std::istringstream is(line);Item it{};std::string extra;const std::string where=index+": index line "+std::to_string(items.size());
        if(!(is>>it.id>>it.L>>it.offset>>it.length))throw std::runtime_error(where+" is incomplete or malformed (four fields id L offset length required)");
        if(is>>extra)throw std::runtime_error(where+" has a trailing field");
        if(it.id<0||it.L<2||it.L>LMAX||!it.length)throw std::runtime_error(index+": bad index line "+std::to_string(items.size()));items.push_back(it);}
    if(idx.bad())throw std::runtime_error(index+": read error");
    if(items.empty())throw std::runtime_error(index+": empty index (no member to inspect)");
    std::vector<std::string>out(items.size());std::string error;
    #pragma omp parallel num_threads(threads)
    {
        std::ifstream pk(pack,std::ios::binary);std::string buf;
        #pragma omp for schedule(dynamic,1)
        for(size_t i=0;i<items.size();++i){try{
            const auto&x=items[i];if(!pk)throw std::runtime_error(pack+": cannot open the pack");
            buf.assign(x.length,'\0');pk.seekg(x.offset);pk.read(&buf[0],x.length);
            if(!pk)throw std::runtime_error(pack+": cannot read graph "+std::to_string(x.id)+" at offset "+std::to_string(x.offset));
            std::istringstream is(buf);const std::string where=pack+"@"+std::to_string(x.offset)+" (G"+std::to_string(x.id)+")";
            Graph g=read_graph(is,where,1.0L);
            if(g.id!=x.id||g.L!=x.L)throw std::runtime_error(where+": graph identity mismatch (header L "+std::to_string(g.L)+" id "+std::to_string(g.id)+")");
            out[i]=sizes_json(g);
        }catch(const std::exception&e){
            #pragma omp critical
            {if(error.empty())error=e.what();}
        }}
    }
    if(!error.empty())throw std::runtime_error(error);
    for(auto&s:out)std::cout<<s<<'\n';
    if(!std::cout)throw std::runtime_error("write failed");
    return 0;
}
static int files(int argc,char**argv){
    if(argc<3){std::cerr<<"usage: c8d3_inspect files GFILE...\n";return 1;}
    for(int i=2;i<argc;++i){Graph g=load_graph(argv[i],1.0L);std::cout<<sizes_json(g)<<'\n';}
    return 0;
}
static int point(int argc,char**argv){
    int sep=-1;for(int i=2;i<argc;++i)if(std::string(argv[i])=="--"){sep=i;break;}
    if(sep<5||argc-sep-1!=7){std::cerr<<"usage: c8d3_inspect --point GRAPH REP INDEX... -- GRAPHS_ROOT L NET SEED LAYOUT RATE GRID_OR_DASH\n";return 1;}
    const uint64_t gid=std::stoull(argv[2]),rep=std::stoull(argv[3]);std::vector<uint64_t>indices;for(int i=4;i<sep;++i)indices.push_back(std::stoull(argv[i]));
    const std::string root=argv[sep+1],netpath=argv[sep+3],gridarg=argv[sep+7];const int L=std::stoi(argv[sep+2]);
    const uint64_t seed=std::stoull(argv[sep+4]);const int layout=std::stoi(argv[sep+5]);const ld scale=std::stold(argv[sep+6]);
    if(layout<0||layout>2||!(scale>0&&scale<=1)||L<2||L>LMAX)throw std::runtime_error("bad point options");
    const NetFile netf=read_net(netpath,layout,L,{rep});
    const std::string gp=root+"/L"+std::to_string(L)+"/G"+std::to_string(gid)+".txt";const Graph g=load_graph(gp,scale);
    if(g.id!=int(gid)||g.L!=L)throw std::runtime_error(gp+": graph identity mismatch");
    std::map<uint64_t,Grid>grids;if(gridarg!="-")grids=read_grid(gridarg,L,{gid});
    const Grid*grid=grids.empty()?nullptr:&grids.begin()->second;
    Scratch s;s.resize(g);const std::array<ld,NLOGS>logs{};
    std::cout<<std::setprecision(std::numeric_limits<ld>::max_digits10);
    for(uint64_t index:indices){
        if(index>=(uint64_t(1)<<netf.bits))throw std::runtime_error("point index beyond the net period");
        Net net(netf.dim,netf.bits,netf.directions.at(rep),stream_seed(seed,rep,g.id),index);
        std::array<ld,DIMMAX>u{};net.point(u.data());const ld jac=apply_grid(grid,g.E,layout,u.data());
        int level=0;auto v=sample(g,u.data(),0,logs,level,layout,s);const ld y=v[0];v[0]*=jac;
        std::cout<<"{\"graph\":"<<gid<<",\"rep\":"<<rep<<",\"index\":"<<index<<",\"L\":"<<L<<",\"lx\":[";
        for(int j=0;j<g.E;++j){if(j)std::cout<<',';std::cout<<'"'<<s.lx[j]<<'"';}
        std::cout<<"],\"jac\":\""<<jac<<"\",\"y\":\""<<y<<"\",\"t\":\""<<v[0]<<"\",\"abs_t\":\""<<fabsl(v[0])<<"\",\"level\":"<<level
                 <<",\"direct\":"<<(s.direct?"true":"false")<<",\"moderate\":"<<(s.moderate?"true":"false")<<",\"mp_backend\":\""<<mp_backend<<"\"}\n";
    }
    return 0;
}
int main(int argc,char**argv){try{
    const std::string cmd=argc>1?argv[1]:"";
    if(argc==2&&cmd=="--describe"){bool mismatch=false;std::string common=describe_common(mismatch);
        std::cout<<"{\"schema\":\"c8-d3-inspect-1\","<<common<<"}\n";return mismatch?3:0;}
    if(cmd=="sizes")return sizes(argc,argv);
    if(cmd=="files")return files(argc,argv);
    if(cmd=="--point")return point(argc,argv);
    std::cerr<<"usage: c8d3_inspect --describe | sizes PACK INDEX [THREADS] | files GFILE... | --point GRAPH REP INDEX... -- GRAPHS_ROOT L NET SEED LAYOUT RATE GRID_OR_DASH\n";
    return 1;
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 2;}}
