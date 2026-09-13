"""
Faz 3b - Bina segmentasyonu icin veri hazirlama.
Model 1: pre goruntuden bina maskesi ureten model.

EARTHQUAKE-TURKEY maskeleri (0-4 degerli hasar maskesi) ikili
maskeye (0=arka plan, 1=bina) cevrilir.

Cikti: data/seg_turkey_patches/{karo_id}_img.npy (512,512,3)
       data/seg_turkey_patches/{karo_id}_mask.npy (512,512)

KULLANIM:
  python scripts/phase3b_segmentation_data.py
"""
import glob
import os
import numpy as np
from PIL import Image

IMG_DIR = "data/ebd_turkey/EARTHQUAKE-TURKEY/images"
MASK_DIR = "data/ebd_turkey/EARTHQUAKE-TURKEY/masks"
OUT_DIR = "data/seg_turkey_patches"


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    karolar = sorted(set(
        os.path.basename(f).split("_pre_disaster")[0].replace("EARTHQUAKE-TURKEY_", "")
        for f in glob.glob(IMG_DIR + "/*_pre_disaster.png")
    ))
    print("[karo]", len(karolar), "karo bulundu")

    sayac = 0
    for i, kid in enumerate(karolar, 1):
        pre_yolu = IMG_DIR + "/EARTHQUAKE-TURKEY_" + kid + "_pre_disaster.png"
        mask_yolu = MASK_DIR + "/EARTHQUAKE-TURKEY_" + kid + "_pre_disaster.png"
        if not (os.path.exists(pre_yolu) and os.path.exists(mask_yolu)):
            continue

        img = np.array(Image.open(pre_yolu).convert("RGB")).astype("float32") / 255.0
        mask_ham = np.array(Image.open(mask_yolu))
        mask_ikili = (mask_ham > 0).astype("float32")

        np.save(OUT_DIR + "/" + kid + "_img.npy", img)
        np.save(OUT_DIR + "/" + kid + "_mask.npy", mask_ikili)
        sayac += 1

        if i % 100 == 0:
            print(" ", i, "/", len(karolar), "karo islendi")

    print()
    print("[bitti]", sayac, "karo ->", OUT_DIR)


if __name__ == "__main__":
    main()
