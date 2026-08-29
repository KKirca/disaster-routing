"""
Faz 3 - EARTHQUAKE-TURKEY (EBD collection, Wang 2025) patch on isleme.
Maske degerleri: 0=arka plan, 1=no-damage, 2=minor, 3=major, 4=destroyed
KULLANIM:
  python scripts/phase3_preprocess_ebd_turkey.py
"""
import glob
import os
import csv
import numpy as np
from PIL import Image
from scipy import ndimage

IMG_DIR = "data/ebd_turkey/EARTHQUAKE-TURKEY/images"
MASK_DIR = "data/ebd_turkey/EARTHQUAKE-TURKEY/masks"
OUT_DIR = "data/ebd_turkey_patches"
PATCH = 64
MIN_ALAN = 20

SINIF_ADI = {1: "no-damage", 2: "minor-damage", 3: "major-damage", 4: "destroyed"}


def cva_magnitude(pre, post):
    d = post.astype("float32") - pre.astype("float32")
    return np.sqrt((d ** 2).sum(axis=2))


def kirp(img, cx, cy, patch=PATCH):
    h, w = img.shape[:2]
    r = patch // 2
    x0 = int(max(0, min(cx - r, w - patch)))
    y0 = int(max(0, min(cy - r, h - patch)))
    return img[y0:y0+patch, x0:x0+patch]


def karo_isle(karo_id):
    pre_yolu = IMG_DIR + "/EARTHQUAKE-TURKEY_" + karo_id + "_pre_disaster.png"
    post_yolu = IMG_DIR + "/EARTHQUAKE-TURKEY_" + karo_id + "_post_disaster.png"
    mask_yolu = MASK_DIR + "/EARTHQUAKE-TURKEY_" + karo_id + "_post_disaster.png"
    if not (os.path.exists(pre_yolu) and os.path.exists(post_yolu) and os.path.exists(mask_yolu)):
        return []
    pre = np.array(Image.open(pre_yolu).convert("RGB"))
    post = np.array(Image.open(post_yolu).convert("RGB"))
    mask = np.array(Image.open(mask_yolu))
    cva = cva_magnitude(pre, post)
    sonuclar = []
    for sinif_deger, sinif_adi in SINIF_ADI.items():
        bina_maske = (mask == sinif_deger)
        if not bina_maske.any():
            continue
        etiketli, n = ndimage.label(bina_maske)
        for i in range(1, n + 1):
            bilesen = (etiketli == i)
            alan = bilesen.sum()
            if alan < MIN_ALAN:
                continue
            ys, xs = np.where(bilesen)
            cy, cx = ys.mean(), xs.mean()
            pre_p = kirp(pre, cx, cy).astype("float32") / 255.0
            post_p = kirp(post, cx, cy).astype("float32") / 255.0
            cva_p = kirp(cva, cx, cy)
            cva_p = (cva_p / (cva_p.max() + 1e-8)).astype("float32")
            if pre_p.shape[:2] != (PATCH, PATCH):
                continue
            uid = karo_id + "_" + str(sinif_deger) + "_" + str(i)
            np.save(OUT_DIR + "/" + uid + "_pre.npy", pre_p)
            np.save(OUT_DIR + "/" + uid + "_post.npy", post_p)
            np.save(OUT_DIR + "/" + uid + "_cva.npy", cva_p)
            sonuclar.append((uid, sinif_adi))
    return sonuclar


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    karolar = sorted(set(
        os.path.basename(f).split("_pre_disaster")[0].replace("EARTHQUAKE-TURKEY_", "")
        for f in glob.glob(IMG_DIR + "/*_pre_disaster.png")
    ))
    print("[karo]", len(karolar), "karo bulundu")
    tum_etiketler = []
    for i, kid in enumerate(karolar, 1):
        sonuc = karo_isle(kid)
        tum_etiketler.extend(sonuc)
        if i % 100 == 0:
            print(" ", i, "/", len(karolar), "karo,", len(tum_etiketler), "bina")
    csv_yolu = OUT_DIR + "/etiketler.csv"
    with open(csv_yolu, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["uid", "sinif"])
        w.writerows(tum_etiketler)
    print()
    print("[bitti]", len(tum_etiketler), "bina ->", OUT_DIR)
    from collections import Counter
    sayac = Counter(s for _, s in tum_etiketler)
    for k, v in sayac.most_common():
        print(" ", v, " ", k)


if __name__ == "__main__":
    main()
