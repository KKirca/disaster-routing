"""
Faz 3 — Adim 1: CVA (Change Vector Analysis) BASELINE.

Egitim YOK. Klasik, denetimsiz bir degisim tespiti yontemi.
Amac: CNN'in gecmesi gereken referans sayiyi uretmek + degerlendirme
hattini kurmak.

YONTEM:
  1. Pre ve post goruntuyu oku.
  2. Her piksel icin fark vektorunun buyuklugu:  |post - pre|
     (RGB kanallarinda kare farklarin toplaminin karekoku)
  3. Her bina poligonunun icindeki ORTALAMA CVA degerini hesapla.
  4. Bir esikle sinifla: ortalama > esik -> "hasarli" tahmini.
  5. Gercek etiketle (major-damage / destroyed) karsilastir.

METRIK — GUVENLIK ASIMETRISI:
  Bu projede yanlis-negatif (hasarliyi saglam sanmak) cok daha pahali,
  cunku kapali bir yolu acik sanmak kurtarma aracini cikmaza sokar.
  Bu yuzden RECALL'a oncelik veriyoruz, precision'a degil.

Calistirma:
    cd ~/disaster-routing
    conda activate disaster
    python scripts/phase3_cva_baseline.py
"""

import glob
import json
import os

import matplotlib.pyplot as plt
import numpy as np
from rasterio.features import rasterize
from rasterio.transform import Affine
from shapely import wkt

# ---------------------------------------------------------------------------
# Ayarlar
# ---------------------------------------------------------------------------
DISASTER = "palu-tsunami"   # hasar sinyali en zengin olay
MAX_TILES = 40              # hiz icin sinir; artirabilirsin
DAMAGED = {"major-damage", "destroyed"}   # "hasarli" tanimi
OUT_CURVE = "outputs/cva_baseline_curve.png"
OUT_SAMPLE = "outputs/cva_baseline_sample.png"


# ---------------------------------------------------------------------------
# 1) CVA sinyali
# ---------------------------------------------------------------------------
def cva_magnitude(pre, post): 
    """
    Fark vektorunun buyuklugu.
    pre/post: (H, W, 3) float dizi.
    Donen: (H, W) — her piksel icin degisim miktari.
    """
    diff = post.astype("float32") - pre.astype("float32")
    return np.sqrt((diff ** 2).sum(axis=2))


# ---------------------------------------------------------------------------
# 2) Bina bazinda ortalama (hizli: tek rasterize + bincount)
# ---------------------------------------------------------------------------
def per_building_means(cva, polys, shape):
    """
    Her poligonun icindeki ortalama CVA degerini dondurur.
    Poligonlari tek seferde ID'lerle rasterize edip bincount ile topluyoruz.
    """
    shapes = [(p, i + 1) for i, p in enumerate(polys)]
    labels = rasterize(shapes, out_shape=shape, transform=Affine.identity(),
                       fill=0, dtype="int32")
    n = len(polys)
    flat_lab = labels.ravel()
    sums = np.bincount(flat_lab, weights=cva.ravel(), minlength=n + 1)
    cnts = np.bincount(flat_lab, minlength=n + 1)
    return sums[1:] / np.maximum(cnts[1:], 1), labels


# ---------------------------------------------------------------------------
# 3) Bir karoyu isle
# ---------------------------------------------------------------------------
def process_tile(post_json):
    post_img_p = post_json.replace("labels", "images").replace(".json", ".png")
    pre_img_p = post_img_p.replace("post_disaster", "pre_disaster")
    if not (os.path.exists(post_img_p) and os.path.exists(pre_img_p)):
        return None

    with open(post_json) as f:
        feats = json.load(f)["features"]["xy"]
    if not feats:
        return None

    pre = plt.imread(pre_img_p)[:, :, :3]
    post = plt.imread(post_img_p)[:, :, :3]
    # plt.imread PNG'yi 0-1 float dondurebilir; 0-255'e normalize et.
    if pre.max() <= 1.0:
        pre, post = pre * 255.0, post * 255.0

    cva = cva_magnitude(pre, post)

    polys = [wkt.loads(ft["wkt"]) for ft in feats]
    y_true = np.array([ft["properties"].get("subtype") in DAMAGED
                       for ft in feats], dtype=bool)
    scores, labels = per_building_means(cva, polys, cva.shape)

    return {"scores": scores, "y_true": y_true, "cva": cva,
            "pre": pre, "post": post, "path": post_json}


# ---------------------------------------------------------------------------
# 4) Degerlendirme: esik taramasi
# ---------------------------------------------------------------------------
def evaluate(scores, y_true):
    print(f"\n[veri] toplam bina: {len(y_true)}, "
          f"hasarli: {int(y_true.sum())} ({100*y_true.mean():.1f}%)")
    print("\n  esik   recall  precision      F1   tahmin_hasarli")
    print("  " + "-" * 52)

    rows = []
    for thr in np.percentile(scores, [50, 70, 80, 85, 90, 95, 97, 99]):
        pred = scores >= thr
        tp = int((pred & y_true).sum())
        fp = int((pred & ~y_true).sum())
        fn = int((~pred & y_true).sum())
        rec = tp / max(tp + fn, 1)
        prec = tp / max(tp + fp, 1)
        f1 = 2 * rec * prec / max(rec + prec, 1e-9)
        rows.append((thr, rec, prec, f1))
        print(f"  {thr:6.1f}  {rec:6.3f}  {prec:9.3f}  {f1:6.3f}   {int(pred.sum()):6d}")
    return rows


def main():
    os.makedirs("outputs", exist_ok=True)

    paths = sorted(glob.glob(
        f"data/**/labels/*{DISASTER}*_post_disaster.json", recursive=True))
    if not paths:
        raise SystemExit(f"'{DISASTER}' karolari bulunamadi.")
    paths = paths[:MAX_TILES]
    print(f"[karo] {len(paths)} karo isleniyor ({DISASTER})...")

    all_scores, all_true, sample = [], [], None
    for i, p in enumerate(paths):
        r = process_tile(p)
        if r is None:
            continue
        all_scores.append(r["scores"])
        all_true.append(r["y_true"])
        # Ornek gorsel icin en cok hasarli karoyu sakla
        if sample is None or r["y_true"].sum() > sample["y_true"].sum():
            sample = r
        if (i + 1) % 10 == 0:
            print(f"       {i+1}/{len(paths)}")

    scores = np.concatenate(all_scores)
    y_true = np.concatenate(all_true)
    rows = evaluate(scores, y_true)

    # --- Grafik 1: recall / precision egrisi ---
    thrs = [r[0] for r in rows]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(thrs, [r[1] for r in rows], "o-", label="recall (hasarli)")
    ax.plot(thrs, [r[2] for r in rows], "s-", label="precision")
    ax.plot(thrs, [r[3] for r in rows], "^--", label="F1")
    ax.set_xlabel("CVA esigi")
    ax.set_ylabel("skor")
    ax.set_title(f"CVA baseline — {DISASTER} ({len(y_true)} bina)")
    ax.grid(alpha=0.3)
    ax.legend()
    fig.savefig(OUT_CURVE, dpi=140, bbox_inches="tight")
    print(f"\n[ciz] {OUT_CURVE}")

    # --- Grafik 2: ornek karo (pre / post / CVA) ---
    fig, axes = plt.subplots(1, 3, figsize=(16, 6))
    axes[0].imshow(sample["pre"].astype("uint8")); axes[0].set_title("pre")
    axes[1].imshow(sample["post"].astype("uint8")); axes[1].set_title("post")
    im = axes[2].imshow(sample["cva"], cmap="inferno")
    axes[2].set_title("CVA buyuklugu")
    fig.colorbar(im, ax=axes[2], fraction=0.046)
    for a in axes:
        a.axis("off")
    fig.suptitle(os.path.basename(sample["path"]))
    fig.savefig(OUT_SAMPLE, dpi=130, bbox_inches="tight")
    print(f"[ciz] {OUT_SAMPLE}")


if __name__ == "__main__":
    main()