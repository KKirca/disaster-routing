"""
Faz 0 — Uçtan uca en ince dilim (ML yok).

Amaç:
  1. Gerçek bir bölgenin yol grafını OSMnx ile çek.
  2. Iki nokta arasi A* calistir (once engelsiz).
  3. Her kenara 'traversability' arayuzunu tanimla (passable/difficult/closed).
  4. Elle bir engel koyup rerouting'i gozlemle.

Bu script'in asil degeri Adim 7-8: koprunun ileride dolduracagi
'traversability' sozlesmesini simdiden sabitliyoruz. Faz 1'de tek yapacagimiz
sey, elle atadigimiz 'closed' etiketini USGS katmanlarindan deterministik
uretmek olacak — sistemin geri kalani hic degismeyecek.

Calistirma:
    conda activate disaster
    unset PYTHONPATH        # (activate.d script'i kurduysan gerek yok)
    python phase0_routing.py
"""

import math
import networkx as nx
import osmnx as ox

# ---------------------------------------------------------------------------
# AYARLAR — burayi kendi bolgene/koordinatlarina gore degistir
# ---------------------------------------------------------------------------
# Merkez nokta (lat, lon). Ornek: Antakya merkez civari.
CENTER = (36.2028, 36.1608)

# Grafin yaricapi (metre). Kucuk basla; buyutmek her zaman kolay.
DIST = 2000

# Baslangic ve bitis koordinatlari (lat, lon).
# Ornek degerler — kendi depo -> hastane koordinatlarinla degistir.
ORIGIN_LATLON = (36.2090, 36.1520)
DEST_LATLON = (36.1960, 36.1700)

# 'difficult' kenarlar icin ceza katsayisi (yol uzunlugu ile carpilir).
DIFFICULT_PENALTY = 5.0

# Cikti dosyalari
GRAPH_CACHE = "data/graph.graphml"
OUT_BASELINE = "outputs/route_baseline.png"
OUT_BLOCKED = "outputs/route_blocked.png"


# ---------------------------------------------------------------------------
# Adim 2 — Grafi cek (varsa cache'ten oku, yoksa indir ve kaydet)
# ---------------------------------------------------------------------------
def load_graph():
    import os
    if os.path.exists(GRAPH_CACHE):
        print(f"[graf] cache'ten okunuyor: {GRAPH_CACHE}")
        return ox.load_graphml(GRAPH_CACHE)
    print(f"[graf] indiriliyor: merkez={CENTER}, dist={DIST}m")
    G = ox.graph_from_point(CENTER, dist=DIST, network_type="drive")
    os.makedirs("data", exist_ok=True)
    ox.save_graphml(G, GRAPH_CACHE)
    print(f"[graf] kaydedildi: {GRAPH_CACHE}")
    return G


# ---------------------------------------------------------------------------
# Adim 5 — A* icin cografi (great-circle) heuristik
# ---------------------------------------------------------------------------
def great_circle_heuristic(G):
    """Iki dugum arasi kus ucusu mesafeyi (metre) donduren fonksiyon uretir."""
    def h(u, v):
        y1, x1 = G.nodes[u]["y"], G.nodes[u]["x"]
        y2, x2 = G.nodes[v]["y"], G.nodes[v]["x"]
        # OSMnx yardimci fonksiyonu; sonuc metre cinsinden.
        return ox.distance.great_circle(y1, x1, y2, x2)
    return h


# ---------------------------------------------------------------------------
# Adim 7 — Traversability arayuzu (KOPRUNUN SOZLESMESI)
# ---------------------------------------------------------------------------
def init_traversability(G):
    """Her kenara varsayilan 'passable' etiketi ekler."""
    for u, v, k, data in G.edges(keys=True, data=True):
        data.setdefault("traversability", "passable")
    return G


def edge_cost(u, v, data):
    """
    Traversability etiketini A* maliyetine cevirir.
      passable  -> normal uzunluk
      difficult -> uzunluk * ceza
      closed    -> None (kenar graftan tamamen cikarilir)
    Coklu-kenar (MultiDiGraph) durumunda en dusuk maliyetli paraleli secer.
    """
    best = None
    for key, attrs in data.items():
        length = attrs.get("length", 1.0)
        state = attrs.get("traversability", "passable")
        if state == "closed":
            continue  # bu paralel kenar yok sayilir
        elif state == "difficult":
            cost = length * DIFFICULT_PENALTY
        else:  # passable
            cost = length
        best = cost if best is None else min(best, cost)
    # Tum paraleller kapali -> None. A* kenari graftan tamamen disar.
    # math.inf DONDURULMEZ: A* onu "cok pahali ama gecilebilir" sayar ve
    # baska yol yoksa kapali yoldan rota uretir (sessiz hata).
    return best


# ---------------------------------------------------------------------------
# Yardimci — rota bul ve ciz
# ---------------------------------------------------------------------------
def route_and_plot(G, orig, dest, out_path, title):
    try:
        route = nx.astar_path(
            G, orig, dest,
            heuristic=great_circle_heuristic(G),
            weight=edge_cost,
        )
    except nx.NetworkXNoPath:
        print(f"[rota] YOL YOK: {title}")
        return None
    fig, ax = ox.plot_graph_route(
        G, route, route_color="red", route_linewidth=3,
        node_size=0, show=False, close=False,
    )
    ax.set_title(title)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"[rota] cizildi: {out_path} ({len(route)} dugum)")
    return route


# ---------------------------------------------------------------------------
# Ana akis
# ---------------------------------------------------------------------------
def main():
    import os
    os.makedirs("outputs", exist_ok=True)

    # Adim 2-3
    G = load_graph()
    print(f"[graf] {len(G.nodes)} dugum, {len(G.edges)} kenar")

    # Adim 4 — baslangic/bitis dugumleri
    orig = ox.distance.nearest_nodes(G, X=ORIGIN_LATLON[1], Y=ORIGIN_LATLON[0])
    dest = ox.distance.nearest_nodes(G, X=DEST_LATLON[1], Y=DEST_LATLON[0])
    print(f"[dugum] orig={orig}, dest={dest}")

    # Adim 7 — arayuzu kur (hepsi passable)
    init_traversability(G)

    # Adim 5-6 — engelsiz baseline rota
    route = route_and_plot(G, orig, dest, OUT_BASELINE, "Baseline (engelsiz)")
    if route is None:
        print("Baseline rota bulunamadi — koordinatlari kontrol et.")
        return

    # Adim 8 — rotanin ortasindaki bir kenari KAPAT, tekrar cizdir
    mid = route[len(route) // 2]
    nxt = route[len(route) // 2 + 1]
    for k in G[mid][nxt]:
        G[mid][nxt][k]["traversability"] = "closed"
    print(f"[engel] kenar KAPATILDI: {mid} -> {nxt}")

    route2 = route_and_plot(
        G, orig, dest, OUT_BLOCKED, "Engel sonrasi (rerouting)"
    )
    if route2 is None:
        print("[engel] Kapatilan kenar tek gecisti — reroute yapilamadi.")
    elif route2 == route:
        print("[engel] Rota degismedi (beklenmedik).")
    else:
        print("[engel] Rota kendini yeniden yonlendirdi. ✓")


if __name__ == "__main__":
    main()