# Graphs source-fidelity va release auditi

**Audit sanasi:** 2026-08-20  
**Upstream pin:** `85a94001d46b9f34d3b2cf26aca6bd0f7a7e8681`  
**Maqolalar:** 47/47

## Natija

47 ta Graphs sahifasining barchasida source-ordered full-draft metadata, pinned commit, bitta H1, yopilgan fenced code bloklari, to‘liq tarjima ogohlantirishi, attribution bo‘limi va `pending` review holati tekshirildi. Hech bir sahifa `published` yoki reviewdan o‘tgan deb belgilanmagan.

## Tekshirilgan invariants

- 47 ta pinned Graphs route manifest va `docs/graph/` ichida mavjud.
- Har bir sahifada `translation_status: ai_full_translation_draft` va `full_prose_translated: true`.
- Har bir sahifada `translation_scope: full_upstream_article` va `translation_fidelity: sentence_preserving_full_copy`.
- Barcha source commit qiymatlari `UPSTREAM_PIN` bilan teng.
- Har bir Markdown bodyda aynan bitta H1 mavjud.
- Barcha fenced code bloklari yopilgan.
- Full-draft ogohlantirishi va source/litsenziya footer mavjud.
- Synopsis ogohlantirishi Graphs full sahifalarida yo‘q.
- Manifest sarlavhalari front matter bilan mos.
- Texnik va til reviewi barcha sahifalarda `pending`.
- Graphs maqolalari ishlatadigan 27 ta lokal rasm/SVG asset `docs/graph/` ichida mavjud; static builddagi 30 ta route-local nusxa manba assetlar bilan byte-for-byte mos.
- Generated saytdagi barcha lokal `href`, `src` va HTML fragmentlar buzilmagan.

## Maqolama-maqola strukturaviy ko‘rsatkichlar

| # | Maqola | Fayl | Satr | Sarlavha | Kod | Formula | Havola | SHA-256 |
|---:|---|---|---:|---:|---:|---:|---:|---|
| 1 | Kenglik bo‘yicha qidiruv (BFS) | `graph/breadth-first-search.md` | 159 | 6 | 4 | 0 | 29 | `8437e3f24ee7…` |
| 2 | Chuqurlik bo‘yicha qidiruv (DFS) | `graph/depth-first-search.md` | 144 | 7 | 2 | 0 | 42 | `4b61e3fb31e0…` |
| 3 | Grafda bog‘langan komponentlarni topish | `graph/search-for-connected-components.md` | 105 | 6 | 2 | 0 | 5 | `6be9ae48872b…` |
| 4 | Grafdagi ko‘priklarni $O(N+M)$ vaqtda topish | `graph/bridge-searching.md` | 122 | 5 | 1 | 2 | 16 | `46fc5c387ebd…` |
| 5 | Ko‘priklarni onlayn topish | `graph/bridge-searching-online.md` | 197 | 5 | 1 | 0 | 6 | `0f54c6e2baaf…` |
| 6 | Grafdagi artikulyatsiya nuqtalarini $O(N+M)$ vaqtda topish | `graph/cutpoints.md` | 95 | 5 | 1 | 1 | 8 | `cbbfff7ff006…` |
| 7 | Kuchli bog‘langan komponentlar va kondensatsiya grafi | `graph/strongly-connected-components.md` | 380 | 12 | 4 | 1 | 25 | `6be458c4cf87…` |
| 8 | Kuchli yo‘naltirish | `graph/strong-orientation.md` | 104 | 6 | 1 | 0 | 6 | `95a39be25ddd…` |
| 9 | Dijkstra algoritmi | `graph/dijkstra.md` | 194 | 8 | 2 | 9 | 41 | `d1783f9ce2de…` |
| 10 | Siyrak graflarda Dijkstra algoritmi | `graph/dijkstra_sparse.md` | 131 | 7 | 2 | 1 | 4 | `6b6a6fd7faa4…` |
| 11 | Bellman–Ford algoritmi | `graph/bellman_ford.md` | 289 | 12 | 6 | 0 | 8 | `85f8e10a22e2…` |
| 12 | 0–1 BFS | `graph/01_bfs.md` | 116 | 5 | 2 | 1 | 14 | `a99e1fff7fc3…` |
| 13 | D´Esopo–Pape algoritmi | `graph/desopo_pape.md` | 108 | 5 | 1 | 0 | 4 | `d8b719cda324…` |
| 14 | Floyd–Warshall algoritmi | `graph/all-pair-shortest-path-floyd-warshall.md` | 194 | 8 | 3 | 1 | 30 | `ce2b3f663166…` |
| 15 | Belgilangan uzunlikdagi yo‘llar soni va eng qisqa yo‘llar | `graph/fixed_length_paths.md` | 126 | 5 | 0 | 7 | 4 | `27705fa6d341…` |
| 16 | Minimal ostov daraxt — Prim algoritmi | `graph/mst_prim.md` | 263 | 9 | 2 | 0 | 3 | `d7d40f1aa505…` |
| 17 | Minimal ostov daraxt — Kruskal algoritmi | `graph/mst_kruskal.md` | 166 | 8 | 1 | 0 | 32 | `4762daf00551…` |
| 18 | Minimal ostov daraxt — DSU bilan Kruskal algoritmi | `graph/mst_kruskal_with_dsu.md` | 92 | 5 | 1 | 0 | 5 | `6f750149f390…` |
| 19 | Ikkinchi eng yaxshi minimal ostov daraxt | `graph/second_best_mst.md` | 220 | 8 | 1 | 0 | 6 | `81a51946d4fe…` |
| 20 | Kirchhoff teoremasi: ostov daraxtlar sonini topish | `graph/kirchhoff-theorem.md` | 54 | 5 | 0 | 1 | 7 | `e67ba09655b4…` |
| 21 | Prüfer kodi | `graph/pruefer_code.md` | 373 | 12 | 4 | 8 | 6 | `463d779bc13a…` |
| 22 | Grafning siklsizligini tekshirish va siklni $O(M)$ vaqtda topish | `graph/finding-cycle.md` | 142 | 5 | 2 | 0 | 6 | `afc4e8743ea6…` |
| 23 | Grafda manfiy siklni topish | `graph/finding-negative-cycle-in-graph.md` | 126 | 7 | 2 | 0 | 7 | `24193f4fe948…` |
| 24 | Euler yo‘lini $O(M)$ vaqtda topish | `graph/euler_path.md` | 182 | 6 | 3 | 0 | 6 | `62d7454c37a3…` |
| 25 | Eng yaqin umumiy ajdod — $O(N)$ oldindan ishlov bilan $O(\sqrt{N})$ va $O(\log N)$ | `graph/lca.md` | 170 | 5 | 1 | 1 | 25 | `9202869c3ad2…` |
| 26 | Eng yaqin umumiy ajdod — ikkilik ko‘tarilish | `graph/lca_binary_lifting.md` | 124 | 5 | 1 | 0 | 6 | `274ff07eaa52…` |
| 27 | Eng yaqin umumiy ajdod — Farach–Colton va Bender algoritmi | `graph/lca_farachcoltonbender.md` | 243 | 4 | 1 | 4 | 5 | `cb822379a536…` |
| 28 | RMQ masalasini LCA topishga keltirib yechish | `graph/rmq_linear.md` | 91 | 4 | 1 | 0 | 3 | `276f425be708…` |
| 29 | Eng yaqin umumiy ajdod — Tarjanning offlayn algoritmi | `graph/lca_tarjan.md` | 123 | 4 | 1 | 0 | 4 | `c000e0878c96…` |
| 30 | Maksimal oqim — Ford–Fulkerson va Edmonds–Karp | `graph/edmonds_karp.md` | 224 | 9 | 1 | 3 | 12 | `9d3da01ce519…` |
| 31 | Maksimal oqim — push–relabel algoritmi | `graph/push-relabel.md` | 209 | 6 | 1 | 2 | 3 | `68a543e8187c…` |
| 32 | Maksimal oqim — yaxshilangan push–relabel usuli | `graph/push-relabel-faster.md` | 102 | 4 | 1 | 0 | 3 | `12d4591b5d6d…` |
| 33 | Maksimal oqim — Dinic algoritmi | `graph/dinic.md` | 161 | 12 | 1 | 0 | 4 | `7fe5b25b1ba1…` |
| 34 | Maksimal oqim — MPM algoritmi | `graph/mpm.md` | 220 | 4 | 1 | 1 | 4 | `338664bfa4e9…` |
| 35 | Talabli oqimlar | `graph/flow_with_demands.md` | 64 | 4 | 0 | 1 | 3 | `75dc4801999f…` |
| 36 | Minimal narxli oqim — ketma-ket eng qisqa yo‘llar algoritmi | `graph/min_cost_flow.md` | 161 | 8 | 1 | 0 | 12 | `414ae4fd7c8c…` |
| 37 | Tayinlash masalasini minimal narxli oqim yordamida yechish | `graph/Assignment-problem-min-flow.md` | 116 | 4 | 1 | 0 | 6 | `e3a0aea6a162…` |
| 38 | Minimal kesim — Stoer–Wagner algoritmi | `graph/stoer_wagner_mincut.md` | 143 | 7 | 1 | 10 | 4 | `8358343a9c5d…` |
| 39 | Grafning ikki bo‘lakli ekanini tekshirish | `graph/bipartite-check.md` | 61 | 5 | 1 | 0 | 8 | `7af7870e5a22…` |
| 40 | Ikki bo‘lakli grafda eng katta matching uchun Kuhn algoritmi | `graph/kuhn_maximum_bipartite_matching.md` | 188 | 15 | 2 | 0 | 6 | `999e8fc73880…` |
| 41 | Tayinlash masalasini yechish uchun Hungarian algoritmi | `graph/hungarian-algorithm.md` | 281 | 12 | 3 | 3 | 14 | `ec446c92ebde…` |
| 42 | Topologik saralash | `graph/topological-sort.md` | 91 | 5 | 1 | 0 | 5 | `0c2341c79e7d…` |
| 43 | Qirra bog‘liqligi / tugun bog‘liqligi | `graph/edge_vertex_connectivity.md` | 91 | 12 | 0 | 1 | 4 | `2c867c95000e…` |
| 44 | Daraxt qirralarini bo‘yash | `graph/tree_painting.md` | 202 | 4 | 1 | 0 | 4 | `373fc4c17827…` |
| 45 | 2-SAT | `graph/2SAT.md` | 193 | 5 | 1 | 3 | 10 | `078e9eaa0557…` |
| 46 | Og‘ir-yengil dekompozitsiya | `graph/hld.md` | 185 | 11 | 2 | 2 | 14 | `6a08789a58f7…` |
| 47 | Centroid dekompozitsiyasi | `graph/centroid_decomposition.md` | 232 | 13 | 2 | 0 | 10 | `f7d5417207ee…` |

## Muhim cheklov

The package does not bundle every English Graphs Markdown snapshot. This audit verifies the translated files, metadata, protected Markdown structure where locally available, generated routes, and release integrity; it does not claim a byte-for-byte English/Uzbek line diff.

Shuning uchun ushbu avtomatik audit inson texnik va til reviewining o‘rnini bosmaydi. Har bir ta’rif, isbot, formula, murakkablik da’vosi, precondition, kod va havola pinned upstream source bilan alohida tekshirilishi kerak.
