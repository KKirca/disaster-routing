"""
Faz 4 — Adim 2 (4b): Hasarli binalari yol kenarlariyla mekansal olarak eslestir.

NE YAPAR:
  Her agir hasarli bina icin, BUFFER_M metre yaricap icindeki yol kenarlarini
  bulur ve gercek mesafeyi hesaplar. Mesafe bina POLIGONUNDAN olculur, centroid'den
  degil: enkaz binanin merkezinden degil cephesinden dokulur. Bu sette taban alani
  26–1499 m2 araliginda; en buyuk binada merkez-cephe farki ~19 m'dir, yani
  centroid kullanmak mesafeyi sistematik olarak fazla olcer. Skor URETMEZ — bu asama sadece
  "hangi bina hangi kenara ne kadar yakin" iliskisini kurar.

KOORDINAT SISTEMI:
  Bina ve graf verisi WGS84'tur (derece). Derece bir uzunluk birimi degildir:
  Mexico City enleminde 1 derece boylam ~105 km, 1 derece enlem ~111 km.
  Mesafe hesabi icin metrik projeksiyona gecilir: EPSG:32614 (UTM Zone 14N).
  (Faz 1'de fay ruptur koridoru icin UTM 32637'ye gecilmesiyle ayni gerekce.)

MEKANSAL INDEKS:
  Kaba yontem her bina icin 133k kenari taramaktir (20 x 133k = 2.7M hesap).
  Bunun yerine R-tree indeksi kurulur; her bina icin yalnizca yakin adaylar
  sorgulanir. Kahramanmaras'ta binlerce hasarli bina olacagi icin bu sart.

NOT: LC_ALL=C ile calistirin. Turkce locale'de (tr_TR) OSMnx GraphML yazarken
     'LINESTRING' -> 'LiNESTRiNG' bozulmasi olusur (Turkce i problemi).

KULLANIM:
  cd ~/disaster-routing
  LC_ALL=C python scripts/phase4_match_buildings.py
"""

import geopandas as gpd
import osmnx as ox
import pandas as pd
from shapely import wkt

GRAPH = "data/mexico_city_graph.graphml"
DAMAGE_CSV = "data/damage/mexico-earthquake_xbd_gt.csv"
METRIC_CRS = "EPSG:32614"          # UTM 14N — Mexico City
BUFFER_M = 30.0                    # GECICI: gerekcelendirilmedi (Adim 5)
HEAVY = {"major-damage", "destroyed"}


def main():
    print(f"[graf]  {GRAPH}")
    G = ox.load_graphml(GRAPH)
    _, edges = ox.graph_to_gdfs(G)
    edges = edges.to_crs(METRIC_CRS)
    print(f"        {len(edges)} kenar, {METRIC_CRS}'e projekte edildi")

    df = pd.read_csv(DAMAGE_CSV)
    heavy = df[df.damage_class.isin(HEAVY)].copy()
    print(f"[bina]  {len(df)} toplam, {len(heavy)} agir hasarli")

    bld = gpd.GeoDataFrame(
        heavy,
        geometry=heavy.footprint_wkt.apply(wkt.loads),
        crs="EPSG:4326",
    ).to_crs(METRIC_CRS)

    sindex = edges.sindex
    print(f"[indeks] R-tree kuruldu\n")

    alanlar = dict(zip(heavy.uid, heavy.area_m2))
    kayitlar = []
    for _, b in bld.iterrows():
        alan = b.geometry.buffer(BUFFER_M)
        aday_idx = list(sindex.intersection(alan.bounds))
        if not aday_idx:
            kayitlar.append((b.uid, b.damage_class, 0, None, None))
            continue
        aday = edges.iloc[aday_idx]
        d = aday.geometry.distance(b.geometry)
        yakin = d[d <= BUFFER_M]
        if yakin.empty:
            kayitlar.append((b.uid, b.damage_class, 0, None, None))
            continue
        en_yakin = aday.loc[yakin.idxmin()]
        kayitlar.append((b.uid, b.damage_class, len(yakin),
                         round(yakin.min(), 1),
                         en_yakin.get("highway")))

    print(f"--- {BUFFER_M:.0f} m yaricap icindeki kenarlar ---")
    print(f"{'uid':10s} {'sinif':14s} {'alan':>7s} {'kenar':>6s} "
          f"{'en yakin':>9s}  tip")
    eslesmeyen = 0
    for uid, cls, n, dmin, hw in kayitlar:
        a = alanlar[uid]
        if n == 0:
            eslesmeyen += 1
            print(f"{uid[:8]:10s} {cls:14s} {a:6.0f}m2 {0:6d} {'-':>9s}  -")
        else:
            print(f"{uid[:8]:10s} {cls:14s} {a:6.0f}m2 {n:6d} {dmin:8.1f}m  {hw}")

    eslesen = len(kayitlar) - eslesmeyen
    print(f"\n[ozet] {eslesen}/{len(kayitlar)} bina en az bir kenarla eslesti")
    if eslesmeyen:
        print(f"       {eslesmeyen} bina {BUFFER_M:.0f} m icinde yol bulamadi")


if __name__ == "__main__":
    main()
