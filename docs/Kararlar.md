# Kararlar.md

> Alınan tasarım kararları, **gerekçeleri** ve **reddedilen alternatifler**.
> Amaç: aynı tartışmayı iki kez yapmamak.
> Yeni karar eklerken formatı koru: karar → gerekçe → reddedilen alternatif.
> Son güncelleme: 2026-08-17

---

## K-01 · Hibrit yaklaşım: OSM graf iskeleti + görüntüden türetilen kenar ağırlıkları

**Karar:** Yol ağı OSM'den alınır; görüntü sadece kenar maliyetlerini belirler.

**Gerekçe:** Yol topolojisini görüntüden çıkarmak hem gereksiz hem hataya açık.
OSM zaten güvenilir topoloji veriyor; asıl bilinmeyen "bu yol geçilebilir mi".

**Reddedildi:** Saf piksel→rota (uçtan uca görüntüden rota) — daha az güvenilir.

---

## K-02 · Üç kademeli traversability

**Karar:** `passable` / `difficult` / `closed`. Maliyet sırasıyla: uzunluk,
uzunluk × ceza, sonsuz.

**Gerekçe:** İkili (açık/kapalı) gerçekliği yansıtmıyor. Kısmen tıkalı yol
"gerekmezse kullanma" davranışı gerektiriyor. Faz 1'de görsel olarak doğrulandı:
rota `closed`'dan tamamen kaçtı, `difficult`'a sadece mecbur kalınca girdi.

---

## K-03 · Fay rüptürü operasyonel girdi DEĞİL, doğrulama verisi

**Karar:** Fay rüptürü Kademe 1'in operasyonel bileşeni sayılmaz. İleride model
çıktısını doğrulamak için kullanılacak.

**Gerekçe:** Veri araştırmacılar tarafından uydu görüntülerinden **elle** çiziliyor;
deprem Şubat 2023, veri sürümü Şubat 2024. Kamyonun yola çıkacağı ilk saatlerde
böyle bir veri yok.

**Not:** Faz 1'de yine de entegre edildi — veri okuma/CRS/buffer/kesişim
borularını kurmak için iskele görevi gördü.

---

## K-04 · Operasyonel Kademe 1 = USGS Ground Failure (likefaksiyon)

**Karar:** Hızlı, otomatik üretilen likefaksiyon olasılık haritası operasyonel
zemin riski sinyali olarak kullanılır → `difficult`.

**Gerekçe:** ShakeMap tetiklemesiyle **~30 dakikada** otomatik üretiliyor.
K-03'ün aksine gerçekten elde olan veri.

**Sınır:** ~460 m hücre çözünürlüğü, bölgesel. Yol ölçeğinde keskinlik vermiyor,
bu yüzden `closed` değil `difficult`.

---

## K-05 · Model tüm afet tipleriyle eğitilir, sadece depremle değil

**Karar:** xBD'nin tamamı (kasırga, yangın, sel dahil) eğitim havuzu.

**Gerekçe:** Ölçüldü — xBD'de `mexico-earthquake` tüm veri setinde sadece
**20** ağır/yıkık bina içeriyor. Deprem alt kümesiyle eğitim imkânsız.
Modelin öğrendiği şey afet tipi değil; çökmüş çatı, moloz dokusu, yapısal
deformasyon imzaları — bunlar afetler arası ortak.

**Yan fayda:** "Kasırgada eğit, Türkiye depreminde test et" zaten genelleme
iddiasının en katı sınavı.

---

## K-06 · Spatial cross-validation: blok bazlı + leave-disaster-out

**Karar:** İki ayrı bölme, iki ayrı amaç.
- **Blok bazlı** (~5.5 km, 0.05°) → hiperparametre ayarı, hızlı geri bildirim
- **Leave-disaster-out** → genelleme iddiasının sınanması
- **Türkiye (EMSR648)** → hiç dokunulmamış nihai held-out

**Gerekçe:** Ölçüldü — rastgele karo bölmesinde blokların **%80.2'si** birden
fazla fold'a dağılıyor. Blok bazlı bölmede **%0**. Komşu karo = aynı mahalle,
aynı yıkım örüntüsü, aynı uydu geçişi → model öğrenmez, tanır.

**Reddedildi:** Düz rastgele bölme.

---

## K-07 · `difficult` kademesi bina sınıfından değil, MOLOZ GEOMETRİSİNDEN türetilir

**Karar:** Köprünün orta kademesi, hasar sınıfının kendisine değil, yıkık bina
sayısı + yola uzaklıktan hesaplanan **kalan açık genişliğe** dayanır.

**Gerekçe:** Ölçüldü — hem xBD hem EMSR648'de ara kademeler neredeyse boş.
Örnek: xBD Palu karosunda 294 sağlam / 1540 yıkık ama sadece 9 `major-damage`.
EMSR648 AOI04'te 21 `Destroyed` ama sadece 7 `Damaged`.
Sebep ortak: uydudan tam yıkımı görmek kolay, kısmi hasarı ayırt etmek zor.
Yani en nüanslı karar, en zayıf sinyale dayanamaz.

---

## K-08 · Güvenlik asimetrisi: recall > precision

**Karar:** Kapalı segmentlerde **recall** birincil metrik.

**Gerekçe:** Yanlış-negatif (kapalı yolu açık sanmak) kurtarma aracını çıkmaza
sokar. Yanlış-pozitif (açık yolu kapalı sanmak) sadece biraz uzun yol demek.
Maliyetler simetrik değil, metrik de olmamalı.

---

## K-09 · Kendi etiketlememizin amacı: domain adaptasyonu + doğrulama, hacim değil

**Karar:** Label Studio ile **hedefli, az ama kaliteli** etiketleme.
İki bağımsız annotatör + hasarlı bölge çevresinden stratified sampling.
SAM sınıflandırıcı değil, **bina sınırı önerici** olarak kullanılır.

**Gerekçe:** Etiket miktarı değil kalitesi ve dağılımı belirleyici. Kör hacim
artışı sınıf dengesizliğini kötüleştirir. İki annotatör anlaşmazlığı ölçmek
(Cohen's kappa) veri kalitesine dürüst sinyal verir.

**Ek gerekçe (ölçüldü):** Hiçbir mevcut kaynak yol geçilebilirliğini doğrudan
vermiyor → hazır ground truth yoksa üretmek zorundayız.

---

## K-10 · Örnekleme küçük kasabaları hedefler, büyük şehirleri değil

**Karar:** Etiketleme ve doğrulama örnekleri Nurdağı/Türkoğlu gibi küçük
yerleşimlerden seçilir.

**Gerekçe:** Ölçüldü — hasarlı blok oranı: Kahramanmaraş **%0.4**,
Nurdağı **%9.3**, Türkoğlu **%11.8**. Küçük kasabalar 20-30 kat daha iyi
sınıf dengesi veriyor.

---

## K-11 · Model öncesi klasik baseline (CVA/NDBI)

**Karar:** CNN'den önce eğitimsiz baseline çalıştırılır.

**Gerekçe:** (a) Karşılaştırma noktası olmadan CNN skoru anlamsız,
(b) değerlendirme hattı zaten kurulmalı, (c) dakikalar sürer, GPU istemez.

---

## K-12 · Faz kapılı geliştirme, riskli iş sona

**Karar:** Her fazın sonunda çalışan bir çıktı olur. Model eğitimi Faz 3'e
kadar başlamaz.

**Gerekçe:** En yavaş ve en riskli parça sona kalır; o gelene kadar elde
gösterilebilir bir sistem olur. Faz 0'da bile demo vardı.

---

## K-13 · Türkiye etiketlemesinden önce xBD ile kalibrasyon

**Karar:** İki anotatör de önce doğru cevabı bilinen ~100 xBD örneğini etiketler.
Uzman etiketiyle uyum ve anotatörler arası kappa ölçülür.

**Gerekçe:** Türkiye verisinde ground truth yok — orada ürettiğimiz etiketler
ground truth olacak. Kalibre olmadan üretilirse hata payı ölçülemez, raporlanamaz.

**Reddedildi:** Etiketleri LLM'e doğrulatmak. Sebep: (a) xBD'nin uzman etiketleri
zaten elimizde ve daha güvenilir, (b) LLM kararları oturumlar arası tutarsız,
(c) "iki bağımsız etiketleyici, kappa 0.78" savunulabilir bir yöntem cümlesi.

## K-14 · Anotasyon dosyaları repoda tutulmaz
**Karar:** `data/labeling/annotations_*.json`, `ground_truth.csv` ve `calib/`
`.gitignore` ile engellenir. Anotasyon dosyaları, her iki tur da bittikten sonra
doğrudan karşılıklı paylaşılır.
**Gerekçe:** Kappa'nın ölçtüğü şey "iki anotatör aynı protokolü uygulayınca aynı
sonuca varıyor mu" sorusudur. Biri diğerinin etiketlerini veya cevap anahtarını
görürse bağımsızlık bozulur, kappa yapay olarak yükselir ve ölçüm anlamsızlaşır.
Bağımsızlık **mekanizmayla** korunur, ricayla değil.
**Uygulama notu:** `.gitignore` satır içi yorum desteklemez —
`ground_truth.csv  # GIZLI` satırı desenin parçası sanılır ve kural hiçbir şeyi
engellemez. Her kural `git check-ignore -v <dosya>` ile doğrulanır; çıktı boşsa
dosya engellenmiyor demektir.
**Reddedildi:** Dosyayı pushlayıp "açma" notu düşmek. Sebep: tek bir dikkatsizlik
100 görevlik turu geçersiz kılar; maliyeti geri alınamaz.

---

## K-15 · Faz 4 çıktısı: önce sürekli skor, sonra eşik
**Karar:** Köprü katmanı her yol kenarı için `damage_pressure` (0.0–1.0) üretir ve
graf kenar özniteliğine yazar. `traversability` etiketi bu skordan eşikle türetilir:
`≥ CLOSED_THRESHOLD` → `closed`, `≥ DIFFICULT_THRESHOLD` → `difficult`, altı →
`passable`. Ham skor her koşulda saklanır.
**Gerekçe:** (a) Eşik sonradan ayarlanabilir — skorlar bir kez hesaplanır, farklı
eşiklerle duyarlılık analizi yapılır. (b) "Bu kenar neden kapalı?" sorusuna sayısal
cevap verilir; katman kara kutu olmaz. (c) `difficult` zaten sürekli bir büyüklüğün
("ne kadar zor?") ayrıklaştırılmış halidir; onu doğrudan ikili kuralla üretmek bilgi
kaybıdır. (d) Bu katmanın doğruluğunu kanıtlayacak ground truth yok — doğrulanamayan
bir sistem en azından şeffaf olmalıdır.
**Reddedildi:** Doğrudan etiket üretmek (ara skor tutmadan). Sebep: eşik değişiminde
tüm hesap yeniden koşar, ablation yapılamaz, karar denetlenemez.
**Not:** `DIFFICULT_THRESHOLD = 0.30`, `CLOSED_THRESHOLD = 0.70` şu an **yer
tutucudur**. Skor formülü belirlendikten sonra gerçek dağılıma bakılarak ayarlanacak.

---

## K-16 · Katman birleştirme: konservatif (en kısıtlayıcı kazanır)
**Karar:** Bir kenarın `traversability` değeri, kaynaklardan **herhangi biri** `closed`
diyorsa `closed`'dır. Öncelik: `closed` > `difficult` > `passable`. Kaynaklar: fay
rüptürü (Faz 1), likefaksiyon (Faz 1), bina enkazı (Faz 4).
Faz 4, Faz 1'in yazdığı etiketi **gevşetemez** — yalnızca kısıtlayıcı yönde
değiştirebilir. `damage_pressure` skoru her koşulda yazılır; kenar rüptürden kapalı
olsa bile enkaz baskısı ayrıca kaydedilir.
**Gerekçe:** Hata maliyeti asimetriktir. Geçilebilir yolu kapalı saymak rotayı uzatır;
kapalı yolu geçilebilir saymak aracı enkaza yollar. Aracı ilgilendiren şey yolun hangi
sebeple kapandığı değil, kapalı olmasıdır. Faz 1'de rüptür `closed`'ının likefaksiyon
`difficult`'ını ezmesiyle (K-03/K-04) aynı ilke.
**Reddedildi:** Kaynakları ağırlıklı ortalamayla birleştirmek. Sebep: iki bağımsız
sebepten biri tek başına yeterliyken ortalama almak riski sulandırır.

---

## K-17 · Faz 4 geliştirme zemini: mexico-earthquake
**Karar:** Köprü katmanı `mexico-earthquake` seti üzerinde geliştirilip doğrulanır.
Merkez 19.3154 N, −99.1867 W (Mexico City güney merkezi); 121 karo, 32.271 bina,
~9 × 19 km. Yol grafı aynı bölgeden OSMnx ile çekilir.
**Veri hacmi:** 32.271 binanın sınıf dağılımı: no-damage 32.066, minor-damage 110,
un-classified 75, major-damage 18, destroyed 2. Yani **ağır hasarlı (yol tıkayabilecek)
bina sayısı 20'dir.** Bu 20 bina beş mekânsal kümede toplanmıştır (3+3+2+3+5 bina;
en sıkısı ~10 m yayılımlı, bitişik nizam) ve 4'ü yalıtıktır. Çoğu −99.14…−99.15
boylam şeridinde, 2017 Puebla depreminin bilinen çökme koridorunda (Roma/Condesa/
Del Valle) yer alır.
**Gerekçe:** Enkazın yolu tıkama davranışı afet tipine göre kökten değişir. Yangında
(`socal-fire`, 823 karo — en büyük set) bina çöker ama yola moloz saçmaz. Sel ve
kasırgada (`florence`, `harvey`, `matthew`) yol suyla kapanır, enkazla değil; su
çekilince açılır. Tsunamide (`palu`) moloz akıntıyla kaynak binadan uzağa taşınır.
Yalnızca depremde bina kendi üzerine/yana çöker ve moloz komşu sokağa dökülür —
Kahramanmaraş'ta olan budur. **En büyük veri seti burada yanlış veri setidir.**
Ayrıca Mexico City yoğun kentsel dokuya sahiptir (dar sokak, bitişik nizam), Antakya'ya
morfolojik olarak yakındır; kırsal setlerde (`guatemala-volcano`, 18 karo) bina-yol
ilişkisi kurulamaz.
**20 bina neden yeterli:** Faz 4 öğrenen bir model değil, **deterministik geometrik
kuraldır**. Parametreleri (moloz yayılma mesafesi, kat sayısı katsayısı, sokak genişliği
eşiği) veriden öğrenilmez; fiziksel akıldan ve literatürden gelir. Zaten öğrenilemez de:
"hangi yol gerçekten kapandı" diye bir ground truth yoktur, yani optimize edilecek bir
hedef değişken mevcut değildir. Veriye ihtiyaç parametre uydurmak için değil, **kuralın
makul davrandığını gözlemek** içindir ("3 bitişik bina çöktü, kural bu sokağı closed
diyor mu?"). Bunun için 20 bina yeterlidir; 20.000 bina aynı kontrolü tekrarlardı.
Ayrıca 20 bina tek tek uydu görüntüsünden incelenebilir — kuralın çıktısıyla
karşılaştırılacak bir **uzman muhakemesi referansı** oluşturulabilir. Bu ground truth
değildir ama tezde savunulabilir bir doğrulama yöntemidir.
**Sınırlılık (tezde belirtilecek):** Mexico City yapı stoku Antakya'dan farklıdır
(yönetmelik, kat dağılımı) ve 2017 Puebla depreminde yıkım noktasaldı — mahalleler
düzleşmedi. Kahramanmaraş'ta yıkım çok daha yaygındır. Buradan türetilen parametrelerin
aktarımı bir **transfer varsayımıdır**.

---

## K-18 · Faz 4 girdisi: model değil, ara CSV tablosu
**Karar:** Köprü katmanının girdisi sabit şemalı bir CSV'dir:
`uid,lon,lat,damage_class,confidence,source`
Koordinatlar WGS84 (EPSG:4326). `no-damage` binalar dahil edilir. `confidence` xBD
ground truth için `1.0`, model çıktısı için olasılıktır. `source` alanı `xbd_gt` veya
`model_v1` değerini alır. Faz 4 ne `.npz` okur ne de modeli çağırır.
**Gerekçe:** (a) **Tekrarlanabilirlik** — model yeniden eğitilince Faz 4 sonuçları
sessizce değişmez; tezdeki rota görseli aylar sonra yeniden üretilebilir.
(b) **Hata ayrıştırma** — rota yanlışsa hatanın modelde mi köprü katmanında mı olduğu
ayırt edilebilir. (c) **Karşılaştırmalı değerlendirme** — aynı bölgede `xbd_gt` ve
`model_v1` ile iki koşu yapılıp modelin hatasının rotaya ne kadar yansıdığı ölçülebilir
("model %70 doğrulukta, rota kalitesi %92 korunuyor" tipi bir sonuç, tek başına
sınıflandırma metriğinden değerlidir). (d) Yan fayda: Faz 4, Faz 3 tamamlanmadan
geliştirilebilir.
**Reddedildi:** `.npz` okumak — eğitim formatına kilitler, koordinat içermez, Maxar
verisine geçişte yeniden yazım gerektirir. Modeli doğrudan çağırmak — tekrarlanabilirlik
ve hata ayrıştırma kaybı.

---

## K-19 · Faz 4 karar kuralı: hasar baskısı formülü
**Karar:** Her (bina, yol kenarı) çifti için bir katkı hesaplanır, kenar başına
doygunlaşan birleştirmeyle `damage_pressure` üretilir.

    katki = sinif × mesafe × alan × darlik

      sinif  : destroyed 1.00 | major-damage 0.60 | minor-damage 0.15 | no-damage 0.00
      mesafe : max(0, 1 - d/R)         d = bina POLIGONU ile kenar arası mesafe (m)
      alan   : min(alan_m2 / 400, 1.0)
      darlik : min(7.0 / W, 1.0)       W = tahmini sokak genişliği (m)

    damage_pressure = 1 - Π(1 - katki_i)

> **Not (2026-08-17):** `alan` ve `genislik` çarpanları başlangıçta `min(x, 3.0)` /
> `min(x, 1.3)` idi (1'i aşabiliyordu, `katki` sonradan `min(.,1.0)` ile kırpılıyordu).
> Bu yapısal hataydı — bkz. `ChangeLog.md` "Skor kırpması" maddesi. Yukarıdaki, düzeltilmiş
> ve fiilen kullanılan formüldür; her faktör tanım gereği 0–1 aralığındadır.

**Sokak genişliği tahmini (W):** OSM'de `width` alanı pratikte boştur (133.559
kenarın 288'i, %0.2). `lanes` %24.3 dolu, `highway` %100 dolu. Bu nedenle taban
değer yol sınıfından okunur, şerit bilgisi varsa yukarı düzeltilir:

    W = highway_tablosu[tip]
    if lanes: W = max(W, lanes * 3.2 + 1.5)

    motorway/trunk 20 | primary 14 | secondary 11 | tertiary 9
    residential 7 | living_street 5 | service/unclassified 4
    (_link ekli tipler ana tipiyle aynı)

**Alt kararların gerekçeleri:**

*Mesafe — doğrusal azalma (eşikli veya ters kare değil):* Enkaz yayılması fiziksel
olarak sınırlıdır, yani bir kesme mesafesi vardır — ters kare bunu vermez, her bina
her kenarı bir miktar etkiler. Ama sınır keskin de değildir — eşikli fonksiyon
29.9 m'de tam etki, 30.1 m'de sıfır etki verir. Nitekim 30 m eşiğiyle yapılan ilk
denemede bir bina 30.5 m'de dışarıda, başkası 26.4 m'de içeride kaldı; aradaki 4 m
farkın fiziksel bir karşılığı yoktu. Doğrusal azalma ikisinin ortasıdır ve `R`
parametresi tek başına anlamlıdır: "bu binanın molozu en fazla R metre gider".

*Sınıf ağırlıkları — minor-damage dahil:* Projenin çıktısı ikili değil üçlüdür;
`difficult` tam olarak "geçilebilir ama yavaş" durumunu temsil eder. Cephe kaplaması
veya balkon döküntüsü bir sokağı `closed` yapmaz ama `difficult` yapabilir. 0.15
ağırlığı tek başına eşiği aşmaz, ancak birden fazla `minor` bina birikirse etki üretir.
`major-damage` için 0.60: tanım gereği binanın bir kısmı ayakta kalır, moloz hacmi
kabaca yarıdır. Daha düşük bir değer (0.4) seçilmedi çünkü Faz 2c'de anotatörde
`major-damage`/`no-damage` ayrımında **sistematik iyimserlik yanlılığı** ölçüldü
(22 örnekte 3 doğru, 12'si no-damage); model de aynı yanlılığı taşıyabilir ve düşük
ağırlık bu yanlılığı katlardı.

*Bina büyüklüğü — yayılma mesafesine değil, enkaz miktarına bağlandı:* Fiziksel
olarak `R` bina **yüksekliğine** bağlıdır (devrilen duvar kendi yüksekliği kadar
mesafeye düşer), ancak xBD kat sayısı vermez. Taban alanından yükseklik tahmin etmek
(alan → kat → yükseklik → yayılma) doğrulanamaz bir varsayım zinciri kurar ve her
halka hata ekler; geniş tek katlı depo ile dar 8 katlı apartman aynı tabana sahip
olabilir. Bunun yerine tek savunulabilir cümleye dayanıldı: **daha büyük bina daha
fazla enkaz üretir.** `R` sabit tutulduğu için duyarlılık analizi de tek parametre
üzerinden yapılabilir. Üst sınır 3.0, tek bir devasa binanın skoru tek başına
doldurmasını engeller (bu sette taban alanı 26–1499 m², 57 kat fark).

*Genişlik — doğrusal bölen, 1.3 üst sınırlı:* Tıkanma oranı kabaca
`moloz_genişliği / sokak_genişliği`'dir, yani ilişki doğrusaldır; karekök yumuşatma
fiziksel bir gerekçeye dayanmaz. Ancak sınırsız doğrusal `service` yollarını (4 m)
1.75 ile cezalandırır ve `closed` etiketleri rota açısından önemsiz arka sokaklara
yığılır. 1.3 üst sınırı bu abartıyı keser, geniş yollardaki azalma doğrusal kalır.

*Birleştirme — doygunlaşan çarpım:* Maksimum almak birikimi yok sayar (üç orta
hasarlı bina, tek ağır hasarlı binadan az sayılır — oysa üç ayrı moloz yığını sokağı
daha kesin tıkar). Düz toplam ise 0–1 aralığını bozar ve doygunluk vermez.
`1 - Π(1 - katki)` her iki sorunu da çözer ve olasılık yorumuyla savunulur: *her bina
yolu bağımsız olarak tıkayabilir; baskı, en az birinin tıkama olasılığıdır.*
Bağımsızlık varsayımı tam doğru değildir (bitişik binalar birlikte çöker), ancak bu
**konservatif yönde** hatadır — gerçek risk hesaplanandan yüksek çıkar, düşük değil.
K-16 ile uyumludur.

**Doğrulanabilirlik sınırı (tezde belirtilecek):** Bu formülün "doğru" olduğunu
gösterecek ground truth yoktur — deprem sonrası hangi yolun gerçekten kapandığını
veren bir veri seti mevcut değildir. Dolayısıyla ölçüt doğruluk değil,
**savunulabilirliktir**: her parametrenin fiziksel bir gerekçesi vardır ve yukarıda
yazılıdır. Doğrulama, 20 ağır hasarlı binanın uydu görüntüsünden tek tek incelenip
kuralın çıktısıyla karşılaştırılması yoluyla yapılacaktır (uzman muhakemesi referansı).

**Açık parametre:** `R` (moloz yayılma mesafesi) henüz sabitlenmedi. Skor dağılımı
görüldükten sonra eşiklerle (K-15) birlikte ayarlanacak.

**Doğrulama sonucu (2026-08-17):** 20 binanın uzman muhakemesiyle karşılaştırılması
%63.2 (12/19) uyum verdi. Ayrışma rastgele değil, iki sistematik kümede toplandı
(detay: `ChangeLog.md`, `reports/phase4_bina_dogrulama.csv`):

- Düşük katkıda (`< T_DIFF`) uzman çoğunlukla yine de `difficult` dedi — çoğunlukla
  görüntü okunurluğu belirsizliğinden (ihtiyati karar), bir vakada (uid `5d0b8a88`)
  küçük taban alanı + mesafenin `katki`yi olması gerekenden düşürmesinden.
- Yüksek katkıda (`≥ T_CLOSED`) iki vaka (uid `4db97035`, `66ab3129`) uzman tarafından
  `difficult` bulundu — yapı bütünlüğü büyük ölçüde korunmuş görünüyordu, formülün
  `closed` çıkarımı (alan+mesafe+darlik birleşimi) görsel kanıttan daha kötümserdi.

Bu, formülün **yanlış** olduğunu değil, `T_CLOSED = 0.50` sabit eşiğinin özellikle
büyük-alanlı-yola-çok-yakın vakalarda agresif tarafta durabileceğini gösteriyor.
Eşik zaten K-15 gereği sabitlenmedi (duyarlılık analiziyle raporlanıyor); bu bulgu
o analizin okunuşuna bir veri noktası ekliyor, tek başına eşik değişikliğini
gerektirmiyor — örneklem küçük (n=20).

---

## K-20 · Artçı sarsıntı riski kapsam dışıdır
**Karar:** Sistem yalnızca **anlık fiziksel geçilebilirliği** modeller. Hasarlı
binaların artçı sarsıntıda çökerek yolu kapatma riski hesaba katılmaz; ne rota
maliyetine girer ne de ayrı bir uyarı etiketi olarak üretilir. K-02'deki
`traversability` sözleşmesi (`passable` / `difficult` / `closed`) değişmez.

**Gerekçe:** Riski modellemek için gereken hiçbir veri elimizde yok. Çökme
olasılığı yapının taşıyıcı sistemine, hasarın gerçek yapısal karşılığına ve artçı
büyüklüğüne bağlıdır — üçü de uydu görüntüsünden okunamaz. Bir eşik seçilse
("30 m içinde ağır hasarlı bina varsa uyar") o eşiğin *neden 30 metre olduğu*
savunulamaz. Bu, K-19'da her parametre için kurulan gerekçe zincirinin
(R = 25 m → devrilen duvar kendi yüksekliği kadar düşer; alan → moloz hacmi;
darlik → tıkanma oranı) karşılığı olmayan bir sayı eklemek olurdu.

Kapsamı bilerek sınırlamak, gerekçesiz bir mekanizma eklemekten güçlüdür.

**Reddedildi — A, tam risk modeli:** Çökme olasılığı hesaplayıp rota maliyetine
katmak. Sebep: hiçbir şekilde doğrulanamaz ve K-19'un savunulabilirlik ilkesini
zayıflatır.

**Reddedildi — Orta yol, bilgilendirme etiketi:** Rota maliyetine dokunmadan
ağır hasarlı binalara yakın segmentlere "dikkat" etiketi eklemek. İki sebeple:
(a) etiketin eşiği gerekçesiz kalır, (b) sistemin çıktısını değiştirmediği için
sınanamaz — kullanılmayan ve doğrulanamayan bir çıktı projeye yük olur.

**Tezde nasıl savunulur:** "Artçı sarsıntı riskini neden hesaba katmadınız?"
sorusunun cevabı hazırdır: değerlendirildi, savunulabilir biçimde modellenemediği
için kapsam dışı bırakıldı ve bu sınır belgelendi. Bu, bilinçli bir kapsam
kararıdır.

**Bağlam:** Vaka 13'ün (`4db97035`, 1499 m²) görsel doğrulamasında ortaya çıktı —
yol yüzeyi temiz ama bina ağır hasarlı. Doğrulamanın netleştirdiği kural: karar
bina hasarına değil, **yol yüzeyinde görünür fiziksel engele** dayanır.

---

## Açık konular (henüz karara bağlanmadı)

- Likefaksiyon eşiği `THRESHOLD = 0.05` fazla geniş — grafın yarısını
  `difficult` yapıyor. `0.1`–`0.15` denenecek.
- Spatial CV fold'ları hasar açısından dengesiz (fold 3: 8431, fold 1: 3194).
  Dengeli atama (bin-packing) yapılabilir.
- 516 karo binasız olduğu için koordinatsız kaldı, fold'a atanamadı.
- Nokta/blok granülerlik farkı: model bina bazında çıktı verecek, EMSR648
  blok bazında. Karşılaştırma yöntemi netleşmedi.
- GPU durumu teyit edilmedi (Siamese CNN eğitimi için gerekli).
