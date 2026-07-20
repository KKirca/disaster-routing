"""
Faz 1 — Kademe 1: Deterministik tehlike katmanindan traversability.

FIKIR: Faz 0'da engeli ELLE koymustuk. Simdi ayni engeli, cografi bir
"tehlike bolgesi" (hazard zone) poligonundan OTOMATIK uretiyoruz.
Rota cekirdegi (A*, edge_cost, heuristik) HIC DEGISMIYOR — sadece
traversability etiketinin KAYNAGI degisiyor.

Bu Faz'da tehlike poligonu hala SENTETIK (elle cizilmis dikdortgen).
Faz 1'in ikinci adiminda bunu gercek USGS fay rupturu / likefaksiyon
verisiyle degistirecegiz — mekanizma ayni kalacak.

Iki tehlike tipi:
  - Fault rupture (yuzey kirilmasi)  -> yol fiziksel kopar -> "closed"
  - Liquefaction (sivilasma)         -> yol riskli ama gecebilir -> "difficult"

Calistirma (Faz 0 ile ayni dizinden):
    cd ~/disaster-routing
    conda activate disaster
    python scripts/phase1_hazard.py
"""

import osmnx as ox
import networkx as nx
from shapely.geometry import box

# Faz 0'daki cekirdek fonksiyonlari YENIDEN KULLANIYORUZ — yeniden yazmiyoruz.
# (phase0_routing.py ayni scripts/ klasorunde oldugu icin import calisir.)
from phase0_routing import (
    load_graph,
    great_circle_heuristic,
    init_traversability,
    edge_cost,
    ORIGIN_LATLON,
    DEST_LATLON,
)

OUT_HAZARDS = "outputs/route_hazards.png"


# ---------------------------------------------------------------------------
# 1) Sentetik tehlike bolgeleri
# ---------------------------------------------------------------------------
def make_synthetic_hazards():
    """
    Elle cizilmis tehlike poligonlari donduren fonksiyon.
    shapely box(minx, miny, maxx, maxy) = (lon_bati, lat_guney, lon_dogu, lat_kuzey)
    NOT: koordinatlar lon(x)/lat(y) sirasinda — enlem/boylam degil, boylam/enlem!

    Bu koordinatlar Antakya ornek bolgesine gore kabaca secildi.
    Haritada rotayla kesismezlerse (asagida "0 kenar etkilendi" cikarsa),
    poligonlari rotanin ustune gelecek sekilde kaydir.
    """
    # Fault rupture serit (closed) — haritanin ortasindan gecen ince bant
    rupture = box(36.156, 36.199, 36.164, 36.204)
    # Liquefaction alan (difficult) — hedefe giden yol uzerinde genis bolge
    liquefaction = box(36.162, 36.196, 36.172, 36.201)
    return {"closed": [rupture], "difficult": [liquefaction]}


# ---------------------------------------------------------------------------
# 2) Tehlike poligonlarini yol grafiyla KESISTIR (bu fazin yeni teknigi)
# ---------------------------------------------------------------------------
def apply_hazards(G, hazards):
    """
    Her tehlike poligonunu grafin kenarlariyla kesistirir; kesisen kenarlara
    ilgili traversability etiketini atar.

    Onem sirasi: once 'difficult', sonra 'closed' uygulanir. Boylece bir kenar
    hem likefaksiyon hem ruptur icindeyse, 'closed' ustune yazar (daha ciddi).
    """
    # Kenarlari GeoDataFrame'e cevir: her kenar bir LineString geometrisi olur.
    # nodes=False -> sadece kenarlari istiyoruz.
    edges = ox.graph_to_gdfs(G, nodes=False)

    for severity in ["difficult", "closed"]:
        for poly in hazards.get(severity, []):
            # .intersects(poly) -> her kenar icin True/False (poligona degiyor mu?)
            hit = edges[edges.intersects(poly)]
            # GeoDataFrame'in indeksi (u, v, key) uclusu — kenari tanimlayan anahtar.
            for (u, v, k) in hit.index:
                G[u][v][k]["traversability"] = severity
            print(f"[hazard] {severity}: {len(hit)} kenar etkilendi")
    return G


# ---------------------------------------------------------------------------
# 3) Ciz: rota + tehlike bolgelerini ustte goster
# ---------------------------------------------------------------------------
def plot_with_hazards(G, route, hazards, out_path):
    fig, ax = ox.plot_graph_route(
        G, route, route_color="red", route_linewidth=3,
        node_size=0, show=False, close=False,
    )
    # Poligonlari yari saydam ciz. exterior.xy -> (lon listesi, lat listesi)
    for poly in hazards.get("closed", []):
        xs, ys = poly.exterior.xy
        ax.fill(xs, ys, alpha=0.35, color="red", zorder=1)
    for poly in hazards.get("difficult", []):
        xs, ys = poly.exterior.xy
        ax.fill(xs, ys, alpha=0.35, color="orange", zorder=1)
    ax.set_title("Faz 1 — tehlike katmani (kirmizi=closed, turuncu=difficult)")
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"[ciz] kaydedildi: {out_path}")


# ---------------------------------------------------------------------------
# Ana akis
# ---------------------------------------------------------------------------
def main():
    import os
    os.makedirs("outputs", exist_ok=True)

    # Faz 0'daki grafi cache'ten yukle (yeniden indirmez)
    G = load_graph()
    init_traversability(G)  # hepsi passable ile basla

    orig = ox.distance.nearest_nodes(G, X=ORIGIN_LATLON[1], Y=ORIGIN_LATLON[0])
    dest = ox.distance.nearest_nodes(G, X=DEST_LATLON[1], Y=DEST_LATLON[0])

    # --- FAZ 0'DAN FARK: elle engel YOK. Engel tehlike katmanindan geliyor. ---
    hazards = make_synthetic_hazards()
    apply_hazards(G, hazards)

    # A* cagrisi Faz 0 ile BIREBIR AYNI — cekirdek degismedi.
    try:
        route = nx.astar_path(
            G, orig, dest,
            heuristic=great_circle_heuristic(G),
            weight=edge_cost,
        )
    except nx.NetworkXNoPath:
        print("YOL YOK — tehlike bolgeleri tum gecisleri kapatmis olabilir.")
        return

    print("ROTA dugum sayisi:", len(route))
    plot_with_hazards(G, route, hazards, OUT_HAZARDS)


if __name__ == "__main__":
    main()