# Data Structures — source-ordered o‘zbekcha tarjima hisoboti

**Release:** 2026-08-21  
**Upstream pin:** `85a94001d46b9f34d3b2cf26aca6bd0f7a7e8681`  
**Qamrov:** Data Structures 10/10  
**Holat:** to‘liq AI-tarjima qoralamalari; texnik va til reviewi `pending`

## Tuzatish

Oldingi Data Structures paketi to‘liq tarjima deb belgilangan bo‘lsa-da, keyingi release’da source-faithful ekanligi ishonchli tasdiqlanmagani sababli konspekt holatiga qaytarilgan edi. Ushbu release’da Data Structures navigatsiyasidagi o‘nta sahifa pinned cp-algorithms maqolalari tartibi bo‘yicha qayta tekshirildi va source-ordered o‘zbekcha tarjima qoralamasi sifatida tiklandi.

Har bir maqolada upstream bo‘limlar, tushuntirishlar, formulalar, kod bloklari, misollar, havolalar va mashq masalalari ketma-ketligi saqlangan. Barcha sahifalar `ai_full_translation_draft` holatida; inson texnik yoki til reviewi tasdiqlanmagan.

## Maqolalar

| # | O‘zbekcha sarlavha | Asl sarlavha | Fayl | Source satr | Tarjima satr | Kod | Formula | Source snapshot |
|---:|---|---|---|---:|---:|---:|---:|---|
| 1 | Minimum Stack va Minimum Queue | Minimum Stack / Minimum Queue | `data_structures/stack_queue_modification.md` | 192 | 185 | 16 | 1 | bundled |
| 2 | Sparse Table | Sparse Table | `data_structures/sparse-table.md` | 155 | 160 | 8 | 1 | pinned raw URL |
| 3 | Kesishmaydigan to‘plamlar birlashmasi (DSU) | Disjoint Set Union | `data_structures/disjoint_set_union.md` | 592 | 489 | 12 | 2 | bundled |
| 4 | Fenwick daraxti | Fenwick Tree | `data_structures/fenwick.md` | 458 | 457 | 10 | 10 | pinned raw URL |
| 5 | Sqrt Decomposition | Sqrt Decomposition | `data_structures/sqrt_decomposition.md` | 250 | 219 | 4 | 5 | bundled |
| 6 | Segment daraxti | Segment Tree | `data_structures/segment_tree.md` | 1213 | 1211 | 23 | 0 | bundled |
| 7 | Treap | Treap | `data_structures/treap.md` | 384 | 416 | 9 | 0 | pinned raw URL |
| 8 | Sqrt Tree | Sqrt Tree | `data_structures/sqrt-tree.md` | 351 | 345 | 2 | 6 | bundled |
| 9 | Tasodifiylashtirilgan heap | Randomized Heap | `data_structures/randomized_heap.md` | 113 | 108 | 2 | 4 | pinned raw URL |
| 10 | Ma’lumotlar tuzilmasidan O(T(n) log n) da o‘chirish | Deleting from a data structure in O(T(n) log n) | `data_structures/deleting_in_log_n.md` | 145 | 150 | 1 | 0 | pinned raw URL |

## Umumiy ko‘rsatkichlar

| Ko‘rsatkich | Soni |
|---|---:|
| Data Structures maqolalari | 10 |
| Ushbu release’dagi yangi source-ordered maqolalar | 10 |
| Repositorydagi source-ordered to‘liq tarjima qoralamalari | 95 |
| Qolgan konspekt/adaptatsiya qoralamalari | 68 |
| Bundled exact English Markdown snapshotlari | 5 |
| Pinned raw URL bilan indekslangan manbalar | 5 |
| O‘zbekcha source-ordered article-content satrlari | 3,740 |
| Kod bloklari | 87 |
| Display-math bloklari | 29 |
| Havola targetlari | 159 |

## Source snapshot holati

Quyidagi beshta exact pinned source snapshot repositoryda mavjud va validator ularni tarjima bilan avtomatik solishtiradi: `stack_queue_modification.md`, `disjoint_set_union.md`, `sqrt_decomposition.md`, `segment_tree.md`, `sqrt-tree.md`.

Qolgan beshta maqola — `sparse-table.md`, `fenwick.md`, `treap.md`, `randomized_heap.md`, `deleting_in_log_n.md` — exact pinned raw URL, upstream tag va source satr soni bilan `upstream/data-structures-source-index.json` faylida qayd etilgan. Internet mavjud muhitda `scripts/fetch_upstream.py` ularning exact Markdown snapshotlarini yuklaydi. Ushbu release avtomatik bajarilmagan byte-level tekshiruvni bajarilgandek ko‘rsatmaydi.

## Review holati

Barcha o‘nta sahifada `technical_review: pending` va `language_review: pending`. Strukturaviy va protected-content tekshiruvlar tarjimaning qisqa konspekt emasligini ko‘rsatadi, lekin har bir o‘zbekcha jumlaning texnik va til jihatdan mukammalligini isbotlamaydi.
