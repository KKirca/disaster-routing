"""
Faz 4 — Adim 4: damage_pressure skorunu grafa yaz.

NE YAPAR:
  K-19 formuluyle her kenar icin skoru hesaplar ve graf kenar oznitelgi
  olarak yazar. Skoru olmayan kenarlara 0.0 yazilir.

NE YAPMAZ:
  traversability URETMEZ. Esikler (K-15'teki 0.30/0.70) henuz gecicidir ve
  Adim 6'da rota karsilastirmasiyla belirlenecektir. Esigi simdi sabitleyip
  sonucuna bakmak dongusel gerekcelendirme olurdu.

R = 25 m gerekcesi (K-19'a eklenecek):
  Devrilen duvar kabaca kendi yuksekligi kadar mesafeye duser. Bu bolgedeki
  tipik yapi stoku 3-6 kat = 10-20 m; moloz sacilmasiyla etkili mesafe 20-30 m
  araligina oturur. 25 m bu araligin ortasidir. 40 m ancak 12+ katli bloklar
  icin savunulabilir, bu sette medyan taban alani 199 m2 ile boyle bir doku yok.
  15 m'de hicbir kenar 0.70'i asmiyor — iki destroyed bina bile yol kapatamiyor.

NOT: LC_ALL=C ile calistirin.

KULLANIM:
  LC_ALL=C python scripts/phase4_apply_to_graph.py
"""

import sys
sys.path.insert(0, "scripts")   # proje kokunden calistirilir; veri yollari
                                # ('data/...') koke goreli oldugu icin cd
                                # scripts YAPILMAZ.

import geopandas as gpd
import networkx as nx
import numpy as np
import osmnx as ox
import pandas as pd
from shapely import wkt

from phase4_damage_pressure import (DAMAGE_CSV, GRAPH, METRIC_CRS,
                                    SINIF_AGIRLIK, hesapla)

R = 25.0
OUT_GRAPH = "data/mexico_city_graph_faz4.graphml"


def main():
    print(f"[graf] {GRAPH}")
    G = ox.load_graphml(GRAPH)
    _, edges = ox.graph_to_gdfs(G)
    edges = edges.to_crs(METRIC_CRS).reset_index()
    print(f"       {len(edges)} kenar")

    df = pd.read_csv(DAMAGE_CSV)
    etkili = df[df.damage_class.isin(SINIF_AGIRLIK) &
                (df.damage_class != "no-damage")].copy()
    bld = gpd.GeoDataFrame(
        etkili,
        geometry=etkili.footprint_wkt.apply(wkt.loads),
        crs="EPSG:4326",
    ).to_crs(METRIC_CRS)
    print(f"[bina] {len(etkili)} etkili bina, R = {R:.0f} m")

    skorlar = hesapla(edges, bld, R)
    print(f"[skor] {len(skorlar)} kenar etkilendi")

    # Once tum kenarlara 0.0, sonra hesaplananlari yaz
    nx.set_edge_attributes(G, 0.0, "damage_pressure")
    yazilan = 0
    for i, s in skorlar.items():
        row = edges.iloc[i]
        u, v, k = row["u"], row["v"], row["key"]
        if G.has_edge(u, v, k):
            G[u][v][k]["damage_pressure"] = round(float(s), 4)
            yazilan += 1

    print(f"[yaz]  {yazilan}/{len(skorlar)} kenara yazildi")

    ox.save_graphml(G, OUT_GRAPH)
    print(f"[kayit] {OUT_GRAPH}")

    # Dogrulama: geri oku
    G2 = ox.load_graphml(OUT_GRAPH)
    vals = [float(d.get("damage_pressure", 0))
            for _, _, d in G2.edges(data=True)]
    nz = [v for v in vals if v > 0]
    print(f"\n[dogrulama] geri okundu: {len(vals)} kenar, "
          f"{len(nz)} tanesi sifirdan buyuk")
    if nz:
        print(f"            max {max(nz):.3f}  medyan {np.median(nz):.3f}")


if __name__ == "__main__":
    main()
