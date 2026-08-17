"""
Faz 4 — K-19 dogrulama: 20 agir hasarli binanin gorsel incelemesi.

NEDEN VAR:
  K-19'daki formulun "dogru" oldugunu gosterecek ground truth yok. Yapilabilecek
  sey: her binanin uydu goruntusune bakip bir insan muhendis olarak "bu bina
  coktugunde hangi sokak kapanir" sorusunu cevaplamak ve kuralin ciktisiyla
  karsilastirmak.

  Bu ground truth DEGIL, uzman muhakemesi referansidir. Tezde: "kuralin ciktisi
  20 vakada uzman degerlendirmesiyle karsilastirildi; N'inde uyumlu, M'sinde
  ayristi ve sebepleri sunlardir."

NE URETIR:
  Her bina icin uc panelli PNG:
    sol  = pre-disaster kirpma (bina nasildi)
    orta = post-disaster kirpma (bina ne oldu)
    sag  = yol agi + bina poligonu + kuralin verdigi skorlar
  Ayrica doldurulacak bir degerlendirme sablonu (CSV).

NOT: LC_ALL=C ile calistirin.

KULLANIM:
  LC_ALL=C python scripts/phase4_verify_buildings.py
"""

import csv
import os
import sys

import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import osmnx as ox
import pandas as pd
from PIL import Image
from shapely import wkt

sys.path.insert(0, "scripts")
from phase4_damage_pressure import (ALAN_DOYMA, DAMAGE_CSV, SINIF_AGIRLIK,
                                    W_REF, sokak_genisligi)
from phase4_apply_to_graph import R

GRAPH = "data/mexico_city_graph_faz4.graphml"
IMG_DIR = "data/xbd/train/images"
OUT_DIR = "outputs/faz4_dogrulama"
FORM_CSV = "reports/phase4_bina_dogrulama.csv"

METRIC = "EPSG:32614"
KIRP = 220          # genis kirpma: bina cevresindeki baglam
KIRP_YAKIN = 90     # yakin kirpma: hasar derecesi ayrimi icin
                    # xBD cozunurlugu ~0.5 m/px; 220 px kirpmada yikim tek
                    # bakista secilmiyor, manuel zoom gerekiyor.
HARITA_MARJ = 70.0  # harita panelinde bina cevresi payi (metre)


def piksel_merkez(tile, uid):
    """Binanin goruntu icindeki piksel merkezini xBD etiketinden okur."""
    import json
    p = f"data/xbd/train/labels/{tile}_post_disaster.json"
    with open(p) as f:
        d = json.load(f)
    for ft in d["features"].get("xy", []):
        if ft["properties"].get("uid") == uid:
            c = wkt.loads(ft["wkt"]).centroid
            return c.x, c.y
    return None, None


def poligon_piksel(tile, uid):
    """Bina poligonunun piksel koordinatlarini dondurur (xBD 'xy' blogu)."""
    import json
    with open(f"data/xbd/train/labels/{tile}_post_disaster.json") as f:
        d = json.load(f)
    for ft in d["features"].get("xy", []):
        if ft["properties"].get("uid") == uid:
            return wkt.loads(ft["wkt"])
    return None


def kirp(yol, cx, cy, r=KIRP):
    """Goruntuden bina merkezli kare kirpma. Sinirlarda tasma engellenir."""
    if not os.path.exists(yol):
        return None
    im = Image.open(yol)
    W, H = im.size
    x0 = int(max(0, min(cx - r, W - 2 * r)))
    y0 = int(max(0, min(cy - r, H - 2 * r)))
    return im.crop((x0, y0, x0 + 2 * r, y0 + 2 * r)), x0, y0


def skor_bandi(s):
    if s >= 0.50:
        return "firebrick", 3.0
    if s >= 0.20:
        return "darkorange", 2.2
    if s > 0.0:
        return "gold", 1.4
    return "silver", 0.7


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs("reports", exist_ok=True)

    print("[graf]", GRAPH)
    G = ox.load_graphml(GRAPH)
    _, edges = ox.graph_to_gdfs(G)
    edges = edges.to_crs(METRIC).reset_index()
    edges["dp"] = [float(x) for x in edges["damage_pressure"]]

    df = pd.read_csv(DAMAGE_CSV)
    hv = df[df.damage_class.isin(["major-damage", "destroyed"])].copy()
    print("[bina]", len(hv), "agir hasarli")

    bld = gpd.GeoDataFrame(
        hv, geometry=hv.footprint_wkt.apply(wkt.loads), crs="EPSG:4326"
    ).to_crs(METRIC)

    satirlar = []
    for i, (_, b) in enumerate(bld.iterrows(), 1):
        kisa = b.uid[:8]
        cx, cy = piksel_merkez(b.tile, b.uid)
        if cx is None:
            print("  [atlandi]", kisa, "piksel merkezi bulunamadi")
            continue

        pre_r = kirp(f"{IMG_DIR}/{b.tile}_pre_disaster.png", cx, cy)
        post_r = kirp(f"{IMG_DIR}/{b.tile}_post_disaster.png", cx, cy)
        pre, px0, py0 = pre_r if pre_r else (None, 0, 0)
        post, _, _ = post_r if post_r else (None, 0, 0)
        # Bina konturu pre/post panellerine cizilir: 440x440 kirpmada onlarca
        # yapi var, isaretlenmezse hangisinin degerlendirildigi belli olmaz.
        poly_px = poligon_piksel(b.tile, b.uid)

        x0, y0, x1, y1 = b.geometry.bounds
        pen = edges.cx[x0 - HARITA_MARJ:x1 + HARITA_MARJ,
                       y0 - HARITA_MARJ:y1 + HARITA_MARJ]

        fig, ax = plt.subplots(1, 3, figsize=(16, 5.6))
        for a, im, ad in [(ax[0], pre, "ONCE"), (ax[1], post, "SONRA")]:
            if im is not None:
                a.imshow(np.asarray(im))
            if poly_px is not None:
                xs, ys = poly_px.exterior.xy
                a.plot([x - px0 for x in xs], [y - py0 for y in ys],
                       color="magenta", linewidth=2.4, zorder=5)
            a.set_title(ad, fontsize=11)
            a.set_axis_off()

        for _, e in pen.iterrows():
            renk, kal = skor_bandi(e.dp)
            gpd.GeoSeries([e.geometry]).plot(ax=ax[2], color=renk,
                                             linewidth=kal, zorder=2)
        gpd.GeoSeries([b.geometry]).plot(ax=ax[2], color="purple",
                                         alpha=0.75, zorder=3)
        ax[2].set_xlim(x0 - HARITA_MARJ, x1 + HARITA_MARJ)
        ax[2].set_ylim(y0 - HARITA_MARJ, y1 + HARITA_MARJ)
        ax[2].set_axis_off()

        # DIKKAT: pen.dp bu kenarin TOPLAM skorudur ve komsu binalarin
        # katkisini da icerir. Dogrulama icin gereken sey, BU BINANIN tek
        # basina uretttigi katkidir — yoksa kumelenmis binalarda komsunun
        # skoru bu binaya atfedilir ve degerlendirme anlamsizlasir.
        w_sinif = SINIF_AGIRLIK.get(b.damage_class, 0.0)
        w_alan = min(float(b.area_m2) / ALAN_DOYMA, 1.0)
        en_yuksek, tip, W, d_min = 0.0, "-", 0.0, -1.0
        toplam_dp = 0.0
        for _, e in pen.iterrows():
            d = e.geometry.distance(b.geometry)
            if d > R:
                continue
            katki = (w_sinif * max(0.0, 1.0 - d / R) * w_alan
                     * min(W_REF / sokak_genisligi(e.get("highway"),
                                                   e.get("lanes")), 1.0))
            if katki > en_yuksek:
                en_yuksek = katki
                tip = str(e.get("highway"))
                W = sokak_genisligi(e.get("highway"), e.get("lanes"))
                d_min = d
                toplam_dp = e.dp

        ax[2].set_title(f"BU BINANIN katkisi {en_yuksek:.3f}  "
                        f"(kenarin toplami {toplam_dp:.3f})  |  {tip[:14]}  "
                        f"W={W:.0f}m  d={d_min:.1f}m", fontsize=10)

        fig.suptitle(f"[{i}/{len(bld)}]  {kisa}  {b.damage_class}  "
                     f"{b.area_m2:.0f} m2  |  {b.tile}", fontsize=12)
        fig.tight_layout()
        cikti = f"{OUT_DIR}/{i:02d}_{kisa}.png"
        fig.savefig(cikti, dpi=120, bbox_inches="tight")
        plt.close(fig)

        # Yakin kirpma: hasar derecesini ayirt etmek icin
        f2, a2 = plt.subplots(1, 2, figsize=(15, 7.5))
        for a, kind, ad in [(a2[0], "pre", "ONCE"), (a2[1], "post", "SONRA")]:
            r2 = kirp(f"{IMG_DIR}/{b.tile}_{kind}_disaster.png",
                      cx, cy, KIRP_YAKIN)
            if r2:
                im2, ix0, iy0 = r2
                a.imshow(np.asarray(im2), interpolation="lanczos")
                if poly_px is not None:
                    xs, ys = poly_px.exterior.xy
                    a.plot([x - ix0 for x in xs], [y - iy0 for y in ys],
                           color="magenta", linewidth=2.5, zorder=5)
            a.set_title(ad, fontsize=13)
            a.set_axis_off()
        f2.suptitle(f"{kisa}  {b.damage_class}  {b.area_m2:.0f} m2  "
                    f"(yakin kirpma)", fontsize=13)
        f2.tight_layout()
        f2.savefig(f"{OUT_DIR}/{i:02d}_{kisa}_yakin.png", dpi=170,
                   bbox_inches="tight")
        plt.close(f2)

        satirlar.append({
            "sira": i, "uid": b.uid, "kisa": kisa, "tile": b.tile,
            "sinif": b.damage_class, "alan_m2": b.area_m2,
            "bina_katkisi": round(en_yuksek, 3),
            "kenar_toplam_dp": round(toplam_dp, 3),
            "en_yakin_m": round(d_min, 1), "yol_tipi": tip, "W_m": W,
            "UZMAN_KARARI": "", "UYUMLU_MU": "", "NOT": "",
        })
        print(f"  [{i:2d}/{len(bld)}] {kisa}  katki {en_yuksek:.3f}  "
              f"kenar {toplam_dp:.3f}  -> {cikti}")

    with open(FORM_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(satirlar[0].keys()))
        w.writeheader()
        w.writerows(satirlar)

    print("\n[form]", FORM_CSV)
    print("  UZMAN_KARARI sutununa yaz: closed / difficult / passable")
    print("  UYUMLU_MU sutununa yaz   : evet / hayir")
    print("  NOT sutununa             : ayrisma varsa sebebi")


if __name__ == "__main__":
    main()
