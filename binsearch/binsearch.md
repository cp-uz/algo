# Ikkilik qidiruv (Binary Search)

Ikkilik qidiruv bu juda ham sodda va bir vaqtning o'zida juda ham qudratli bo'lgan qidirish algoritmi hisoblanadi.

## Tartiblangan massivda qidiruv

Aytaylik bizga tartiblangan $a$ massiv berilgan bo'lsin, ya'ni $a[0] \le a[1] \le \ldots \le a[n-1]$. Ushbu massivda $x$ soni bor yoki yo'qligini tekshirmoqchimiz. 

Bu masalani chiziqli qidiruv bilan, ya'ni barcha elementlar bo'ylab yurib chiqish orqali $O(n)$ vaqtda yechish mumkin. Ikkilik qidiruv esa buni tezroq bajarish imkonini beradi.

Bizga quyidagi massiv berilgan bo'lsin. Bu massivda $x=10$ soni bor yoki yo'qligini topmoqchimiz.
<center> 
    <img src="pic0.png" height="82" >
</center>
<br>

Keling massivning o'rtasidagi elementni topib ko'ramiz, ya'ni $a[6]=15$.

<center> 
    <img src="pic1.png" height="120" >
</center>

$a[6]=15 \gt 10 = x$ bo'lgani uchun, $x$ soni massivning faqat chap tarafida bo'lishi mumkinligini topishimiz mumkin, chunki o'ng tarafdagi barcha elementlar $x$ dan katta. 

Massivni ikkiga "bo'lib" yuboramiz va uning ham o'rtasini topamiz:

<center> 
    <img src="pic2.png" height="120" >
</center>

E'tibor bering, massivda elementlar soni juft bo'lgani uchun o'rtadagi element $a[2]$ yoki $a[3]$ bo'lishi mumkin. Bunda ularning ixtiyoriysini tanlash mumkin.

Ko'rish mumkinki $a[2]=8 \lt 10 = x$, demak massivning chap tomonidagi barcha elementlar $x$ dan kichik.

Bu massivni ikkiga bo'lib yuboramiz va o'rtasini topamiz:
<center> 
    <img src="pic3.png" height="120" >
</center>

$a[4]=12 \gt 10 = x$. Massivning chap tomoniga o'tamiz:

<center> 
    <img src="pic4.png" height="120" >
</center>

$a[3]=10=x$. Demak massivda $x$ soni bor va uning indeksi $3$. 

Agar massivda bitta element qolsa va u ham $x$ ga teng bo'lmasa, demak massivda $x$ soni yo'q bo'lardi.

### Asimptotika

Ko'rish mumkinki, har safar massivni bo'lganimizda uning o'lchami 2 baravar kamayib boradi, ya'ni $n \rightarrow \lfloor \frac{n}{2} \rfloor \rightarrow \lfloor \frac{n}{4} \rfloor \rightarrow \ldots \rightarrow 1$. Bo'lishlar soni esa $\log_2{n}$ dan ko'p emas. Demak, binar qidiruv $O(\log{n})$ vaqtda ishlaydi.

### Kod

Qulaylik uchun ikkita indeks saqlaylik: $l=0$ va $r=n-1$. Massivni bo'lish o'rniga shunchaki $[l, r]$ oraliq ichida elementni qidiramiz, bunda massivning o'rtasi $m = \lfloor \frac{l+r}{2} \rfloor$. Massivni chap tomoniga o'tish uchun shunchaki $r=m-1$, o'ng tomoniga o'tish uchun esa $l=m+1$ tenglashtirib qo'yish yetarli.

```cpp
... // a[0], a[1], ..., a[n-1] tartiblangan massiv bo'lsin
int l = 0, r = n - 1;
bool found = false;
while (l <= r) {
    int m = (l + r) / 2;
    
    if (a[m] == x) {
        found = true;
        break;
    }
    
    if (a[m] < x) {
        l = m + 1;
    } else {
        r = m - 1;
    }
    
}
```

### Alternativ kod

Ko'pincha oraliqni inklyuziv, ya'ni $[l, r]$ ko'rinishida emas, balki $[l, r)$ yoki $(l,r)$ ko'rinishida saqlash ham foydali bo'lishi mumkin. Bunga misollardan biri quyidagicha:
- Lower bound -- massivda $x$ dan katta yoki teng bo'lgan eng kichkina element.
- Upper bound -- $x$ dan kichik yoki teng bo'lgan eng katta element.

Qulaylik uchun $l=-1$ va $r=n$ deb olaylik, ya'ni $a[-1]=-\infty$ va $a[n]=\infty$ deb faraz qilishingiz mumkin. Lower bound'ni topish uchun, quyidagi ikki hossani saqlaylik: $a[l]$ har doim $x$ dan kichik va $a[r]$ har doim $x$ dan katta yoki teng.
```cpp
...
int l = -1; // a[l] < x
int r = n;  // a[r] >= x
while (r > l + 1) {
    int m = (l + r) / 2;
    if (a[m] < x) {
        l = m;
    } else {
        r = m;
    }    
}
// lower bound = r
```

Upper bound'ni ham shunga o'xshash usulda topsa bo'ladi, faqat hossa biroz o'zgaradi: $a[l]$ har doim $x$ dan kichik yoki teng va $a[r]$ har doim $x$ dan katta.
```cpp
...
int l = -1; // a[l] <= x
int r = n;  // a[r] > x
while (r > l + 1) {
    int m = (l + r) / 2;
    if (a[m] <= x) {
        l = m;
    } else {
        r = m;
    }    
}
// upper bound = l
```



## Javob bo'ylab ikkilik qidiruv

Ikkilik qidiruvni massiv aniq berilmagan holatda ham ishlatish mumkin. Quyidagi masalani olaylik ([Factory Machines](https://cses.fi/problemset/task/1620)):

> Fabrikada $n$ ta mashina bor. $i$-mashina bitta detal ishlab chiqarishga $k[i]$ daqiqa vaqt sarflaydi. $t$ ta detal yasash uchun kamida qancha vaqt kerak?

**Yechim:**
Aytaylik $f(x)$ bu $x$ daqiqa ichida jami yasaladigan detallar soni bo'lsin. Ya'ni,

$$f(x) = \Bigg\lfloor \frac{x}{k[0]} \Bigg\rfloor + \Bigg\lfloor \frac{x}{k[1]} \Bigg\rfloor + \ldots + \Bigg\lfloor \frac{x}{k[n-1]} \Bigg\rfloor$$

Ko'rinib turibdiki, vaqt oshgani sari, ishlab chiqariladigan detallar soni ham oshadi, ya'ni $f(0) \le f(1) \le f(2) \le \ldots$ Vazifamiz $f(x) \ge t$ bo'lgan minimal $x$ ni topish.

Faqat kichik muammo $l$ va $r$ o'zgaruvchilariga boshlang'ich qiymat berish. Boshlang'ich qiymatda har doim $f(l) \lt t$ va $f(r) \ge t$ bo'lishi kerak. $l$ uchun $0$ ni tanlashimiz mumkin, chunki $f(0)=0$. Boshqa tomondan, $r$ uchun eng yomon holat $t=10^9$ bo'lganda va faqatgina bitta mashina, $n=1$ va $k[0]=10^9$ bo'lganida sodir bo'ladi, bu holatda $r=10^{18}$ tanlashimiz mumkin.

```cpp
#include <bits/stdc++.h>

using namespace std;

int n, t;
vector<int> k;

long long f(long long x) {
    long long details = 0;
    for (int i = 0; i < n; i++) {
        details += x / k[i];
        if (details >= t) break; // overflow bo'lmasligi uchun
    }
    return details;
}

int main(){
    cin >> n >> t;

    k.resize(n);
    for (int i = 0; i < n; i++) cin >> k[i];

    long long l = 0;
    long long r = (long long)1e18;
    while (r > l + 1) {
        long long m = (l + r) / 2;
        if (f(m) >= t) {
            r = m;
        } else {
            l = m;
        }
    }

    cout << r << endl;

    return 0;
}
```

Ko'rinib turibdiki, $f(m)$ ni hisoblash uchun $O(n)$ vaqt ketadi, ikkilik qidiruv uchun esa $O(\log{10^{18}})$. Demak yechimimizning umumiy ishlash vaqti $O(n \log{10^{18}})$. 

### Eksponensial qidiruv

Yuqoridagi masalada $f(r) \ge t$ bo'lgan $r$ ni hech qanday hisob-kitobsiz topish ham mumkin. Buning uchun eksponensial qidiruvni qo'llashimiz mumkin:
```cpp
long long r = 1;
while (f(r) < t) r *= 2;
```
Ushbu kodni qo'shgandan so'ng overflow haqida qayg'urmasak ham bo'ladi.

## Haqiqiy sonlar

Agar masalada butun bo'lmagan (haqiqiy) sonlar ishlatilsa, yuqoridagi kodlarimiz ishlamasligi mumkin. `while (r > l + 1)` o'rniga o'rniga `while (r - l > eps)` yozishingiz mumkin, bu yerda $\text{eps}$ juda ham kichkina son -- masalada javobning so'ralayotgan aniqligidan kelib chiqib belgilanadigan konstanta (odatda $10^{-6}$).

Boshqacha usuli, shunchaki javobni topish uchun bir-nechta iteratsiya bajarish. Ya'ni `while (r > l + 1)` o'rniga `for (int it = 0; it < 80; it++)`. Bunda ham so'ralayotgan aniqlikdan kelib chiqib iteratsiyalar sonini kamaytirish yoki ko'paytirish mumkin.

## Mashg'ulot uchun masalalar

- [Codeforces EDU Practice 1](https://codeforces.com/edu/course/2/lesson/6/1/practice)
- [Codeforces EDU Practice 2](https://codeforces.com/edu/course/2/lesson/6/2/practice)
- [Codeforces EDU Practice 3](https://codeforces.com/edu/course/2/lesson/6/3/practice)
- [Codeforces EDU Practice 4](https://codeforces.com/edu/course/2/lesson/6/4/practice)
- [Codeforces - Interesting Drink](https://codeforces.com/problemset/problem/706/B)
- [Codeforces - Magic Powder 1](https://codeforces.com/problemset/problem/670/D1)
- [Codeforces - Another Problem on Strings](https://codeforces.com/problemset/problem/165/C)
- [Codeforces - Frodo and pillows](https://codeforces.com/problemset/problem/760/B)
- [Codeforces - GukiZ hates Boxes](https://codeforces.com/problemset/problem/551/C)
- [Codeforces - Enduring Exodus](https://codeforces.com/problemset/problem/645/C)
- [CSES - Factory Machines](https://cses.fi/problemset/task/1620)
- [CSES - Array Division](https://cses.fi/problemset/task/1085)
- [CSES - Multiplication Table](https://cses.fi/problemset/task/2422)