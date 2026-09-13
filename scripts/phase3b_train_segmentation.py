"""
Faz 3b - Model 1: bina segmentasyon egitimi.
U-Net mimarisi (segmentation-models-pytorch), pre goruntuden
ikili bina maskesi (bina/arka plan) uretir.

KULLANIM:
  python scripts/phase3b_train_segmentation.py --epochs 20
"""
import argparse
import glob
import os

import numpy as np
import torch
import torch.nn as nn
import segmentation_models_pytorch as smp
from torch.utils.data import DataLoader, Dataset

PATCH_DIR = "data/seg_turkey_patches"
MODEL_DIR = "models"


class SegDataset(Dataset):
    def __init__(self):
        self.karolar = sorted(set(
            os.path.basename(f).replace("_img.npy", "")
            for f in glob.glob(PATCH_DIR + "/*_img.npy")
        ))
        print("[veri]", len(self.karolar), "karo yuklendi")

    def __len__(self):
        return len(self.karolar)

    def __getitem__(self, idx):
        kid = self.karolar[idx]
        img = np.load(PATCH_DIR + "/" + kid + "_img.npy")
        mask = np.load(PATCH_DIR + "/" + kid + "_mask.npy")
        img_t = torch.from_numpy(img.transpose(2, 0, 1)).float()
        mask_t = torch.from_numpy(mask).float().unsqueeze(0)
        return img_t, mask_t


def iou_skoru(tahmin, hedef, esik=0.5):
    tahmin = (tahmin > esik).float()
    kesisim = (tahmin * hedef).sum()
    birlesim = tahmin.sum() + hedef.sum() - kesisim
    return (kesisim / (birlesim + 1e-8)).item()


def egit(model, loader, optimizer, kayip_fn, cihaz):
    model.train()
    toplam_kayip = 0.0
    toplam_iou = 0.0
    for img, mask in loader:
        img, mask = img.to(cihaz), mask.to(cihaz)
        optimizer.zero_grad()
        cikti = model(img)
        kayip = kayip_fn(cikti, mask)
        kayip.backward()
        optimizer.step()
        toplam_kayip += kayip.item() * len(img)
        toplam_iou += iou_skoru(torch.sigmoid(cikti), mask) * len(img)
    n = len(loader.dataset)
    return toplam_kayip / n, toplam_iou / n


def degerlendir(model, loader, kayip_fn, cihaz):
    model.eval()
    toplam_kayip = 0.0
    toplam_iou = 0.0
    with torch.no_grad():
        for img, mask in loader:
            img, mask = img.to(cihaz), mask.to(cihaz)
            cikti = model(img)
            kayip = kayip_fn(cikti, mask)
            toplam_kayip += kayip.item() * len(img)
            toplam_iou += iou_skoru(torch.sigmoid(cikti), mask) * len(img)
    n = len(loader.dataset)
    return toplam_kayip / n, toplam_iou / n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=20)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()

    os.makedirs(MODEL_DIR, exist_ok=True)
    cihaz = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("[cihaz]", cihaz)

    dataset = SegDataset()
    n_val = max(1, int(len(dataset) * 0.15))
    n_train = len(dataset) - n_val
    train_ds, val_ds = torch.utils.data.random_split(
        dataset, [n_train, n_val],
        generator=torch.Generator().manual_seed(42))

    train_loader = DataLoader(train_ds, batch_size=args.batch,
                              shuffle=True, num_workers=args.workers)
    val_loader = DataLoader(val_ds, batch_size=args.batch,
                            shuffle=False, num_workers=args.workers)

    model = smp.Unet(
        encoder_name="resnet18",
        encoder_weights="imagenet",
        in_channels=3,
        classes=1,
    ).to(cihaz)

    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)
    kayip_fn = nn.BCEWithLogitsLoss()

    print("\n[egitim]", n_train, "train,", n_val, "val,", args.epochs, "epoch\n")
    en_iyi_iou = 0.0
    for epoch in range(args.epochs):
        tr_kayip, tr_iou = egit(model, train_loader, optimizer, kayip_fn, cihaz)
        vl_kayip, vl_iou = degerlendir(model, val_loader, kayip_fn, cihaz)
        print(f"Epoch {epoch+1:3d} | train {tr_kayip:.4f}/IoU={tr_iou:.3f} | "
              f"val {vl_kayip:.4f}/IoU={vl_iou:.3f}")

        if vl_iou > en_iyi_iou:
            en_iyi_iou = vl_iou
            torch.save(model.state_dict(), MODEL_DIR + "/seg_unet_en_iyi.pth")
            print(f"  -> en iyi model kaydedildi (IoU: {vl_iou:.3f})")

    print("\n[bitti] en iyi IoU:", round(en_iyi_iou, 3))
    print("        model:", MODEL_DIR + "/seg_unet_en_iyi.pth")


if __name__ == "__main__":
    main()
