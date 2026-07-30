"""
Faz 3 — Adim 2: Siamese CNN icin YAMA VERI SETI hazirla.

FIKIR: Tam 1024x1024 karo yerine, her binanin etrafindan kucuk bir yama
kesiyoruz. Boylece:
  - 8 GB VRAM'e rahat sigar (batch buyuk olabilir)
  - Degerlendirme birimi (bina) ile egitim birimi ayni olur
  - CVA baseline'iyla birebir karsilastirilabilir

CIKTI: her bina icin (pre_yama, post_yama, etiket, fold, olay)

DENGELEME (K-09, K-10): Hasarli binalar nadir. Hepsini tutuyoruz,
saglamlari ise RATIO oraninda ORNEKLIYORUZ. Boylece model "her sey
saglam" demeyi ogrenmiyor.

SIZINTISIZLIK (K-06): Fold atamasi spatial_cv.py'den geliyor — blok
bazli, yani komsu karolar ayni fold'da kaliyor.

Calistirma:
    cd ~/disaster-routing
    conda activate disaster
    python scripts/phase3_make_patches.py
"""

import glob
import json
import os
import random
from collections import Counter, defaultdict

import matplotlib.pyplot as plt
import numpy as np
from shapely import wkt

# Fold atamasi Faz 2'de kurduğumuz spatial CV'den geliyor.
import spatial_cv as scv

# ---------------------------------------------------------------------------
# Ayarlar
# ---------------------------------------------------------------------------
PATCH = 128                  # yama kenari (piksel). ~0.5 m/px -> ~64 m
RATIO = 3                    # saglam / hasarli hedef orani
MAX_TILES_PER_DISASTER = 120 # hiz icin olay basina karo siniri
MAX_PATCHES = 20000          # bellek siniri (20k x 128x128x3x2 ~ 2 GB)
SEED = 42
DAMAGED = {"major-damage", "destroyed"}

OUT_NPZ = "data/patches/patches.npz"
OUT_FIG = "outputs/patch_samples.png"


# ---------------------------------------------------------------------------
# Yama kesme (kenardaki binalar icin sifir dolgulu)
# ---------------------------------------------------------------------------
def crop_centered(img, cx, cy, size):
    h, w = img.shape[:2]
    half = size // 2
    x0, y0 = int(cx) - half, int(cy) - half
    out = np.zeros((size, size, 3), dtype=img.dtype)
    sx0, sy0 = max(x0, 0), max(y0, 0)
    sx1, sy1 = min(x0 + size, w), min(y0 + size, h)
    if sx1 <= sx0 or sy1 <= sy0:
        return out
    out[sy0 - y0:sy1 - y0, sx0 - x0:sx1 - x0] = img[sy0:sy1, sx0:sx1]
    return out


def load_rgb(path):
    img = plt.imread(path)[:, :, :3]
    if img.max() <= 1.0:
        img = img * 255.0
    return img.astype("uint8")


# ---------------------------------------------------------------------------
# Ana akis
# ---------------------------------------------------------------------------
def main():
    os.makedirs("data/patches", exist_ok=True)
    os.makedirs("outputs", exist_ok=True)
    rng = random.Random(SEED)

    # --- 1) Karolari topla, olay basina sinirla ---
    paths = sorted(glob.glob("data/**/labels/*_post_disaster.json", recursive=True))
    by_dis = defaultdict(list)
    for p in paths:
        by_dis[os.path.basename(p).split("_")[0]].append(p)
    selected = []
    for dis, ps in by_dis.items():
        selected.extend(ps[:MAX_TILES_PER_DISASTER])
    print(f"[karo] {len(by_dis)} olay, secilen karo: {len(selected)}")

    # --- 2) Koordinat + fold atamasi (spatial_cv'den) ---
    print("[fold] koordinatlar cikariliyor ve bloklara atanıyor...")
    tiles = [t for t in (scv.tile_info(p) for p in selected) if t is not None]
    scv.assign_folds(tiles, scv.K, scv.SEED)
    print(f"[fold] {len(tiles)} karoya fold atandi (BLOCK_DEG={scv.BLOCK_DEG})")

    # --- 3) Denge orani: kac saglam bina tutacagiz? ---
    n_dmg = sum(t["n_damaged"] for t in tiles)
    n_ok = sum(t["n_buildings"] - t["n_damaged"] for t in tiles)
    print(f"[denge] hasarli: {n_dmg}, saglam: {n_ok}")
    if n_dmg == 0:
        raise SystemExit("Hic hasarli bina yok — karo secimini genislet.")

    keep_ok = min(1.0, (RATIO * n_dmg) / max(n_ok, 1))
    # Genel ust sinir: toplam yama MAX_PATCHES'i asmasin
    est = n_dmg + keep_ok * n_ok
    scale = min(1.0, MAX_PATCHES / est)
    keep_dmg = scale
    keep_ok = keep_ok * scale
    print(f"[denge] tutma olasiligi — hasarli: {keep_dmg:.3f}, saglam: {keep_ok:.3f}")

    # --- 4) Yamalari cikar ---
    pre_list, post_list, y_list, fold_list, dis_list = [], [], [], [], []
    for i, t in enumerate(tiles):
        post_json = t["path"]
        post_p = post_json.replace("labels", "images").replace(".json", ".png")
        pre_p = post_p.replace("post_disaster", "pre_disaster")
        if not (os.path.exists(pre_p) and os.path.exists(post_p)):
            continue

        with open(post_json) as f:
            feats = json.load(f)["features"]["xy"]
        if not feats:
            continue

        # Once hangi binalari alacagimiza karar ver (goruntuyu bosuna yukleme)
        picks = []
        for ft in feats:
            dmg = ft["properties"].get("subtype") in DAMAGED
            p = keep_dmg if dmg else keep_ok
            if rng.random() < p:
                picks.append((ft, dmg))
        if not picks:
            continue

        pre_img, post_img = load_rgb(pre_p), load_rgb(post_p)
        for ft, dmg in picks:
            c = wkt.loads(ft["wkt"]).centroid
            pre_list.append(crop_centered(pre_img, c.x, c.y, PATCH))
            post_list.append(crop_centered(post_img, c.x, c.y, PATCH))
            y_list.append(int(dmg))
            fold_list.append(t["fold_block"])
            dis_list.append(t["disaster"])

        if (i + 1) % 100 == 0:
            print(f"       {i+1}/{len(tiles)} karo — {len(y_list)} yama")

    pre = np.stack(pre_list)
    post = np.stack(post_list)
    y = np.array(y_list, dtype="int8")
    fold = np.array(fold_list, dtype="int8")
    dis = np.array(dis_list)
    del pre_list, post_list

    print(f"\n[sonuc] toplam yama: {len(y)}, hasarli: {int(y.sum())} "
          f"({100*y.mean():.1f}%)")
    print(f"[sonuc] dizi boyutu: {pre.nbytes/1e9:.2f} GB (pre) + ayni kadar (post)")

    # Fold bazinda denge
    print("\n[fold] dagilim:")
    for f in sorted(set(fold.tolist())):
        m = fold == f
        print(f"       fold {f}: {int(m.sum()):6d} yama, "
              f"hasarli %{100*y[m].mean():.1f}, "
              f"{len(set(dis[m]))} olay")

    np.savez_compressed(OUT_NPZ, pre=pre, post=post, y=y, fold=fold, disaster=dis)
    print(f"\n[kaydet] {OUT_NPZ}")

    # --- 5) Ornek yamalar: 4 hasarli + 4 saglam ---
    idx_d = np.where(y == 1)[0][:4]
    idx_o = np.where(y == 0)[0][:4]
    fig, axes = plt.subplots(4, 4, figsize=(11, 11))
    for col, (idx, title) in enumerate([(idx_d, "HASARLI"), (idx_o, "SAGLAM")]):
        for row, k in enumerate(idx):
            axes[row][col * 2].imshow(pre[k]);  axes[row][col * 2].set_title(f"{title} pre", fontsize=8)
            axes[row][col * 2 + 1].imshow(post[k]); axes[row][col * 2 + 1].set_title(f"{title} post", fontsize=8)
    for a in axes.ravel():
        a.axis("off")
    fig.suptitle(f"Ornek yamalar ({PATCH}x{PATCH})")
    fig.savefig(OUT_FIG, dpi=120, bbox_inches="tight")
    print(f"[ciz] {OUT_FIG}")


if __name__ == "__main__":
    main()