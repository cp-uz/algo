# Geometriya bo‘limi tarjima hisoboti

**Release:** 2026-08-21  
**Pinned upstream commit:** `85a94001d46b9f34d3b2cf26aca6bd0f7a7e8681`

Ushbu release pinned cp-algorithms navigatsiyasidagi **26 ta Geometry maqolasining barchasini** upstream mavzu va bo‘lim ketma-ketligiga tayangan to‘liq o‘zbekcha AI-tarjima qoralamasi sifatida qayta quradi. Maqsad mustaqil yangi darslik yozish emas, balki ta’riflar, tushuntirishlar, formulalar, isbotlar, algoritmlar, kod namunalari, havolalar va mashq bo‘limlarini manba tartibida o‘zbekchaga ko‘chirishdir.

Har bir sahifada:

```yaml
translation_status: ai_full_translation_draft
translation_scope: full_upstream_article
translation_fidelity: source_ordered_full_translation
full_prose_translated: true
technical_review: pending
language_review: pending
```

| # | Upstream turkum | O‘zbekcha sarlavha | Fayl | Qatorlar | Kod bloklari |
|---:|---|---|---|---:|---:|
| 1 | Elementary operations | Geometriya asoslari | `geometry/basic-geometry.md` | 324 | 7 |
| 2 | Elementary operations | Kesma uchun to‘g‘ri chiziq tenglamasini topish | `geometry/segment-to-line.md` | 124 | 2 |
| 3 | Elementary operations | To‘g‘ri chiziqlarning kesishish nuqtasi | `geometry/lines-intersection.md` | 168 | 4 |
| 4 | Elementary operations | Ikki kesma kesishishini tekshirish | `geometry/check-segments-intersection.md` | 94 | 1 |
| 5 | Elementary operations | Kesmalar kesishmasi | `geometry/segments-intersection.md` | 138 | 4 |
| 6 | Elementary operations | Aylana va to‘g‘ri chiziq kesishmasi | `geometry/circle-line-intersection.md` | 140 | 2 |
| 7 | Elementary operations | Ikki aylananing kesishmasi | `geometry/circle-circle-intersection.md` | 154 | 1 |
| 8 | Elementary operations | Ikki aylanaga umumiy urinmalar | `geometry/tangents-to-two-circles.md` | 138 | 3 |
| 9 | Elementary operations | Kesmalar birlashmasining uzunligi | `geometry/length-of-segments-union.md` | 93 | 2 |
| 10 | Polygons | Uchburchakning yo‘nalgan yuzi | `geometry/oriented-triangle-area.md` | 100 | 2 |
| 11 | Polygons | Sodda ko‘pburchak yuzi | `geometry/area-of-simple-polygon.md` | 107 | 2 |
| 12 | Polygons | Nuqtaning qavariq ko‘pburchakka tegishliligini O(log N) da tekshirish | `geometry/point-in-convex-polygon.md` | 165 | 3 |
| 13 | Polygons | Qavariq ko‘pburchaklarning Minkowski yig‘indisi | `geometry/minkowski.md` | 136 | 1 |
| 14 | Polygons | Pick teoremasi — panjaraviy ko‘pburchak yuzi | `geometry/picks-theorem.md` | 138 | 1 |
| 15 | Polygons | Panjaraviy bo‘lmagan ko‘pburchakdagi panjara nuqtalari | `geometry/lattice-points.md` | 137 | 1 |
| 16 | Convex hull | Qavariq qobiqni qurish | `geometry/convex-hull.md` | 171 | 2 |
| 17 | Convex hull | Convex Hull Trick va Li Chao Tree | `geometry/convex_hull_trick.md` | 154 | 4 |
| 18 | Sweep-line | Kesishuvchi kesmalar juftini topish | `geometry/intersecting_segments.md` | 155 | 2 |
| 19 | Planar graphs | Tekis graf yuzlarini topish | `geometry/planar.md` | 152 | 2 |
| 20 | Planar graphs | Nuqta joylashuvini O(log N) da aniqlash | `geometry/point-location.md` | 145 | 4 |
| 21 | Miscellaneous | Eng yaqin nuqtalar juftini topish | `geometry/nearest_points.md` | 161 | 1 |
| 22 | Miscellaneous | Delaunay triangulyatsiyasi va Voronoi diagrammasi | `geometry/delaunay.md` | 349 | 1 |
| 23 | Miscellaneous | Vertikal dekompozitsiya | `geometry/vertical_decomposition.md` | 193 | 1 |
| 24 | Miscellaneous | Yarim tekisliklar kesishmasi — O(N log N) S&I algoritmi | `geometry/halfplane-intersection.md` | 166 | 1 |
| 25 | Miscellaneous | Manhattan masofasi | `geometry/manhattan-distance.md` | 226 | 2 |
| 26 | Miscellaneous | Eng kichik qamrab oluvchi aylana | `geometry/enclosing-circle.md` | 201 | 4 |

## Audit qamrovi

* So‘ralgan Geometry maqolalari: **26/26**.
* Pinned source commit va har bir maqolaning exact raw-source URL manzili source indexda qayd etilgan.
* Ushbu Geometry release ichiga exact inglizcha Markdown snapshotlari bundle qilinmagan; shu sababli byte-level yoki jumlama-jumla avtomatik source-fidelity taqqoslash da’vo qilinmaydi.
* Har bir target sahifa to‘liq maqola ko‘lamidagi source-ordered AI-tarjima qoralamasi sifatida qurilgan.
* Inson texnik reviewi va til reviewi: **0/26**; barcha sahifalar `pending` holatida.

## Kumulative loyiha holati

| Holat | Soni |
|---|---:|
| Jami upstream article route | 163 |
| Algebra source-ordered draft | 29 |
| Data Structures source-ordered draft | 10 |
| Graphs source-ordered draft | 47 |
| Dynamic Programming source-ordered draft | 7 |
| Game Theory source-ordered draft | 2 |
| Combinatorics source-ordered draft | 10 |
| String Processing source-ordered draft | 12 |
| Geometry source-ordered draft | 26 |
| **Jami full-article AI translation draft** | **143** |
| Synopsis yoki source-faithful bo‘lmagan qoralama | 20 |
| Texnik review tasdiqlangan | 0 |
| Til reviewi tasdiqlangan | 0 |

Avtomatik build va strukturaviy tekshiruvlar inson reviewini almashtirmaydi. Geometrik degeneratsiyalar, sonli aniqlik, preconditionlar, kodning kompilyatsiyasi hamda o‘zbekcha terminologiya mutaxassislar tomonidan alohida tekshirilishi kerak.
