"""
Faz 3 - Patch on isleme.
Her bina icin 64x64 pre/post patch ve CVA haritasini diske kaydeder.
Bu script bir kez calistirilir; egitim kucuk dosyalari okur, buyuk
PNG'leri acmaz. GPU bekleme suresi dramatik duser.
Cikti: data/xbd_patches/{uid}_pre.npy, {uid}_post.npy, {uid}_cva.npy
KULLANIM:
  python scripts/phase3_preprocess_patches.py
  python scripts/phase3_preprocess_patches.py --disaster mexico-earthquake
"""
import argparse
import glob
import json
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
import numpy as np
from PIL import Image
from shapely import wkt

IMG_DIR = "data/xbd/train/images"
LBL_DIR = "data/xbd/train/labels"
OUT_DIR = "data/xbd_patches"
PATCH   = 64
SINIFLAR = {"no-damage", "minor-damage", "major-damage", "destroyed"}


def cva_magnitude(pre, post):
    d = post.astype("float32") - pre.astype("float32")
    return np.sqrt((d ** 2).sum(axis=2))


def kirp(img, cx, cy, patch=PATCH):
    h, w = img.shape[:2]
    r = patch // 2
    x0 = int(max(0, min(cx - r, w - patch)))
    y0 = int(max(0, min(cy - r, h - patch)))
    return img[y0:y0+patch, x0:x0+patch]


def karo_isle(args):
    lbl_yolu, out_dir = args
    karo = os.path.basename(lbl_yolu).replace("_post_disaster.json", "")
    pre_yolu  = f"{IMG_DIR}/{karo}_pre_disaster.png"
    post_yolu = f"{IMG_DIR}/{karo}_post_disaster.png"
    if not os.path.exists(pre_yolu) or not os.path.exists(post_yolu):
        return 0
    with open(lbl_yolu) as f:
        d = json.load(f)
    pre  = np.array(Image.open(pre_yolu).convert("RGB"))
    post = np.array(Image.open(post_yolu).convert("RGB"))
    cva  = cva_magnitude(pre, post)
    sayac = 0
    for ft in d["features"]["xy"]:
        st = ft["properties"].get("subtype", "no-damage")
        if st not in SINIFLAR:
            continue
        uid  = ft["properties"]["uid"]
        poly = wkt.loads(ft["wkt"])
        cx, cy = poly.centroid.x, poly.centroid.y
        pre_p  = kirp(pre,  cx, cy).astype("float32") / 255.0
        post_p = kirp(post, cx, cy).astype("float32") / 255.0
        cva_p  = kirp(cva,  cx, cy)
        cva_p  = (cva_p / (cva_p.max() + 1e-8)).astype("float32")
        np.save(f"{out_dir}/{uid}_pre.npy",  pre_p)
        np.save(f"{out_dir}/{uid}_post.npy", post_p)
        np.save(f"{out_dir}/{uid}_cva.npy",  cva_p)
        sayac += 1
    return sayac


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--disaster", type=str, default=None)
    ap.add_argument("--workers",  type=int, default=8)
    args = ap.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)
    desen = f"{LBL_DIR}/{args.disaster or '*'}_*_post_disaster.json"
    karolar = sorted(glob.glob(desen))
    print(f"[karo] {len(karolar)} karo isleniyor...")

    toplam = 0
    gorevler = [(k, OUT_DIR) for k in karolar]

    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        futures = {ex.submit(karo_isle, g): g for g in gorevler}
        for i, fut in enumerate(as_completed(futures), 1):
            toplam += fut.result()
            if i % 100 == 0:
                print(f"  {i}/{len(karolar)} karo, {toplam} patch")

    print(f"\n[bitti] {toplam} patch")
    os.system(f"du -sh {OUT_DIR}")


if __name__ == "__main__":
    main()
