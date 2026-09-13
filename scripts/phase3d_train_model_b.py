"""
Model B: Siamese CNN, SADECE EBD_TR verisiyle egitim.
4 sinif korunur. Test karolari egitimden haric tutulur.

Model A ile farki:
  A: xBD + EBD_TR (tamami), 4 sinif
  B: sadece EBD_TR (egitim bolumu), 4 sinif

KULLANIM:
  python scripts/phase3d_train_model_b.py --epochs 30
"""
import argparse
import csv
import os
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset

import sys
sys.path.insert(0, "scripts")
from phase3_siamese_cnn import SiameseCVA, FocalLoss, SINIFLAR, SINIF_IDX

PATCH_DIR = "data/ebd_turkey_patches"
SPLIT_DIR = "data/splits"
MODEL_DIR = "models"


class EBDTurkeyDataset(Dataset):
    """Sadece EBD_TR, belirtilen karo listesinden."""
    def __init__(self, karo_dosyasi):
        with open(karo_dosyasi) as f:
            izinli = set(line.strip() for line in f if line.strip())

        self.ornekler = []
        with open(PATCH_DIR + "/etiketler.csv") as f:
            for row in csv.DictReader(f):
                karo = row["uid"].split("_")[0]
                if karo not in izinli:
                    continue
                if row["sinif"] not in SINIF_IDX:
                    continue
                self.ornekler.append((row["uid"], SINIF_IDX[row["sinif"]]))

        from collections import Counter
        sayac = Counter(s for _, s in self.ornekler)
        print("[veri]", len(self.ornekler), "ornek")
        for i, ad in enumerate(SINIFLAR):
            print(f"  {sayac[i]:6d}  {ad}")

    def __len__(self):
        return len(self.ornekler)

    def __getitem__(self, idx):
        uid, sinif = self.ornekler[idx]
        pre = np.load(f"{PATCH_DIR}/{uid}_pre.npy")
        post = np.load(f"{PATCH_DIR}/{uid}_post.npy")
        cva = np.load(f"{PATCH_DIR}/{uid}_cva.npy")
        return (torch.from_numpy(pre.transpose(2,0,1)).float(),
                torch.from_numpy(post.transpose(2,0,1)).float(),
                torch.from_numpy(cva[None]).float(),
                torch.tensor(sinif, dtype=torch.long))


def calistir(model, loader, cihaz, kayip_fn, optimizer=None):
    egitim_modu = optimizer is not None
    model.train() if egitim_modu else model.eval()
    toplam_kayip = 0.0
    dogru = [0] * len(SINIFLAR)
    toplam = [0] * len(SINIFLAR)
    baglam = torch.enable_grad() if egitim_modu else torch.no_grad()
    with baglam:
        for pre, post, cva, sinif in loader:
            pre, post, cva, sinif = (pre.to(cihaz), post.to(cihaz),
                                      cva.to(cihaz), sinif.to(cihaz))
            if egitim_modu:
                optimizer.zero_grad()
            cikti = model(pre, post, cva)
            kayip = kayip_fn(cikti, sinif)
            if egitim_modu:
                kayip.backward()
                optimizer.step()
            toplam_kayip += kayip.item() * len(sinif)
            tahmin = cikti.argmax(1)
            for i in range(len(SINIFLAR)):
                maske = sinif == i
                dogru[i] += (tahmin[maske] == sinif[maske]).sum().item()
                toplam[i] += maske.sum().item()
    n = sum(toplam)
    recall = [dogru[i] / max(toplam[i], 1) for i in range(len(SINIFLAR))]
    return toplam_kayip / max(n, 1), recall


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=30)
    ap.add_argument("--batch", type=int, default=64)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()
    os.makedirs(MODEL_DIR, exist_ok=True)
    cihaz = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("[cihaz]", cihaz)
    print("--- EGITIM VERISI ---")
    train_ds = EBDTurkeyDataset(SPLIT_DIR + "/ebd_tr_egitim_karolar.txt")
    print("--- TEST VERISI ---")
    test_ds = EBDTurkeyDataset(SPLIT_DIR + "/ebd_tr_test_karolar.txt")
    train_loader = DataLoader(train_ds, batch_size=args.batch, shuffle=True,
                              num_workers=args.workers)
    test_loader = DataLoader(test_ds, batch_size=args.batch, shuffle=False,
                             num_workers=args.workers)
    model = SiameseCVA(n_sinif=len(SINIFLAR)).to(cihaz)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)
    from collections import Counter
    sayac = Counter(s for _, s in train_ds.ornekler)
    agirlik = torch.tensor(
        [1.0 / max(sayac.get(i, 1), 1) for i in range(len(SINIFLAR))],
        dtype=torch.float32).to(cihaz)
    agirlik = agirlik / agirlik.sum() * len(SINIFLAR)
    kayip_fn = FocalLoss(alpha=agirlik, gamma=2.0)
    print("[egitim]", args.epochs, "epoch")
    en_iyi = 0.0
    for epoch in range(args.epochs):
        tr_kayip, tr_recall = calistir(model, train_loader, cihaz, kayip_fn, optimizer)
        te_kayip, te_recall = calistir(model, test_loader, cihaz, kayip_fn)
        hasar_recall = sum(te_recall[1:]) / 3
        print(f"Epoch {epoch+1:3d} | train {tr_kayip:.4f} | test {te_kayip:.4f} | "
              f"recall [no:{te_recall[0]:.2f} mi:{te_recall[1]:.2f} "
              f"ma:{te_recall[2]:.2f} de:{te_recall[3]:.2f}]")
        if hasar_recall > en_iyi:
            en_iyi = hasar_recall
            torch.save(model.state_dict(), MODEL_DIR + "/model_b_ebd_tr.pth")
            print(f"  -> kaydedildi (hasar recall: {hasar_recall:.3f})")
    print("[bitti] en iyi hasar recall:", round(en_iyi, 3))
if __name__ == "__main__":
    main()
