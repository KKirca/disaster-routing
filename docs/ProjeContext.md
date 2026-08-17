# ProjeContext.md

> Bu dosya **yavaş değişen** bilgiyi tutar: proje amacı, mimari, ortam, veri kaynakları.
> Kararlar → `Kararlar.md` · Tarihçe → `ChangeLog.md`
> Son güncelleme: 2026-07-30

## Amaç

Deprem sonrası acil durum araçları (kamyon, ambulans) için **kalkış öncesi optimal rota**
planlama. Uydu görüntüsünden yol geçilebilirliğini çıkarıp rota maliyetine çeviriyoruz.

İlham: 2023 Kahramanmaraş depreminde yaşanan lojistik tıkanıklık.

**Başarı tanımı:** Tek bölgeye özel demo değil, **genellenebilir ve operasyonel olarak
uygulanabilir** bir sistem.

## Mimari — üç katman

1. **Hasar tespiti** — Siamese CNN (xBD), Prithvi-tipi foundation backbone,
   SAM etiketleme yardımcısı olarak, CVA/NDBI klasik baseline
2. **Köprü katmanı** *(çekirdek özgünlük)* — bina hasarı → yol geçilebilirlik maliyeti
   **Faz 4'te inşa edildi ve doğrulandı** (K-15…K-20, `scripts/phase4_*.py`).
   - Girdi: sabit şemalı CSV — `uid, lon, lat, footprint_wkt, area_m2,
     damage_class, confidence, source` (K-18). Katman modeli çağırmaz, `.npz`
     okumaz; kaynağı `xbd_gt` de olabilir `model_v1` de.
   - Ara değer: `damage_pressure` ∈ [0,1], graf kenar özniteliği (K-15)

         katki = sinif × mesafe × alan × darlik      (her faktör 0-1)
         damage_pressure = 1 - Π(1 - katki_i)

           sinif  : destroyed 1.00 | major 0.60 | minor 0.15
           mesafe : max(0, 1 - d/R),  R = 25 m,  d = POLİGON-kenar mesafesi
           alan   : min(alan_m2 / 400, 1.0)
           darlik : min(7.0 / W, 1.0),  W = highway tablosu + lanes düzeltmesi
   - Çıktı: üç kademe `passable` / `difficult` / `closed`, eşikle türetilir
   - Eşik **kasıtlı sabitlenmedi** — ground truth yok, seçip sonucuna bakmak
     döngüsel olurdu. Varsayılan 0.50/0.20, duyarlılık analiziyle raporlanır.
   - Birleştirme konservatif: en kısıtlayıcı etiket kazanır; Faz 4 Faz 1'in
     yazdığı etiketi gevşetemez (K-16)
   - Kapsam: yalnızca **anlık fiziksel geçilebilirlik**. Artçı sarsıntı çökme
     riski kapsam dışı (K-20)

   *Not: erken plan metninde geçen "taraf-içi max + çapraz summation",
   "kamyon genişliği (~3.5 m) eşiği", "darboğaz kuralı" ve "recall-öncelikli
   kalibrasyon" uygulanmadı. Gerekçeler K-19'da; özetle mesafe/alan/genişlik
   çarpanları sürekli bir skorda birleştirildi ve kalibrasyon yerine duyarlılık
   analizi seçildi (kalibre edilecek hedef değişken yok).*
3. **Rota** — OSMnx yol grafı + ağırlıklı A*

### Temel mimari ilke

> **Rota çekirdeği (`edge_cost`, heuristik, A*) hiç değişmez.
> Sadece `traversability` etiketinin KAYNAĞI değişir.**

Faz 0'dan Faz 2'ye kadar üç farklı kaynakla (elle → sentetik poligon → gerçek USGS
vektör + raster) doğrulandı. Çekirdek tek satır değişmedi.

## Kademe yapısı (yol yüzeyi bütünlüğü)

| Kademe | Kaynak | Üretim süresi | Rol |
|---|---|---|---|
| Kademe 1 | USGS Ground Failure (likefaksiyon) | ~30 dk | **operasyonel** |
| Kademe 1 (yan) | USGS fay rüptürü | aylar | **sadece doğrulama** |
| Kademe 2 | Özel yol yüzeyi segmentasyonu | — | planlanan |

## Ortam

- Ubuntu 22.04 LTS, ROS2 Humble kurulu (sistem Python'unda)
- conda ortamı: `disaster` (Python 3.11, miniforge/conda-forge)
- **Kritik:** ROS2 `PYTHONPATH` sızıntısı yapar. `activate.d` script'i ile
  otomatik `unset PYTHONPATH` kurulu.
- Kütüphaneler: osmnx, networkx, geopandas, rasterio, shapely, matplotlib
- Editör: VS Code, `disaster` interpreter seçili

```bash
conda activate disaster
cd ~/disaster-routing
python scripts/<ad>.py     # tüm script'ler PROJE KÖKÜNDEN çalıştırılır
```

## Repo

İki uzak depo kullanılıyor:
- `github.com/Meyusun/disaster-routing` — orijinal (`origin`)
- `github.com/KKirca/disaster-routing` — Kuzey'in fork'u (`myrepo`)

Faz 2c etiketleme ve Faz 4 köprü katmanı çalışması `myrepo`'da. Meyusun'un
takip etmesi için: `git remote add kuzey <url>` sonra `git fetch kuzey`.

```
~/disaster-routing/
├── scripts/     # tüm .py dosyaları
├── docs/        # ProjeContext.md, Kararlar.md, ChangeLog.md, FAZ4_KULLANIM.md
├── data/        # veri (xbd/ ve buyuk graf'lar gitignore'da)
├── reports/     # metin ciktilari (dogrulama, duyarlilik analizi)
├── outputs/     # üretilen görseller (gitignore'da, anahtar olanlar -f ile eklendi)
├── cache/
├── README.md, environment.yml, .gitignore
```

**`data/xbd/` asla commit edilmez** (~11 GB). `.gitignore` bunu engelliyor.

## Veri kaynakları

| Veri | Kaynak | Format | Konum |
|---|---|---|---|
| xBD | xview2.org → Challenge training set (~7.8 GB) | PNG + JSON | `data/xbd/train/` |
| USGS fay rüptürü | ScienceBase, Reitman ve ark. 2023 | geoJSON (vektör) | `data/` |
| USGS likefaksiyon | olay `us6000jllz` → Ground Failure → `zhu_2017_general_model.tif` | GeoTIFF (raster) | `data/` |
| Copernicus EMSR648 | mapping.emergency.copernicus.eu | shapefile | `data/emsr648/` |
| Maxar Open Data | STAC, koleksiyon `Kahramanmaras-turkey-earthquake-23` | COG | *henüz indirilmedi* |

**Kullanılan AOI'ler:** AOI04 Kahramanmaraş · AOI16 Nurdağı · AOI17 Türkoğlu

**Deprem olay kimlikleri:** M7.8 Pazarcık = `us6000jllz` · M7.5 Elbistan = `us6000jlqa`

## Demo bölgesi

**Türkoğlu** (`CENTER = (37.38, 36.87)`, `DIST = 5000`). Seçilme sebebi: fay rüptürü
bölgeden geçiyor, EMSR648 AOI17 kapsıyor, ve en yüksek bina hasar oranına sahip
(%11.8). Dört katman burada hizalandı ve doğrulandı.

**Faz 4 geliştirme zemini ayrıdır: `mexico-earthquake` / Mexico City**
(`CENTER = (19.3154, -99.1867)`, `DIST = 11000`). Sebep (K-17): köprü katmanı
deprem enkazının yolu nasıl tıkadığını modelliyor ve bu davranış afet tipine
göre kökten değişiyor — yangında bina çöker ama yola moloz saçmaz, selde yol
suyla kapanır. xBD'deki tek deprem seti mexico-earthquake'tir (121 karo,
32.271 bina, 20'si ağır hasarlı). En büyük set olan socal-fire (823 karo)
burada yanlış settir.

Türkoğlu ve Mexico City farklı amaçlara hizmet eder: Türkoğlu Faz 0-2'nin
hazard katmanı doğrulama zemini, Mexico City Faz 4'ün geliştirme zemini.
Kahramanmaraş'a transfer bir **varsayımdır** — yapı stoku farklı ve 2017
Puebla'da yıkım noktasaldı, mahalleler düzleşmedi. Eşikler ve `R` orada
yeniden bakılmalı.

## Şema eşlemesi — EMSR648 ↔ xBD

| EMSR648 | xBD | Not |
|---|---|---|
| `Destroyed` | `destroyed` | |
| `Damaged` | `major-damage` | |
| `No visible damage` | `no-damage` | |
| `Possibly damaged` | **hiçbiri** | belirsizlik kategorisi, şiddet değil — ayrı raporlanır |

## Ekip çalışma şekli

İki kişi, ayrı Claude Project'leri, ortak knowledge dosyaları (bu üç dosya).
Faz sonlarında knowledge yeniden yüklenir. Etiketlemede iki bağımsız annotatör.
