"""
Faz 4 — Adim 3: Hasar baskisi skorunu hesapla (K-19 formulu).

    katki = sinif x mesafe x alan x darlik      (her faktor 0-1)
    damage_pressure = 1 - PI(1 - katki_i)

      sinif  : destroyed 1.00 | major 0.60 | minor 0.15
      mesafe : max(0, 1 - d/R)
      alan   : min(alan_m2 / 400, 1.0)
      darlik : min(7.0 / W, 1.0)

Gerekceler docs/Kararlar.md K-19'da.

BU ASAMADA skor grafa YAZILMAZ, traversability URETILMEZ. R parametresi ve
esikler bu dagilima bakilarak belirlenecek.

NOT: LC_ALL=C ile calistirin (Turkce locale'de OSMnx GraphML bozulmasi).

KULLANIM:
  LC_ALL=C python scripts/phase4_damage_pressure.py --R 15 25 40
"""

import argparse
from collections import defaultdict

import geopandas as gpd
import numpy as np
import osmnx as ox
import pandas as pd
from shapely import wkt

GRAPH = "data/mexico_city_graph.graphml"
DAMAGE_CSV = "data/damage/mexico-earthquake_xbd_gt.csv"
METRIC_CRS = "EPSG:32614"

SINIF_AGIRLIK = {
    "destroyed": 1.00,
    "major-damage": 0.60,
    "minor-damage": 0.15,
    "no-damage": 0.00,
    # K-21: EMSR648 "Possibly damaged" — belirsizlik ifadesi, hasar derecesi degil.
    # Beklenti degeri (0+0.60)/2=0.30, Copernicus metodolojisi hafif hasar yonune
    # yatkin oldugu icin 0.20'ye kalibre edildi. Tek basina T_CLOSED'i asamaz.
    "possibly-damaged": 0.20,
}
# Her faktor 0-1 araliginda tanimlidir. Katki bir OLASILIKTIR ("bu bina bu
# yolu tikar mi?"), dolayisiyla 1'i asamaz. Sinirsiz carpim + min() kirpmasi
# yerine faktorlerin kendisi sinirlanir: kirpilan skor bilgi tasimaz ve R
# duyarliligini yok eder.
ALAN_DOYMA = 400.0   # 400 m2 ustu bina zaten tipik sokagi dolduracak moloz uretir
W_REF = 7.0          # residential; bu ve daha dar yollar 1.0, genisler indirim alir

HIGHWAY_GENISLIK = {
    "motorway": 20.0, "trunk": 20.0,
    "primary": 14.0, "secondary": 11.0, "tertiary": 9.0,
    "residential": 7.0, "living_street": 5.0,
    "service": 4.0, "unclassified": 4.0,
}


def sokak_genisligi(highway, lanes):
    if isinstance(highway, list):
        highway = highway[0] if highway else "residential"
    hw = str(highway).replace("_link", "")
    W = HIGHWAY_GENISLIK.get(hw, 7.0)
    if lanes is not None and not (isinstance(lanes, float) and np.isnan(lanes)):
        if isinstance(lanes, list):
            lanes = lanes[0] if lanes else None
        try:
            W = max(W, float(lanes) * 3.2 + 1.5)
        except (TypeError, ValueError):
            pass
    return W


def hesapla(edges, bld, R):
    sindex = edges.sindex
    katkilar = defaultdict(list)
    for _, b in bld.iterrows():
        w_sinif = SINIF_AGIRLIK.get(b.damage_class, 0.0)
        if w_sinif == 0.0:
            continue
        w_alan = min(float(b.area_m2) / ALAN_DOYMA, 1.0)
        alan = b.geometry.buffer(R)
        for i in sindex.intersection(alan.bounds):
            e = edges.iloc[i]
            d = e.geometry.distance(b.geometry)
            if d > R:
                continue
            w_mesafe = max(0.0, 1.0 - d / R)
            if w_mesafe == 0.0:
                continue
            W = sokak_genisligi(e.get("highway"), e.get("lanes"))
            w_darlik = min(W_REF / W, 1.0)
            katkilar[i].append(w_sinif * w_mesafe * w_alan * w_darlik)
    return {i: 1.0 - np.prod([1.0 - k for k in ks])
            for i, ks in katkilar.items()}


def rapor(skorlar, edges, R, n_edge):
    vals = np.array(list(skorlar.values()))
    print("\n" + "=" * 62)
    print(f"R = {R:.0f} m")
    print("=" * 62)
    if vals.size == 0:
        print("  hicbir kenar etkilenmedi")
        return
    print(f"  etkilenen kenar : {vals.size} / {n_edge} "
          f"({100 * vals.size / n_edge:.3f}%)")
    print(f"  skor min/medyan/max : "
          f"{vals.min():.3f} / {np.median(vals):.3f} / {vals.max():.3f}")
    print("\n  --- skor dagilimi ---")
    kenarlar = [0.0, 0.1, 0.2, 0.3, 0.5, 0.7, 0.9, 1.01]
    for lo, hi in zip(kenarlar[:-1], kenarlar[1:]):
        n = int(((vals >= lo) & (vals < hi)).sum())
        print(f"  {lo:.1f}-{hi:.1f}  {n:5d}  {'#' * min(n, 50)}")
    kapali = int((vals >= 0.70).sum())
    zor = int(((vals >= 0.30) & (vals < 0.70)).sum())
    print("\n  --- K-15 yer tutucu esikleriyle (0.30 / 0.70) ---")
    print(f"  closed    : {kapali}")
    print(f"  difficult : {zor}")
    print("\n  --- en yuksek 8 kenar ---")
    for i, s in sorted(skorlar.items(), key=lambda kv: -kv[1])[:8]:
        e = edges.iloc[i]
        W = sokak_genisligi(e.get("highway"), e.get("lanes"))
        print(f"  {s:.3f}  {str(e.get('highway'))[:14]:14s} W={W:4.1f}m  "
              f"{str(e.get('name'))[:30]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--R", type=float, nargs="+", default=[25.0])
    args = ap.parse_args()

    print(f"[graf] {GRAPH}")
    G = ox.load_graphml(GRAPH)
    _, edges = ox.graph_to_gdfs(G)
    edges = edges.to_crs(METRIC_CRS).reset_index()
    print(f"       {len(edges)} kenar")

    df = pd.read_csv(DAMAGE_CSV)
    etkili = df[df.damage_class.isin(SINIF_AGIRLIK) &
                (df.damage_class != "no-damage")].copy()
    print(f"[bina] {len(df)} toplam, {len(etkili)} etkili")

    bld = gpd.GeoDataFrame(
        etkili,
        geometry=etkili.footprint_wkt.apply(wkt.loads),
        crs="EPSG:4326",
    ).to_crs(METRIC_CRS)

    for R in args.R:
        rapor(hesapla(edges, bld, R), edges, R, len(edges))


if __name__ == "__main__":
    main()
