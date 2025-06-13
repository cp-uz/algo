# Samaradorlik

Dastur tuzganingizda uning ishlash samaradorligini o'lchashingiz kerak bo'ladi, har doim. 

Keling quyidagi masalani ishlaylik:
- Uzunligi $n$ ga teng bo'lgan $a[0], a[1], \ldots, a[n-1]$ massiv berilgan. Uning eng katta (maksimum) va eng kichik (minimum) elementlarining ayirmasini topuvchi dastur tuzing.

Ushbu masalaga C++ tilida quyidagi yechimni yozish mumkin:

```cpp
int max_minus_min(int n, vector<int> a){
    int mx = a[0], mn = a[0];

    for (int i = 1; i < n; i++){
        if (a[i] > mx){
            mx = a[i];
        }
        if (a[i] < mn){
            mn = a[i];
        }
    }

    return mx - mn;
}
```

Yechimning samaradorligini qanday o'lchaymiz? Dastur ishlashiga ketgan vaqtni o'lchashimiz mumkin, lekin bunda bir-nechta muammolar bor:

1. Vaqtni kiritilgan ma'lumotlar (input) qanchalik kattaligiga bog'liqligi. Masalan, ushbu masalada $n=1000$ ta elementlik massiv kiritilsa dasturimiz $1$ms dan kamroq vaqt ishlaydi. $n=100\;000$ qilsak $5$ms, $n=10\;000\;000$ qilsak $400$ms ishlamoqda.
1. Kompyuterlarning tezligidagi farqlar. Misol uchun yuqoridagi kodni o'z kompyuteringizda ishlatib ko'rsangiz sizda bizdan ko'ra tezroq yoki sekinroq natijalar chiqishi tabiiy.
1. Dasturlash tillarining farqi. Bir dasturlash tilida $2$ sekund ishlagan kod boshqa dasturlash tilida $5$ sekund ishlashi mumkin.

Ko'rib turganingizdek, samaradorlikni shunchaki soniyalar orqali o'lchash yetarli emas.

## Amallar soni

Keling yuqoridagi kodda bajariladigan amallar sonini sanaymiz. Soddaroq bo'lishi uchun bitta qatorni bitta amal deb hisoblaymiz.

```cpp
int max_minus_min(int n, vector<int> a){
    int mx = a[0], mn = a[0];       // 1 ta amal

    for (int i = 1; i < n; i++){    // sikl (n-1) marta ishlaydi
        if (a[i] > mx){             // 1 ta amal
            mx = a[i];              // 1 ta amal
        }
        if (a[i] < mn){             // 1 ta amal
            mn = a[i];              // 1 ta amal
        }
    }

    return mx - mn;                 // 1 ta amal
}
```

Jami bo'lib, ushbu kod $1 + (n-1) \cdot 4 + 1 = 4n-2$ ta amal bajarmoqda. Lekin har bir qator bitta amal deb oldik. Yangi o'zgaruvchi e'lon qilish ham alohida amal, sonlarni solishtirishni alohida amal deb hisoblaganimizda $6n-1$ ta amal bo'lar edi. Demak, shunchaki amallar sonini sanashning ham o'ziga yarasha kamchiliklari bor.

## Katta O

Yechim samaradorligini o'lchash uchun **katta O** (big O notation) ishlatiladi. Katta O bu funksiyalarni ularning o'sish tezligiga qarab guruhlarga ajratadi. Masalan, yuqoridagi kodimiz $4n-2$ ta (yoki $6n-1$ ta, farqi yo'q) amal bajargani uchun, $O(n)$ guruhiga kiradi. Boshqacharoq nomi chiziqli funksiyalar guruhi. Chiziqli funksiyalarning asosiy xususiyati kiritilgan ma'lumotlar soni qanchalik ortsa, bajariladigan amallar soni ham taxminan shunchaga ortishi.

Ko'p hollarda (har doim emas!) yechimning samaradorligini aniqlash uchun shunchaki kichikroq darajalarni hamda konstantalarni tashlab ketish yetarli bo'ladi. Masalan, $O(4n^5+5n^3+2n+17)$ emas, shunchaki $O(n^5)$. Yoki $O(n^2 + 1000000n)$ emas $O(n^2)$.

Buning sababi kattaroq darajali funksiyalar qachondir kichkina darajali funksiyalarni quvib o'tadi.

<center> 
    <img src="pic1.png" width="400" >
</center>
    
Quyidagi rasmda esa, amalda $n^2$ hamda $n^2 + 100n$ orasida unchalik katta farq yo'qligini ko'rishimiz mumkin:
<center> 
    <img src="pic2.png" width="600" >
</center>

Yana boshqa misolni ko'raylik:

```cpp
int foo(int n, vector<int> a){
    int cnt = 1;

    for (int i = 0; i < n; i++){
        for (int j = i + 1; j < n; j++){
            if (a[i] > a[j]) cnt++;
        }
    }

    return cnt;
}
```

Jami nechta amal ketishini hisoblab ko'raylik:
- birinchi siklda $i=0$ bo'lsa, ikkinchi sikl $n-1$ ta amal bajaradi
- $i=1$ bo'lsa $n-2$ ta amal
- $\ldots$
- $i=n-2$ bo'lsa $1$ ta amal
- $i=n-1$ bo'lsa $0$ ta amal

Jami bajarilgan amallar soni: $(n-1) + (n-2) + \ldots + 1 + 0 = \frac{n(n-1)}{2}$, ya'ni $O(n^2)$.
