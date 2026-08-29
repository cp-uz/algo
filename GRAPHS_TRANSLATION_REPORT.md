# Graphs — source-ordered o‘zbekcha tarjima hisoboti

**Release:** 2026-08-20  
**Upstream pin:** `85a94001d46b9f34d3b2cf26aca6bd0f7a7e8681`  
**Qamrov:** Graphs navigatsiyasi 47/47  
**Holat:** to‘liq AI-tarjima qoralamalari; texnik va til reviewi `pending`

## Tuzatish

Oldingi Graphs paketi cp-algorithms maqolalarining to‘liq tarjimasi emas, qayta yozilgan texnik izohlar to‘plami edi. Ushbu release’da Graphs navigatsiyasidagi barcha 47 maqola pinned upstream Markdown maqolalari asosida, bo‘limlar va mazmun ketma-ketligi saqlangan holda qayta tarjima qilindi. Oldingi Graphs fayllari ushbu release’dagi fayllar bilan almashtirilishi kerak.

Algebra bo‘limidagi 29 source-ordered tarjima qoralamasi saqlanadi. Repository bo‘yicha jami 76 ta to‘liq tarjima qoralamasi va 87 ta konspekt yoki source-faithful bo‘lmagan adaptatsiya qoralamasi mavjud.

## Maqolalar

### Graf bo‘ylab yurish

| # | O‘zbekcha sarlavha | Asl sarlavha | Fayl | Satr | Kod bloklari |
|---:|---|---|---|---:|---:|
| 1 | Kenglik bo‘yicha qidiruv (BFS) | Breadth-first search | `graph/breadth-first-search.md` | 159 | 4 |
| 2 | Chuqurlik bo‘yicha qidiruv (DFS) | Depth First Search | `graph/depth-first-search.md` | 144 | 2 |

### Bog‘langan komponentlar, ko‘priklar va artikulyatsiya nuqtalari

| # | O‘zbekcha sarlavha | Asl sarlavha | Fayl | Satr | Kod bloklari |
|---:|---|---|---|---:|---:|
| 3 | Grafda bog‘langan komponentlarni topish | Search for connected components in a graph | `graph/search-for-connected-components.md` | 105 | 2 |
| 4 | Grafdagi ko‘priklarni $O(N+M)$ vaqtda topish | Finding bridges in a graph in O(N+M) | `graph/bridge-searching.md` | 122 | 1 |
| 5 | Ko‘priklarni onlayn topish | Finding Bridges Online | `graph/bridge-searching-online.md` | 197 | 1 |
| 6 | Grafdagi artikulyatsiya nuqtalarini $O(N+M)$ vaqtda topish | Finding articulation points in a graph in O(N+M) | `graph/cutpoints.md` | 95 | 1 |
| 7 | Kuchli bog‘langan komponentlar va kondensatsiya grafi | Strongly connected components and the condensation graph | `graph/strongly-connected-components.md` | 380 | 4 |
| 8 | Kuchli yo‘naltirish | Strong Orientation | `graph/strong-orientation.md` | 104 | 1 |

### Bitta manbadan eng qisqa yo‘llar

| # | O‘zbekcha sarlavha | Asl sarlavha | Fayl | Satr | Kod bloklari |
|---:|---|---|---|---:|---:|
| 9 | Dijkstra algoritmi | Dijkstra Algorithm | `graph/dijkstra.md` | 194 | 2 |
| 10 | Siyrak graflarda Dijkstra algoritmi | Dijkstra on sparse graphs | `graph/dijkstra_sparse.md` | 131 | 2 |
| 11 | Bellman–Ford algoritmi | Bellman-Ford Algorithm | `graph/bellman_ford.md` | 289 | 6 |
| 12 | 0–1 BFS | 0-1 BFS | `graph/01_bfs.md` | 116 | 2 |
| 13 | D´Esopo–Pape algoritmi | D´Esopo-Pape algorithm | `graph/desopo_pape.md` | 108 | 1 |

### Barcha juftliklar uchun eng qisqa yo‘llar

| # | O‘zbekcha sarlavha | Asl sarlavha | Fayl | Satr | Kod bloklari |
|---:|---|---|---|---:|---:|
| 14 | Floyd–Warshall algoritmi | Floyd-Warshall Algorithm | `graph/all-pair-shortest-path-floyd-warshall.md` | 194 | 3 |
| 15 | Belgilangan uzunlikdagi yo‘llar soni va eng qisqa yo‘llar | Number of paths of fixed length / Shortest paths of fixed length | `graph/fixed_length_paths.md` | 126 | 0 |

### Ostov daraxtlar

| # | O‘zbekcha sarlavha | Asl sarlavha | Fayl | Satr | Kod bloklari |
|---:|---|---|---|---:|---:|
| 16 | Minimal ostov daraxt — Prim algoritmi | Minimum spanning tree - Prim's algorithm | `graph/mst_prim.md` | 263 | 2 |
| 17 | Minimal ostov daraxt — Kruskal algoritmi | Minimum spanning tree - Kruskal's algorithm | `graph/mst_kruskal.md` | 166 | 1 |
| 18 | Minimal ostov daraxt — DSU bilan Kruskal algoritmi | Minimum spanning tree - Kruskal with Disjoint Set Union | `graph/mst_kruskal_with_dsu.md` | 92 | 1 |
| 19 | Ikkinchi eng yaxshi minimal ostov daraxt | Second Best Minimum Spanning Tree | `graph/second_best_mst.md` | 220 | 1 |
| 20 | Kirchhoff teoremasi: ostov daraxtlar sonini topish | Kirchhoff's theorem. Finding the number of spanning trees | `graph/kirchhoff-theorem.md` | 54 | 0 |
| 21 | Prüfer kodi | Prüfer code | `graph/pruefer_code.md` | 373 | 4 |

### Sikllar

| # | O‘zbekcha sarlavha | Asl sarlavha | Fayl | Satr | Kod bloklari |
|---:|---|---|---|---:|---:|
| 22 | Grafning siklsizligini tekshirish va siklni $O(M)$ vaqtda topish | Checking a graph for acyclicity and finding a cycle in O(M) | `graph/finding-cycle.md` | 142 | 2 |
| 23 | Grafda manfiy siklni topish | Finding a negative cycle in the graph | `graph/finding-negative-cycle-in-graph.md` | 126 | 2 |
| 24 | Euler yo‘lini $O(M)$ vaqtda topish | Finding the Eulerian path in O(M) | `graph/euler_path.md` | 182 | 3 |

### Eng yaqin umumiy ajdod

| # | O‘zbekcha sarlavha | Asl sarlavha | Fayl | Satr | Kod bloklari |
|---:|---|---|---|---:|---:|
| 25 | Eng yaqin umumiy ajdod — $O(N)$ oldindan ishlov bilan $O(\sqrt{N})$ va $O(\log N)$ | Lowest Common Ancestor - O(sqrt(N)) and O(log N) with O(N) preprocessing | `graph/lca.md` | 170 | 1 |
| 26 | Eng yaqin umumiy ajdod — ikkilik ko‘tarilish | Lowest Common Ancestor - Binary Lifting | `graph/lca_binary_lifting.md` | 124 | 1 |
| 27 | Eng yaqin umumiy ajdod — Farach–Colton va Bender algoritmi | Lowest Common Ancestor - Farach-Colton and Bender Algorithm | `graph/lca_farachcoltonbender.md` | 243 | 1 |
| 28 | RMQ masalasini LCA topishga keltirib yechish | Solve RMQ (Range Minimum Query) by finding LCA (Lowest Common Ancestor) | `graph/rmq_linear.md` | 91 | 1 |
| 29 | Eng yaqin umumiy ajdod — Tarjanning offlayn algoritmi | Lowest Common Ancestor - Tarjan's off-line algorithm | `graph/lca_tarjan.md` | 123 | 1 |

### Oqimlar va bog‘liq masalalar

| # | O‘zbekcha sarlavha | Asl sarlavha | Fayl | Satr | Kod bloklari |
|---:|---|---|---|---:|---:|
| 30 | Maksimal oqim — Ford–Fulkerson va Edmonds–Karp | Maximum flow - Ford-Fulkerson and Edmonds-Karp | `graph/edmonds_karp.md` | 224 | 1 |
| 31 | Maksimal oqim — push–relabel algoritmi | Maximum flow - Push-relabel algorithm | `graph/push-relabel.md` | 209 | 1 |
| 32 | Maksimal oqim — yaxshilangan push–relabel usuli | Maximum flow - Push-relabel method improved | `graph/push-relabel-faster.md` | 102 | 1 |
| 33 | Maksimal oqim — Dinic algoritmi | Maximum flow - Dinic's algorithm | `graph/dinic.md` | 161 | 1 |
| 34 | Maksimal oqim — MPM algoritmi | Maximum flow - MPM algorithm | `graph/mpm.md` | 220 | 1 |
| 35 | Talabli oqimlar | Flows with demands | `graph/flow_with_demands.md` | 64 | 0 |
| 36 | Minimal narxli oqim — ketma-ket eng qisqa yo‘llar algoritmi | Minimum-cost flow - Successive shortest path algorithm | `graph/min_cost_flow.md` | 161 | 1 |
| 37 | Tayinlash masalasini minimal narxli oqim yordamida yechish | Solving assignment problem using min-cost-flow | `graph/Assignment-problem-min-flow.md` | 116 | 1 |
| 38 | Minimal kesim — Stoer–Wagner algoritmi | Minimum cut - Stoer-Wagner algorithm | `graph/stoer_wagner_mincut.md` | 143 | 1 |

### Matchinglar va bog‘liq masalalar

| # | O‘zbekcha sarlavha | Asl sarlavha | Fayl | Satr | Kod bloklari |
|---:|---|---|---|---:|---:|
| 39 | Grafning ikki bo‘lakli ekanini tekshirish | Check whether a graph is bipartite | `graph/bipartite-check.md` | 61 | 1 |
| 40 | Ikki bo‘lakli grafda eng katta matching uchun Kuhn algoritmi | Kuhn's Algorithm for Maximum Bipartite Matching | `graph/kuhn_maximum_bipartite_matching.md` | 188 | 2 |
| 41 | Tayinlash masalasini yechish uchun Hungarian algoritmi | Hungarian algorithm for solving the assignment problem | `graph/hungarian-algorithm.md` | 281 | 3 |

### Turli mavzular

| # | O‘zbekcha sarlavha | Asl sarlavha | Fayl | Satr | Kod bloklari |
|---:|---|---|---|---:|---:|
| 42 | Topologik saralash | Topological Sorting | `graph/topological-sort.md` | 91 | 1 |
| 43 | Qirra bog‘liqligi / tugun bog‘liqligi | Edge connectivity / Vertex connectivity | `graph/edge_vertex_connectivity.md` | 91 | 0 |
| 44 | Daraxt qirralarini bo‘yash | Paint the edges of the tree | `graph/tree_painting.md` | 202 | 1 |
| 45 | 2-SAT | 2-SAT | `graph/2SAT.md` | 193 | 1 |
| 46 | Og‘ir-yengil dekompozitsiya | Heavy-light decomposition | `graph/hld.md` | 185 | 2 |
| 47 | Centroid dekompozitsiyasi | Centroid Decomposition | `graph/centroid_decomposition.md` | 232 | 2 |

## Umumiy ko‘rsatkichlar

| Ko‘rsatkich | Soni |
|---|---:|
| Graphs maqolalari | 47 |
| Repositorydagi source-ordered to‘liq tarjima qoralamalari | 76 |
| Qolgan konspekt/adaptatsiya qoralamalari | 87 |
| Graphs tarjima body satrlari | 7,757 |
| Graphs sarlavhalari | 329 |
| Graphs fenced code bloklari | 74 |
| Graphs display-math bloklari | 63 |
| Graphs havolalari | 489 |
| Graphs Markdown ichidagi rasm ishlatilishlari | 32 |
| Bundled noyob lokal Graphs asset fayllari | 27 |
| Generated route-local asset nusxalari | 30 |
| Texnik review approved | 0 |
| Til reviewi approved | 0 |
| Published | 0 |

## Metadata

Barcha 47 sahifa quyidagicha belgilangan:

```yaml
translation_status: ai_full_translation_draft
translation_scope: full_upstream_article
translation_fidelity: sentence_preserving_full_copy
full_prose_translated: true
technical_review: pending
language_review: pending
```

Bu metadata sahifaning maqola ko‘lamidagi, source-order AI-tarjima qoralamasi ekanini bildiradi. U inson tomonidan texnik yoki til jihatdan tasdiqlanganini bildirmaydi.

## Audit chegarasi

Tarjimalar pinned raw cp-algorithms maqolalari bo‘yicha yaratildi; sarlavhalar, bo‘limlar, izohlar, formulalar, kod namunalari, havolalar va mashq masalalari source tartibida saqlanishi ko‘zlangan. Repository barcha 47 English Markdown snapshotni bundle qilmagani sababli audit byte-for-byte English/Uzbek line diff deb da’vo qilmaydi. Inson revieweri har bir paragraf, isbot, formula va preconditionni pinned source bilan tekshirishi kerak.
