"""
Faz 1 dogrulama — edge_cost sozlesmesi ve A* kapali yol davranisi.

NEDEN VAR:
  edge_cost eskiden kapali kenar icin math.inf donduruyordu. NetworkX A*
  agirlik fonksiyonu inf dondururse kenari GECERLI sayar, sadece pahali
  bulur. Sonuc: hedefe giden tum yollar kapaliysa A* kapali yoldan gecen
  bir rota uretir ve dondurur. Sistem hata vermez, sessizce yanlis cevap
  verir. Bu, acil durum aracini enkaza yollamak demektir.

  Duzeltme: kapali kenar icin None dondurulur. A* None goren kenari
  graftan tamamen disar; hic yol yoksa NetworkXNoPath firlatir.

KULLANIM:
  cd ~/disaster-routing
  python scripts/verify_phase1.py
"""

import sys
import networkx as nx

sys.path.insert(0, "scripts")
from phase0_routing import DIFFICULT_PENALTY, edge_cost  # noqa: E402

FAIL = []


def check(name, cond, detail=""):
    if cond:
        print(f"  [GECTI] {name}")
    else:
        print(f"  [KALDI] {name}   {detail}")
        FAIL.append(name)


def md(*edges):
    """Tek u-v cifti icin MultiDiGraph veri sozlugu uretir."""
    return {i: dict(length=L, traversability=s) for i, (L, s) in enumerate(edges)}


print("\n[1] edge_cost sozlesmesi — tekil kenar")
check("passable  -> uzunluk",
      edge_cost(0, 1, md((100.0, "passable"))) == 100.0)
check("difficult -> uzunluk * ceza",
      edge_cost(0, 1, md((100.0, "difficult"))) == 100.0 * DIFFICULT_PENALTY)
c = edge_cost(0, 1, md((100.0, "closed")))
check("closed    -> None (inf DEGIL)", c is None, f"donen: {c!r}")
check("etiketsiz kenar passable sayilir",
      edge_cost(0, 1, {0: dict(length=42.0)}) == 42.0)

print("\n[2] edge_cost — coklu paralel kenar")
check("kapali + acik  -> acik olanin maliyeti",
      edge_cost(0, 1, md((50.0, "closed"), (80.0, "passable"))) == 80.0)
c = edge_cost(0, 1, md((50.0, "closed"), (80.0, "closed")))
check("tum paraleller kapali -> None", c is None, f"donen: {c!r}")
check("iki acik paralel -> ucuz olan",
      edge_cost(0, 1, md((90.0, "passable"), (40.0, "passable"))) == 40.0)
check("difficult vs uzun passable -> ucuz olan secilir",
      edge_cost(0, 1, md((10.0, "difficult"), (100.0, "passable")))
      == min(10.0 * DIFFICULT_PENALTY, 100.0))

print("\n[3] A* entegrasyonu — asil regresyon testi")
G = nx.MultiDiGraph()
G.add_edge("A", "C", length=100.0, traversability="closed")
G.add_edge("A", "B", length=400.0, traversability="passable")
G.add_edge("B", "C", length=400.0, traversability="passable")
route = nx.astar_path(G, "A", "C", weight=edge_cost)
check("alternatif varken kapali yol SECILMEZ",
      route == ["A", "B", "C"], f"donen rota: {route}")

H = nx.MultiDiGraph()
H.add_edge("A", "C", length=100.0, traversability="closed")
H.add_edge("A", "B", length=400.0, traversability="closed")
H.add_edge("B", "C", length=400.0, traversability="passable")
try:
    bad = nx.astar_path(H, "A", "C", weight=edge_cost)
    check("tum yollar kapali -> NetworkXNoPath", False,
          f"HATA: rota dondu -> {bad}  (math.inf regresyonu!)")
except nx.NetworkXNoPath:
    check("tum yollar kapali -> NetworkXNoPath", True)

print("\n[4] difficult mekanizmasi — ceza esigi")
D = nx.MultiDiGraph()
D.add_edge("K", "M", length=50.0, traversability="difficult")
D.add_edge("K", "L", length=1000.0, traversability="passable")
D.add_edge("L", "M", length=1000.0, traversability="passable")
kisa_cezali = 50.0 * DIFFICULT_PENALTY
uzun_temiz = 2000.0
beklenen = ["K", "M"] if kisa_cezali < uzun_temiz else ["K", "L", "M"]
route_d = nx.astar_path(D, "K", "M", weight=edge_cost)
check(f"ceza={DIFFICULT_PENALTY}: 50m difficult ({kisa_cezali:.0f}) vs "
      f"2000m passable ({uzun_temiz:.0f})",
      route_d == beklenen, f"donen: {route_d}, beklenen: {beklenen}")

print("\n[5] math.inf sizintisi taramasi")
src = open("scripts/phase0_routing.py").read()
body = src.split("def edge_cost", 1)[1].split("\ndef ", 1)[0]
# Yorum satirlari ve satir ici yorumlar atilir: aciklama metninde gecen
# "math.inf" ifadesi ihlal degildir, taranan sey CALISAN koddur.
kod = "\n".join(l.split("#")[0] for l in body.splitlines())
check("edge_cost calisan kodunda math.inf yok",
      "math.inf" not in kod,
      "edge_cost hala math.inf iceriyor")

print("\n" + "=" * 60)
if FAIL:
    print(f"SONUC: {len(FAIL)} test KALDI -> {', '.join(FAIL)}")
    sys.exit(1)
print("SONUC: tum testler gecti. Faz 1 edge_cost sozlesmesi dogrulandi.")
