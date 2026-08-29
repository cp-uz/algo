# Data Structures source-fidelity auditi

**Release:** 2026-08-21  
**Upstream pin:** `85a94001d46b9f34d3b2cf26aca6bd0f7a7e8681`  
**Audit natijasi:** barcha qo‘llaniladigan avtomatik va manual source-order tekshiruvlari o‘tdi; inson reviewi `pending`

## Qamrov va usul

- Pinned upstream navigatsiyasidagi Data Structures bo‘limining 10/10 maqolasi manifestga kiritilgan.
- 5 ta exact English Markdown snapshot `upstream/src/data_structures/` ichida mavjud.
- 5 ta qolgan manba exact pinned raw URL bilan `upstream/data-structures-source-index.json` ichida qayd etilgan.
- Bundled snapshotlar uchun fenced code byte-for-byte, display-math ketma-ketligi, link targetlari, inline-code tokenlari va heading soni avtomatik tekshirildi.
- Pinned raw URL bilan indekslangan besh sahifa uchun source bo‘lim tartibi, kod bloklari va article completeness ko‘rib chiqildi; lokal source snapshot bo‘lmagani uchun byte-level automatic comparison bajarilgan deb da’vo qilinmaydi.
- Barcha sahifalarda full-draft warning, attribution footer va `pending` review holati tekshirildi.

## Maqolama-maqola natijalar

| # | Maqola | Fayl | Source satr | Tarjima satr | Sarlavha | Kod | Formula | Havola | Tekshiruv |
|---:|---|---|---:|---:|---:|---:|---:|---:|---|
| 1 | Minimum Stack va Minimum Queue | `data_structures/stack_queue_modification.md` | 192 | 185 | 7 | 16 | 1 | 3 | automated bundled snapshot |
| 2 | Sparse Table | `data_structures/sparse-table.md` | 155 | 160 | 7 | 8 | 1 | 25 | pinned raw source review |
| 3 | Kesishmaydigan to‘plamlar birlashmasi (DSU) | `data_structures/disjoint_set_union.md` | 592 | 489 | 20 | 12 | 2 | 20 | automated bundled snapshot |
| 4 | Fenwick daraxti | `data_structures/fenwick.md` | 458 | 457 | 16 | 10 | 10 | 40 | pinned raw source review |
| 5 | Sqrt Decomposition | `data_structures/sqrt_decomposition.md` | 250 | 219 | 10 | 4 | 5 | 13 | automated bundled snapshot |
| 6 | Segment daraxti | `data_structures/segment_tree.md` | 1213 | 1211 | 33 | 23 | 0 | 33 | automated bundled snapshot |
| 7 | Treap | `data_structures/treap.md` | 384 | 416 | 16 | 9 | 0 | 19 | pinned raw source review |
| 8 | Sqrt Tree | `data_structures/sqrt-tree.md` | 351 | 345 | 14 | 2 | 6 | 2 | automated bundled snapshot |
| 9 | Tasodifiylashtirilgan heap | `data_structures/randomized_heap.md` | 113 | 108 | 7 | 2 | 4 | 0 | pinned raw source review |
| 10 | Ma’lumotlar tuzilmasidan O(T(n) log n) da o‘chirish | `data_structures/deleting_in_log_n.md` | 145 | 150 | 5 | 1 | 0 | 4 | pinned raw source review |

## Machine-readable fayllar

- `reports/data-structures-source-fidelity-audit.json` — article-level metrikalar, source-snapshot holati va check natijalari.
- `reports/data-structures-fidelity/article-map.tsv` — source/target xaritasi.
- `upstream/data-structures-source-index.json` — exact pinned raw source URLlari va snapshot coverage.

## Muhim cheklov

Ushbu audit source tartibi va himoyalangan texnik material saqlanganini tekshiradi. U har bir tarjima jumlasining semantik aniqligini to‘liq kafolatlamaydi. Shu sababli barcha maqolalarda texnik va til reviewi `pending` bo‘lib qoladi.
