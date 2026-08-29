# Dynamic Programming va Game Theory source-fidelity auditi

**Audit sanasi:** 2026-08-21  
**Upstream pin:** `85a94001d46b9f34d3b2cf26aca6bd0f7a7e8681`  
**Maqolalar:** 9/9

## Natija

Pinned English Markdown snapshotlari va o‘zbekcha target fayllari to‘qqiz maqolaning barchasi uchun avtomatik solishtirildi. Barcha belgilangan strukturaviy va protected-content tekshiruvlari muvaffaqiyatli yakunlandi.

## Tekshirilgan invariantlar

- 7 ta Dynamic Programming va 2 ta Game Theory source snapshoti `upstream/src/` ichida mavjud.
- Har bir sahifada `translation_status: ai_full_translation_draft`, `translation_scope: full_upstream_article` va `full_prose_translated: true` mavjud.
- Har bir source commit qiymati `UPSTREAM_PIN` bilan teng.
- Fenced code bloklarining information stringlari va tanasi pinned source bilan byte-for-byte bir xil.
- Display-math bloklari aynan va asl ketma-ketlikda saqlangan.
- Markdown link targetlari multiset sifatida aynan saqlangan.
- Source inline-code tokenlarining har biri targetda saqlangan.
- Markdown heading darajalari ketma-ketligi aynan saqlangan.
- List item, table row va admonition marker sonlari aynan saqlangan.
- Tarjima body hajmi source bodyga nisbatan 0.75–1.50 oralig‘ida; bu accidental summary yoki keskin ortiqcha matnni aniqlash uchun completeness heuristic.
- Full-draft warning, attribution footer va `pending` review holati mavjud.

## Maqolama-maqola ko‘rsatkichlar

| # | Maqola | Fayl | Source satr | Tarjima satr | Nisbat | Sarlavha | Kod | Formula | Havola | Source SHA-256 |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | Dinamik dasturlashga kirish | `dynamic_programming/intro-to-dp.md` | 161 | 154 | 1.065 | 7 | 6 | 1 | 13 | `0890c7073400…` |
| 2 | Ryukzak masalasi | `dynamic_programming/knapsack.md` | 181 | 181 | 1.016 | 16 | 4 | 8 | 10 | `1504123247f0…` |
| 3 | Eng uzun o‘suvchi qism ketma-ketlik | `dynamic_programming/longest_increasing_subsequence.md` | 311 | 343 | 1.006 | 16 | 4 | 7 | 16 | `ee605f44916f…` |
| 4 | Divide and Conquer yordamida DP optimallashtirishi | `dynamic_programming/divide-and-conquer-dp.md` | 132 | 107 | 1.036 | 6 | 1 | 2 | 20 | `d5a841ed2e8e…` |
| 5 | Knuth optimallashtirishi | `dynamic_programming/knuth-optimization.md` | 191 | 190 | 1.018 | 9 | 1 | 12 | 8 | `4a729deb6739…` |
| 6 | Buzilgan profil bo‘yicha DP: “Parquet” masalasi | `dynamic_programming/profile-dynamics.md` | 78 | 82 | 1.020 | 5 | 1 | 0 | 16 | `bc32e72e05fe…` |
| 7 | Eng katta nollardan iborat ostmatritsani topish | `dynamic_programming/zero_matrix.md` | 89 | 88 | 1.013 | 5 | 2 | 0 | 0 | `b7ec4ab9a042…` |
| 8 | Ixtiyoriy graflardagi o‘yinlar | `game_theory/games_on_graphs.md` | 196 | 204 | 1.001 | 4 | 2 | 0 | 1 | `8015a949d9f7…` |
| 9 | Sprague–Grundy teoremasi. Nim | `game_theory/sprague-grundy-nim.md` | 218 | 210 | 1.034 | 14 | 0 | 2 | 7 | `67efb1abe537…` |

## Machine-readable fayllar

- `reports/dynamic-programming-game-theory-source-fidelity-audit.json` — to‘liq article-level metrikalar, SHA-256 qiymatlari va barcha check natijalari.
- `reports/dynamic-programming-game-theory-fidelity/article-map.tsv` — maqolalar bo‘yicha ixcham source/target xaritasi.

## Muhim cheklov

Strukturaviy tenglik tarjimaning konspekt emasligini va protected texnik material yo‘qolmaganini kuchli ko‘rsatadi, ammo avtomatik audit har bir jumlaning ma’nosi mutlaqo to‘g‘ri tarjima qilinganini tasdiqlay olmaydi. Texnik va til reviewi shuning uchun barcha sahifalarda `pending` bo‘lib qoladi.
