"""
Faz 1 TAMAMLAMA — Kademe 1'in iki katmani birlikte:
  - Fay rupturu  -> closed    (vektor, onceki script'ten)
  - Likefaksiyon -> difficult (raster, bu script'in yeni kismi)

UC YENI ISLEM (likefaksiyon icin):
  1. Pencereli okuma: devasa rasterin sadece graf alanini oku.
  2. Esikleme: olasilik > THRESHOLD olan hucreler 'riskli' (maske).
  3. Poligonlastirma: bitisik riskli hucreleri poligona cevir.

Sonra bu poligonlara giren yollari difficult yapiyoruz — ama closed
olanlari EZMEDEN (ruptur daha ciddi).

Calistirma:
    cd ~/disaster-routing
    conda activate disaster
    python scripts/phase1_liquefaction.py
"""

import os
import glob
import math
import numpy as np
import osmnx as ox
import networkx as nx
import geopandas as gpd
import rasterio
from rasterio.features import shapes
from rasterio.windows import from_bounds
from shapely.geometry import shape
from shapely.ops import unary_union

# Faz 0 cekirdegi
from phase0_routing import great_circle_heuristic, init_traversability, edge_cost
# Onceki script'ten graf yukleyici + ruptur mantigi (ayni Turkoglu bolgesi)
from phase1_rupture_real import load_graph, load_rupture, apply_rupture, CENTER, DIST

# Likefaksiyon esigi. Veri araligi 0–0.42 idi; 0.05 orta+yuksek riski yakalar.
# 0 poligon cikarsa DUSUR, cok genis alan cikarsa YUKSELT.
THRESHOLD = 0.10  # K-22: 0.05'ten 0.10'a revize edildi.
# Veri araligi 0-0.394; 0.05 grafin %34.9'unu difficult yapiyordu (fazla genis).
# 0.10 ile %25.1'e dusuyor — orta+yuksek riski yakalayip dusuk riski disarda birakir.
# Likefaksiyon fizigi: gevşek+suya_doygun zemin + yeterli sarsinti gerektirir;
# dusuk olasilikli hucreler bu kosulun tam saglanmadigi alanlari temsil eder.

OUT = "outputs/route_kademe1.png"


# Likefaksiyon: raster -> esik -> poligonlar
def load_liquefaction_polygons(graph_bounds, threshold):
    tifs = glob.glob("data/*.tif") + glob.glob("data/*.tiff")
    if not tifs:
        raise SystemExit("data/ icinde likefaksiyon .tif yok.")
    liq = [t for t in tifs if "liq" in t.lower() or "zhu" in t.lower()]
    path = liq[0] if liq else tifs[0]

    with rasterio.open(path) as src:
        minx, miny, maxx, maxy = graph_bounds
        # 1) PENCERELI OKUMA: sadece graf alanina denk gelen bolgeyi oku.
        window = from_bounds(minx, miny, maxx, maxy, src.transform)
        band = src.read(1, window=window)
        transform = src.window_transform(window)  # bu pencerenin geo-donusumu

    # 2) ESIKLEME: NaN'lari 0 yap, esigi gecenler True.
    band = np.nan_to_num(band, nan=0.0)
    mask = band >= threshold
    print(f"[likef] pencere boyutu: {band.shape}, riskli hucre: {int(mask.sum())}")

    # 3) POLIGONLASTIRMA: bitisik True hucreler tek poligon olur.
    polys = [shape(geom) for geom, val in
             shapes(mask.astype("uint8"), mask=mask, transform=transform)]
    return polys, path


def apply_liquefaction(G, polys):
    if not polys:
        print("[likef] esigi gecen bolge yok — THRESHOLD'u dusur.")
        return None
    edges = ox.graph_to_gdfs(G, nodes=False)
    zone = unary_union(polys)
    hit = edges[edges.intersects(zone)]
    count = 0
    for (u, v, k) in hit.index:
        # closed'u EZME — ruptur daha ciddi.
        if G[u][v][k].get("traversability") != "closed":
            G[u][v][k]["traversability"] = "difficult"
            count += 1
    print(f"[likef] difficult yapilan kenar: {count} (esik={THRESHOLD})")
    return gpd.GeoSeries([zone], crs=4326)


# Ciz: graf + ruptur (kirmizi) + likefaksiyon (turuncu) + rota (yesil)
def plot_all(G, route, corridor_4326, liq_zone, out):
    fig, ax = ox.plot_graph_route(
        G, route, route_color="lime", route_linewidth=3,
        node_size=0, show=False, close=False,
    )
    if corridor_4326 is not None:
        corridor_4326.plot(ax=ax, color="red", alpha=0.4, zorder=1)
    if liq_zone is not None:
        liq_zone.plot(ax=ax, color="orange", alpha=0.4, zorder=1)
    ax.set_title("Faz 1 Kademe 1 — kirmizi=ruptur(closed), turuncu=likefaksiyon(difficult)")
    fig.savefig(out, dpi=150, bbox_inches="tight")
    print(f"[ciz] kaydedildi: {out}")


def main():
    os.makedirs("outputs", exist_ok=True)

    G = load_graph()
    init_traversability(G)
    print(f"[graf] {len(G.nodes)} dugum, {len(G.edges)} kenar")

    # --- Kademe 1a: ruptur -> closed ---
    rupture = load_rupture()
    corridor_4326 = apply_rupture(G, rupture)

    # --- Kademe 1b: likefaksiyon -> difficult ---
    # Graf sinirlarini bul (raster penceresi icin), kucuk pay ekle.
    nodes = ox.graph_to_gdfs(G, edges=False)
    b = nodes.total_bounds  # (minx, miny, maxx, maxy)
    m = 0.01
    graph_bounds = (b[0] - m, b[1] - m, b[2] + m, b[3] + m)
    polys, path = load_liquefaction_polygons(graph_bounds, THRESHOLD)
    print(f"[likef] uretilen poligon: {len(polys)} (dosya: {path})")
    liq_zone = apply_liquefaction(G, polys)

    # --- orig/dest: kosegen (KB -> GD) ---
    dlat = 0.6 * DIST / 111000.0
    dlon = 0.6 * DIST / (111000.0 * math.cos(math.radians(CENTER[0])))
    orig = ox.distance.nearest_nodes(G, X=CENTER[1] - dlon, Y=CENTER[0] + dlat)
    dest = ox.distance.nearest_nodes(G, X=CENTER[1] + dlon, Y=CENTER[0] - dlat)

    try:
        route = nx.astar_path(
            G, orig, dest,
            heuristic=great_circle_heuristic(G),
            weight=edge_cost,
        )
        print("ROTA dugum sayisi:", len(route))
    except nx.NetworkXNoPath:
        print("YOL YOK.")
        return

    plot_all(G, route, corridor_4326, liq_zone, OUT)


if __name__ == "__main__":
    main()