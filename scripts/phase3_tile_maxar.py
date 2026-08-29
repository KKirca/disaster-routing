"""
Maxar GeoTIFF'leri Label Studio icin 2048x2048 PNG alt karolara boler.
Her buyuk karo icin pre/post cifti uretir.
Cikti: data/maxar_tiles/{karo_id}_pre.png ve {karo_id}_post.png

KULLANIM:
  python scripts/phase3_tile_maxar.py
"""
import os
import numpy as np
import rasterio
from PIL import Image
from pathlib import Path

PRE_DIR   = "data/maxar/pre"
POST_DIR  = "data/maxar/post"
OUT_DIR   = "data/maxar_tiles"
TILE_SIZE = 2048

def normalize(arr):
    arr = arr.astype("float32")
    lo, hi = np.percentile(arr, 2), np.percentile(arr, 98)
    arr = np.clip((arr - lo) / (hi - lo + 1e-8), 0, 1)
    return (arr * 255).astype("uint8")

def bol(tif_yolu, out_prefix, tile_size=TILE_SIZE):
    kaydedilenler = []
    with rasterio.open(tif_yolu) as src:
        W, H = src.width, src.height
        data = src.read([1, 2, 3])  # (3, H, W)
        bounds = src.bounds
        crs = src.crs

    img = np.moveaxis(data, 0, -1)  # (H, W, 3)
    # Her kanal normalize
    for c in range(3):
        img[:, :, c] = normalize(img[:, :, c])

    nx = (W + tile_size - 1) // tile_size
    ny = (H + tile_size - 1) // tile_size

    for iy in range(ny):
        for ix in range(nx):
            x0, y0 = ix * tile_size, iy * tile_size
            x1, y1 = min(x0 + tile_size, W), min(y0 + tile_size, H)
            patch = img[y0:y1, x0:x1]
            if patch.shape[0] < tile_size or patch.shape[1] < tile_size:
                padded = np.zeros((tile_size, tile_size, 3), dtype="uint8")
                padded[:patch.shape[0], :patch.shape[1]] = patch
                patch = padded
            dosya = f"{out_prefix}_tx{ix:02d}_ty{iy:02d}.png"
            Image.fromarray(patch).save(dosya)
            kaydedilenler.append(dosya)
    return kaydedilenler

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    pre_dosyalar = sorted(Path(PRE_DIR).glob("*.tif"))
    print(f"[pre] {len(pre_dosyalar)} karo bulundu")

    for pre_yolu in pre_dosyalar:
        # Eslesme: karo ID'si orta kisimda (031133031132 gibi)
        parcalar = pre_yolu.stem.split("_")
        karo_id = [p for p in parcalar if p.startswith("031")][0]
        post_esles = list(Path(POST_DIR).glob(f"*{karo_id}*.tif"))
        if not post_esles:
            print(f"  [atla] {karo_id} icin post yok")
            continue

        print(f"\n[karo] {karo_id}")
        pre_prefix  = f"{OUT_DIR}/{karo_id}_pre"
        post_prefix = f"{OUT_DIR}/{karo_id}_post"
        pre_list  = bol(str(pre_yolu),     pre_prefix)
        post_list = bol(str(post_esles[0]), post_prefix)
        print(f"  pre : {len(pre_list)} alt karo")
        print(f"  post: {len(post_list)} alt karo")

    print(f"\n[bitti] -> {OUT_DIR}/")
    os.system(f"ls {OUT_DIR}/*.png | wc -l | xargs echo 'toplam PNG:'")

if __name__ == "__main__":
    main()
