"""
Faz 4 negatif kontrol: Kilis (buyuk olcude hasarsiz varsayilan kent) uzerinde zincir.

SORU: Model 2 + Faz 4, gorsel olarak saglam bir kentte kac kenari kapatiyor ve
kac yolculugu uzatiyor? Bu bir SAHTE POZITIF UST SINIRIDIR, dogruluk iddiasi degil.
Ground truth yok; hasarsiz varsayimi iki onizleme ve ornek sayfasina dayanir.

Birden fazla CSV verilirse (ham / sigma-eslemeli) yan yana karsilastirilir.

KULLANIM:
  LC_ALL=C python scripts/phase4_negatif_kontrol.py --csv outputs/phase3i_kilis_k18.csv
  LC_ALL=C python scripts/phase4_negatif_kontrol.py --csv A.csv B.csv
"""
import argparse
import os
import random
import sys

import geopandas as gpd
import networkx as nx
import numpy as np
import osmnx as ox
import pandas as pd
from shapely import wkt

sys.path.insert(0, "scripts")
from phase4_damage_pressure import SINIF_AGIRLIK, hesapla
from phase4_route_compare import etiketle, rota, say

GRAF = "data/graph_kilis.graphml"
MERKEZ = (36.719, 37.117)          # (lat, lon)
DIST = 2500                        # m, graph_from_point yarim kenar
METRIC_CRS = "EPSG:32637"          # UTM 37N
R = 25.0                           # K-19
ESIKLER = [(0.20, 0.50), (0.30, 0.70), (0.40, 0.80)]   # (t_diff, t_closed)
N_CIFT = 300
MIN_MESAFE = 1000.0                # m, kus ucusu


def csv_bbox(dosyalar):
    df = pd.concat([pd.read_csv(f, usecols=["lon", "lat"]) for f in dosyalar])
    return df.lon.min(), df.lat.min(), df.lon.max(), df.lat.max()


def graf_yukle(bbox):
    if os.path.exists(GRAF):
        G = ox.load_graphml(GRAF)
    else:
        G = ox.graph_from_point(MERKEZ, dist=DIST, network_type="drive")
        ox.save_graphml(G, GRAF)
        print("[graf] indirildi ve kaydedildi:", GRAF)
    lon0, lat0, lon1, lat1 = bbox
    ic = [n for n, d in G.nodes(data=True)
          if lon0 <= float(d["x"]) <= lon1 and lat0 <= float(d["y"]) <= lat1]
    H = G.subgraph(ic).copy()
    en_buyuk = max(nx.strongly_connected_components(H), key=len)
    return H.subgraph(en_buyuk).copy()


def skorla(G, csv_yolu):
    """damage_pressure i grafa yazar. Donus: (df, etkili_bina, etkilenen_kenar)."""
    _, edges = ox.graph_to_gdfs(G)
    edges = edges.to_crs(METRIC_CRS).reset_index()
    df = pd.read_csv(csv_yolu)
    etkili = df[df.damage_class.isin(SINIF_AGIRLIK) &
                (df.damage_class != "no-damage")].copy()
    bld = gpd.GeoDataFrame(etkili, geometry=etkili.footprint_wkt.apply(wkt.loads),
                           crs="EPSG:4326").to_crs(METRIC_CRS)
    skorlar = hesapla(edges, bld, R)
    nx.set_edge_attributes(G, 0.0, "damage_pressure")
    for i, s in skorlar.items():
        r = edges.iloc[i]
        u, v, k = r["u"], r["v"], r["key"]
        if G.has_edge(u, v, k):
            G[u][v][k]["damage_pressure"] = float(s)
    return df, len(etkili), len(skorlar)


def cift_sec(G, n, min_mesafe):
    dugumler = list(G.nodes)
    rng = random.Random(42)
    ciftler, deneme = [], 0
    while len(ciftler) < n and deneme < 200000:
        deneme += 1
        a, b = rng.sample(dugumler, 2)
        dx = (float(G.nodes[a]["x"]) - float(G.nodes[b]["x"])) * 89000.0
        dy = (float(G.nodes[a]["y"]) - float(G.nodes[b]["y"])) * 111000.0
        if (dx * dx + dy * dy) ** 0.5 >= min_mesafe:
            ciftler.append((a, b))
    return ciftler


def sifirla(G):
    for _, _, _, d in G.edges(keys=True, data=True):
        d.pop("traversability", None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", nargs="+", required=True)
    args = ap.parse_args()

    bbox = csv_bbox(args.csv)
    print("[bbox] lon %.4f..%.4f  lat %.4f..%.4f" % (bbox[0], bbox[2], bbox[1], bbox[3]))
    G = graf_yukle(bbox)
    n_kenar = G.number_of_edges()
    print("[graf] %d dugum, %d kenar (en buyuk guclu bilesen)" % (G.number_of_nodes(), n_kenar))

    ciftler = cift_sec(G, N_CIFT, MIN_MESAFE)
    for _, _, _, d in G.edges(keys=True, data=True):
        d["traversability"] = "passable"
    ref = {c: rota(G, *c)[1] for c in ciftler}
    gecerli = [c for c in ciftler if ref[c] is not None]
    print("[yolculuk] %d gecerli cift (>= %.0f m)\n" % (len(gecerli), MIN_MESAFE))

    for csv_yolu in args.csv:
        print("=" * 72)
        print(csv_yolu)
        print("=" * 72)
        df, n_etkili, n_etkilenen = skorla(G, csv_yolu)
        sayac = df.damage_class.value_counts()
        print("  bina: " + ", ".join("%s=%d" % (k, v) for k, v in sayac.items()))
        print("  hasarli (etkili) bina %d, skor alan kenar %d/%d\n" % (n_etkili, n_etkilenen, n_kenar))
        print("  %6s %8s %8s %7s %12s %8s %11s %8s" % (
            "t_diff", "t_closed", "closed%", "diff%", "ulasilamaz%",
            "sapan%", "medyan_ek%", "p95_ek%"))
        for td, tc in ESIKLER:
            sifirla(G)
            etiketle(G, td, tc)
            nc, nd = say(G)
            yok = sapan = 0
            ekler = []
            for c in gecerli:
                yol, L = rota(G, *c)
                if yol is None:
                    yok += 1
                elif L - ref[c] > 1:
                    sapan += 1
                    ekler.append(100.0 * (L - ref[c]) / ref[c])
            m = len(gecerli)
            med = float(np.median(ekler)) if ekler else 0.0
            p95 = float(np.percentile(ekler, 95)) if ekler else 0.0
            print("  %6.2f %8.2f %8.2f %7.2f %12.1f %8.1f %11.1f %8.1f" % (
                td, tc, 100 * nc / n_kenar, 100 * nd / n_kenar,
                100 * yok / m, 100 * sapan / m, med, p95))
        print()

    print("Not: bu bolge ground truth olmadan buyuk olcude hasarsiz varsayiliyor.")
    print("closed ve sapan yuzdeleri sahte pozitif UST SINIRI olarak okunmali, dogruluk olarak degil.")


if __name__ == "__main__":
    main()
