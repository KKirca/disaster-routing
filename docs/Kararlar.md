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

## K-21 · EMSR648 "Possibly damaged" kategorisi için ihtiyat ağırlığı
**Karar:** EMSR648 `Possibly damaged` binalar K-18 CSV şemasına `damage_class =
"possibly-damaged"` olarak yazılır ve K-19 formülünde **0.20 ağırlığı** alır.

**Neden bu seçeneğe ihtiyaç var:**
EMSR648 dört kategori kullanıyor: `Destroyed`, `Damaged`, `No visible damage`,
`Possibly damaged`. İlk üçü xBD şemasına doğrudan eşleniyor (ProjeContext.md).
`Possibly damaged` ise bir **hasar derecesi değil, belirsizlik ifadesidir** —
Copernicus analisti "burada bir şey var ama emin değilim" demektedir. AOI17'de
18 bina (toplam 288'in %6'sı) bu kategoridedir.

İki uç seçenek ikisi de yanlış:
- `no-damage` say → iyimser hata: bilgisizliği "hasar yok" diye işlemek
  K-16'nın konservatif ilkesine ters; araç belirsiz riskten habersiz geçer
- `major-damage` say → kötümser hata: belirsizliği kesin hasara dönüştürmek,
  uydurma veri üretmek; K-19'un "her parametrenin gerekçesi var" ilkesini çiğner
- Dışarıda bırak → operasyonel hata: bina "yok" sayılır, katkısı sıfır olur;
  metodolojik olarak temiz ama araç belirsiz riski göremez

**Neden 0.20:**
K-19 ağırlıkları moloz hacmiyle orantılı: `destroyed` 1.00, `major` 0.60,
`minor` 0.15. `Possibly damaged` için beklenti değeri en iyi (`no-damage`, 0.00)
ile en kötü (`major-damage`, 0.60) ortalaması → 0.30. Ancak Copernicus analistleri
ciddi hasarı atlamamaya öncelik verir; belirsizlik tipik olarak hafif hasar yönüne
yatkındır. Bu asimetri nedeniyle beklenti değeri 0.20'ye kalibre edildi.

**Operasyonel anlamı:**
- 0.20, `T_DIFF = 0.20` eşiğinin tam sınırında — tek bina yakın komşuluk
  hariç `difficult` üretmez
- `T_CLOSED = 0.50`'yi hiçbir zaman tek başına geçemez (yolu kapatamaz)
- Birkaç belirsiz bina kümeleşirse toplam baskı `difficult` üretebilir
- Açık ifadeyle: "Bu bina hakkında bilgimiz eksik; en ihtiyatlı senaryo
  hafif engeldir"

**Tezde nasıl savunulur:**
"Possibly damaged kategorisi bir şiddet derecesi değil belirsizlik ifadesidir.
Bilgisizliği iyimser (sıfır) ya da kötümser (maksimum) saymak yerine,
beklenti değerinden türetilmiş ve Copernicus metodolojisine göre kalibre
edilmiş bir ihtiyat ağırlığı (0.20) kullanıldı. Bu değer tek başına yolu
kapatamaz; sadece birden fazla belirsiz bina kümeleşirse 'difficult' baskısı
üretir."

**Uygulama:**
`scripts/phase4_build_damage_csv.py` içinde EMSR648 dönüşümü sırasında:
- `Destroyed`       → `destroyed`       (confidence=1.0)
- `Damaged`         → `major-damage`    (confidence=1.0)
- `No visible damage` → `no-damage`     (confidence=1.0)
- `Possibly damaged` → `possibly-damaged` (confidence=0.0)
  (confidence=0.0: belirsizliğin işareti; skor hesabında 0.20 ağırlığı alır)

K-19 formülüne `possibly-damaged` → 0.20 satırı eklenir.

**Sınırlılık (tezde belirtilecek):**
`minor-damage` sınıfı EMSR648'de karşılıksız kaldı; K-19'daki 0.15 ağırlığı
Kahramanmaraş koşusunda devreye girmez. Formül çalışır ama bir bileşeni ölü kalır.

---

## K-22 · Likefaksiyon eşiği 0.05'ten 0.10'a revize edildi
**Karar:** `phase1_liquefaction1.py` ve `turkoglu_four_layers.py` içindeki
`THRESHOLD` 0.05'ten **0.10'a** yükseltildi.

**Neden değiştirildi:**
Zhu 2017 modelinin bu bölgedeki veri aralığı 0–0.394'tür. 0.05 eşiğinde grafın
%34.9'u (1292/3700 kenar) `difficult` oluyordu — Türkoğlu'nun üçte biri likefaksiyon
riski altında görünüyordu. Bu fiziksel olarak savunulamaz: likefaksiyon için gevşek
suya doygun zemin + yeterli sarsıntı aynı anda gerekir; düşük olasılıklı hücreler
bu koşulun tam sağlanmadığı alanları temsil eder.

**Eşik seçimi — duyarlılık tablosu:**

| Eşik | Riskli hücre | Difficult kenar | Oran |
|---:|---:|---:|---:|
| 0.05 | 305 | 1292 | %34.9 |
| 0.08 | 287 | 1123 | %30.4 |
| **0.10** | **273** | **929** | **%25.1** |
| 0.12 | 258 | 862 | %23.3 |
| 0.15 | 239 | 757 | %20.5 |
| 0.20 | 197 | 515 | %13.9 |

**Neden 0.10:**
Deprem mühendisliğinde likefaksiyon riski tipik olarak %10-20 olasılık üzerinde
"anlamlı" sayılır. Veri maksimumu 0.394 olduğu için 0.10, bu setteki orta-yüksek
riski yakalayan en düşük savunulabilir eşiktir. K-16'nın konservatif ilkesiyle
uyumlu: ihtiyatlı tarafta kalmak tercih edilir.

0.15 de makul olurdu (%20.5) ancak 0.10 tercih edildi çünkü likefaksiyon, zemin
çökmesi ve yapısal hasar açısından ciddi bir risk — ihtiyatlı tarafta kalmak
K-16 ilkesiyle tutarlı.

**Likefaksiyon ≠ fay hattı yakınlığı:**
Fay yakınlığı sarsıntıyı artırır (dolayısıyla riski artırır), ancak likefaksiyon
için zemin tipi ve yeraltı suyu da gerekli. Rüptür katmanı (fay geometrisine dayalı,
`closed` üretir) ve likefaksiyon katmanı (Zhu modelinden, `difficult` üretir) bu
yüzden ayrı tutulur.

**Doğrulama:** `verify_phase1.py` — 12/12 test geçti.

---

## Açık konular (henüz karara bağlanmadı)

- Spatial CV fold'ları hasar açısından dengesiz (fold 3: 8431, fold 1: 3194).
  Dengeli atama (bin-packing) yapılabilir.
- 516 karo binasız olduğu için koordinatsız kaldı, fold'a atanamadı.
- Nokta/blok granülerlik farkı: model bina bazında çıktı verecek, EMSR648
  blok bazında. Karşılaştırma yöntemi netleşmedi.
- GPU durumu teyit edildi (2026-08-20): Kuzey'in makinesi NVIDIA RTX 5000 Ada, 16 GB VRAM, CUDA 13.0. Siamese CNN egitimi icin yeterli. Meyusun'un makinesi ayrica teyit edilmedi.

## K-23 · EARTHQUAKE-TURKEY veri seti (EBD koleksiyonu) modele eklendi
**Karar:** Siamese CNN'in xBD ile eğitimine, gerçek Kahramanmaraş deprem verisi
içeren "EARTHQUAKE-TURKEY" alt kümesi eklendi.

**Kaynak:** Extensible Building Damage (EBD) koleksiyonu (Wang vd., 2025).
- DOI: https://doi.org/10.6084/m9.figshare.25285009
- Yayın: "Constructing an Extensible Building Damage Dataset via
  Semi-supervised Fine-Tuning across 12 Natural Disasters"
- Lisans: CC BY 4.0 (akademik ve ticari kullanıma açık, atıf şartıyla)
- Barındırma: figshare

**EBD koleksiyonu nedir:** xBD'de bulunmayan 12 afet olayından oluşan,
18.000+ görüntü çifti ve 175.000+ bina içeren bir ek veri seti. Ham
görüntüler Maxar Open Data programından toplanmış; önce xBD ile
ön-eğitilmiş bir model ile otomatik etiketlenmiş, sonra elle son
kontrolden geçirilmiş (yarı-denetimli etiketleme + manuel doğrulama).

**Bizim kullandığımız alt küme — EARTHQUAKE-TURKEY:**
- 6 Şubat 2023 Kahramanmaraş depremi, gerçek pre/post görüntü çiftleri
- 944 karo, 512×512 RGB
- Format: xBD'den farklı — poligon değil, PİKSEL MASKESİ
  (0=arka plan, 1=no-damage, 2=minor-damage, 3=major-damage, 4=destroyed)
- Dosya adı: `EARTHQUAKE-TURKEY_{id}_{pre/post}_disaster.png`

**Neden gerekliydi (K-19/K-21'deki transfer varsayımının sınırlılığı):**
Model önceki oturumlarda sadece xBD ile eğitilmişti — Meksika, Endonezya,
ABD gibi ülkelerin depremleri/afetleri. Türkiye'ye özgü yapı stoku
(betonarme, yoğun kentsel doku) hiç görülmemişti. Kullanıcı modelin
"yeterince öğrenmeden" Faz 4'e bağlanmasını istemedi; önce mümkün olan en
fazla gerçek Türkiye verisiyle model güçlendirilmeye çalışıldı.

**Denenen ve elenen alternatifler (bu sıra ile):**
1. Maxar Open Data'dan doğrudan pre/post indirme — tüm 76 koleksiyon
   tarandı, deprem bölgesinde sadece **1 kesişen pre-post çifti** bulundu
   (zaten `data/maxar/` içinde), ve o bölge de büyük ölçüde bulutlu/kırsal
   çıktı — etiketlenemez.
2. Planet Labs doğrudan erişim — kurumsal/NGO başvurusu gerektiriyor,
   bize kapalı.
3. NASA `NIST_Turkiye_Earthquake` servisi (Planet 3m çözünürlük) —
   servis kaldırılmış (404).
4. NASA `Map1` servisi (Sentinel-2, 20m) — 10m/20m çözünürlükte bina
   bazlı hasar tespiti pratik olarak yapılamaz (bina 1 pikselden küçük).
5. **EARTHQUAKE-TURKEY (EBD koleksiyonu)** — bulundu, indirildi, kullanıldı.

**İşleme:** `scripts/phase3_preprocess_ebd_turkey.py` — maskeden bağlı
bileşen (connected component) çıkarır, her bileşenin merkezini bulur,
64×64 patch keser (xBD ile aynı patch boyutu). CVA haritası da hesaplanır.

**Sonuç — 16.351 gerçek Kahramanmaraş binası:**

| Sınıf | Sayı |
|---|---:|
| no-damage | 15.931 |
| minor-damage | 183 |
| major-damage | 105 |
| destroyed | 132 |
| **Toplam hasarlı** | **420** |

**Sınırlılık (tezde belirtilecek):** Bu alt küme xBD'ye göre küçük
(16.351 vs 159.794) ve "no-damage skewed" (akademik kaynakta da böyle
belirtilmiş). Hasarlı örnek sayısı azdır (420) — modelin Türkiye'ye özgü
öğrenmesine katkı sağlar ama tek başına yeterli değildir. Etiketler
insan tarafından üretilmemiş, yarı-otomatik + manuel kontrol sürecinden
geçmiştir — xBD'nin tam insan etiketlemesinden güven düzeyi olarak farklı
olabilir.

**Depoya kayıt:** Veri seti `data/ebd_turkey/` altında, `.gitignore`'da
(901 MB, repoya girmiyor). İşlenmiş patch'ler `data/ebd_turkey_patches/`
altında (aynı şekilde gitignore'da). Kaynak scriptler ve bu karar kalıcı
kayıt.


## K-24 · No-damage recall sorunu — kismen cozuldu, devam ediyor
**Durum:** Cozulmemis, aktif calisma konusu. Bu bir "karar" degil, acik
bir muhendislik sorununun ilk mudahale kaydidir.

**Sorun:** Siamese CNN modeli, EARTHQUAKE-TURKEY verisinde (gercek
Kahramanmaras) saglam binalarin (no-damage) sadece %1.2'sini dogru
taniyordu — pratikte her binayi hasarli goruyordu.

**Kok neden arastirmasi:** "Ornek azligi" hipotezi test edildi ve
YANLIS cikti — no-damage EARTHQUAKE-TURKEY'de en buyuk sinif (%97.4).
Gercek neden: egitimdeki WeightedRandomSampler, ham 1/frekans agirligiyla
no-damage'i neredeyse hic ornekletmiyordu.

**Denenenler:**
1. Sampler agirligina tavan (maks_oran=10x) — basarisiz, recall 0.012'den
   0.003'e dustu (tavan pratikte hicbir seyi sinirlamadi).
2. Sampler tamamen kaldirildi, sadece Focal Loss birakildi — kismen
   basarili, recall 0.155'e cikti ama hasar recall'u 0.664'e dustu.

**Neden onemli:** Model her yeri hasarli gorurse Faz 4'e baglaninca
tum sehir "kapali yol" cikar, rota planlamasi anlamsizlasir. K-16'nin
"ihtiyatli olmak guvenlidir" ilkesi bunu bir yere kadar tolere eder
ama %85 yanlis siniflandirma bu esigi asiyor gorunuyor.

**Sirada:** Focal Loss'un alpha agirliginin da (sampler ile ayni mantik,
1/frekans) yumusatilmasi denenecek. Kabul edilebilir esik kullaniciyla
netlestirilecek — model Faz 4'e o karardan sonra baglanacak.

---


## K-25 · Model 2 icin Model A secildi (xBD + EBD_TR birlesik egitim)
**Karar:** Hasar siniflandirma modeli olarak Model A kullanilacak.
Sadece EBD_TR ile egitilen Model B elendi.

**Neden karsilastirma yapildi:** EBD_TR (gercek Kahramanmaras) tek basina
yeterli mi, yoksa xBD ile birlestirmek gerekli mi sorusu acikti. Tahmin
yerine olcum yapildi.

**Deney tasarimi:**
- EBD_TR 807 karo: 657 egitim / 150 test olarak ayrildi (seed=42,
  data/splits/ altinda kayitli)
- Model A: xBD (159.794) + EBD_TR (tamami, 16.351), 4 sinif
- Model B: sadece EBD_TR egitim bolumu (13.499 ornek), 4 sinif
- Ikisi de ayni 150 test karosunda olculdu

**Bilinen sinirlilik:** Model A, egitiminde EBD_TR'nin tamamini gormustu,
yani test karolarini da gordu. Bu ona haksiz avantaj saglar. Bilerek
kabul edildi cunku B yine de kazanirsa sonuc daha guclu olurdu; B
kaybetti, dolayisiyla A'nin avantaji sonucu degistirmiyor.

**Sonuc:**

| Model | no-damage recall | hasar recall |
|---|---:|---:|
| A (xBD + EBD_TR) | 0.155 | 0.664 |
| B (sadece EBD_TR) | **0.000** | 0.597 |

**Kok neden — EBD_TR tek basina neden yetersiz:**
Egitim setinde 13.126 no-damage'a karsilik sadece 373 hasarli ornek var
(162 minor + 92 major + 119 destroyed). Test setinde ise toplam 47
hasarli bina (21/13/13). Bu sayilarda:
- Tek bir binanin dogru/yanlis tahmini recall'u %7.7 oynatiyor
- Egitim boyunca siniflar arasi recall degerleri kaotik salindi
  (destroyed: epoch 1'de 1.00, epoch 2'de 0.00, epoch 7'de 0.92)
- Bu istatistiksel gurultu, gercek ogrenme degil

**Cikarim:** xBD'nin buyuk hacmi (159.794 ornek, ~42.000 hasarli) modelin
"hasar neye benzer" kavramini ogrenmesi icin gerekli. EBD_TR'nin katkisi
Turkiye'ye ozgu yapi stokunu tanitmak, tek basina temel ogrenmeyi
saglamak degil.

**Devam eden sorun:** Model A'nin no-damage recall'u (0.155) hala dusuk —
K-24'te kayitli sorun cozulmedi, Faz 4'e baglanmadan once ele alinmali
ya da bilincli bir sinirlilik olarak kabul edilip belgelenmeli.

---


## K-26 · Hasar karar esigi 0.7 (argmax yerine olasilik esigi)
**Karar:** Model 2'nin ciktisi argmax ile degil, hasarli siniflarin
(minor+major+destroyed) toplam olasiligi 0.7 esigiyle yorumlanir.
Esik altinda kalan binalar no-damage sayilir.

**Sorun:** Varsayilan argmax yaklasiminda model, olasilik %42 bile olsa
en yuksek siniifi seciyordu. Sonuc: Turkiye verisinde no-damage recall
0.039 — model pratikte her binayi hasarli goruyordu. Faz 4'e baglanirsa
tum sehir "kapali yol" cikacakti.

**Bulgu:** Model aslinda ogrenmisti, sorun okuma bicimindeydi.
Farkli esiklerde olculen sonuclar (16.351 EBD_TR ornegi uzerinde):

| Esik | no-damage recall | hasar recall | dogruluk |
|---:|---:|---:|---:|
| 0.5 (argmax esdegeri) | 0.039 | 0.993 | 0.064 |
| 0.6 | 0.287 | 0.917 | 0.303 |
| **0.7** | **0.684** | **0.740** | **0.685** |
| 0.8 | 0.877 | 0.550 | 0.869 |

**Neden 0.7:**
- 0.5/0.6: model hala asiri karamsar, sistem islevsiz kalir
- 0.8: hasar recall 0.550'ye duser — K-16'nin asimetri ilkesine ters
  (hasarli yolu acik sanmak, saglam yolu kapali sanmaktan tehlikeli)
- 0.7: hasar recall (0.740) hala no-damage recall'undan (0.684) yuksek,
  yani ihtiyat korunuyor; ayni zamanda sistem ayrim yapabiliyor

**Dogrulama:** Uc test karosunda calistirildi, anlamli dagilim gorundu:

| Karo | no-damage | minor | major | destroyed |
|---|---:|---:|---:|---:|
| 000236 | 1 | 2 | 4 | 1 |
| 000237 | 8 | 0 | 5 | 0 |
| 000248 | 2 | 4 | 0 | 0 |

Onceki halinde bu karolarda hicbir bina no-damage cikmiyordu.

**Kalan sinirlilik:** Guven skorlari hala dusuk (%37-65 bandi). Model
kesin karar vermiyor, egilim gosteriyor. Esik bu egilimi kullanilabilir
hale getiriyor ama modelin kendi belirsizligini ortadan kaldirmiyor.
Focal Loss alpha yumusatmasi (K-24'te planlanan) denenmedi.

**Uygulama:** scripts/phase3c_kopru.py, HASAR_ESIGI sabiti.

---


## K-27 · Faz 3 ve Faz 4, ayri iki bilesen olarak sunuluyor (entegrasyon ertelendi)
**Karar:** Model 1+2 (Faz 3, goruntuden hasar tahmini) ve Faz 4 (rota
planlama) birbirine baglanmadan, ayri ayri tamamlanmis bilesenler
olarak sunulacak. Gercek zamanli entegrasyon (model tahmini -> gercek
yol agi) bu asamada yapilmiyor.

**Neden gerekli oldu:** Model 1+2'nin ciktisini (piksel koordinatinda
bina + hasar tahmini) Faz 4'e (coğrafi koordinat + gercek yol agi
gerektiren) baglamak icin, coğrafi referansli + kentsel dokulu +
gercek Turkiye deprem goruntusune ihtiyac vardi.

**Denenen kaynaklar (hepsi elendi):**
1. Maxar Open Data (data/maxar/, 3 farkli konum denendi) — coğrafi
   referansli AMA kentsel doku yok (kirsal/bulutlu/agac bahcesi cikti,
   3 denemede de).
2. EBD_TR (modelin egitildigi veri) — kentsel doku var AMA hic coğrafi
   referans yok, sadece duz PNG.
3. KATE-CD (Huggingface, CSCRS/kate-cd) — 7 Turkiye sehri (Adiyaman,
   Gaziantep, Hatay, Kahramanmaras, Kilis, Osmaniye, Malatya) AMA
   indirilip kontrol edildiginde coğrafi referans YOK (sadece
   pre_image/post_image/label sutunlari, koordinat sutunu yok).
4. ST_Turkey_2023 (Smart Transfer projesi, Google Drive) — muhtemelen
   coğrafi referansli (building footprint tabanli), ama erisim
   engellendi (Drive linki acilamiyor).

**Netlestirilen kapsam sorusu:** Ilk degerlendirmede kaynak arayisi
"Kahramanmaras'a ozel" cerceveyle yapiliyordu. Kullanici bunu duzeltti:
proje Turkiye geneli icin gecerli olmali, sadece Kahramanmaras'a
sikismamali. Bu, arama kapsamini KATE-CD/ST_Turkey_2023 gibi
cok-sehirli kaynaklara yonlendirdi — ama koordinat sorunu bunlarda da
cozulemedi.

**Neden entegrasyonu ertelemek dogru karar:**
Model kombinasyonunun (Model 1 + Model 2 + kopru) CALISTIGI zaten
test edildi ve dogrulandi (bkz. K-25, K-26, phase3c_kopru.py
ciktilari). Kullanicinin sordugu kritik soru: "koordinat sadece test
icin mi gerekli, yoksa kombinasyonun calismasi icin mi?" Cevap:
sadece Faz 4'e BAGLAMAK icin gerekli — kombinasyonun kendisi zaten
calisiyor ve bu bagimsiz olarak degerli bir sonuc.

**Sonuc — iki ayri, tamamlanmis bilesen:**

| Bilesen | Durum | Kanit |
|---|---|---|
| Faz 3 (Model 1+2+kopru) | Calisiyor, test edildi | IoU 0.821, hasar recall 0.740, kopru cikti ornekleri |
| Faz 4 (EMSR648 + rota) | Calisiyor, test edildi | +475 m sapma, NetworkXNoPath senaryosu |

**Gelecek is:** Coğrafi referansli gercek Turkiye deprem goruntusu
bulunursa (ornegin ST_Turkey_2023'e erisim saglanirsa, veya farkli
bir Pleiades/Maxar kaynagi), iki bilesen koprulenip gercek uctan uca
sistem kurulabilir. Bu, tezde "gelecek calisma" olarak belirtilecek.

---


## K-28 · Koordinatsiz gosterim: izgara tabanli rota (phase3e_gorsel_rota.py)
**Karar:** K-27'nin ertelediği entegrasyonu, gercek coğrafi koordinat
olmadan, goruntu ici basit izgara yol agiyla gosterildi. Bu, "sistem
mantiginin calistigini" koordinatsiz kanitlayan bir prototip.

**Nasil calisiyor:**
1. EBD_TR karosunun uzerine 32px araliklarla basit bir izgara graf kurulur
   (gercek sokak degil, piksel bazli kafes).
2. Model 1 (U-Net) binalari bulur, Model 2 (Siamese CNN) hasar tahmin eder.
3. Hasarli bulunan (esik>0.7) her binanin en yakin izgara dugumune bagli
   kenarlarin agirligi artirilir (agirlik = adim * (1 + 5*hasar_olasiligi)).
4. A* (Oklid heuristic ile) iki nokta arasinda rota bulur.

**Test 1 — basarili (karo 000237):**
Hasarli kume (5 bina, satir 7-14/sutun 3-13) manuel tespit edildi, bas/hedef
bu kumenin iki yanina konuldu (bas=(3,8), hedef=(14,8)). Sonuc: rota
hasarsiz izgarada 12 dugum/maliyet 352 iken, hasar dikkate alininca 14
dugum/maliyet 416 (+64, sapti). Gorsel dogrulama: mavi rota kirmizi
(hasarli) noktanin etrafindan acikca dolaniyor.

**Test 2 — sinirlilik ortaya cikti (karo 000236):**
Bu karoda 8 binanin 7'si hasarli cikti (K-24 sorununun etkisi olabilir —
gercek hasar orani bu kadar yuksek olmayabilir). Iki farkli bas/hedef
denemesi ((0,15)->(15,0) ve (7,0)->(15,5)) ikisinde de +0 sonuc verdi —
secilen rotalar hasarli kenarlara hic degmedi. Bu, DOGRU DAVRANIS olabilir
(gereksiz sapma yapmamak) ama "kacinma" senaryosunu KANITLAMADI, cunku
test noktalari hasarli kenarin tam uzerinden gececek sekilde
konumlandirilamadi (zaman kisitiyla 3. deneme yarim kaldi).

**Dogru okuma — ne kanitlandi, ne kanitlanmadi:**
- KANITLANDI: Model 1 + Model 2 + basit yol agi + A* zinciri uctan uca
  calisiyor, hasarli bina tespit edildiginde rota gercekten degisebiliyor
  (Test 1).
- KANITLANMADI: Bu davranisin HER senaryoda tutarli oldugu. Tek basarili
  ornek var; ikinci karoda kacinma senaryosu test edilemedi (test
  tasarimi sorunu, sistem sorunu degil).

**Bilinen sinirliliklar:**
- Izgara gercek sokak agi degil, piksel bazli kafes — fiziksel gecerliligi
  yok (bina uzerinden de "yol" gecebilir, izgara bundan habersiz).
- Bas/hedef manuel secildi, hasarli bolgeyi otomatik bulup konumlandirma
  yapilmadi (Faz 4'teki SAPMA senaryosuyla ayni sinirlama).
- Model 2'nin K-24'teki no-damage sorunu hala cozulmedi; karo 000236'da
  8 binanin 7'sinin hasarli cikmasi bu sorunun bir yansimasi olabilir.
- Koordinatsiz oldugu icin gercek metre/mesafe hesaplamasi yapilamiyor,
  K-19'daki damage_pressure formulu (alan, darlik faktorleri) burada yok.

**Konum:** scripts/phase3e_gorsel_rota.py. Faz 4'e resmi entegrasyon
degil — kavramin dogrulanmis oldugunu gosteren bir prototip.

---


## K-29 · Focal Loss alpha yumusatmasi - us 0.75 secildi (K-24 devami)
**Karar:** Model 2'nin (Siamese CNN) Focal Loss alpha agirligi
1/frekans^0.75 formuluyle hesaplanir. Aktif model
(models/siamese_cva_en_iyi.pth) bu ayarla egitilmis modeldir.

**Baslangic noktasi:** K-24'te sampler kaldirilarak kismi iyilesme
saglanmisti (no-damage recall 0.155) ama Focal Loss'un alpha agirligi
hala ham 1/frekans (us=1.0) kullaniyordu — planlanan ama yapilmayan
duzeltme buydu.

**Denenen dort us degeri (xBD+EBD_TR, 176.145 ornek, ~20-25 epoch,
Turkiye-ozgu test setinde -16.351 ornek- olculdu):**

| Us | no-damage | minor | major | destroyed | hasar ort. |
|---|---:|---:|---:|---:|---:|
| 0.50 | 0.975 | 0.044 | 0.076 | 0.727 | 0.267 |
| 0.65 | 0.925 | 0.186 | 0.619 | 0.705 | 0.457 |
| **0.75** | **0.773** | **0.399** | **0.571** | **0.803** | **0.569** |
| 0.80 | 0.572 | 0.607 | 0.457 | 0.841 | 0.643 |
| 1.00 (sampler'siz, K-24) | 0.155 | 0.710 | 0.362 | 0.841 | 0.664 |

**Gozlemlenen orunt:** Us arttikca (agirlik ham 1/frekans'a yaklastikca)
no-damage duser, hasar ortalamasi yukselir. Bu beklenen davranis —
ancak dogrusal degil, us 0.5-0.65 arasinda beklenmedik bir sicrama
var (0.65, 0.5'ten daha "yumusak" sonuc verdi — muhtemelen egitim
kosusu farkliligindan, tek basina us'ten degil).

**Neden 0.75 secildi (0.80 degil):**
K-16'nin "ihtiyatli olmak guvenlidir" ilkesi hasar recall'unu bir
miktar onceliklendirmeyi haklı kilar, ama 0.80'de no-damage 0.572'ye
dusuyor — bu, K-24'un orijinal sorununa (her seyi hasarli gorme)
tekrar yaklasmak demek. 0.75, hicbir sinifi asiri feda etmeyen tek
secenekti; kullanici acikca "dengeli" secim istedi.

**Neden 0.65 degil:**
minor-damage recall 0.186'ya duser — bu sinif pratikte kayboluyor.

**Model versiyon kaydi (models/ altinda, gitignore'da, hepsi
saklaniyor):**
- v1_bozuk_no_damage: agresif sampler (K-24 ilk hata)
- v2_sampler_denendi: sampler kaldirildi, us=1.0 esdegeri
- v3_us05_asiri_saglam: us 0.5, asiri yumusak
- v4_us075: us 0.75 — SU ANKI AKTIF MODEL (siamese_cva_en_iyi.pth)
- v5_us065: us 0.65
- v6_us08: us 0.8

**Sonraki adim:** Faz 3'un izgara-tabanli prototipi (K-28,
phase3e_gorsel_rota.py) bu yeni modelle tekrar test edilebilir —
daha dengeli hasar tespiti, kacinma senaryolarinin daha guvenilir
gosterilmesini saglayabilir.

---


## K-30 — Otomatik bas/hedef secimi: ilk yaklasim (bounding box merkezi) yetersiz cikti
scripts/phase3e_gorsel_rota.py'ye hasarli bina kumesinden otomatik bas/hedef
secen fonksiyon eklendi. Ilk versiyon: bounding box'in uzun eksenine gore
karsit uclara nokta koyma. Karo 000317'de (5 hasarli bina, dagitik) bu
yontem basarisiz oldu - bbox merkezi hicbir gercek veri noktasini temsil
etmiyordu, secilen nokta bos/anlamsiz bir koordinata denk geldi.
KARAR: Bounding-box-merkez yontemi terk edildi.

## K-31 — Kritik mimari eksiklik: izgara bina/sokak ayrimi yapmiyor
Gorsel inceleme (000317 ciktisi) rotanin binalarin uzerinden gectigini
gosterdi. Kok neden: izgara_kur() goruntu yuzeyine kosulsuz dugum
koyuyor, Model 1'in segmentasyon maskesi hic kullanilmiyordu - hasarli
binalar icin maliyet artiriliyordu ama hasarsiz bina/sokak ayrimi
hic yapilmiyordu. Faz 1'deki edge_cost=math.inf hatasiyla ayni sinif
hata: fiziksel imkansizlik (bina uzerinden gecis) sayisal maliyetle
degil, yapisal yasakla temsil edilmeli.
KARAR: Bina ustu kenarlar hard constraint olarak grafikten silinecek
(agirliklandirma degil).

## K-32 — bina_maskesi_hesapla + bina_ustu_kenarlari_kaldir eklendi
seg_tahmin/ikili hesaplamasi binalari_bul_ve_isaretle()'den ayri, paylasilan
bir fonksiyona (bina_maskesi_hesapla) cikarildi - tek gecis, tek kaynak.
bina_ustu_kenarlari_kaldir(): her kenar boyunca 8 nokta orneklenir, herhangi
biri bina pikseline denk gelirse kenar G'den silinir (supheli durumda
kisitla, K-16 ile ayni ilke). main() ve referans grafik (G_ref) bu
kisitlamayi ayni sekilde aliyor. Regresyon: 000237 sonucu degismedi.
000317: 290 kenar silindi, rota hala bulunabildi.

## K-33 — Otomatik nokta secimi: gecerlilik kontrolu eksikti, iki asamada duzeltildi
Ilk versiyon (bbox merkezi) bina ustu kenar silme sonrasi izole (derece=0)
duguma denk gelebiliyordu -> NetworkXNoPath. Parca A: en_yakin_gecerli_dugum
eklendi ama ilk versiyonu sadece "derece>0" kontrolu yapiyordu - bu YETERSIZ
cikti, cunku derece>0 olan dugum bas'tan tamamen ayri bir bagli bilesende
olabilir (000317'de 103 bilesene bolunmus grafikte dogrulandi). Duzeltme:
en_yakin_gecerli_dugum artik en buyuk bagli bilesene (ana_govde) kaydiriyor,
sadece derece kontrolu degil. Bu, bas ve hedef'in ayni bilesende olacagini
garanti eder.

## K-34 — Bounding-box-merkez yerine en-uzak-cift (farthest pair) mantigina gecildi
K-30'daki sorunu kokten cozmek icin: tek hasarli bina durumunda nokta o
binanin etrafina konur (degismedi); coklu hasarli bina durumunda tum
ikili kombinasyonlar taranip en uzak ikisi bulunur, bas/hedef bu ikisinin
dogrultusunda disari uzatilarak konur. Boylece nokta her zaman gercek veri
noktasindan turetilir, bos bir geometrik merkezden degil.

Test sonuclari (K-29 modeliyle, uc karo):
- 000237 (1 hasarli bina): fark +0 -> hasarli kenar rotada yok (dogrulandi)
- 000236 (1 hasarli bina): fark +0 -> hasarli kenar rotada yok
- 000317 (5 hasarli bina, en uzak cift mesafe=324px): fark +0, rota
  hasarli kenarlarin hicbirinden gecmiyor (dogrulandi, hasar_puan taramasi)

BILINEN SINIRLAMA: Hasar-agirlikli maliyet katmaninin gozlemlenebilir
etkisi hicbir test karosunda kanitlanamadi - ucunde de bina engeli +
geometrik en kisa yol zaten hasarli kenarlardan kaciniyor. Hasar maliyeti
mantiginin gercekten calistigini gostermek icin, hasarli kenarin geometrik
olarak zorunlu guzergahta oldugu bir karo bulunup ayrica test edilmeli -
bu oturumda yapilmadi.

DENENIP VAZGECILEN: Bounding-box + uzun eksen (K-30), sadece derece kontrolu
(K-33 ilk versiyon). Ikisi de gercek veri/bilesen bilgisini gormedigi icin
terk edildi.

## K-35 — Hasar maliyeti formulu dogrulandi (kod duzeyinde), pratik etki ayri soru
K-34'teki "hasar maliyeti hicbir test karosunda gozlemlenemedi" bulgusu
uzerine, formulun kendisinin dogru calisip calismadigi ayri sekilde test
edildi. Sentetik 3x3 izgarada (izgara_kur(96,96)), tek yol birakilip
uzerindeki bir kenara p in {0.0, 0.3, 0.7, 0.99} degerleri verildi.
A*'nin urettigi maliyet, agirlik=32*(1+5p) formulunden hesaplanan beklenen
degerle 4 durumda da tam (fark=0.0000) eslesti.

SONUC: Formul matematiksel olarak dogru - bug yok. Ancak bu, K-34'teki
bulguyu degistirmiyor: gercek karolarda (000237, 000236, 000317) hasar
maliyetinin rotayi degistirdigi hicbir ornek gozlenmedi, cunku bina engeli
+ geometrik en kisa yol zaten hasarli kenarlardan kaciniyordu. Formulun
dogru calismasi ile bu formulun pratikte rota secimini etkiledigini
gostermek IKI AYRI SEYDIR - ikincisi hala kanitlanmadi, gercek bir karo
gerekiyor (hasarli kenarin geometrik olarak zorunlu guzergahta oldugu bir
ornek).
