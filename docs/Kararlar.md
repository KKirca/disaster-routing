# Kararlar.md

> Alınan tasarım kararları, **gerekçeleri** ve **reddedilen alternatifler**.
> Amaç: aynı tartışmayı iki kez yapmamak.
> Yeni karar eklerken formatı koru: karar → gerekçe → reddedilen alternatif.
> Son güncelleme: 2026-07-30

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

## Açık konular (henüz karara bağlanmadı)

- Likefaksiyon eşiği `THRESHOLD = 0.05` fazla geniş — grafın yarısını
  `difficult` yapıyor. `0.1`–`0.15` denenecek.
- Spatial CV fold'ları hasar açısından dengesiz (fold 3: 8431, fold 1: 3194).
  Dengeli atama (bin-packing) yapılabilir.
- 516 karo binasız olduğu için koordinatsız kaldı, fold'a atanamadı.
- Nokta/blok granülerlik farkı: model bina bazında çıktı verecek, EMSR648
  blok bazında. Karşılaştırma yöntemi netleşmedi.
- GPU durumu teyit edilmedi (Siamese CNN eğitimi için gerekli).
