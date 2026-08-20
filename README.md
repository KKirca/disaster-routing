# disaster-routing

Deprem sonrası acil durum araçları için **uydu görüntüsünden yol geçilebilirliği**
çıkarımı yapan rota planlama sistemi.

Temel fikir: bina hasarı ve zemin riski sinyallerini yol segmenti maliyetlerine
çevirip A* ile güvenli rota üretmek. Sistemin çekirdek özgünlüğü **köprü katmanı** —
bina hasarını yol geçilebilirliğine dönüştüren ara katman.

> **Detaylı bağlam `docs/` altında:**
> [ProjeContext.md](docs/ProjeContext.md) (mimari, ortam, veri kaynakları) ·
> [Kararlar.md](docs/Kararlar.md) (tasarım kararları ve gerekçeleri) ·
> [ChangeLog.md](docs/ChangeLog.md) (ilerleme kaydı ve bulgular)

## Mimari

1. **Hasar tespiti** — Siamese CNN (xBD) + foundation backbone
2. **Köprü katmanı** *(çekirdek katkı)* — bina hasarı → yol geçilebilirlik maliyeti
3. **Rota** — OSMnx graf + ağırlıklı A*

**Temel ilke:** rota çekirdeği (`edge_cost`, heuristik, A*) hiç değişmez;
sadece `traversability` etiketinin kaynağı değişir.

## Faz durumu

- [x] **Faz 0** — İskelet: graf, A*, `traversability` arayüzü, dummy engel
- [x] **Faz 1** — Kademe 1: USGS fay rüptürü (`closed`) + likefaksiyon (`difficult`)
- [x] **Faz 2** — Veri altyapısı: xBD, spatial CV (%0 sızıntı), EMSR648, dört katman doğrulaması
  - [ ] Maxar Open Data görüntü çekimi
  - [ ] Faz 2c — Label Studio etiketleme *(1/2 anotatör tamam; kappa ölçümü Meyusun'un turunu bekliyor)*
- [ ] **Faz 3** — Hasar tespiti modeli
  - [x] CVA baseline — **recall 0.72 @ precision 0.20**
  - [ ] Siamese CNN
  - [ ] Foundation backbone
- [x] **Faz 4** — Köprü katmanı *(mexico-earthquake üzerinde; Kahramanmaraş transferi açık)*
  - [x] `damage_pressure` skoru (K-19) — bina hasarı → yol maliyeti
  - [x] Rota doğrulaması: SAPMA (+44 m) ve IZOLASYON (`NetworkXNoPath`) senaryoları
  - [x] 20 ağır hasarlı binanın görsel doğrulaması (uzman muhakemesi referansı — 12/19 uyumlu, 7 ayrışma; karar: yol yüzeyinde görünür fiziksel engel)
  - [ ] Kahramanmaraş'a transfer — eşikler ve `R` yeniden bakılacak
- [ ] **Faz 5** — Kademe 2: yol yüzeyi segmentasyonu
- [ ] **Faz 6** — Kalibrasyon ve uçtan uca değerlendirme

## Kurulum

```bash
conda env create -f environment.yml
conda activate disaster
```

**ROS2 kuruluysa:** `PYTHONPATH` sızıntısını otomatik temizle —

```bash
mkdir -p $CONDA_PREFIX/etc/conda/activate.d
echo 'unset PYTHONPATH' > $CONDA_PREFIX/etc/conda/activate.d/unset_pythonpath.sh
```

Model eğitimi için (GPU gerekir):

```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
```

## Veri

Büyük veri repoda **yok**. İndirme adresleri ve klasör yapısı:
[docs/ProjeContext.md → Veri kaynakları](docs/ProjeContext.md)

Kısaca: xBD → `data/xbd/` (~7.8 GB, gitignore'da) · USGS rüptür + likefaksiyon →
`data/` (repoda) · Copernicus EMSR648 → `data/emsr648/` (repoda).

## Çalıştırma

Tüm script'ler **proje kökünden** çalıştırılır:

```bash
python scripts/<ad>.py
```

| Script | Ne yapar |
|---|---|
| `phase0_routing.py` | Graf + A* + `traversability` arayüzü + dummy engel |
| `phase1_rupture_real.py` | Fay rüptürünü buffer'layıp `closed` uygular |
| `phase1_liquefaction1.py` | Likefaksiyon rasterını eşikleyip `difficult` uygular |
| `turkoglu_four_layers.py` | Dört katmanı tek haritada birleştirir |
| `spatial_cv.py` | Mekânsal blok bazlı fold bölünmesi + sızıntı ölçümü |
| `phase3_cva_baseline.py` | CVA baseline + recall-öncelikli değerlendirme |
| `phase3_make_patches.py` | Model için bina merkezli pre/post yamaları |
| `phase2c_calibration_set.py` | Label Studio kalibrasyon seti üretir |
| `phase2c_compare.py` | Anotatör etiketlerini xBD ile karşılaştırır |
| `inspect_*.py` | İlgili veri kaynağını tanıma/görselleştirme |

## Ekip

İki kişi, ayrı Claude Project'leri, ortak knowledge = `docs/` altındaki üç dosya.
Faz sonlarında güncellenir ve Project'e yeniden yüklenir.

**Güncel iş bölümü:** etiketleme izi (Faz 2c, Meyusun'un anotasyon turu) ve köprü
katmanı izi (Faz 4, tamamlandı) paralel yürüdü. Faz 4'ün Faz 3'e bağımlı olmaması
K-18'in doğrudan sonucudur: köprü katmanının girdisi sabit şemalı bir CSV'dir, modeli
çağırmaz. Bugün xBD uzman etiketiyle beslendi, model hazır olduğunda aynı şemayla
`model_v1` kaynağı kullanılacak — ve aynı bölgede iki koşu karşılaştırılarak modelin
hatasının rotaya ne kadar yansıdığı ölçülebilecek.
