# Complete graph and mixed-forest construction at eight loops

This package reconstructs the graph calculation; it does not extrapolate an eighth coefficient from lower orders. The supplied C7 archive contained the already generated Schwinger graph kernels but no graph enumerator or forest-builder source. The new programs reproduce every available archived kernel and extend the same construction to nine vertices.

## Census and exact selection

A graph at loop order L has L+1 vertices and 2L individually labelled internal edges. Self-loops are absent in the supplied tadpole prescription. Graphs are connected and one-particle irreducible, so every vertex has internal degree between two and four. Since the sum of external half-edge counts is four, the possible internal degree patterns have either four degree-three vertices, one degree-two and two degree-three vertices, or two degree-two vertices; all remaining vertices have degree four.

| L | All classes | Power-containing classes | Primitive classes | Nonzero free kernels retained | Nonzero power kernels retained |
|---:|---:|---:|---:|---:|---:|
| 3 | 8 | 1 | 1 | 5 | 1 |
| 4 | 27 | 5 | 1 | 16 | 3 |
| 5 | 129 | 31 | 3 | 76 | 20 |
| 6 | 660 | 173 | 10 | 395 | 107 |
| 7 | 3,986 | 1,091 | 44 | 2,441 | 709 |
| 8 | 26,540 | 7,231 | 248 | 16,064 | 4,336 |

The complete eight-loop graph inventory represents 8,038,582,020 vertex-labelled graphs. Exact sums of class weights are

- sum wA = 49,985,915 / 768;
- sum wB = 33,994,099 / 6,912.

Here D = |Aut(G)| product(m_ij!) product(e_i!), sG = sum e_i(e_i-1), wA = 24/D and wB = 2 sG/D. Vertex automorphisms and all factorials are computed as integers before numerical conversion.

At eight loops there are 4,851 identically zero grouped Schwinger mixed kernels and 2,254 classes with sG=4. These sets overlap in 965 classes. Thus 26,540 - 4,851 - (2,254 - 965) = 20,400 kernels enter the top-loop target. The exact-zero count belongs to the d=3 Schwinger representation inherited from the supplied package. It must not be replaced with the different coordinate-forest count quoted in the manuscript's d=1 C8 section.

The top-loop identity 3wB-wA = 6(sG-4)/D permits the sG=4 exclusion only at L=8. At L=7 their constant beta/mass terms contribute to C8 through lower-loop products. The first-derivative top-channel contribution of an individual sG=4 class still cancels, but that does not cancel its constant-term mixing. Consequently 143 free and 119 power nonzero L7 classes omitted by the original C7 top-loop selection are restored. Every nonzero L3 through L7 graph retains its two channels.

## Enumeration and independent isomorphism checks

`src/enumerate_graphs.cpp` distributes edge multiplicities for each allowed degree pattern. Future vertices with the same degree and the same already assigned adjacency prefix are ordered by their current-row multiplicity. This removes only relabellings inside an indistinguishable prefix cell: every graph admits such an ordering recursively.

Every completed adjacency matrix is checked for connectivity and bridges. Deterministic partition refinement and individualization provide a canonical graph invariant and the vertex automorphism count. The implementation uses a string of multiplicities, avoiding the 64-bit packed-key overflow that would otherwise arise with 36 vertex pairs at nine vertices.

An independent nauty calculation represents every multigraph as a two-color incidence graph. Original vertices form one color class and individually labelled edge vertices form the other. Dividing the incidence automorphism order by product(m_ij!) yields the vertex automorphism order. This independently verified all 26,540 eight-loop graph identities and automorphism counts. It also reproduced the complete archived lower-loop inventories, including the class-by-class exact weights. See `verification/graph_validation.json`.

Archived graph IDs and edge order are retained at L3 through L7 using the complete supplied integer adjacency inventories. Eight-loop IDs follow the deterministic new canonical enumeration. A graph ID must therefore always be accompanied by its loop order and the delivered inventory.

## Schwinger forest construction

`src/build_forests.cpp` enumerates complement-of-spanning-tree masks of the first Symanzik polynomial. Each mask has L distinct edge labels. For a selected proper 1PI subgraph gamma with edge set Egamma and loop number hgamma, a mask m remains in the forest denominator precisely when

    popcount(m & Egamma) = hgamma.

Logarithmic subgraphs have e=2v-2, while unmarked power subgraphs have e=2v-1. Compatible forest members are nested, or have disjoint edges and meet in at most one vertex. A selected logarithmic member removes its edges from the root numerator; a selected power member does not. The sign is (-1) to the number of selected members.

For each selected denominator, the program accumulates the signed root numerators as exact integer vectors. Identical denominator lists are combined; zero vectors are discarded before floating-point operations. The resulting d=3 integrand is the sum of these linear numerator vectors divided by S times the corresponding denominator polynomial raised to 3/2. The exponent is applied separately to each forest denominator, as in the supplied C7 kernel.

The importance rates are the same positive quarter-integer prescription as in the C7 archive. For a denominator basis, the minimum exponent under a subset scaling is obtained by a Hamming-distance transform of its tree-complement masks. The numerator support supplies its corresponding valuation. The prescribed positive rate replacement is then applied where individual forest terms have nonpositive valuations. Changing these positive importance rates changes the sampling distribution, not the exact projective integral.

## Why non-induced divergent subgraphs cancel exactly

The fast generator uses induced divergent subgraphs. This is a reduction of the full edge-subgraph forest sum, not an omission of its non-induced members.

Let G be one of the connected 1PI graphs above. For a nonempty proper vertex set S, the cut has at least two edges. The degree bound therefore gives

    |E_ind(S)| <= 2|S| - 1.

A proper divergent subgraph cannot contain all vertices: the full graph already has exactly 2|V|-2 edges. Thus any non-induced divergent edge subgraph gamma must be logarithmic, with 2|S|-2 edges, and must miss exactly one edge e0 of its induced closure P. That closure is a proper power subgraph with 2|S|-1 edges. It is 1PI because adding an edge to the 1PI graph gamma preserves that property. There are no non-induced power subgraphs.

For a full-graph spanning-tree complement m obeying gamma's forest constraint, the tree contains exactly |S|-1 edges of gamma. Those edges form a spanning tree of S. Its missing closure edge e0 cannot also belong to the full tree, since that would create a cycle. Consequently e0 belongs to m, and the power-closure constraint is already implied:

    |m intersect Egamma| = hgamma  implies  |m intersect EP| = hgamma+1 = hP.

Now consider any compatible forest containing a non-induced logarithmic member. Choose a fixed deterministic inclusion-maximal such member gamma. Its power closure P is compatible with every other forest member. Members inside gamma are inside P; disjoint members meet S in at most one vertex; members containing gamma must be induced by maximality and therefore contain P. Toggle P's membership in the forest.

This toggle leaves the denominator unchanged because its additional constraint is already implied by gamma. It leaves the logarithmic root numerator unchanged because P is a power member. It reverses the forest sign. The selected non-induced logarithmic members are unchanged, so the same gamma is selected on the return operation. This is a fixed-point-free sign-reversing involution. All forests containing a non-induced logarithmic member cancel pairwise. The remaining induced forest sum is therefore exactly the full sum.

This argument was also checked by direct unreduced enumeration. The `--all-edge` mode does not use induced classification: it visits every proper labelled-edge subset, constructs its vertex support, tests 1PI connectivity, and enumerates the resulting mixed forests. All 8,532 power-containing classes at L3 through L8 were rebuilt this way. Their 492,490,392 edge subsets and 11,123,924 unreduced forests gave exactly the same grouped integer maps, including all zero maps and all top-channel-zero maps. At L8 alone the comparison covers every one of the 7,231 power classes, 40,679 non-induced logarithmic subgraphs and 10,451,732 unreduced forests. See `verification/all_edge_validation.json`.

## Reproducibility and coverage certificate

The masks, exact denominator lists, integer numerators and importance-rate tokens match all 3,511 available C7 graph payloads byte for byte after excluding the first header line. Header weights are independently checked against the exact rational denominators and mass numerators; the graph format label changes from C7D3GRAPH1 to C8D3GRAPH1. Metadata and complete class inventories also agree. All comparisons include the original 2,888 retained L7 files; the 262 restored L7 files are generated from the complete archived adjacency and weight inventories.

`inputs/coverage.json` binds these checks and the complete selection to the exact SHA-256 hash of `inputs/inventory.json`. Each active inventory record contains its payload hash and byte count. The campaign planner checks those hashes, and the physical assembly requires the complete coverage certificate.

To reproduce every graph and rate table into a separate destination:

```bash
python3 tools/generate_graphs.py --output regenerated_graph_inputs --threads 8
```

This compiles the two source programs, regenerates the complete graph census, rebuilds all L3 through L8 forests and rates, and requires exact agreement with the delivered canonical census and payload hashes. The default output is a separate directory. Existing nonempty destinations are rejected to avoid mixing inventories from different calculations. Low-loop analytic inputs are produced separately by `tools/prepare_low.py`.

To repeat the complete edge-subgraph forest audit against the delivered inputs:

```bash
python3 tools/audit_graph_forests.py --threads 8
```

To repeat independent nauty census and automorphism checks:

```bash
python3 tools/verify_graph_census.py
```

The last command requires `pynauty`; normal graph generation and integration do not. Complete graph inputs occupy about 9.15 GB before archive compression. Generation on the evaluation machine took about 200 seconds for L8 with eight threads; the time and storage requirements on another machine may differ.
