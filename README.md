# Afet Lojistik Rota Planlama Sistemi

Deprem hasarina gore acil durum kamyonlarini **kalkistan once** guvenli rotaya yonlendiren, AI destekli bir on-rota planlama sistemi.

> **Motivasyon:** 2023 Turkiye depreminde acil guc ekipmani tasiyan bir kamyon, gecilmez yollar yuzunden bir gunden fazla gecikti. Bu proje, uydu goruntusunden cikarilan hasar bilgisini yol gecilebilirligine cevirerek bu tur gecikmeleri kalkis oncesinde onlemeyi hedefler.

## Mimari (ozet)

1. **Yol grafi:** OSMnx ile vektor yol grafi (dugum/kenar).
2. **Hasar tespiti (Layer 1):** Siamese CNN (xBD) + Prithvi-tipi backbone; SAM etiketleme yardimcisi; baseline CVA/NDBI.
3. **Kopru katmani (Layer 2 — CEKIRDEK YENILIK):** Bina hasarini yol gecilebilirligine cevirir. Taraf-ici max + karsi-taraf toplami ile enkaz katkisi, kamyon genisligine (~3.5 m) gore uc kademeli maliyet (passable/difficult/closed), segment basina darbogaz kurali, guvenlik-asimetrik kalibrasyon.
4. **Rota secimi:** Cok kriterli kenar agirliklariyla agirlikli A*.
5. **Yol yuzeyi butunlugu:** Kademe 1 (USGS fay ruptquru, likefaksiyon) + Kademe 2 (ozel segmentasyon).

## Yol Haritasi / Ilerleme

- [x] **Faz 0 — Yuruyen iskelet:** OSMnx yol grafi, great-circle sezgili A*, traversability arayuzu, dummy blok kenarla yeniden rota.
- [x] **Faz 1 — Kademe 1 hazard katmanlari:** Reitman 2023 fay ruptquru (Turkoglu, 100 m tampon, 28 kenar closed), Zhu 2017 likefaksiyon rasteri.
- [x] **Faz 2 — Veri ve ground truth altyapisi**
- [ ] **Faz 3 — Hasar tespiti ML (Siamese CNN / Prithvi)**
- [ ] **Faz 4 — Kopru katmani (cekirdek yenilik)**
- [ ] **Faz 5 — Yol yuzeyi butunlugu (Kademe 2)**
- [ ] **Faz 6 — Degerlendirme ve uctan uca demo**

## Kurulum

\`\`\`bash
conda env create -f environment.yml
conda activate disaster
\`\`\`

Yigin: Python 3.11, OSMnx, NetworkX, GeoPandas, Rasterio, Matplotlib.

## Veri (buyuk dosyalar repoda yok)

data/ altindaki graphml dosyalari (yol graflari) repoda tutulur; buyuk raster/goruntu dosyalari degil. Indir ve data/ icine koy:

- **Fay ruptquru:** Reitman 2023 yuzey ruptquru (ScienceBase, GeoJSON).
- **Likefaksiyon:** USGS Ground Failure — Zhu 2017 GeoTIFF.
- **Bina hasari:** Maxar Open Data, Copernicus EMS (EMSR648), xBD.
- **USGS olaylari:** M7.8 Pazarcik (us6000jllz), M7.5 Elbistan (us6000jlqa).

## Calistirma

\`\`\`bash
conda activate disaster
python scripts/phase0_routing.py
\`\`\`
