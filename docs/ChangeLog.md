# ChangeLog.md

> Kronolojik ilerleme kaydı. **Yeni girdiler en üste** eklenir.
> Format: fazın sonunda bir girdi — her konuşmadan sonra değil.
> Yerleşmiş bilgiler periyodik olarak `ProjeContext.md`'ye taşınıp buradan kısaltılır.

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
