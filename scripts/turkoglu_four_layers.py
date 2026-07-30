"""
Faz 2 KAPANIS — Turkoglu dort katman haritasi.

Dort bagimsiz kaynagi tek haritada ust uste bindirip cografi hizalanmayi
dogruluyoruz:
  1. OSM yol grafi        (OSMnx)        -> gri
  2. USGS fay rupturu     (vektor)       -> kirmizi koridor, closed
  3. USGS likefaksiyon    (raster)       -> turuncu alan, difficult
  4. Copernicus EMSR648   (vektor)       -> bina bloklari, hasar rengine gore

Ayrica kucuk bir FAZ 4 ONIZLEMESI: hasarli bloklarin kac yol segmentine
komsu oldugunu sayiyoruz. Koprunun tuketecegi iliski tam da bu.

Calistirma:
    cd ~/disaster-routing
    conda activate disaster
    python scripts/turkoglu_four_layers.py
"""

import glob
import math
import os

import geopandas as gpd
import matplotlib.pyplot as plt
import networkx as nx
import osmnx as ox
from matplotlib.patches import Patch

from phase0_routing import great_circle_heuristic, init_traversability, edge_cost
from phase1_rupture_real import load_graph, load_rupture, apply_rupture, CENTER, DIST

# Likefaksiyon fonksiyonlari — dosya adi phase1_liquefaction1.py olabilir.
try:
    from phase1_liquefaction1 import load_liquefaction_polygons, apply_liquefaction
except ImportError:
    from phase1_liquefaction import load_liquefaction_polygons, apply_liquefaction

UTM = 32637
THRESHOLD = 0.05          # likefaksiyon esigi
NEAR_M = 30               # "yola komsu" sayilma mesafesi (metre)
OUT = "outputs/turkoglu_four_layers.png"

# Hasar kategorisi -> renk (EMSR648 damage_gra degerleri)
DMG_COLORS = {
    "Destroyed": "#B00020",
    "Damaged": "#E8593C",
    "Possibly damaged": "#EF9F27",
}


def load_emsr648_buildings():
    """AOI17 (Turkoglu) bina bloklarini yukler."""
    cands = glob.glob("data/emsr648/**/*AOI17*builtUpA*.shp", recursive=True)
    if not cands:
        raise SystemExit("AOI17 builtUpA shapefile bulunamadi (data/emsr648/).")
    gdf = gpd.read_file(cands[0])
    print(f"[emsr] okundu: {os.path.basename(cands[0])} — {len(gdf)} blok")
    return gdf


def proximity_preview(G, damaged):
    """FAZ 4 ONIZLEMESI: hasarli bloklara NEAR_M icinde kac yol segmenti var?"""
    edges = ox.graph_to_gdfs(G, nodes=False).to_crs(UTM)
    blocks = damaged.to_crs(UTM)
    zone = blocks.buffer(NEAR_M).union_all()
    near = edges[edges.intersects(zone)]
    print(f"\n[FAZ4 onizleme] hasarli blok: {len(blocks)}")
    print(f"[FAZ4 onizleme] bu bloklara {NEAR_M} m icinde olan yol segmenti: {len(near)}")
    print(f"[FAZ4 onizleme] grafin toplam kenar sayisi: {len(edges)}")
    print("                (koprü ileride bu iliskiyi moloz genisligine cevirecek)")
    return near


def main():
    os.makedirs("outputs", exist_ok=True)

    # --- Katman 1: yol grafi ---
    G = load_graph()
    init_traversability(G)
    print(f"[graf] {len(G.nodes)} dugum, {len(G.edges)} kenar")

    # --- Katman 2: fay rupturu -> closed ---
    rupture = load_rupture()
    corridor = apply_rupture(G, rupture)

    # --- Katman 3: likefaksiyon -> difficult ---
    nodes = ox.graph_to_gdfs(G, edges=False)
    b = nodes.total_bounds
    m = 0.01
    polys, _ = load_liquefaction_polygons((b[0] - m, b[1] - m, b[2] + m, b[3] + m),
                                          THRESHOLD)
    liq_zone = apply_liquefaction(G, polys)

    # --- Katman 4: EMSR648 bina hasari ---
    buildings = load_emsr648_buildings()
    damaged = buildings[buildings["damage_gra"].isin(DMG_COLORS.keys())]
    print(f"[emsr] hasarli blok dagilimi: {dict(damaged['damage_gra'].value_counts())}")

    # Hizalama kontrolu — iki veri ayni yerde mi?
    print(f"\n[hizalama] graf sinirlari : {[round(v, 4) for v in b]}")
    print(f"[hizalama] EMSR sinirlari : {[round(v, 4) for v in buildings.total_bounds]}")

    # --- Rota ---
    dlat = 0.6 * DIST / 111000.0
    dlon = 0.6 * DIST / (111000.0 * math.cos(math.radians(CENTER[0])))
    orig = ox.distance.nearest_nodes(G, X=CENTER[1] - dlon, Y=CENTER[0] + dlat)
    dest = ox.distance.nearest_nodes(G, X=CENTER[1] + dlon, Y=CENTER[0] - dlat)
    try:
        route = nx.astar_path(G, orig, dest,
                              heuristic=great_circle_heuristic(G), weight=edge_cost)
        print(f"\n[rota] {len(route)} dugum")
    except nx.NetworkXNoPath:
        route = None
        print("\n[rota] YOL YOK")

    # --- Faz 4 onizlemesi ---
    proximity_preview(G, damaged)

    # --- Cizim ---
    if route:
        fig, ax = ox.plot_graph_route(G, route, route_color="lime", route_linewidth=2.5,
                                      node_size=0, show=False, close=False)
    else:
        fig, ax = ox.plot_graph(G, node_size=0, show=False, close=False)

    if liq_zone is not None:
        liq_zone.plot(ax=ax, color="orange", alpha=0.22, zorder=1)
    if corridor is not None:
        corridor.plot(ax=ax, color="red", alpha=0.35, zorder=2)

    for grade, color in DMG_COLORS.items():
        sel = damaged[damaged["damage_gra"] == grade]
        if len(sel):
            sel.plot(ax=ax, color=color, alpha=0.9, edgecolor=color,
                     linewidth=0.4, zorder=4)

    # Graf sinirlarina kirp (EMSR daha genis olabilir)
    ax.set_xlim(b[0], b[2])
    ax.set_ylim(b[1], b[3])

    legend = [
        Patch(facecolor="red", alpha=0.35, label="USGS fay rupturu (closed)"),
        Patch(facecolor="orange", alpha=0.22, label="USGS likefaksiyon (difficult)"),
        Patch(facecolor=DMG_COLORS["Destroyed"], label="EMSR648: Destroyed"),
        Patch(facecolor=DMG_COLORS["Damaged"], label="EMSR648: Damaged"),
        Patch(facecolor=DMG_COLORS["Possibly damaged"], label="EMSR648: Possibly damaged"),
        Patch(facecolor="lime", label="A* rotasi"),
    ]
    ax.legend(handles=legend, loc="lower left", fontsize=7, framealpha=0.85)
    ax.set_title("Turkoglu — dort katman: OSM + USGS ruptur + likefaksiyon + EMSR648")

    fig.savefig(OUT, dpi=160, bbox_inches="tight")
    print(f"\n[ciz] kaydedildi: {OUT}")


if __name__ == "__main__":
    main()