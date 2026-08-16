"""
Faz 4 — Adim 5: damage_pressure -> traversability, ve rota karsilastirmasi.

============================================================================
 ESIK KONUSU — BURAYI OKUMADAN ESIK DEGISTIRME
============================================================================
NEDEN SABIT BIR ESIK YOK:
  damage_pressure surekli bir skordur (0-1). A* ise uc kategori bekler:
  passable / difficult / closed. Esik, skoru kategoriye ceviren sinirdir.

  Hangi esigin "dogru" oldugunu gosterecek ground truth YOKTUR — deprem
  sonrasi hangi yolun gercekten kapandigini veren bir veri seti mevcut
  degildir. Dolayisiyla tek bir sayi secip savunmak mumkun degildir.

  Bunun yerine: varsayilan deger kullanilir, sonuclar BIRDEN FAZLA esikle
  raporlanir (duyarlilik analizi). Tezde "esigi 0.5 sectik" demek yerine
  "esik 0.3'te 13 yol, 0.7'de 2 yol kapaniyor" denir — bu daha savunulabilir
  bir ifadedir ve juri "neden bu sayi?" sorusunu soramaz.

VARSAYILAN DEGERLER VE GEREKCESI:
  T_CLOSED = 0.50 — tikanma olasiligi %50'yi asan sokaga acil durum araci
                    yonlendirmek savunulamaz. K-16'daki asimetri: yolu
                    kapali saymanin maliyeti rotanin uzamasi, acik saymanin
                    maliyeti aracin enkaza gitmesidir.
  T_DIFF   = 0.20 — bu bandda sistem "gecilebilir ama dikkatli" uyarisi
                    uretir, abartmadan.

NE ZAMAN DEGISTIRILMELI:
  1. KAHRAMANMARAS'A GECERKEN. Bu degerler Mexico City'de 20 agir hasarli
     bina ile ayarlandi. Kahramanmaras'ta binlerce olacak; ayni esik cok
     daha genis bir agi kapatir. K-17'de not edilen "transfer varsayimi"
     tam olarak bu riski isaret eder. Yeni bolgede skor DAGILIMINA bakip
     yeniden ayarlayin.
  2. MODEL CIKTISI KULLANILIRKEN. Su an girdi xBD uzman etiketidir
     (confidence=1.0). Model tahmini gurultuludur; ayrica Faz 2c'de
     anotatorde sistematik IYIMSERLIK yanliligi olculdu (major-damage:
     22 ornekte 3 dogru). Model ayni yanliligi tasirsa skorlar oldugundan
     dusuk cikar ve esigin ASAGI cekilmesi gerekebilir.
  3. R DEGISTIGINDE. R (moloz yayilma mesafesi) skor dagilimini dogrudan
     kaydirir: R=15'te hicbir kenar 0.70'i asmiyordu, R=40'ta 8 kenar
     asiyordu. R'yi degistirirseniz esikler de yeniden bakilmalidir.
  4. SAHA VERISI GELIRSE. Gercek yol kapanma kaydi bulunursa (belediye,
     AFAD, OSM afet haritalari) esik artik tahmin degil OLCUM olur.
     Bu durumda duyarlilik analizi yerine kalibrasyon yapilabilir.

NASIL DEGISTIRILIR:
  --t-closed / --t-diff parametreleriyle. Kodu duzenlemeyin.
============================================================================

KULLANIM:
  LC_ALL=C python scripts/phase4_route_compare.py
  LC_ALL=C python scripts/phase4_route_compare.py --t-closed 0.7 --t-diff 0.3
  LC_ALL=C python scripts/phase4_route_compare.py --tara      # duyarlilik analizi
"""

import argparse
import sys

import networkx as nx
import osmnx as ox

sys.path.insert(0, "scripts")
from phase0_routing import DIFFICULT_PENALTY  # noqa: E402

GRAPH = "data/mexico_city_graph_faz4.graphml"
T_CLOSED = 0.50
T_DIFF = 0.20

# Test senaryosu: bir yerlesim adasina disaridan erisim.
# Hedef kavsagin UC KOLU DA hasarli (0.638 / 0.697 / 0.677), yani esik
# 0.638'in altina inince ada tamamen izole oluyor. Bu, deprem sonrasi
# gercek bir olgudur: izgara planda bir sokak kapanirsa arac dolanir,
# cikmaz sokak adasinda tek baglanti kapanirsa iceridekiler izole olur.
BASLANGIC = 6184109963
HEDEF = 1860819095


def etiketle(G, t_diff, t_closed):
    """damage_pressure -> traversability. Faz 1 etiketini EZMEZ (K-16)."""
    for _, _, _, d in G.edges(keys=True, data=True):
        s = float(d.get("damage_pressure", 0.0))
        yeni = ("closed" if s >= t_closed
                else "difficult" if s >= t_diff
                else "passable")
        eski = d.get("traversability")
        # K-16 konservatif birlestirme: en kisitlayici kazanir.
        oncelik = {"passable": 0, "difficult": 1, "closed": 2}
        if eski in oncelik and oncelik[eski] > oncelik[yeni]:
            continue
        d["traversability"] = yeni


def maliyet(u, v, data):
    """Faz 1 ile ayni sozlesme: closed kenar None dondurur (math.inf DEGIL)."""
    best = None
    for _, a in data.items():
        st = a.get("traversability", "passable")
        if st == "closed":
            continue
        L = float(a.get("length", 1.0))
        c = L * DIFFICULT_PENALTY if st == "difficult" else L
        best = c if best is None else min(best, c)
    return best


def say(G):
    c = d = 0
    for _, _, a in G.edges(data=True):
        t = a.get("traversability")
        c += t == "closed"
        d += t == "difficult"
    return c, d


def rota(G, a, b):
    try:
        yol = nx.astar_path(G, a, b, weight=maliyet)
        L = sum(min(float(x.get("length", 0)) for x in G[u][v].values())
                for u, v in zip(yol[:-1], yol[1:]))
        return yol, L
    except nx.NetworkXNoPath:
        return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--t-closed", type=float, default=T_CLOSED)
    ap.add_argument("--t-diff", type=float, default=T_DIFF)
    ap.add_argument("--tara", action="store_true",
                    help="duyarlilik analizi: bircok esikle calistir")
    args = ap.parse_args()

    print(f"[graf] {GRAPH}")
    G = ox.load_graphml(GRAPH)
    print(f"       {G.number_of_edges()} kenar\n")

    # Referans: hasarsiz senaryo (tum kenarlar passable)
    for _, _, _, d in G.edges(keys=True, data=True):
        d["traversability"] = "passable"
    y0, L0 = rota(G, BASLANGIC, HEDEF)
    print(f"[referans — hasar yok] rota {len(y0)} dugum, {L0:.0f} m\n")

    if args.tara:
        ciftler = [(0.05, 0.30), (0.10, 0.40), (0.15, 0.50),
                   (0.20, 0.50), (0.20, 0.60), (0.30, 0.70)]
    else:
        ciftler = [(args.t_diff, args.t_closed)]

    print(f"{'t_diff':>7s} {'t_closed':>9s} {'closed':>7s} {'difficult':>10s}"
          f"  sonuc")
    print("-" * 68)
    for td, tc in ciftler:
        for _, _, _, d in G.edges(keys=True, data=True):
            d.pop("traversability", None)
        etiketle(G, td, tc)
        nc, nd = say(G)
        yol, L = rota(G, BASLANGIC, HEDEF)
        if yol is None:
            s = "ULASILAMIYOR — hedef izole"
        else:
            fark = L - L0
            s = (f"rota {len(yol)} dugum, {L:.0f} m"
                 + (f"  (+{fark:.0f} m)" if fark > 1 else "  (degismedi)"))
        print(f"{td:7.2f} {tc:9.2f} {nc:7d} {nd:10d}  {s}")

    print("\nNot: kenarlar cift yonludur; 'closed 10' = ~5 fiziksel sokak.")
    if not args.tara:
        print("Duyarlilik analizi icin: --tara")


if __name__ == "__main__":
    main()
