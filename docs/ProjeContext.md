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
   - taraf-içi max toplama + çapraz taraf summation
   - üç kademe: `passable` / `difficult` / `closed`
   - eşik: mevcut açık genişlik vs kamyon genişliği (~3.5 m)
   - darboğaz (en kötü nokta) kuralı
   - recall-öncelikli kalibrasyon
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

`github.com/Meyusun/disaster-routing`

```
~/disaster-routing/
├── scripts/     # tüm .py dosyaları
├── data/        # veri (xbd/ gitignore'da, gerisi repoda)
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
