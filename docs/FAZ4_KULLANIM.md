# Faz 4 — Köprü Katmanı: Çalıştırma Kılavuzu

Bina hasarını yol geçilebilirliğine çeviren katman. Kararlar `Kararlar.md`
K-15…K-19'da, süreç kaydı `ChangeLog.md`'de.

## ÖNEMLİ: LC_ALL=C

OSMnx/GraphML işleyen **her** komutu `LC_ALL=C` ile çalıştır.

Türkçe locale'de (`LANG=tr_TR.UTF-8`) OSMnx GraphML yazarken `LINESTRING`
→ `LiNESTRiNG` oluyor ve dosya geri okunamıyor. Sebep: Türkçede `i` harfinin
büyüğü `İ`'dir; yerel ayara duyarlı dönüşüm ASCII'ye düşerken noktaları
kaybediyor. Klasik "Türkçe i problemi".

Hata belirtisi: `GEOSException: ParseException: Unknown type: 'LiNESTRiNG'`

## Boru hattı

    xBD etiketi → CSV → mekansal eşleştirme → damage_pressure → traversability → A* → rota

## Adımlar

### 0. Ortam

    conda activate disaster
    cd ~/disaster-routing

### 1. Girdi tablosunu üret

    python scripts/phase4_build_damage_csv.py

Çıktı: `data/damage/mexico-earthquake_xbd_gt.csv` (32.196 bina)
Şema (K-18): `uid, lon, lat, footprint_wkt, area_m2, damage_class, confidence, source, tile`

Bu dosya repoda mevcut; yeniden üretmek zorunda değilsin.

### 2. Yol grafını indir

    LC_ALL=C python -c "
    import osmnx as ox
    G = ox.graph_from_point((19.3154,-99.1867), dist=11000, network_type='drive')
    ox.save_graphml(G, 'data/mexico_city_graph.graphml')
    print(G.number_of_nodes(), 'dugum', G.number_of_edges(), 'kenar')
    "

Beklenen: 59.862 düğüm, 133.559 kenar. ~53 MB, repoda yok (.gitignore).

### 3. Eşleştirmeyi kontrol et (opsiyonel)

    LC_ALL=C python scripts/phase4_match_buildings.py

20 ağır hasarlı binanın hangi yollara ne kadar yakın olduğunu listeler.
Beklenen: 18/20 bina eşleşir.

### 4. Skor dağılımına bak (opsiyonel)

    LC_ALL=C python scripts/phase4_damage_pressure.py --R 15 25 40

Farklı `R` (moloz yayılma mesafesi) değerlerinde skor dağılımı.
Grafa yazmaz, sadece raporlar.

### 5. Skorları grafa yaz

    LC_ALL=C python scripts/phase4_apply_to_graph.py

Çıktı: `data/mexico_city_graph_faz4.graphml` (~56 MB, repoda yok)
R = 25 m sabit. 234 kenar etkilenir.

### 6. Rota karşılaştırması

    LC_ALL=C python scripts/phase4_route_compare.py --tara

Çıktı: `reports/phase4_esik_duyarlilik.txt`

İki senaryo:
- **IZOLASYON** — hedef kavşağın üç kolu da hasarlı, `closed` mekanizmasını sınar
- **SAPMA** — alternatif mevcut, `difficult` mekanizmasını sınar

Tek eşikle çalıştırmak için: `--t-closed 0.7 --t-diff 0.3`

### 7. Görselleştir

    LC_ALL=C python scripts/phase4_visualize.py

Çıktı: `outputs/phase4_izolasyon.png`, `outputs/phase4_sapma.png`
Sol panel hasarsız rota, sağ panel hasarlı rota.

## Eşik hakkında

**Eşik kasıtlı olarak sabitlenmedi.** Hangi eşiğin doğru olduğunu gösterecek
ground truth yok; eşiği seçip sonucuna bakmak döngüsel gerekçelendirme olurdu.

Varsayılan `0.50 / 0.20`. Sonuçlar birden fazla eşikle raporlanır (duyarlılık
analizi). Tezde "eşiği 0.5 seçtik" yerine "eşik 0.3'te 13 yol, 0.7'de 2 yol
kapanıyor" denir.

Ne zaman değiştirilmeli — ayrıntı `scripts/phase4_route_compare.py` başlığında:
1. Kahramanmaraş'a geçerken (K-17 transfer varsayımı)
2. Model çıktısı kullanılırken (Faz 2c'de ölçülen iyimserlik yanlılığı)
3. `R` değiştiğinde
4. Saha verisi gelirse (o zaman eşik tahmin değil ölçüm olur)

## Model çıktısıyla çalıştırmak için

Faz 4 modeli çağırmaz (K-18). Model tahminlerini aynı şemayla CSV'ye yaz:

    data/damage/<bolge>_model_v1.csv
    uid,lon,lat,footprint_wkt,area_m2,damage_class,confidence,source

`confidence` = model olasılığı, `source` = `model_v1`.

Sonra `phase4_damage_pressure.py` içindeki `DAMAGE_CSV` yolunu değiştir.

Bu yapının amacı: aynı bölgede `xbd_gt` ve `model_v1` ile iki koşu yapıp
**modelin hatasının rotaya ne kadar yansıdığını** ölçmek. "Model %70 doğrulukta,
rota kalitesi %92 korunuyor" tipi bir sonuç, tek başına sınıflandırma
metriğinden değerlidir.

## Bilinen açıklar

- 20 binanın görsel doğrulaması yapılmadı (K-19'da söz verilen uzman muhakemesi
  referansı)
- 2 bina hiçbir kenarla eşleşmedi: `adbab63d` (51.6 m), `081e6c40` (280 m —
  aykırı, OSM boşluğu veya tesis içi olabilir)
- `f3865521` ve `66ab3129` yol çizgisiyle kesişiyor (0.0 m mesafe); ters orantılı
  bir formüle geçilirse sıfıra bölme riski
