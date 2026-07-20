"""
Faz 1 — Gercek veri, Adim C: USGS fay rupturunu rotaya ENTEGRE et.

Sentetik dikdortgen yerine GERCEK USGS ruptur cizgilerini kullaniyoruz.
Cekirdek mantik ayni: bir bolge -> kesisen kenarlar -> closed -> A*.

IKI YENI KAVRAM:
  1. BUFFER: sifir genislikli ruptur cizgisini, metre cinsinden bir
     koridora (poligon) cevirmek. Koridora giren yollar closed olur.
  2. CRS: buffer'i METRE cinsinden yapabilmek icin geometriyi gecici
     olarak UTM'e (EPSG:32637, zone 37N) projekte ediyoruz. Derece
     cinsinden buffer yapmak yanlis olurdu.

Calistirma:
    cd ~/disaster-routing
    conda activate disaster
    python scripts/phase1_rupture_real.py
"""

import glob
import math
import osmnx as ox
import networkx as nx
import geopandas as gpd

# Faz 0'daki cekirdek — degismedi.
from phase0_routing import great_circle_heuristic, init_traversability, edge_cost

# ---------------------------------------------------------------------------
# Ayarlar
# ---------------------------------------------------------------------------
CENTER = (37.38, 36.87)       # Turkoglu — ruptur hattinin gectigi kasaba
DIST = 5000                          # graf yaricapi (metre)
BUFFER_M = 100                        # ruptur koridoru yari-genisligi (metre)
UTM = 32637                          # UTM zone 37N — bu bolge icin metrik CRS
GRAPH_CACHE = "data/graph_turkoglu.graphml"
OUT = "outputs/route_rupture_real.png"


def load_graph():
    import os
    if os.path.exists(GRAPH_CACHE):
        print(f"[graf] cache'ten: {GRAPH_CACHE}")
        return ox.load_graphml(GRAPH_CACHE)
    print(f"[graf] indiriliyor: {CENTER}, {DIST}m")
    G = ox.graph_from_point(CENTER, dist=DIST, network_type="drive")
    os.makedirs("data", exist_ok=True)
    ox.save_graphml(G, GRAPH_CACHE)
    return G


def load_rupture():
    cands = glob.glob("data/*.geojson") + glob.glob("data/*.json")
    if not cands:
        raise SystemExit("data/ icinde ruptur geojson bulunamadi.")
    print(f"[ruptur] okunuyor: {cands[0]}")
    return gpd.read_file(cands[0])


# ---------------------------------------------------------------------------
# Rupturu buffer'la ve kesisen kenarlari closed yap
# ---------------------------------------------------------------------------
def apply_rupture(G, rupture):
    # 1) Kenarlari GeoDataFrame'e cevir ve UTM'e projekte et (metrik).
    edges = ox.graph_to_gdfs(G, nodes=False).to_crs(UTM)

    # 2) Rupturu ayni UTM'e cevir, metre cinsinden buffer'la.
    rupture_utm = rupture.to_crs(UTM)
    #    .buffer(BUFFER_M) her cizgiyi koridora cevirir; union_all tek poligon yapar.
    #    (Eski geopandas surumunde union_all yerine .unary_union kullan.)
    corridor = rupture_utm.buffer(BUFFER_M).union_all()

    # 3) Koridora giren kenarlari bul ve closed yap.
    hit = edges[edges.intersects(corridor)]
    for (u, v, k) in hit.index:
        G[u][v][k]["traversability"] = "closed"
    print(f"[ruptur] closed olarak isaretlenen kenar: {len(hit)}")

    if len(hit) == 0:
        print("[UYARI] Hicbir kenar etkilenmedi. Ruptur bu grafla kesismiyor.")
        print("        CENTER'i ruptur hattina yaklastir ya da DIST'i buyut.")
        print("        (rupture_raw.png ile bolgeyi karsilastir.)")

    # Cizim icin koridoru 4326'ya geri cevir.
    corridor_4326 = gpd.GeoSeries([corridor], crs=UTM).to_crs(4326)
    return corridor_4326


# ---------------------------------------------------------------------------
# Ciz: graf + ruptur koridoru + rota
# ---------------------------------------------------------------------------
def plot_result(G, route, corridor_4326, out_path):
    fig, ax = ox.plot_graph_route(
        G, route, route_color="lime", route_linewidth=3,
        node_size=0, show=False, close=False,
    )
    corridor_4326.plot(ax=ax, color="red", alpha=0.4, zorder=1)
    ax.set_title("Faz 1 — gercek USGS ruptur (kirmizi=closed koridor)")
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"[ciz] kaydedildi: {out_path}")


def main():
    import os
    os.makedirs("outputs", exist_ok=True)

    G = load_graph()
    init_traversability(G)
    print(f"[graf] {len(G.nodes)} dugum, {len(G.edges)} kenar")

    rupture = load_rupture()
    corridor_4326 = apply_rupture(G, rupture)

    # Baslangic/bitis: bolgenin KD ve GB koselerine yakin iki dugum.
    # (Kosegen ruptur hattini kesme sansini artirir.)
    dlat = 0.6 * DIST / 111000.0
    dlon = 0.6 * DIST / (111000.0 * math.cos(math.radians(CENTER[0])))
    orig = ox.distance.nearest_nodes(G, X=CENTER[1] - dlon, Y=CENTER[0] + dlat)  # KB
    dest = ox.distance.nearest_nodes(G, X=CENTER[1] + dlon, Y=CENTER[0] - dlat)  # GD
    print(f"[dugum] orig={orig}, dest={dest}")

    try:
        route = nx.astar_path(
            G, orig, dest,
            heuristic=great_circle_heuristic(G),
            weight=edge_cost,
        )
        print("ROTA dugum sayisi:", len(route))
    except nx.NetworkXNoPath:
        print("YOL YOK — orig/dest arasi tum gecisler kapali olabilir.")
        return

    plot_result(G, route, corridor_4326, OUT)


if __name__ == "__main__":
    main()
