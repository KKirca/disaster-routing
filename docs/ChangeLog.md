# ChangeLog.md

> Kronolojik ilerleme kaydı. **Yeni girdiler en üste** eklenir.
> Format: fazın sonunda bir girdi — her konuşmadan sonra değil.
> Yerleşmiş bilgiler periyodik olarak `ProjeContext.md`'ye taşınıp buradan kısaltılır.

---

## [Faz 3 - Koordinat sorunu ve Yol A karari (K-27)] - 2026-09-13

### Kritik soru: Model kombinasyonu Faz 4'e neden hemen baglanamiyor

Onceki oturumda Model 1 (U-Net, IoU 0.821) ve Model 2 (Siamese CNN,
esik 0.7 ile hasar recall 0.740) EBD_TR verisiyle basariyla test
edilmisti. Kopru scripti (phase3c_kopru.py) ikisini birbirine
basariyla bagliyordu.

Bu oturumda amac: bu kombinasyonu Faz 4'e (rota planlama) baglamak.
Sorun ortaya cikti: EBD_TR goruntulerinde HIC coğrafi koordinat yok
(sadece duz PNG). Model 1+2'nin urettigi bina konumlari piksel
bazinda ("x=382, y=130"), Faz 4 ise gercek dunya mesafesi (metre,
lon/lat) gerektiriyor. Bu ikisi baglanamiyordu.

### Kapsam duzeltmesi

Ilk arayis "Kahramanmaras'a ozel" cerceveyle yapiliyordu. Kullanici
bunu duzeltti: proje Turkiye geneli icin gecerli olmali, tek sehre
sikismamali. Bu, arama kapsamini genisletti.

### Denenen kaynaklar - 4 deneme, hepsi elendi

**1. Maxar Open Data (data/maxar/) - 3. deneme**
Onceki oturumlarda 2 kez denenmis (bulutlu, kirsal). Bu oturumda
3. kez: en yuksek varyansli nokta bulundu (varyans analiziyle,
512x512 pencereler halinde taranarak), Model 1'e verildi.
Sonuc: 0 bina bulundu. Goruntu incelendiginde zeytin/bag bahcesi
oldugu gorundu - varyans agac dokusundan geliyordu, binadan degil.
Kentsel bolge aramasi rastgele/varyans bazli yontemle basarisiz
oldu. Uc denemenin ucu de ayni sonuca vardi: bu Maxar karosu genel
olarak kirsal bir bolgeyi kapsiyor.

**2. EMSR648 kaynak goruntusu arama**
EMSR648'in kaynak XML metadata'sina bakildi (source_r1_v2.xml),
uydu/saglayici bilgisi bulunamadi (satellite/sensor/platform
anahtar kelimeleri hic gecmiyordu). Bu yol tukendi.

**3. KATE-CD (Huggingface, CSCRS/kate-cd)**
Akademik literatur taramasinda bulundu: 7 Turkiye sehri (Adiyaman,
Gaziantep, Hatay, Kahramanmaras, Kilis, Osmaniye, Malatya), Maxar +
Airbus Pleiades kaynakli, 0.3-0.5m cozunurluk. datasets kutuphanesi
kuruldu, indirildi (404 train + 44 val + 38 test = 486 ornek).
Sutunlar kontrol edildi: sadece pre_image, post_image, label.
Koordinat/metadata sutunu YOK. Bu kaynak da elendi.

**4. ST_Turkey_2023 (Smart Transfer projesi)**
Ayni literatur taramasinda "Smart Transfer" makalesi bulundu -
9 Turkiye bolgesi (Gaziantep, Hatay, Kahramanmaras, Kirikhan,
Nurdagi, Sakcagozu, Satirhuyuk, Sekeroba, TURKOGLU dahil), 288.567
bina, Pleiades VHR (0.3m) + GlobalBuildingAtlas bina footprint'leri
(footprint = coğrafi referansli poligon, umut vericiydi). Google
Drive'da acik erisimli. Ancak Drive linkine bu ortamdan erisim
saglanamadi (engellenmis).

### Karar noktasi: entegrasyon mu, ayri sunma mi

Kullanici kritik bir soru sordu: koordinat SADECE Faz 4'e baglamak
icin mi gerekli, yoksa model kombinasyonunun CALISMASI icin mi?
Cevap netlesti: model kombinasyonu (Model 1 + Model 2 + kopru) zaten
calisiyor ve test edildi - koordinat sadece Faz 4 ile birlesim icin
gerekliydi.

Bu netlik, "Yol A" secimine goturdu: iki bileseni (Faz 3 model
kombinasyonu + Faz 4 rota planlama) birbirine baglamadan, AYRI AMA
TAMAMLANMIS iki sistem olarak sunmak. "Yol B" (gercek entegrasyon)
gelecek is olarak birakildi.

### Karar: K-27

Faz 3 ve Faz 4 ayri bilesenler olarak belgelendi. Detaylar K-27'de
(docs/Kararlar.md). Ozet: her iki bilesen bagimsiz olarak calisiyor
ve test edilmis durumda; aralarindaki kopru gercek coğrafi
referansli Turkiye deprem goruntusu bulunana kadar kurulmayacak.

### Acik konular
- ST_Turkey_2023'e erisim tekrar denenebilir (farkli agdan, gdown
  komut satiri araciyla, veya baskasindan link istenerek).
- Faz 3 ve Faz 4'un "ayri iki bilesen" olarak nasil sunulacagi
  (tez formatinda) henuz yazilmadi.

### Karara donusenler
K-27

---

## [Faz 3b/3c — Iki modelli mimari: bina tespiti + hasar siniflandirma] — 2026-09-12

### Mimari degisiklik: tek model yerine iki model

Onceki yaklasimda Siamese CNN, bina konumlarini HAZIR etiketten
(xBD poligonu / EBD_TR maskesi) aliyordu — yani sistem gercek bir
goruntude "bina nerede" sorusunu hic cozmuyordu. Kullanici bunu fark
etti ve iki asamali bir mimari onerdi:

  Asama 1: PRE goruntuden binalari BUL (segmentasyon)
  Asama 2: Bulunan her bina icin PRE/POST karsilastir, hasar sinifla

Iki secenek tartisildi: tek birlesik model (ucta uca) vs iki ayri model.
Iki ayri model secildi — gerekce: mevcut Siamese CNN korunur, hata
ayiklama kolaylasir (hangi asama hatali belli olur), modulerlik.

### Model 1: U-Net bina segmentasyonu (YENI)

segmentation-models-pytorch kutuphanesi kuruldu. U-Net + ResNet18
encoder (ImageNet on-egitimli), sadece EBD_TR verisiyle egitildi.

Veri hazirligi (phase3b_segmentation_data.py): EBD_TR'nin 0-4 degerli
hasar maskesi ikili maskeye (0=arka plan, 1=bina) cevrildi. 944 karo.

Egitim (phase3b_train_segmentation.py): 20 epoch, batch 16.
**En iyi val IoU: 0.821** (epoch 12). IoU>0.7 "iyi" kabul edilir.

Epoch 16'da ani istikrarsizlik gorundu (val IoU 0.393'e dustu), sonraki
epochlarda toparlanamadi — ama en iyi model epoch 12'de kaydedilmisti,
etkilenmedi.

Gorsel dogrulama yapildi: uc ornek karoda model binalari dogru buluyor,
bos/kirsal alanlarda dogru sekilde bos cikti veriyor.

### Format uyumu dogrulandi

Model 1'in ciktisi (olasilik haritasi) -> esikleme -> bagli bilesen
analizi -> her bina icin merkez koordinati (cx, cy). Bu, Model 2'nin
bekledigi girdi formati. Test: karo 000042'de 33 bilesen bulundu,
26'si gecerli (alan>20px), merkez koordinatlari cikarildi.

Bilinen sinirlilik: bitisik binalar bazen tek buyuk bilesen olarak
birlesiyor (18.413 px gibi). Kullanici bunu "onemsiz" olarak
degerlendirdi, simdilik ele alinmadi.

### Kopru scripti (phase3c_kopru.py)

Iki modeli birbirine baglayan script yazildi. Akis: PRE goruntu ->
Model 1 -> bina konumlari -> her konum icin PRE/POST/CVA patch kes ->
Model 2 -> hasar sinifi.

Ilk testte sistem calisti ama sorun ortaya cikti: 26 binanin hicbiri
no-damage cikmadi, guven skorlari %35-55 bandindaydi. K-24'teki sorun
gercek senaryoda tekrar gorundu.

### Model A vs Model B karsilastirmasi (K-25)

Kullanici sordu: EBD_TR tek basina yeterli mi, yoksa xBD gerekli mi?
Tahmin yerine olcum yapildi.

EBD_TR 807 karo, 657 egitim / 150 test olarak ayrildi (seed=42).
Model B egitildi: sadece EBD_TR egitim bolumu (13.499 ornek), 4 sinif,
30 epoch. Model A (xBD+EBD_TR) ile ayni test setinde karsilastirildi.

Not: Model A egitiminde EBD_TR'nin tamamini gormustu, yani test
karolarini da gordu. Bu avantaj bilerek kabul edildi — B yine de
kazanirsa sonuc daha guclu olurdu.

Sonuc:

| Model | no-damage recall | hasar recall |
|---|---:|---:|
| A (xBD + EBD_TR) | 0.155 | 0.664 |
| B (sadece EBD_TR) | 0.000 | 0.597 |

Model B'nin egitimi boyunca recall degerleri kaotik salindi
(destroyed: epoch 1'de 1.00, epoch 2'de 0.00, epoch 7'de 0.92) —
test setinde sadece 47 hasarli bina oldugu icin tek bir binanin
tahmini recall'u %7.7 oynatiyor. Bu gercek ogrenme degil, gurultu.

**Karar: Model A secildi.** EBD_TR'nin katkisi Turkiye'ye ozgu yapi
stokunu tanitmak; temel "hasar neye benzer" ogrenmesi icin xBD'nin
hacmi (159.794 ornek) gerekli.

### Hasar esigi cozumu (K-26)

Kullanici sebepleri ayristirdi: (1) sinif dengesizligi araclarinin
asiri agresifligi, (2) no-damage'in gorsel cesitliligi, (3) modelin
kararsizligi. Sebep 2 zaten Model 1 sayesinde kismen cozulmustu
(siniflandiriciya artik "kesin bina" garantili patch geliyor).

Sebep 3 icin hizli bir mudahale denendi: modeli yeniden egitmeden,
sadece karar mekanizmasini degistirmek. argmax yerine olasilik esigi.

Bulgu carpiciydi — model aslinda ogrenmisti, biz yanlis okuyorduk:

| Esik | no-damage recall | hasar recall | dogruluk |
|---:|---:|---:|---:|
| 0.5 (argmax) | 0.039 | 0.993 | 0.064 |
| 0.6 | 0.287 | 0.917 | 0.303 |
| 0.7 | 0.684 | 0.740 | 0.685 |
| 0.8 | 0.877 | 0.550 | 0.869 |

Esik 0.7 secildi: hasar recall (0.740) hala no-damage recall'undan
(0.684) yuksek — K-16 asimetri ilkesi korunuyor — ama sistem artik
ayrim yapabiliyor.

Uc test karosunda dogrulandi, anlamli dagilim gorundu (000237'de
13 binanin 8'i saglam, 000236'da cogu hasarli). Onceki halinde hicbir
bina saglam cikmiyordu.

### Acik konular
- Guven skorlari hala dusuk (%37-65). Model kesin karar vermiyor.
  Focal Loss alpha yumusatmasi (K-24'te planlanan) denenmedi.
- Model 1'in bitisik binalari birlestirmesi cozulmedi (bilincli erteleme).
- Model henuz Faz 4'e baglanmadi. Sirada: kopru ciktisini K-18 CSV
  formatina cevirip (source=model_v1) rota planlamasina beslemek.

### Karara donusenler
K-25, K-26

---

## [Faz 3 — Siamese CNN egitimi ve gercek Turkiye verisi] — 2026-08-29
### Model mimarisi ve ilk egitim
Siamese CNN + CVA mimarisi kuruldu: pre/post goruntu paylasimli encoder dan
geciyor, CVA (Change Vector Analysis) degisim haritasi ucuncu kanal olarak
ayri bir encoder ile isleniyor. Focal Loss + agirlikli ornekleme, sinif
dengesizligine (yuzde72 no-damage) karsi.
xBD ile 20 epoch egitildi (159.794 ornek). Hasar recall: 0.813
(CVA baseline: 0.72, +13 puan). En iyi model epoch 14 te. Checkpoint sistemi
kuruldu (--resume), bilgisayar kapatilsa bile kaldigi yerden devam edilebiliyor.
### faz3-siamese dali acildi
Kullanicinin karari: model denemeleri Meyusun donmeden, bagimsiz olarak
yapilacak. Riskli/deneysel oldugu icin ayri dala tasindi, main dokunulmadi.
Begenilirse main e merge edilecek, degilse dal silinip bastan baslanacak.
### Maxar/Turkiye veri arayisi, 4 kaynak denendi, 3u elendi
Kullanicinin talebi: modelin Faz 4 e baglanmadan once mumkun oldugunca
Turkiye ye ozgu veriyle gercekten ogrenmis olmasi.
1. Maxar Open Data, tum 76 koleksiyon tarandi (kesisim testi ile),
   deprem bolgesinde sadece 1 pre-post cifti bulundu (889 MB, indirildi).
   En yuksek varyansli alt karolar bile buyuk olcude bulutlu/kirsal cikti,
   etiketlenemez.
2. Planet Labs dogrudan, kurumsal basvuru gerektiriyor, kapali.
3. NASA NIST_Turkiye_Earthquake servisi (Planet 3m), kaldirilmis (404).
4. NASA Map1 servisi (Sentinel-2, 20m), bina bazli hasar icin cok kaba
   cozunurluk (bina 1 pikselden kucuk).
### EARTHQUAKE-TURKEY veri seti bulundu (K-23)
Akademik literatur taramasi ile EBD koleksiyonu (Wang vd. 2025)
bulundu, Maxar Open Data dan toplanmis, xBD-onegitilmis model ile
yari-otomatik etiketlenmis, elle dogrulanmis 12 afetlik bir koleksiyon.
EARTHQUAKE-TURKEY alt kumesi: 944 karo, gercek Kahramanmaras
pre/post cifti, CC BY 4.0 lisansli, figshare den indirildi (889 MB).
Format xBD den farkli, poligon degil piksel maskesi. Yeni bir on isleme
scripti yazildi (phase3_preprocess_ebd_turkey.py): maskeden bagli
bilesen cikarir, merkez bulur, 64x64 patch keser.
Sonuc: 16.351 gercek Kahramanmaras binasi patch e cevrildi
(15.931 no-damage, 420 hasarli: 183 minor, 105 major, 132 destroyed).
### Iki veri kaynagi birlestirildi ve model egitildi

XBDDataset sinifi iki kaynagi da okuyacak sekilde guncellendi:
ornekler artik (uid, sinif, patch_dir) uclusu tutuyor, boylece hem
data/xbd_patches hem data/ebd_turkey_patches ayni egitim dongusunde
kullanilabiliyor. --ek-turkey parametresi eklendi.

Ilk denemede bir kazayla karsilasildi: --disaster mexico-earthquake
--ek-turkey --epochs 1 ile yapilan hizli test kosusu, asil 20 epoch'luk
xBD egitiminin checkpoint dosyasini (checkpoint_son.pth) uzerine yazdi.
Bu yuzden --resume epoch 14'ten degil epoch 1'den basladi. Ders:
test kosulari once checkpoint yedeklenmeden calistirilmamali.

Buna ragmen egitime devam edildi: xBD (159.794) + EARTHQUAKE-TURKEY
(16.351) = 176.145 ornek, toplam 21 epoch. Sonuc: hasar recall 0.804
(onceki sadece-xBD modelinden, 0.813'ten, hafif dusuk).

### Kritik bulgu: model Turkiye'de sagliksiz calisiyor (K-24)

Genel hasar recall'u (0.804) yanlis soruyu cevapliyordu, asil soru
"model Turkiye'de ne kadar iyi" idi. Ayri bir degerlendirme scripti
yazildi (phase3_eval_turkey.py): sadece EARTHQUAKE-TURKEY verisiyle
model test edildi.

Sonuc alarm vericiydi: no-damage recall SADECE 0.012. Karisiklik
matrisinde 15.931 saglam binadan 11.317'si yanlislikla "minor-damage"
sanilmis. Model pratik olarak her yeri hasarli goruyordu.

**Kok neden arastirmasi:** Once "ornek azligi" hipotezi test edildi
ve REDDEDILDI, EARTHQUAKE-TURKEY'de no-damage 15.931 ornekle en
BUYUK sinif (yuzde 97.4), en kucuk degil. Sorun veri azligi degil,
egitim mekanizmasindaydi.

Gercek neden: WeightedRandomSampler'in ham agirligi (1/frekans)
no-damage'i (133.357 ornek, xBD+TR toplam) neredeyse hic secmiyordu.

**1. duzeltme denemesi, agirlik tavani (basarisiz):** Sampler agirligina
maks_oran=10x tavan konuldu. Sonuc: no-damage recall 0.012 -> 0.003,
DAHA DA KOTULESTI. Sebep: no-damage/hasarli-siniflar orani zaten ~10x
civarindaydi, tavan pratikte hicbir seyi sinirlamadi.

**2. duzeltme denemesi, sampler tamamen kaldirildi (kismen basarili):**
WeightedRandomSampler tamamen kaldirildi, DataLoader'a shuffle=True
verildi, sadece Focal Loss sinif dengesizligiyle basa cikmak icin
birakildi. Sifirdan 20 epoch yeniden egitildi.

Sonuc: no-damage recall 0.155'e cikti (52 kat iyilesme), ama hasar
recall Turkiye'de 0.664'e dustu (major-damage ozellikle zayif: 0.362,
cogu destroyed ile karistiriliyor).

**Degerlendirme:** Sorun kismen cozuldu ama tam degil. Model artik
tamamen kor degil ama no-damage'in hala yuzde85'i yanlis siniflandiriliyor.
Kullanicinin sordugu "belki gercekten no-damage ornegi azdir" sorusu
test edildi ve YANLIS cikti; asil sorun Focal Loss'un alpha
agirliginin da sampler gibi asiri agresif olmasi olabilir (henuz
duzeltilmedi).

**Uc model versiyonu diskte yedeklendi (models/ klasorunde,
gitignore'da, repoya girmiyor):**
- v1_bozuk_no_damage: agresif sampler, no-damage recall 0.003-0.012
- v2_sampler_denendi: sampler kaldirildi, no-damage recall 0.155,
  hasar recall (Turkiye) 0.664, SU ANKI AKTIF MODEL
- (planlanan v3: Focal Loss alpha'sinin da yumusatilmasi)

### Acik, bu oturumda BITMEDI, devam edecek
- Focal Loss alpha agirligi sampler ile ayni mantikla (1/frekans)
  hesaplaniyor, henuz yumusatilmadi. Bir sonraki adim bu.
- no-damage/hasar recall dengesi icin kabul edilebilir esik henuz
  netlesmedi, K-16'nin ihtiyatli olmak guvenlidir ilkesiyle ne
  kadar aski birakilabilecegi kullanici ile netlestirilecek.
- Model henuz Faz 4'e baglanmadi (xbd_gt vs model_v1 karsilastirmasi
  hala yapilmadi), once model kalitesi kabul edilebilir seviyeye
  gelmeli.
- phase3_siamese_cnn.py, phase3_eval_turkey.py degisiklikleri henuz
  commit edilmedi (bu girdiyle birlikte commitlenecek).

### Karara donusenler
K-23, K-24

---

---

## [Faz 4 — çok bölge desteği, Faz 1 eşik revizyonu, birleşik koşu] — 2026-08-20

### 4 — GPU teyidi

**Amaç:** Siamese CNN eğitimi için GPU gerekli. Meyusun'un makinesi bilinmiyor ama
Kuzey'in makinesi teyit edildi.

**Sonuç:** NVIDIA RTX 5000 Ada Generation, 16 GB VRAM, CUDA 13.0. Siamese CNN
eğitimi için yeterli — kappa turu bitince model eğitimi Meyusun'u beklemeye gerek
kalmadan Kuzey'in makinesinde de başlatılabilir.

`Kararlar.md` açık konular bölümüne not düşüldü.

---

### 5 — `phase4_visualize.py` çok bölge desteği

**Neden:** `phase4_visualize.py` Mexico City senaryolarına sabit bağlıydı. Kahramanmaraş
rota karşılaştırması önceki oturumda tek seferlik bir komutla üretilmişti — tekrarlanabilir
değildi. Danışman "Kahramanmaraş görselini yeniden üret" dediğinde tek komutla
yapılabilmeli.

**Ne yapıldı:** Script `phase4_route_compare.py`'deki `BOLGE_TANIM` sözlüğünü
kullanacak şekilde yeniden yapılandırıldı. `--bolge` parametresiyle iki bölge arasında
geçiş yapılıyor. Mexico City için EPSG:32614 (UTM 14N), Kahramanmaraş için EPSG:32637
(UTM 37N) otomatik seçiliyor — yanlış CRS mesafeleri bozardı.

**Geriye dönük uyumluluk:** Parametresiz çalıştırınca Mexico City varsayılan, eski
davranış korundu.

**Çalıştırma:**
```
LC_ALL=C python scripts/phase4_visualize.py                    # Mexico City
LC_ALL=C python scripts/phase4_visualize.py --bolge kahramanmaras
```

**Üretilen görsel:** `outputs/phase4_sapma_km.png` — sol: 1593 m temiz rota,
sağ: 2068 m hasarlı rota (+475 m), kırmızı kenarlar şehir merkezinde yoğun.

---

### K-22 — Likefaksiyon eşiği 0.05'ten 0.10'a revize edildi

**Neden değiştirildi:**
Zhu 2017 modelinin bu bölgedeki veri aralığı 0–0.394. 0.05 eşiğinde grafın %34.9'u
(1292/3700 kenar) `difficult` oluyordu — Türkoğlu'nun üçte biri likefaksiyon riski
altında görünüyordu.

Bu fiziksel olarak savunulamazdı. Likefaksiyon için üç koşul aynı anda gerekli:
gevşek ve suya doygun zemin (jeoloji), yeterince yüksek sarsıntı (faya yakınlık).
Düşük olasılıklı hücreler bu koşulun tam sağlanmadığı alanları temsil eder — bu
alanları `difficult` saymak sistemi gereğinden karamsar yapar.

**Ayrıca:** Likefaksiyon fay hattıyla doğrudan örtüşmez. Fay yakınlığı sarsıntıyı
artırır (riski artırır) ama jeoloji uygun değilse sarsıntı ne kadar güçlü olursa
olsun likefaksiyon gerçekleşmez. Bu yüzden rüptür katmanı (geometrik, `closed`) ve
likefaksiyon katmanı (jeoteknik model, `difficult`) ayrı tutulur.

**Duyarlılık tablosu:**

| Eşik | Riskli hücre | Difficult kenar | Oran |
|---:|---:|---:|---:|
| 0.05 | 305 | 1292 | %34.9 |
| 0.08 | 287 | 1123 | %30.4 |
| **0.10** | **273** | **929** | **%25.1** |
| 0.12 | 258 | 862 | %23.3 |
| 0.15 | 239 | 757 | %20.5 |
| 0.20 | 197 | 515 | %13.9 |

**Neden 0.10:** Deprem mühendisliğinde likefaksiyon riski tipik olarak %10-20 olasılık
üzerinde "anlamlı" sayılır. 0.10, bu setteki orta-yüksek riski yakalayan en düşük
savunulabilir eşiktir. K-16'nın konservatif ilkesiyle uyumlu.

**Doğrulama:** `verify_phase1.py` — 12/12 test geçti. Değişiklik hiçbir Faz 1
sözleşmesini bozmadı.

**Etkilenen dosyalar:** `scripts/phase1_liquefaction1.py`, `scripts/turkoglu_four_layers.py`

---

### 6 — Faz 1 + Faz 4 birleşik koşu (`phase4_integrated_run.py`)

**Neden var:**
Proje üç bağımsız hazard kaynağını birleştiriyor:
- **Faz 1a:** Jeofizik — USGS fay rüptürü vektörü → `closed`
- **Faz 1b:** Jeoteknik — Zhu 2017 likefaksiyon olasılık rasteri → `difficult`
- **Faz 4:** Uzaktan algılama — uydu görüntüsünden bina hasarı → `damage_pressure`

K-16 kararı "en kısıtlayıcı etiket kazanır" diyordu: Faz 4, Faz 1'in yazdığı
etiketi ezememeli. Ama bu hiç gerçek veriyle test edilmemişti.

**Teknik sorun:** `graph_turkoglu.graphml` ham OSM grafı — `traversability` özniteliği
içermiyor. Faz 1 her çalıştırmada sıfırdan hesaplanıp A*'a geçiriliyor, kalıcı
olarak yazılmıyor. Bu yüzden birleşik testi kurmak için Faz 1'i önce çalıştırıp
etiketleri uygulamak, sonra Faz 4'ü üstüne bindirmek gerekti.

**Sonuç:**

| Katman | Closed | Difficult |
|---|---:|---:|
| Faz 1a (ruptur) | 28 | 0 |
| Faz 1b (likefaksiyon, eşik=0.10) | 28 | 923 |
| **Faz 4 ekledi** | **+28** | **+129** |
| **Birleşik toplam** | **56** | **1052** |

**K-16 GEÇTI:** Faz 1'in 28 `closed` kenarının hiçbiri Faz 4 tarafından
gevşetilmedi.

**Rota karşılaştırması (A=2388129147, B=10617812226):**
- Faz 1 tek başına: **1593 m**
- Faz 1 + Faz 4 birlikte: **2068 m**
- Faz 4'ün ek katkısı: **+475 m**

Bu tezin en güçlü teknik kanıtı: üç bağımsız hazard kaynağı tek bir tutarlı rota
planına dönüşüyor ve hiçbiri diğerini ezip daha az kısıtlayıcı hale getiremiyor.

**Çalıştırma:**
```
LC_ALL=C python scripts/phase4_integrated_run.py
```

---

### Bugün kapanan açık konular
- GPU durumu teyit edildi
- Likefaksiyon eşiği 0.05 → 0.10 (K-22)
- `phase4_visualize.py` çok bölge desteği
- Faz 1 + Faz 4 birleşik koşu doğrulandı

### Hâlâ açık
- Meyusun'un kappa turu (Faz 2c kapısı, κ ≥ 0.60)
- Faz 3 (Siamese CNN) — kappa sonrası
- Spatial CV fold dengesizliği — model tarafı
- Nokta/blok granülerlik farkı (model bina bazında, EMSR648 blok bazında)

---

## [Faz 4 — duyarlılık analizi ve çok bölge desteği] — 2026-08-19

### A — Kahramanmaraş R duyarlılık analizi

**Amaç:** R parametresi (moloz yayılma mesafesi, 25 m olarak seçilmişti) sonucu ne
kadar etkiliyor? Jüri "neden 25 m, neden 30 değil?" diye sorduğunda sayısal cevap
verebilmek için.

**Nasıl:** `phase4_damage_pressure.py`'ye `--bolge` parametresi eklendi. Bu aynı
zamanda scripti Mexico City'ye sabit bağlılıktan kurtardı — artık iki bölge
arasında geçiş yapılabiliyor. Kahramanmaraş için UTM 37N (EPSG:32637), Mexico City
için UTM 14N (EPSG:32614) otomatik seçiliyor; yanlış CRS mesafeleri bozardı.

**Geriye dönük uyumluluk:** Diğer scriptler (`phase4_apply_to_graph`,
`phase4_route_compare`, `phase4_verify_buildings`) modül seviyesindeki `GRAPH`,
`DAMAGE_CSV`, `METRIC_CRS` değişkenlerini import ediyordu. Bunlar silinmedi —
varsayılan bölgenin (mexico) değerleri aynı adlara atandı, hiçbir script kırılmadı.

**Sonuç — Kahramanmaraş (T_CLOSED=0.50, T_DIFF=0.20):**

| R | Etkilenen kenar | Closed | Difficult |
|---:|---:|---:|---:|
| 15 m | 242 (%6.5) | 18 | 49 |
| **25 m** | **314 (%8.5)** | **28** | **136** |
| 40 m | 375 (%10.1) | 51 | 155 |

R=25 seçiminin gerekçesi: 15 m'de `destroyed` binalar yeterli baskı üretemiyor,
40 m fiziksel olarak ancak 12+ katlı binalar için savunulabilir (bu setteki medyan
taban alanı küçük). 25 m, tipik 3-6 katlı yapı stoku için devrilen duvar
yayılma mesafesiyle uyumlu.

**Mexico City ile karşılaştırma:**

| R | MX closed | KM closed | Oran |
|---:|---:|---:|---:|
| 15 m | 0 | 18 | — |
| 25 m | 2 | 28 | 14× |
| 40 m | 8 | 51 | 6× |

Rapor: `reports/phase4_kahramanmaras_duyarlilik.txt`

---

### B — `phase4_route_compare.py` çok bölge desteği

**Amaç:** Kahramanmaraş rota karşılaştırması önceki oturumda tek seferlik bir Python
komutuyla üretilmişti — tekrarlanabilir değildi. Danışman "Kahramanmaraş sonucunu
yeniden üret" dediğinde tek komutla yapılabilmeli.

**Nasıl:** Script yeniden yapılandırıldı. `BOLGE_TANIM` sözlüğü hem Mexico City hem
Kahramanmaraş tanımlarını içeriyor; `--bolge` parametresiyle seçiliyor. Kahramanmaraş
senaryosu: `2388129147 → 10617812226` (referans 1593 m, hasarlı 2068 m, +475 m).

**Önemli bulgu — Mexico City ile yapısal fark:**

Mexico City'de max `damage_pressure` skoru **0.759**'du. 0.80 eşiğinde hiçbir kenar
kapalı kalmıyordu — kontrol satırı referansa dönüyordu. Kahramanmaraş'ta max skor
**1.000**; 0.80 eşiğinde bile 6 kenar kapalı kalıyor.

Bu, transfer varsayımının (K-17) önemini somutlaştırıyor: Mexico City geliştirme
zemini olarak kullanıldı çünkü deprem davranışı benzer, ama hasar yoğunluğu çok
farklı. Eşiklerin Kahramanmaraş'a özgü kalibrasyonu bu yüzden açık iş olarak
kaydedildi (K-19).

**Duyarlılık tablosu — Kahramanmaraş:**

| T_DIFF / T_CLOSED | Closed | Difficult | Sonuç |
|---|---:|---:|---|
| 0.05 / 0.30 | 102 | 178 | +475 m SAPTI |
| 0.20 / 0.50 | 28 | 138 | +475 m SAPTI |
| 0.30 / 0.70 | 16 | 86 | +475 m SAPTI |
| 0.80 / 0.95 | 6 | 2 | +238 m SAPTI |

Tüm eşiklerde sapma var — Mexico City SAPMA senaryosundan farklı olarak hiçbir
ayarda "değişmedi" çıkmıyor. Bunun sebebi: Kahramanmaraş'ta hasar yoğun ve geniş
alana yayılmış, A\*'ın alternatif bulması Mexico City'den çok daha zor.

**Çalıştırma:**
```
LC_ALL=C python scripts/phase4_route_compare.py --bolge kahramanmaras --tara
LC_ALL=C python scripts/phase4_route_compare.py --bolge mexico --tara
LC_ALL=C python scripts/phase4_route_compare.py  # varsayilan: mexico
```

Rapor: `reports/phase4_kahramanmaras_rota_duyarlilik.txt`

---

## [Faz 4 — doğrulama, kararlar, Kahramanmaraş transferi] — 2026-08-17

### Artçı sarsıntı riski — K-20 (karar bağlandı)

20 bina görsel doğrulamasında (vaka 13, `4db97035`, 1499 m²) ortaya çıkan soru:
yol yüzeyi temiz ama bina ağır hasarlı — artçı sarsıntıda çökerse araç tehlikede mi?

Üç seçenek değerlendirildi:
- **Tam risk modeli:** çökme olasılığı hesaplanıp rota maliyetine katılsın
- **Kapsam dışı:** sistem sadece anlık fiziksel geçilebilirliği modeller
- **Uyarı etiketi:** rota maliyetine dokunmadan "dikkat" etiketi eklensin

**Karar: kapsam dışı (K-20).** Riski modelleyecek veri yok. Çökme olasılığı yapının
taşıyıcı sistemine, hasarın gerçek yapısal karşılığına ve artçı büyüklüğüne bağlı —
üçü de uydu görüntüsünden okunamıyor. Gerekçesiz bir eşik eklemek K-19'un "her
parametrenin fiziksel dayanağı var" ilkesini çiğnerdi. Uyarı etiketi de elendi:
sistemin çıktısını değiştirmediği için sınanamaz.

Doğrulama sırasında netleşen temel kural: **karar bina hasarına değil, yol yüzeyinde
görünür fiziksel engele dayanır.** Bu kural ilk 8 vakada netleşmemişti; kural
sabitlendikten sonra 5 vaka yeniden değerlendirildi.

---

### ProjeContext.md güncellendi

Belgede üç bölüm gerçeği yansıtmıyordu:

**Mimari bölümü:** Köprü katmanı "kamyon genişliği (~3.5 m) eşiği", "darboğaz kuralı",
"taraf-içi max toplama" ile tarif ediliyordu — bunların hiçbiri uygulanmadı. Erken plan
metniydi. Yerine K-19'un gerçek formülü yazıldı ve eski planın neden uygulanmadığı not
düşüldü. Bu kritik bir hataydı: Meyusun dosyayı Claude Project'ine yüklüyordu ve
yapay zekası köprü katmanının var olmayan bir mekanizmayla çalıştığını sanıyordu.

**Repo bölümü:** Sadece Meyusun'un reposu yazılıydı. Kuzey'in fork'u
(`github.com/KKirca/disaster-routing`) ve `docs/`, `reports/` klasörleri eklendi.

**Demo bölgesi:** Sadece Türkoğlu vardı. Faz 4'ün Mexico City'de geliştirildiği ve
neden deprem verisi seçildiği eklendi (K-17 gerekçesi).

---

### Kahramanmaraş transferi

**Maxar görüntüsü indirmeden yapıldı.** `data/emsr648/` klasöründe Copernicus EMSR648
Kahramanmaraş hasar değerlendirmesi zaten mevcuttu. Üç AOI incelendi:

| AOI | Bina | Ağır hasarlı | Oran | Seçim |
|---|---:|---:|---:|---|
| AOI04 | 7182 | 28 | %0.4 | elendi — neredeyse hasarsız |
| AOI16 | 321 | 30 | %9.3 | elendi |
| **AOI17** | **288** | **34** | **%11.8** | **seçildi** |

AOI17 seçildi: en yüksek hasar oranı, Türkoğlu ile örtüşüyor, ve
`graph_turkoglu.graphml` AOI17'yi tamamen kapsıyor — yeni graf indirmeye gerek kalmadı.
Faz 1'in hazard katmanları (fay rüptürü, likefaksiyon) zaten o grafta mevcut: Faz 1
ve Faz 4 aynı grafta birleşti.

**K-21: `Possibly damaged` ihtiyat ağırlığı (0.20)**

EMSR648'de `Possibly damaged` kategorisi xBD şemasında karşılıksız — bir **hasar
derecesi değil, belirsizlik ifadesidir** (Copernicus analisti "bir şey var ama emin
değilim" demektedir). AOI17'de 18 bina bu kategoridedir.

İki uç seçenek ikisi de yanlış:
- `no-damage` say → iyimser hata, K-16'ya ters
- `major-damage` say → uydurma veri, K-19'un gerekçe ilkesini çiğner
- Dışarıda bırak → araç belirsiz riskten habersiz geçer

Beklenti değeri (0 + 0.60) / 2 = 0.30. Copernicus metodolojisi hafif hasar yönüne
yatkın olduğu için **0.20'ye kalibre edildi.** Tek başına `T_CLOSED = 0.50`'yi hiçbir
zaman geçemez; birkaç belirsiz bina kümeleşirse `difficult` üretebilir.

`minor-damage` sınıfı EMSR648'de karşılıksız kaldı; K-19'daki 0.15 ağırlığı
Kahramanmaraş koşusunda devreye girmez — tezde sınırlılık olarak belirtilecek.

**Sonuçlar (Türkoğlu grafı, R=25 m, T_CLOSED=0.50, T_DIFF=0.20):**

| | Mexico City | Kahramanmaraş |
|---|---:|---:|
| Etkili bina | 20 | 52 |
| Etkilenen kenar | 234 | 314 |
| Closed (≥0.50) | 2 | **28** |
| Difficult (≥0.20) | 11 | **164** |
| Rota sapması | +44 m | **+475 m** |

Kahramanmaraş etkisi Mexico City'nin ~10 katı — beklenen, gerçek deprem bölgesi.

**Üretilen görseller:**
- `outputs/phase4_kahramanmaras_hasar.png` — hasar haritası, şehir merkezinde
  kırmızı yoğunlaşma
- `outputs/phase4_kahramanmaras_rota.png` — rota karşılaştırması, +475 m sapma

**Scriptler:**
- `scripts/phase4_build_emsr_csv.py` — EMSR648 → K-18 CSV dönüşümü
- `scripts/phase4_damage_pressure.py` — K-21 ağırlığı eklendi

### Açık
- Meyusun'un kappa turu bekleniyor (Faz 2c kapısı)
- Kappa ≥ 0.60 sonrası: Siamese CNN (Faz 3), gerçek Kahramanmaraş etiketlemesi
- Eşik (T_CLOSED, T_DIFF) ve R'nin Kahramanmaraş'a özgü kalibrasyonu — K-17/K-19'da
  transfer varsayımı olarak işaretlendi; saha verisi gelirse düzeltilebilir

### Karara dönüşenler
K-20, K-21

---


K-19'da söz verilen "uzman muhakemesi referansı" yapıldı: `scripts/phase4_verify_buildings.py`
ile üretilen 40 görsel (`outputs/faz4_dogrulama/`) tek tek incelendi, her bina için
bağımsız closed/difficult/passable kararı verildi, kuralın çıktısıyla karşılaştırıldı.
Sonuç: `reports/phase4_bina_dogrulama.csv`.

### Yöntem netleştirmesi (vaka 4'te ortaya çıktı)

İlk 8 kararda tutarsızlık görüldü: aynı gözlem ("çatı örüntüsü korunmuş, yıkım izi yok")
bazı vakalarda `difficult`, bazılarında `passable` sonucu üretti. Kriter netleştirildi:
**karar bina hasarına değil, yol yüzeyinde görünür fiziksel engele dayanır.**
`traversability` sözleşmesi zaten fiziksel geçilebilirliği tanımlıyordu (K-02), gelecek
riskini değil — "hasarlı bina yakında, içim rahat etmedi" gerekçesi `difficult` için
yeterli değil. Bu netleştirmeden sonra 5 vaka (2, 3, 6, 15, 18) yeniden değerlendirildi;
ikisi (2, 18) karar değiştirdi, üçü (3, 6, 15) aynı kaldı ama gerekçesi "moloz" değil
"görüntü bulanıklığı/ağaç örtüsü nedeniyle yol net okunamıyor" oldu (ihtiyati karar).

### Sonuç

**12/19 uyumlu (%63.2)**, 7 ayrışma, 1 karşılaştırma dışı (bkz. aşağı). Ayrışma iki
kümede toplanıyor — rastgele gürültü değil, sistematik:

**Küme A — kural `passable`, uzman `difficult` (5 vaka: 1, 3, 6, 7, 15).**
Bina katkısı `T_DIFF = 0.20` eşiğinin altında (0.052–0.175 arası) ama uzman yine de
`difficult` dedi. Dördünde gerekçe görüntü kalitesi (bulanıklık, ağaç örtüsü — yol
yüzeyi net okunamıyor, ihtiyati karar). Vaka 7 farklı: küçük taban alanı (51 m²) ve
mesafe (8.1 m) `katki`yi 0.052'ye düşürüyor ama görsel olarak ciddi enkaz var — K-19'un
alan/mesafe ağırlıklandırmasının küçük ama yol kenarındaki yıkımları hafife
alabileceğine dair somut bir örnek.

**Küme B — kural `closed`, uzman `difficult` (2 vaka: 13, 20).** Bina katkısı
`T_CLOSED = 0.50` eşiğinin üzerinde (0.525, 0.600) ama her ikisinde de çatı örüntüsü
büyük ölçüde korunmuş, yakın kırpmada tam yıkım seçilmiyor. `T_CLOSED = 0.50`'nin,
yapı bütünlüğünü büyük ölçüde koruyan ama yüksek katkı üreten (büyük alan + yola çok
yakın) vakalarda fazla agresif olabileceğine işaret ediyor.

**Karşılaştırma dışı — sıfır katkılı 3 vaka (9, 12, 19).** Kural bu binalara hiçbir
kenar atamıyor (25 m içinde yol yok). İkisi (9, 19) görsel olarak doğrulandı: yoğun
sanayi/pazar dokusu içinde, gerçekten izole — OSM eksikliği değil. Vaka 12 (`081e6c40`,
280 m mesafeli aykırı vaka) bir **lunapark** içinde çıktı — izolasyon mantıklı, ama
ağaç örtüsü + bulanıklık nedeniyle hasar durumu görsel olarak belirlenemedi.

### Açık — taşındı

`Kararlar.md` → K-19 altına eklendi: eşik agresifliği bulgusu, alan/mesafe
ağırlıklandırma sınırı, artçı sarsıntı riski kapsam tartışması (henüz karara
bağlanmadı, kullanıcı 20 vaka bitince ayrıca ele alınmasını istedi).

---

## [Faz 4 — köprü katmanı tamamlandı] — 2026-08-16

Bina hasarını yol geçilebilirliğine çeviren katman. Projenin **özgün katkısı** budur:
A\* ders kitabı algoritması, Siamese CNN literatürde mevcut yöntem, OSMnx ve xBD hazır
araç. Yeni olan tek şey, hasar bilgisini rota maliyetine dönüştüren bu ara katmandır.

### Yapılanlar

- `scripts/phase4_build_damage_csv.py` — xBD etiketlerinden girdi tablosu
- `scripts/phase4_match_buildings.py` — bina–yol mekânsal eşleştirme
- `scripts/phase4_damage_pressure.py` — K-19 skor formülü
- `scripts/phase4_apply_to_graph.py` — skoru graf kenar özniteliğine yazma
- `scripts/phase4_route_compare.py` — traversability üretimi + eşik duyarlılık analizi
- `scripts/phase4_visualize.py` — iki panelli rota karşılaştırma haritası
- `data/damage/mexico-earthquake_xbd_gt.csv` — 32.196 bina
- `reports/phase4_esik_duyarlilik.txt`, `outputs/phase4_{izolasyon,sapma}.png`

Kararlar: **K-15** (sürekli skor + eşik), **K-16** (konservatif birleştirme),
**K-17** (mexico-earthquake zemini), **K-18** (ara CSV girdisi), **K-19** (skor formülü).

### Boru hattı

    xBD etiketi → CSV → mekânsal eşleştirme → damage_pressure → traversability → A* → rota

### Yöntem sırası ve gerekçesi

Kod yazmadan önce **sözleşme** sabitlendi (girdi/çıktı tanımı), sonra zemin seçildi,
sonra geometri kuruldu, en son karar kuralı yazıldı. Faz 1'de `traversability`
sözleşmesinin baştan sabitlenmesi o fazı kurtarmıştı; aynı yaklaşım uygulandı.

### Neden mexico-earthquake (K-17)

Enkazın yolu tıkama davranışı afet tipine göre kökten değişir:

| Afet | Karo | Enkaz davranışı |
|---|---:|---|
| socal-fire | 823 | Bina yanar/çöker ama **yola moloz saçmaz** |
| hurricane-* | 900+ | Yol **suyla** kapanır, enkazla değil; su çekilince açılır |
| palu-tsunami | 113 | Moloz akıntıyla kaynak binadan uzağa taşınır |
| **mexico-earthquake** | **121** | **Bina kendi üzerine/yana çöker, moloz komşu sokağa dökülür** |

**En büyük veri seti burada yanlış veri setidir.** `socal-fire` ile kalibre edilseydi
sistem "hasarlı bina → yol kapanmaz" öğrenir ve Kahramanmaraş'ta yanlış çalışırdı.

Ayrıca Mexico City yoğun kentsel dokuya sahiptir (dar sokak, bitişik nizam), Antakya'ya
morfolojik olarak yakındır. Kırsal setlerde (`guatemala-volcano`, 18 karo) bina–yol
ilişkisi kurulamaz.

### 20 bina neden yeterli

`major-damage` 18 + `destroyed` 2 = **20 ağır hasarlı bina** (32.271 binanın %0.06'sı).
Beş mekânsal kümede toplanmışlar (3+3+2+3+5), en sıkısı ~10 m yayılımlı bitişik nizam;
4'ü yalıtık. Çoğu −99.14…−99.15 boylam şeridinde — 2017 Puebla depreminin bilinen
çökme koridoru (Roma/Condesa/Del Valle).

Faz 4 **öğrenen bir model değil, deterministik geometrik kuraldır.** Parametreleri
veriden öğrenilmez; fiziksel akıldan gelir. Zaten öğrenilemez de: "hangi yol gerçekten
kapandı" diye bir ground truth yoktur, yani optimize edilecek hedef değişken mevcut
değildir. Veriye ihtiyaç parametre uydurmak için değil, **kuralın makul davrandığını
gözlemek** içindir. Bunun için 20 bina yeterlidir; 20.000 bina aynı kontrolü
tekrarlardı.

### Bulunan hatalar

**1. Centroid ile mesafe ölçümü — sistematik hata (düzeltildi)**

İlk sürümde bina bir **nokta** (centroid) olarak ele alınıyordu. Ama enkaz binanın
merkezinden değil **cephesinden** dökülür. Poligona geçince:

| bina | alan | centroid | poligon | fark |
|---|---:|---:|---:|---:|
| f3865521 | 858 m² | 26.4 m | **0.0 m** | 26 m |
| 4db97035 | 1499 m² | 21.0 m | 3.1 m | 18 m |
| 229ba083 (destroyed) | 804 m² | 33.4 m → **dışarıda** | 15.1 m → içeride | 18 m |

Eşleşme **15/20 → 18/20** yükseldi. Centroid'de kalınsaydı iki `destroyed` binadan
biri tamamen kaçırılacaktı. K-18 şemasına `footprint_wkt` ve `area_m2` eklendi.

**2. Türkçe locale — GraphML bozulması**

`LANG=tr_TR.UTF-8` altında OSMnx GraphML yazarken `LINESTRING` → `LiNESTRiNG` oluyor
ve dosya geri okunamıyor (`GEOSException: Unknown type`). Sebep: Türkçede `i` harfinin
büyüğü `İ`'dir; yerel ayara duyarlı büyük harf dönüşümü ASCII'ye düşerken noktaları
kaybediyor. **Klasik "Türkçe i problemi".**

Çözüm: OSMnx/GraphML işleyen tüm scriptler `LC_ALL=C` ile çalıştırılır. Faz 0/1
cache'leri (`graph.graphml`, `graph_turkoglu.graphml`) tarandı — temiz. Ama aynı komut
bugün Türkçe locale'de çalıştırılsa bozuk dosya üretirdi; bu bir zaman bombasıdır.

**3. Skor kırpması — formül yapısal olarak hatalıydı (düzeltildi)**

İlk formülde `alan` (≤3.0) ve `genislik` (≤1.3) çarpanları 1'i aşabiliyordu:
`1.0 × 1.0 × 3.0 × 1.3 = 3.9` → `min(x, 1.0)` ile kırpılıyordu.

İki sonucu vardı: (a) 10 kenar tam `1.000`'de yığılıyordu — o skorlar "kesin kapalı"
değil "hesap taştı" demekti; (b) `R` ne olursa olsun `closed` sayısı 11'de sabit
kalıyordu, yani **duyarlılık analizi imkânsızdı.**

Kök neden kırpma değil, formülün yapısıydı. `katki` K-19'da bir **olasılık** olarak
tanımlanmıştı ("bu bina bu yolu tıkar mı?"); olasılık 1'i aşamaz. Her faktör 0–1
aralığında yeniden tanımlandı: `alan = min(alan_m2/400, 1.0)`,
`darlik = min(7.0/W, 1.0)`. Kırpma gereksizleşti, `R` duyarlılığı geri geldi:

| R | max skor | closed | difficult |
|---:|---:|---:|---:|
| 15 m | 0.600 | 0 | 11 |
| 25 m | 0.759 | 2 | 11 |
| 40 m | 0.849 | 8 | 8 |

### R = 25 m gerekçesi

Devrilen duvar kabaca kendi yüksekliği kadar mesafeye düşer. Bu bölgede tipik yapı
stoku 3–6 kat = 10–20 m; moloz saçılmasıyla etkili mesafe 20–30 m aralığına oturur.
25 m bu aralığın ortasıdır. 40 m ancak 12+ katlı bloklar için savunulabilir (medyan
taban alanı 199 m², böyle bir doku yok). 15 m'de hiçbir kenar 0.70'i aşmıyor — iki
`destroyed` bina bile yol kapatamıyor.

### Eşik neden sabitlenmedi

Hangi eşiğin doğru olduğunu gösterecek ground truth yoktur. Eşiği seçip sonucuna bakmak
**döngüsel gerekçelendirme** olurdu ("hedefe ulaşabildiğim en yüksek eşiği seçeyim" =
sistemin uyarı vermesini engellemek için eşik ayarlamak).

Bunun yerine: varsayılan `0.50 / 0.20`, sonuçlar birden fazla eşikle raporlanır.
Tezde "eşiği 0.5 seçtik" yerine "eşik 0.3'te 13 yol, 0.7'de 2 yol kapanıyor" denir.
Jüri "neden bu sayı?" sorusunu soramaz — bir sayı seçilmedi, etkisi ölçüldü.

Eşiğin **ne zaman değiştirilmesi gerektiği** `phase4_route_compare.py` başlığında
belgelendi: (1) Kahramanmaraş'a geçerken, (2) model çıktısı kullanılırken —
Faz 2c'de ölçülen sistematik iyimserlik yanlılığı skorları düşürebilir, (3) `R`
değiştiğinde, (4) saha verisi gelirse (o zaman eşik tahmin değil **ölçüm** olur).

### Doğrulama — iki senaryo

Test noktaları hasar kümesinden geçecek şekilde seçildi. Bu hile değil: acil durum
aracı zaten hasarlı bölgeye gidiyor. Rastgele nokta seçmek, sistemin işe yaradığı
durumu test etmemek olurdu (234 etkilenen kenar, ağın %0.175'i).

**IZOLASYON** (`6184109963 → 1860819095`) — `closed` mekanizmasını sınar.
Hedef kavşağın **üç kolu da** hasarlı (0.638 / 0.697 / 0.677) ve bölge bir **çıkmaz
sokak adası** (400 m içinde yalnızca 27 düğüm; ızgara planda 100+ beklenir). Eşik
0.638'in altına inince ada tamamen izole oluyor → `NetworkXNoPath`.

Bu bir hata değil, **doğru cevaptır**. Izgara planda bir sokak kapanırsa araç bir blok
dolanır; çıkmaz sokak adasında tek bağlantı kapanırsa içerideki herkes erişilemez hale
gelir. Antakya'da benzer topolojiler vardır.

**Faz 1'deki `edge_cost` düzeltmesi olmasaydı bu senaryo sessizce yanlış cevap
verirdi:** `math.inf` ile A\* kapalı sokaktan geçen bir rota üretir ve "işte yolun"
derdi. Trafo kamyonu enkaza giderdi.

**SAPMA** (`8339935731 → 292423735`) — `difficult` mekanizmasını sınar.
`Calle Los Mendoza` (0.759) üzerinden geçen rota, ancak bölge bağlantılı (1500 m içinde
239 düğüm). Sonuç: **1269 m → 1313 m (+44 m sapma).**

`t_closed = 0.95` satırında da sapma var — o eşikte hiçbir kenar `closed` olamaz
(max skor 0.759). Yani sapmayı üreten **`difficult` etiketidir**: kenar açık ama
`DIFFICULT_PENALTY = 5.0` ile pahalı, A\* hesap yapıp alternatifi tercih ediyor.

**Kontrol satırı** (`t_diff = 0.80`, `t_closed = 0.95`): hiçbir kenar etiketlenmiyor,
rota referansa **birebir** dönüyor (12 düğüm, 1269 m). Bu, gözlenen tüm sapmaların
gerçekten hasar etiketlerinden kaynaklandığını kanıtlar — kodun başka yerindeki bir
yan etkiden değil.

### Sonuç — topolojiye duyarlı davranış

Aynı eşik ayarı iki senaryoda farklı sonuç veriyor:

| Durum | Sonuç | Mekanizma |
|---|---|---|
| `t_diff` > max skor | rota değişmez | kontrol |
| `difficult`, alternatif var | +44 m sapma | ceza çarpanı |
| `difficult`, alternatif yok | rota değişmez | mecburiyet |
| `closed`, tüm kollar kapalı | `NetworkXNoPath` | izolasyon |

### Açık

- **`ProjeContext.md` güncellenmedi** — Faz 4 mimarisi oraya taşınacak.
- ~~20 binanın görsel doğrulaması yapılmadı.~~ **Tamamlandı — 2026-08-17, yukarı bakınız.**
- **İki bina hiçbir kenarla eşleşmedi:** `adbab63d` (588 m², 51.6 m) ve `081e6c40`
  (91 m², **280 m**). **Görsel doğrulamayla açıklığa kavuştu (2026-08-17):**
  `adbab63d` bir sanayi/depo kompleksi içinde, `081e6c40` bir lunapark içinde —
  ikisi de gerçekten izole, OSM eksikliği değil.
- **Sıfır mesafeli kenarlar:** `f3865521` ve `66ab3129` poligonları yol çizgisiyle
  kesişiyor (0.0 m). Ya OSM ekseni bina üzerinden geçiyor ya bina sıfır cepheli
  (Mexico City'de bitişik nizam yaygın). Mesafeyi ters orantıyla kullanan bir
  formüle geçilirse sıfıra bölme riski.
- **Kahramanmaraş'a transfer** — K-17'deki transfer varsayımı: Mexico City yapı stoku
  Antakya'dan farklı (yönetmelik, kat dağılımı) ve 2017 Puebla'da yıkım **noktasaldı**,
  mahalleler düzleşmedi. Kahramanmaraş'ta yıkım çok daha yaygın; eşikler ve `R`
  yeniden bakılmalı.

### Kapanış — artçı sarsıntı konusu karara bağlandı (2026-08-17)
20 vaka doğrulamasında (vaka 13, `4db97035`) ortaya çıkan soru: yol yüzeyi temiz ama
bina ağır hasarlı — artçı sarsıntıda çökerse? Üç seçenek değerlendirildi: (A) tam risk
modeli, (B) kapsam dışı bırak, (orta yol) rota maliyetine dokunmayan uyarı etiketi.

**Karar: B — kapsam dışı** (K-20). Riski modelleyecek veri yok; çökme olasılığı taşıyıcı
sisteme, hasarın yapısal karşılığına ve artçı büyüklüğüne bağlı ve üçü de uydudan
okunamıyor. Seçilecek her eşik gerekçesiz kalırdı — K-19'da her parametre için kurulan
fiziksel gerekçe zincirinin karşılığı olmayan bir sayı eklemek olurdu. Orta yol da
elendi: etiket sistemin çıktısını değiştirmediği için sınanamaz.

Doğrulama sırasında netleşen ve kayda değer kural: **karar bina hasarına değil, yol
yüzeyinde görünür fiziksel engele dayanır.** İlk 8 vakada bu netleşmemişti ve aynı
gözlem bazen `difficult` bazen `passable` sonucu verdi; kural sabitlendikten sonra
5 vaka (2, 3, 6, 15, 18) yeniden değerlendirildi.

### Karara dönüşenler
K-15, K-16, K-17, K-18, K-19, K-20

---

## [Faz 2c — Kuzey anotasyon turu tamamlandı] — 2026-08-05
### Yapılanlar
- Kuzey 100 kalibrasyon görevini etiketledi (`annotations_kuzey.json`, 10 adet `emin-degilim`)
- `PHASE2C_README.md`: Meyusun için kurulum, protokol ve bulgular dokümanı
- `reports/phase2c_kuzey.txt`: karşılaştırma çıktısı repoya alındı
### İki sessiz hata bulundu ve düzeltildi
- **Label Studio 404 — kök neden bulundu.** `phase2c_calibration_set.py` içinde
  `DOC_ROOT = expanduser("~")` idi; Label Studio ise
  `LABEL_STUDIO_LOCAL_FILES_DOCUMENT_ROOT=<proje kökü>` ile başlatılıyordu.
  `relpath` doğru çalışıyordu ama yanlış referansa göre → URL'de `disaster-routing`
  iki kez → var olmayan yol. Kod hatası değil, iki bileşen arası **sözleşme
  uyuşmazlığı**. Düzeltme: `DOC_ROOT` script konumundan türetiliyor
  (`dirname(dirname(abspath(__file__)))`), kullanıcı adından bağımsız.
  Ev dizinini kök yapmak da çözerdi ama Label Studio'ya tüm `$HOME`'u HTTP'den
  sunma yetkisi verirdi — reddedildi.
- **`.gitignore` satır içi yorum hatası.** `data/labeling/ground_truth.csv  # GIZLI`
  satırı, git tarafından yorum + desen olarak değil **tek bir desen** olarak okunuyordu.
  Yani cevap anahtarı ve 200 PNG **engellendiği sanılırken engellenmiyordu**.
  `#` yalnızca satır başındaysa yorumdur. Yorumlar kendi satırlarına taşındı,
  `git check-ignore -v` ile üç dosya için doğrulandı.
### Sonuç (Kuzey turu, xBD referansına karşı)
90/100 değerlendirildi · 4-sınıf doğruluk **0.556** · ikili (hasarlı)
**recall 0.630 | precision 0.829**

Karışıklık matrisinin tek önemli bulgusu: `major-damage` satırı 22 örnekte
yalnızca **3** doğru, **12'si `no-damage`** olarak işaretlendi. `minor-damage`
satırında da 21 örneğin 10'u `no-damage`. Hatalar rastgele değil, **tek yönlü** —
hasar sistematik olarak olduğundan hafif okunuyor. `destroyed` 23/24 doğru,
çünkü tek **ikili** kritere sahip sınıf o.

Teşhis: bu bir dikkat sorunu değil, **protokol sorunu**. `config.xml` hint'lerinde
"büyük ölçüde", "kısmen" gibi ölçülemez niteleyiciler var; `no-damage` ile
`minor/major` arasında zorunlu ayırt edici yok, dolayısıyla belirsizlikte
`no-damage` varsayılan davranışa dönüşüyor. Ayrıca `Choices toName="post"` —
karar bir **fark** kararı olmasına rağmen protokolde "önce/sonra karşılaştır"
talimatı hiç yok.

Projeye etkisi: `major-damage` binayı `no-damage` saymak, molozunu yola
dökebilecek binayı yok saymaktır — planlayıcı kapalı yolu açık kabul eder.
Faz 1'deki `edge_cost` hatasının **veri katmanındaki eşdeğeri**.
### Hata analizi — 12 kaçırılan `major-damage` örneği
İncelenen: xBD `major-damage` / Kuzey `no-damage` olan 12 görev
(task_0018, 0020, 0035, 0038, 0041, 0048, 0058, 0063, 0075, 0084, 0086, 0087).
3 görevin görselleri tek tek incelendi, ardından afet dağılımı veriden çıkarıldı.

**Görsel bulgular (3 örnek):**
- Hasar binanın **geometrisinde** değil, **çevresinde** görünüyor: zemin dokusunun
  değişmesi, öncede net olan yolun sonrada kaybolması.
- Çatı **geometrisi korunurken renk/parlaklık değişiyor** (koyu gri → parlak beyaz):
  çatı üzerinde birikinti işareti.
- Her üç örnekte de bina formu bozulmamış. "Çatı bütünlüğü" kriteri bu vakaları
  yakalayamıyor.

**Afet dağılımı — asıl bulgu:**

| Afet | `major-damage` örnek | Kaçırılan | Oran |
|---|---:|---:|---:|
| hurricane-florence | 13 | 9 | %69 |
| hurricane-michael | 8 | 2 | %25 |
| hurricane-matthew | 3 | 0 | %0 |
| mexico-earthquake | 1 | 1 | (n=1) |

Hatalar taban orana yayılmış değil, **hurricane-florence'ta yoğunlaşmış** (setin %52'si,
hataların %75'i). Florence bir **sel** afetidir: bina ve çatı sağlam, hasar binanın
içinde ve altında. Uydudan görünen tek şey su örtüsü. Görsel incelemede "moloz" sanılan
zemin kararması aslında sudur.

**Kalibrasyon setinin sınırlılığı:** `major-damage` sınıfının 25 örneğinden **24'ü
kasırga, 1'i deprem**. Yani doğruluk 0.556 rakamı Kahramanmaraş performansını tahmin
etmiyor; kasırga/sel hasarını tanıma performansını ölçüyor. xBD'de deprem verisi zaten
çok az olduğu için set yeniden kurulmuyor — bu, eldeki veriyle kurulabilecek en iyi
settir. Kappa kapısı geçerliliğini korur: kappa "ikimiz aynı protokolü aynı şekilde
uyguluyor muyuz" sorusunu ölçer, bu afet tipinden bağımsızdır.
**Tez metnine sınırlılık olarak yazılacak.**

**Protokol revizyonu için türetilen kurallar (Meyusun'un turundan SONRA uygulanacak):**
1. **Kanıt kapsamı genişletilir.** Hedef yine ortadaki binadır, ancak kanıt binanın
   kendisi **ve yakın çevresidir**: moloz saçılması, zemin dokusu/renk değişimi,
   çatı üzerinde birikinti, kenar hattının bozulması. "Ortadaki bina" bir *hedef seçme*
   kuralıdır (iki anotatörün aynı nesneyi değerlendirmesi için), *kanıt kısıtı* değil.
2. **Önce/sonra karşılaştırması zorunlu kılınır.** Mevcut protokolde bu talimat hiç
   yoktu; `<Choices toName="post">` yalnızca sonra görüntüsüne bağlıydı. Oysa karar bir
   **fark** kararıdır.
3. **Yukarıdan bakışta çatı, hasarın en geç görünen kısmıdır.** Üç duvarı çökmüş bina
   tepeden bütün görünebilir. `destroyed`'in %96 doğru olmasının sebebi budur: orada
   hasar çatıya kadar ulaşmıştır. `major-damage` tam olarak "hasar var ama çatıya
   yansımamış" bölgesidir.

**Ayrıca bulundu — yama kırpma kusuru:** Bazı görevlerde (ör. task_0021) kadrajın yarısı
siyah dolgu. Merkezi bina karo sınırına yakınsa yama taşıyor. Bu, "geometrik olarak
ortadaki bina" kuralını belirsizleştiriyor çünkü görüntünün geometrik merkezi kayıyor.
`phase2c_calibration_set.py` kırpma mantığı gözden geçirilecek.

### Açık
- Meyusun'un bağımsız turu → **Cohen's kappa (hedef ≥ 0.60)**. Kappa hesaplanmadı;
  bu script'teki kappa anotatörler arası uyumdur, anotatör–xBD uyumu değil.
- Kappa yüksek çıksa bile yeterli değil: ikimiz de aynı yöne kayıyorsak kappa
  ortak körlüğü gizler. İki karışıklık matrisi birlikte okunacak.
- xBD `major-damage` / Kuzey `no-damage` olan 12 görev görsel olarak incelenecek;
  çıkacak görsel kanıt tipleri protokol revizyonunun girdisi olacak.
### Karar adayı
`annotations_*.json` repoda tutulmaz — anotatör bağımsızlığı mekanizmayla
korunur, ricayla değil. `Kararlar.md`'ye K numarası ile işlenecek.

---
## [Faz 3 baseline tamamlandı · Faz 2c başladı] — 2026-07-30

### Faz 3 — CVA baseline (tamamlandı)
- 40 Palu karosu, 7898 bina (%14.2 hasarlı)
- **Sonuç: recall 0.72 @ precision 0.20** — taban oranın (0.142) sadece 1.44 katı
- Zayıflık sebebi görsel olarak doğrulandı: CVA ısı haritasında en parlak yerler
  yıkım değil, bina/yol **kenarları** → paralaks ve kayıt hatası
- **CNN'in geçmesi gereken referans: recall 0.72 @ precision 0.20**

### Faz 3 — hazırlık
- GPU teyit: RTX 4060 Laptop, 8 GB VRAM, CUDA 13.0 sürücü
- `phase3_make_patches.py`: bina merkezli 128×128 pre/post yamaları,
  3:1 dengeleme, spatial_cv fold'larıyla
- PyTorch `disaster` ortamında yok → pip + cu128 ile kurulacak

### Faz 2c — etiketleme (başladı)
- `phase2c_calibration_set.py`: xBD'den sınıf başına 25 örnek, karıştırılmış
- `phase2c_compare.py`: doğruluk, Cohen's kappa, karışıklık matrisi,
  tartışılacak örnek listeleri
- Yeni karar: **K-13** (kalibrasyon)

### İş bölümü
Arkadaşta GPU yok → **etiketleme izi (Faz 2c) onda**, **model izi (Faz 3) Yusuf'ta**.
İki iz paralel yürüyor, birbirini bloklamıyor.

### Sonraki adım
- Yusuf: PyTorch kur → yamaları üret → Siamese CNN
- Arkadaş: kalibrasyon setini etiketle
- İkisi bitince `phase2c_compare.py`, anlaşmazlıkları tartış

---
---

## [Faz 2 tamamlandı] — 2026-07-30

### Yapılanlar
- **xBD indirildi** (Challenge training set, ~7.8 GB, 2799 karo) ve incelendi
  - `inspect_xbd.py`: pre/post çifti + hasar poligonları görselleştirme
- **Spatial CV kuruldu** (`spatial_cv.py`)
  - Koordinatlar etiket JSON'undaki `lng_lat` alanından çıkarıldı (ek indirme gerekmedi)
  - 2283 karo → 202 blok (0.05° ≈ 5.5 km) → 5 fold
- **Copernicus EMSR648** indirildi (AOI04, AOI16, AOI17), şeması çözüldü
  - `inspect_emsr648.py`: katman/kategori inceleme
- **Dört katman hizalama doğrulaması** (`turkoglu_four_layers.py`)
  - OSM graf + USGS rüptür + likefaksiyon + EMSR648 bina hasarı, tek haritada
- **Repo düzenlendi:** `.gitignore`, README (faz checkbox'ları), push edildi

### Ölçülen bulgular
| Bulgu | Sayı |
|---|---|
| Rastgele bölmede sızıntı | blokların **%80.2**'si iki fold'a dağılıyor |
| Blok bazlı bölmede sızıntı | **%0** |
| xBD deprem hasarı (Meksika) | 121 karo, sadece **20** ağır/yıkık bina |
| xBD Palu en hasarlı karo | 294 sağlam / 1540 yıkık / 9 `major-damage` |
| EMSR648 hasarlı blok oranı | Kahramanmaraş %0.4 · Nurdağı %9.3 · Türkoğlu %11.8 |
| EMSR648 yol hasarı | pratikte **yok** — Nurdağı'nda segmentlerin %55'i "Not Analysed" |
| Türkoğlu: hasarlı bloklara 30 m içindeki yol segmenti | 351 / 3700 (%9.5) |

### Karara dönüşenler
K-05, K-06, K-07, K-08, K-09, K-10 → bkz. `Kararlar.md`

### Önemli gözlem
Türkoğlu'nda **rüptür ile bina hasarı çakışmıyor** — hasar sarsıntı kaynaklı,
yüzey kırılmasından bağımsız. İki ayrı sinyal, ikisi de gerekli.

Dört katman haritasında **rota, yıkık binaların arasından umursamadan geçiyor** —
köprü katmanının dolduracağı boşluk görsel olarak kanıtlandı.

---

## [Faz 1 tamamlandı] — 2026-07

### Yapılanlar
- **Fay rüptürü entegrasyonu** (`phase1_rupture_real.py`)
  - Reitman ve ark. 2023 geoJSON, EPSG:4326
  - UTM 32637'ye projekte → 100 m buffer → koridor → kesişen kenarlar `closed`
  - Demo bölgesi Türkoğlu'na taşındı (rüptür oradan geçiyor)
- **Likefaksiyon entegrasyonu** (`phase1_liquefaction1.py`)
  - Zhu ve ark. 2017 GeoTIFF, EPSG:4326, ~460 m hücre
  - Pencereli okuma → eşikleme (0.05) → poligonlaştırma → `difficult`
  - `closed` ezilmiyor (rüptür daha ciddi)
- Öncesinde sentetik poligonla mekanizma doğrulandı (`phase1_hazard.py`)

### Sonuç
Türkoğlu grafında: 28 kenar `closed`, 1640 kenar `difficult`.
Rota `closed`'dan tamamen kaçtı, `difficult`'a sadece mecbur kalınca girdi.

### Öğrenilen kavramlar
vektör vs raster · CRS/EPSG · buffer · mekânsal kesişim · pencereli okuma ·
eşikleme · poligonlaştırma

### Karara dönüşenler
K-03, K-04

---

## [Faz 0 tamamlandı] — 2026-07

### Yapılanlar
- `phase0_routing.py`: OSMnx graf çekme (Antakya), great-circle heuristik,
  A* rota, `traversability` arayüzü, elle konan dummy engel
- Ortam kuruldu: miniforge, `disaster` conda env, ROS2 `PYTHONPATH` izolasyonu

### Kanıtlanan
Engel konduğunda rota kendini yeniden yönlendiriyor. `traversability`
sözleşmesi (`passable`/`difficult`/`closed`) sabitlendi — bu sözleşme
Faz 1 ve 2 boyunca değişmedi.

### Karara dönüşenler
K-01, K-02, K-11, K-12
