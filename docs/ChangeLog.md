# ChangeLog.md

> Kronolojik ilerleme kaydı. **Yeni girdiler en üste** eklenir.
> Format: fazın sonunda bir girdi — her konuşmadan sonra değil.
> Yerleşmiş bilgiler periyodik olarak `ProjeContext.md`'ye taşınıp buradan kısaltılır.

---

## [Faz 3 başladı] — 2026-07-30

### Yapılanlar
- `phase3_cva_baseline.py` yazıldı: CVA (Change Vector Analysis) baseline
  - pre/post fark vektörü büyüklüğü → bina poligonu içinde ortalama → eşikle sınıflama
  - recall/precision/F1 eşik taraması, güvenlik asimetrisi vurgulu (K-08)
- **Durum:** henüz çalıştırılmadı, sonuç bekleniyor

### Sonraki adım
- Baseline sonucunu al, referans sayıyı kaydet
- GPU durumunu teyit et (`nvidia-smi`)
- Siamese CNN eğitimine geç

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
