"""
Faz 1 + Faz 4 birlesik kosus — K-16 dogrulama ve rota karsilastirmasi.

NE YAPAR:
  1. Ham Turkoglu grafina Faz 1 katmanlarini uygular (ruptur=closed, likefikasyon=difficult)
  2. Faz 4 damage_pressure skorlarini bindirir (K-16: closed ezmez)
  3. K-16 ihlali var mi kontrol eder
  4. Birlesik grafta rota karsilastirmasi yapar

NEDEN VAR:
  Faz 4 Faz 1'in etiketini ezememeli (K-16 konservatif birlestirme). Bu script
  uc katmanin birlikte dogru calistigini kanitlar. Tezde "sistem uc hazard
  kaynagini birlestiriyor" iddiasinin somut kaniti.

NOT: LC_ALL=C ile calistirin.

KULLANIM:
  LC_ALL=C python scripts/phase4_integrated_run.py
"""

import sys
sys.path.insert(0, "scripts")

import osmnx as ox
from phase1_rupture_real import load_graph, load_rupture, apply_rupture
from phase1_liquefaction1 import (load_liquefaction_polygons,
                                   apply_liquefaction, THRESHOLD)
from phase4_route_compare import etiketle, rota

A, B = 2388129147, 10617812226   # Turkoglu SAPMA_KM senaryosu


def main():
    print("=== FAZ 1 + FAZ 4 BIRLESIK KOS ===\n")

    # 1) Ham grafi yukle
    G = load_graph()
    print("[graf]", G.number_of_edges(), "kenar\n")

    # 2) Faz 1a: ruptur -> closed
    rupture = load_rupture()
    apply_rupture(G, rupture)
    f1_closed = sum(1 for _, _, d in G.edges(data=True)
                    if d.get("traversability") == "closed")
    print(f"[Faz 1a] ruptur: {f1_closed} closed")

    # 3) Faz 1b: likefaksiyon -> difficult (closed ezmez)
    nodes, _ = ox.graph_to_gdfs(G)
    b = nodes.total_bounds
    polys, _ = load_liquefaction_polygons((b[0], b[1], b[2], b[3]), THRESHOLD)
    apply_liquefaction(G, polys)
    f1_diff = sum(1 for _, _, d in G.edges(data=True)
                  if d.get("traversability") == "difficult")
    print(f"[Faz 1b] likefaksiyon: {f1_closed} closed, {f1_diff} difficult")

    # 4) Faz 4: damage_pressure grafini yukle, Faz 1 etiketlerini aktar
    G4 = ox.load_graphml("data/graph_turkoglu_faz4.graphml")
    for u, v, k, d in G.edges(keys=True, data=True):
        t = d.get("traversability")
        if t and G4.has_edge(u, v, k):
            G4[u][v][k]["traversability"] = t

    # 5) Faz 4 etiketlerini uygula (K-16: closed ezmez)
    etiketle(G4, t_diff=0.20, t_closed=0.50)
    b4_closed = sum(1 for _, _, d in G4.edges(data=True)
                    if d.get("traversability") == "closed")
    b4_diff = sum(1 for _, _, d in G4.edges(data=True)
                  if d.get("traversability") == "difficult")
    print(f"\n[Birlesik] {b4_closed} closed, {b4_diff} difficult")
    print(f"  Faz 4 ekledi: +{b4_closed - f1_closed} closed, "
          f"+{b4_diff - f1_diff} difficult")

    # 6) K-16 dogrulama
    ihlal = 0
    for u, v, k, d in G.edges(keys=True, data=True):
        if d.get("traversability") == "closed" and G4.has_edge(u, v, k):
            if G4[u][v][k].get("traversability") != "closed":
                print(f"  K-16 IHLAL: {u}->{v}")
                ihlal += 1
    if ihlal == 0:
        print("[K-16] GECTI: Faz 1 closed kenarlarin hicbiri Faz 4 tarafindan "
              "ezilmedi")
    else:
        print(f"[K-16] {ihlal} IHLAL BULUNDU")

    # 7) Referans rota (sadece Faz 1)
    G_ref = load_graph()
    apply_rupture(G_ref, rupture)
    apply_liquefaction(G_ref, polys)
    for _, _, _, d in G_ref.edges(keys=True, data=True):
        if not d.get("traversability"):
            d["traversability"] = "passable"
    y_ref, L_ref = rota(G_ref, A, B)
    print(f"\n[Rota] Faz 1 only : "
          f"{'ULASILAMIYOR' if y_ref is None else str(round(L_ref)) + ' m'}")

    # 8) Birlesik rota (Faz 1 + Faz 4)
    y4, L4 = rota(G4, A, B)
    print(f"[Rota] Faz 1+4    : "
          f"{'ULASILAMIYOR' if y4 is None else str(round(L4)) + ' m'}")

    if y_ref and y4:
        print(f"  Faz 4 etkisi  : +{round(L4 - L_ref)} m ek sapma")


if __name__ == "__main__":
    main()
