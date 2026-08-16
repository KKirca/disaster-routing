"""
Faz 4 — Adim 6: Rota karsilastirmasini gorsellestir.

Her senaryo icin iki panelli harita uretir:
  sol = hasarsiz graf uzerinde rota (referans)
  sag = hasar etiketleri uygulanmis graf uzerinde rota

Tablo "44 m sapti" der; harita bunu bir bakista gosterir.

NOT: LC_ALL=C ile calistirin.
KULLANIM: LC_ALL=C python scripts/phase4_visualize.py
"""

import argparse
import os
import sys

import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import osmnx as ox
import pandas as pd
from matplotlib.lines import Line2D
from shapely import wkt

sys.path.insert(0, "scripts")
from phase4_route_compare import GRAPH, SENARYOLAR, T_CLOSED, T_DIFF
from phase4_route_compare import etiketle, rota
from phase4_damage_pressure import DAMAGE_CSV

OUT_DIR = "outputs"
MARJ = 350.0
METRIC = "EPSG:32614"


def cerceve(edges_m, yollar, marj=MARJ):
    """Rotalari kapsayan sinir kutusu (metrik CRS)."""
    dugumler = set()
    for y in yollar:
        if y:
            dugumler |= set(y)
    alt = edges_m[edges_m.u.isin(dugumler) | edges_m.v.isin(dugumler)]
    x0, y0, x1, y1 = alt.total_bounds
    return x0 - marj, y0 - marj, x1 + marj, y1 + marj


def panel(ax, edges_m, bld_m, yol, baslik, renkli):
    """Tek panel ciz. renkli=False ise kenar hasari gosterilmez.

    Binalar HER IKI panelde de cizilir: iki panel ayni cerceveyi gosterir,
    ancak sol panelde hasar katmani olmadigi icin goz iki haritayi
    eslestiremez. Binalar ortak sabit nokta gorevi gorur.
    """
    edges_m.plot(ax=ax, linewidth=0.4, color="silver", zorder=1)

    if not bld_m.empty:
        bld_m.plot(ax=ax, color="purple", markersize=14,
                   marker="s", zorder=4)

    if renkli:
        bantlar = [(0.001, 0.20, "gold", 1.2),
                   (0.20, 0.50, "darkorange", 2.0),
                   (0.50, 1.01, "firebrick", 3.0)]
        for lo, hi, renk, kalinlik in bantlar:
            alt = edges_m[(edges_m.dp >= lo) & (edges_m.dp < hi)]
            if not alt.empty:
                alt.plot(ax=ax, linewidth=kalinlik, color=renk, zorder=2)

    if yol:
        cift = set(zip(yol[:-1], yol[1:]))
        seg = edges_m[[(u, v) in cift for u, v in zip(edges_m.u, edges_m.v)]]
        if not seg.empty:
            seg.plot(ax=ax, linewidth=3.2, color="royalblue", zorder=3)
        ax.set_title(baslik, fontsize=10)
    else:
        ax.set_title(baslik, fontsize=10, color="firebrick")

    ax.set_axis_off()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--t-closed", type=float, default=T_CLOSED)
    ap.add_argument("--t-diff", type=float, default=T_DIFF)
    args = ap.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)
    print("[graf]", GRAPH)
    G = ox.load_graphml(GRAPH)

    _, edges = ox.graph_to_gdfs(G)
    edges = edges.to_crs(METRIC).reset_index()
    edges["dp"] = [float(x) for x in edges["damage_pressure"]]
    print("      ", len(edges), "kenar,",
          int((edges.dp > 0).sum()), "hasarli")

    df = pd.read_csv(DAMAGE_CSV)
    hv = df[df.damage_class.isin(["major-damage", "destroyed"])]
    bld = gpd.GeoDataFrame(
        hv, geometry=hv.footprint_wkt.apply(wkt.loads), crs="EPSG:4326"
    ).to_crs(METRIC)

    for ad, A, B, _ in SENARYOLAR:
        print("\n[senaryo]", ad)

        for _, _, _, d in G.edges(keys=True, data=True):
            d["traversability"] = "passable"
        y0, L0 = rota(G, A, B)

        for _, _, _, d in G.edges(keys=True, data=True):
            d.pop("traversability", None)
        etiketle(G, args.t_diff, args.t_closed)
        y1, L1 = rota(G, A, B)

        print("  referans :", round(L0), "m")
        print("  hasarli  :",
              "ULASILAMIYOR" if y1 is None else str(round(L1)) + " m")

        x0, yy0, x1, yy1 = cerceve(edges, [y0, y1])
        pen = edges.cx[x0:x1, yy0:yy1]
        pbld = bld.cx[x0:x1, yy0:yy1]

        fig, axes = plt.subplots(1, 2, figsize=(15, 7.5))
        panel(axes[0], pen, pbld, y0,
              "HASAR YOK - " + str(round(L0)) + " m", renkli=False)
        if y1:
            sag = ("HASAR VAR - " + str(round(L1)) + " m  (+"
                   + str(round(L1 - L0)) + " m)")
        else:
            sag = "HASAR VAR - HEDEFE ULASILAMIYOR"
        panel(axes[1], pen, pbld, y1, sag, renkli=True)

        for ax in axes:
            ax.set_xlim(x0, x1)
            ax.set_ylim(yy0, yy1)

        fig.legend(handles=[
            Line2D([], [], color="royalblue", lw=3, label="rota"),
            Line2D([], [], color="gold", lw=2, label="baski < 0.20"),
            Line2D([], [], color="darkorange", lw=2, label="baski 0.20-0.50"),
            Line2D([], [], color="firebrick", lw=3, label="baski > 0.50"),
            Line2D([], [], color="purple", marker="s", ls="",
                   label="agir hasarli bina"),
        ], loc="lower center", ncol=5, frameon=False, fontsize=9)

        fig.suptitle("Faz 4 - " + ad + "   (difficult >= "
                     + str(args.t_diff) + ", closed >= "
                     + str(args.t_closed) + ")", fontsize=12)
        fig.tight_layout(rect=[0, 0.05, 1, 0.96])

        cikti = OUT_DIR + "/phase4_" + ad.lower() + ".png"
        fig.savefig(cikti, dpi=140, bbox_inches="tight")
        plt.close(fig)
        print("  kaydedildi:", cikti)


if __name__ == "__main__":
    main()
