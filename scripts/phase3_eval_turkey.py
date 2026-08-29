"""
Faz 3 - Model degerlendirme: sadece EARTHQUAKE-TURKEY verisiyle.
Amac: modelin GENEL recall'u degil, TURKIYE'YE OZGU performansini olcmek.

KULLANIM:
  python scripts/phase3_eval_turkey.py
"""
import csv
import numpy as np
import torch
from collections import Counter

from phase3_siamese_cnn import SiameseCVA, SINIFLAR, SINIF_IDX

MODEL_YOLU = "models/siamese_cva_en_iyi.pth"
CSV_YOLU = "data/ebd_turkey_patches/etiketler.csv"
PATCH_DIR = "data/ebd_turkey_patches"


def main():
    cihaz = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("[cihaz]", cihaz)

    model = SiameseCVA(n_sinif=len(SINIFLAR)).to(cihaz)
    model.load_state_dict(torch.load(MODEL_YOLU, map_location=cihaz))
    model.eval()
    print("[model]", MODEL_YOLU, "yuklendi")

    ornekler = []
    with open(CSV_YOLU) as f:
        for row in csv.DictReader(f):
            if row["sinif"] in SINIF_IDX:
                ornekler.append((row["uid"], SINIF_IDX[row["sinif"]]))
    print("[veri]", len(ornekler), "Turkiye ornegi")

    dogru = [0] * len(SINIFLAR)
    toplam = [0] * len(SINIFLAR)
    karisiklik = np.zeros((len(SINIFLAR), len(SINIFLAR)), dtype=int)

    with torch.no_grad():
        for i in range(0, len(ornekler), 64):
            grup = ornekler[i:i+64]
            pre_l, post_l, cva_l, sinif_l = [], [], [], []
            for uid, sinif in grup:
                pre = np.load(f"{PATCH_DIR}/{uid}_pre.npy")
                post = np.load(f"{PATCH_DIR}/{uid}_post.npy")
                cva = np.load(f"{PATCH_DIR}/{uid}_cva.npy")
                pre_l.append(pre.transpose(2, 0, 1))
                post_l.append(post.transpose(2, 0, 1))
                cva_l.append(cva[None])
                sinif_l.append(sinif)

            pre_t = torch.from_numpy(np.stack(pre_l)).float().to(cihaz)
            post_t = torch.from_numpy(np.stack(post_l)).float().to(cihaz)
            cva_t = torch.from_numpy(np.stack(cva_l)).float().to(cihaz)
            sinif_t = torch.tensor(sinif_l)

            cikti = model(pre_t, post_t, cva_t)
            tahmin = cikti.argmax(1).cpu()

            for gercek, tah in zip(sinif_t, tahmin):
                toplam[gercek] += 1
                karisiklik[gercek][tah] += 1
                if gercek == tah:
                    dogru[gercek] += 1

    print()
    print("--- TURKIYE-OZGU RECALL ---")
    for i, ad in enumerate(SINIFLAR):
        r = dogru[i] / max(toplam[i], 1)
        print(f"  {ad:15s}  {dogru[i]:5d}/{toplam[i]:5d}  recall={r:.3f}")

    hasar_recall = sum(dogru[1:]) / max(sum(toplam[1:]), 1)
    print(f"\n  Hasar (minor+major+destroyed) recall: {hasar_recall:.3f}")

    print("\n--- KARISIKLIK MATRISI (satir=gercek, sutun=tahmin) ---")
    print("            " + "".join(f"{a[:8]:>10s}" for a in SINIFLAR))
    for i, ad in enumerate(SINIFLAR):
        print(f"  {ad[:10]:10s}" + "".join(f"{karisiklik[i][j]:10d}" for j in range(len(SINIFLAR))))


if __name__ == "__main__":
    main()
