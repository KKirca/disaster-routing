"""
Faz 3 — Siamese CNN + CVA: bina hasar tespiti.

MIMARI:
  Pre goruntu  (3 kanal) -> Encoder (paylasilan agirliklar) -> ozellik A
  Post goruntu (3 kanal) -> Encoder (paylasilan agirliklar) -> ozellik B
  CVA haritasi (1 kanal) -> CVA Encoder                    -> ozellik C
  [A, B, |A-B|, C] -> Siniflandirici -> 4 sinif

NEDEN CVA EK GIRDI:
  Model bazen golge/mevsim farkini hasar sanabilir. CVA haritasi
  degisim nerede yogun ipucunu onceden verir; model bunu kendi
  agirliklarina yansitarak ogrenebilir.

SINIF DENGESIZLIGI yuzde72 no-damage:
  Agirlikli ornekleme + Focal Loss.
  Recall oncelikli: hasarliyi saglan sanmak cok daha tehlikeli.

CHECKPOINT: her epoch sonunda otomatik kaydedilir.
  Bilgisayari kapattiktan sonra --resume ile kaldigi yerden devam.

KULLANIM:
  python scripts/phase3_siamese_cnn.py --epochs 20
  python scripts/phase3_siamese_cnn.py --epochs 20 --disaster mexico-earthquake
  python scripts/phase3_siamese_cnn.py --epochs 20 --resume
"""

import argparse
import glob
import json
import os

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image
from shapely import wkt
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler

IMG_DIR   = "data/xbd/train/images"
LBL_DIR   = "data/xbd/train/labels"
MODEL_DIR = "models"
PATCH     = 64
SINIFLAR  = ["no-damage", "minor-damage", "major-damage", "destroyed"]
SINIF_IDX = {s: i for i, s in enumerate(SINIFLAR)}


def cva_magnitude(pre, post):
    """CVA haritasi: piksel degisim buyuklugu (H,W)."""
    d = post.astype("float32") - pre.astype("float32")
    return np.sqrt((d ** 2).sum(axis=2))


def kirp(img, cx, cy, patch=PATCH):
    """Bina merkezli kare kirpma, sinir kontrollu."""
    h, w = img.shape[:2]
    r = patch // 2
    x0 = int(max(0, min(cx - r, w - patch)))
    y0 = int(max(0, min(cy - r, h - patch)))
    return img[y0:y0+patch, x0:x0+patch]


class XBDDataset(Dataset):
    """
    Her ornek: (pre_patch, post_patch, cva_patch, sinif_idx)
    pre/post: (3, PATCH, PATCH) float32  0-1
    cva     : (1, PATCH, PATCH) float32  0-1 normalize
    """
    def __init__(self, disaster=None):
        self.ornekler = []
        desen = f"{LBL_DIR}/{disaster or '*'}_*_post_disaster.json"
        for lbl_yolu in sorted(glob.glob(desen)):
            karo = os.path.basename(lbl_yolu).replace("_post_disaster.json", "")
            pre_yolu  = f"{IMG_DIR}/{karo}_pre_disaster.png"
            post_yolu = f"{IMG_DIR}/{karo}_post_disaster.png"
            if not os.path.exists(pre_yolu) or not os.path.exists(post_yolu):
                continue
            with open(lbl_yolu) as f:
                d = json.load(f)
            for ft in d["features"]["xy"]:
                st = ft["properties"].get("subtype", "no-damage")
                if st not in SINIF_IDX:
                    continue  # un-classified atla
                uid = ft["properties"]["uid"]
                self.ornekler.append((uid, SINIF_IDX[st]))

        print(f"[veri] {len(self.ornekler)} ornek yuklendi")
        from collections import Counter
        sayac = Counter(s for *_, s in self.ornekler)
        for i, ad in enumerate(SINIFLAR):
            print(f"  {sayac[i]:6d}  {ad}")

    def __len__(self):
        return len(self.ornekler)

    def __getitem__(self, idx):
        uid, sinif = self.ornekler[idx]
        patch_dir = "data/xbd_patches"
        pre_p  = np.load(f"{patch_dir}/{uid}_pre.npy")
        post_p = np.load(f"{patch_dir}/{uid}_post.npy")
        cva_p  = np.load(f"{patch_dir}/{uid}_cva.npy")
        # (H,W,3) -> (3,H,W)
        pre_t  = torch.from_numpy(pre_p.transpose(2, 0, 1))
        post_t = torch.from_numpy(post_p.transpose(2, 0, 1))
        cva_t  = torch.from_numpy(cva_p[None])  # (1,H,W)
        return pre_t, post_t, cva_t, torch.tensor(sinif, dtype=torch.long)


class Encoder(nn.Module):
    """
    Paylasilan encoder: pre ve post goruntu ayni agirliklardan gecer.
    Kucuk ama etkili: 3 conv blok, her biri BN + ReLU + MaxPool.
    Cikis: (128,) vektor.
    """
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(3, 32, 3, padding=1), nn.BatchNorm2d(32), nn.ReLU(),
            nn.MaxPool2d(2),                                      # 64->32
            nn.Conv2d(32, 64, 3, padding=1), nn.BatchNorm2d(64), nn.ReLU(),
            nn.MaxPool2d(2),                                      # 32->16
            nn.Conv2d(64, 128, 3, padding=1), nn.BatchNorm2d(128), nn.ReLU(),
            nn.AdaptiveAvgPool2d(1),                              # 16->1
        )

    def forward(self, x):
        return self.net(x).squeeze(-1).squeeze(-1)  # (B, 128)


class CVAEncoder(nn.Module):
    """
    CVA kanali icin kucuk encoder.
    Girdi: (1, PATCH, PATCH), Cikis: (32,) vektor.
    """
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(1, 16, 3, padding=1), nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(16, 32, 3, padding=1), nn.ReLU(),
            nn.AdaptiveAvgPool2d(1),
        )

    def forward(self, x):
        return self.net(x).squeeze(-1).squeeze(-1)  # (B, 32)


class SiameseCVA(nn.Module):
    """
    Tam model:
      - Encoder(pre) -> A (128)
      - Encoder(post) -> B (128)  [ayni agirliklar]
      - CVAEncoder(cva) -> C (32)
      - [A, B, |A-B|, C] -> siniflandirici -> 4 sinif

    |A-B| fark vektoru: degisen ozellikleri vurgular.
    C: CVA sinyali modele dogrudan verilir.
    Toplam siniflandirici girdisi: 128+128+128+32 = 416
    """
    def __init__(self, n_sinif=4):
        super().__init__()
        self.encoder     = Encoder()
        self.cva_encoder = CVAEncoder()
        self.siniflandirici = nn.Sequential(
            nn.Linear(416, 256), nn.ReLU(), nn.Dropout(0.3),
            nn.Linear(256, 64),  nn.ReLU(), nn.Dropout(0.2),
            nn.Linear(64, n_sinif),
        )

    def forward(self, pre, post, cva):
        a = self.encoder(pre)
        b = self.encoder(post)
        c = self.cva_encoder(cva)
        x = torch.cat([a, b, torch.abs(a - b), c], dim=1)
        return self.siniflandirici(x)


class FocalLoss(nn.Module):
    """
    Focal Loss: kolay ornekleri (no-damage) cezalandirmaz,
    zor orneklere (hasarli binalar) odaklanir.
    gamma=2 standart deger. alpha sinif agirliklari.
    """
    def __init__(self, alpha=None, gamma=2.0):
        super().__init__()
        self.alpha = alpha
        self.gamma = gamma

    def forward(self, girdi, hedef):
        ce = F.cross_entropy(girdi, hedef, weight=self.alpha, reduction="none")
        pt = torch.exp(-ce)
        return ((1 - pt) ** self.gamma * ce).mean()


def agirlikli_ornekleyici(dataset):
    """Sinif dengesizligini gidermek icin WeightedRandomSampler."""
    from collections import Counter
    sayac = Counter(s for *_, s in dataset.ornekler)
    sinif_agirlik = {s: 1.0 / sayac[s] for s in sayac}
    ornek_agirlik = [sinif_agirlik[s] for *_, s in dataset.ornekler]
    return WeightedRandomSampler(ornek_agirlik, len(ornek_agirlik))


def egit(model, loader, optimizer, kayip_fn, cihaz):
    model.train()
    toplam_kayip = 0.0
    dogru = toplam = 0
    for pre, post, cva, sinif in loader:
        pre, post, cva, sinif = (pre.to(cihaz), post.to(cihaz),
                                  cva.to(cihaz), sinif.to(cihaz))
        optimizer.zero_grad()
        cikti = model(pre, post, cva)
        kayip = kayip_fn(cikti, sinif)
        kayip.backward()
        optimizer.step()
        toplam_kayip += kayip.item() * len(sinif)
        dogru += (cikti.argmax(1) == sinif).sum().item()
        toplam += len(sinif)
    return toplam_kayip / toplam, dogru / toplam


def degerlendir(model, loader, kayip_fn, cihaz):
    model.eval()
    toplam_kayip = 0.0
    dogru = toplam = 0
    # Sinif bazli recall icin
    sinif_dogru = [0] * len(SINIFLAR)
    sinif_toplam = [0] * len(SINIFLAR)
    with torch.no_grad():
        for pre, post, cva, sinif in loader:
            pre, post, cva, sinif = (pre.to(cihaz), post.to(cihaz),
                                      cva.to(cihaz), sinif.to(cihaz))
            cikti = model(pre, post, cva)
            kayip = kayip_fn(cikti, sinif)
            toplam_kayip += kayip.item() * len(sinif)
            tahmin = cikti.argmax(1)
            dogru += (tahmin == sinif).sum().item()
            toplam += len(sinif)
            for i in range(len(SINIFLAR)):
                maske = sinif == i
                sinif_dogru[i]  += (tahmin[maske] == sinif[maske]).sum().item()
                sinif_toplam[i] += maske.sum().item()
    recall = [sinif_dogru[i] / max(sinif_toplam[i], 1)
              for i in range(len(SINIFLAR))]
    return toplam_kayip / toplam, dogru / toplam, recall


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs",   type=int, default=20)
    ap.add_argument("--batch",    type=int, default=64)
    ap.add_argument("--lr",       type=float, default=1e-3)
    ap.add_argument("--disaster", type=str, default=None,
                    help="tek bir afet tipiyle egit, ornek: mexico-earthquake")
    ap.add_argument("--resume",   action="store_true",
                    help="en son checkpoint'ten devam et")
    ap.add_argument("--workers",  type=int, default=4)
    args = ap.parse_args()

    os.makedirs(MODEL_DIR, exist_ok=True)
    cihaz = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[cihaz] {cihaz}")

    # Veri
    print("\n[veri yukleniyor...]")
    dataset = XBDDataset(disaster=args.disaster)
    n_val   = max(1, int(len(dataset) * 0.15))
    n_train = len(dataset) - n_val
    train_ds, val_ds = torch.utils.data.random_split(
        dataset, [n_train, n_val],
        generator=torch.Generator().manual_seed(42))

    # Agirlikli ornekleyici sadece train icin
    class SubsetWrapper(Dataset):
        def __init__(self, subset):
            self.subset = subset
            self.ornekler = [dataset.ornekler[i] for i in subset.indices]
        def __len__(self): return len(self.subset)
        def __getitem__(self, i): return self.subset[i]

    train_wrap = SubsetWrapper(train_ds)
    sampler    = agirlikli_ornekleyici(train_wrap)
    train_loader = DataLoader(train_wrap, batch_size=args.batch,
                              sampler=sampler, num_workers=args.workers,
                              pin_memory=True)
    val_loader   = DataLoader(val_ds, batch_size=args.batch,
                              shuffle=False, num_workers=args.workers,
                              pin_memory=True)

    # Model
    model = SiameseCVA(n_sinif=len(SINIFLAR)).to(cihaz)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=7, gamma=0.5)

    # Focal loss — sinif agirliklari ters frekans
    from collections import Counter
    sayac = Counter(s for *_, s in dataset.ornekler)
    agirlik = torch.tensor(
        [1.0 / sayac.get(i, 1) for i in range(len(SINIFLAR))],
        dtype=torch.float32).to(cihaz)
    agirlik = agirlik / agirlik.sum() * len(SINIFLAR)
    kayip_fn = FocalLoss(alpha=agirlik, gamma=2.0)

    # Checkpoint: resume
    baslangic = 0
    en_iyi_recall = 0.0
    ckpt_yolu = f"{MODEL_DIR}/checkpoint_son.pth"
    if args.resume and os.path.exists(ckpt_yolu):
        ck = torch.load(ckpt_yolu, map_location=cihaz)
        model.load_state_dict(ck["model"])
        optimizer.load_state_dict(ck["optimizer"])
        baslangic = ck["epoch"] + 1
        en_iyi_recall = ck.get("en_iyi_recall", 0.0)
        print(f"[resume] epoch {baslangic}'den devam ediliyor")

    # Egitim dongusu
    print(f"\n[egitim] {n_train} train, {n_val} val, {args.epochs} epoch\n")
    for epoch in range(baslangic, baslangic + args.epochs):
        tr_kayip, tr_acc = egit(model, train_loader, optimizer, kayip_fn, cihaz)
        vl_kayip, vl_acc, recall = degerlendir(model, val_loader, kayip_fn, cihaz)
        scheduler.step()

        hasar_recall = sum(recall[1:]) / 3  # minor+major+destroyed ortalama
        print(f"Epoch {epoch+1:3d} | "
              f"train {tr_kayip:.4f}/{tr_acc:.3f} | "
              f"val {vl_kayip:.4f}/{vl_acc:.3f} | "
              f"recall [no:{recall[0]:.2f} mi:{recall[1]:.2f} "
              f"ma:{recall[2]:.2f} de:{recall[3]:.2f}]")

        # Her epoch checkpoint
        torch.save({
            "epoch": epoch,
            "model": model.state_dict(),
            "optimizer": optimizer.state_dict(),
            "en_iyi_recall": en_iyi_recall,
            "val_acc": vl_acc,
            "val_loss": vl_kayip,
        }, ckpt_yolu)
        # ayrica epoch bazli yedek
        torch.save({
            "epoch": epoch,
            "model": model.state_dict(),
        }, f"{MODEL_DIR}/checkpoint_epoch_{epoch}.pth")

        # En iyi model
        if hasar_recall > en_iyi_recall:
            en_iyi_recall = hasar_recall
            torch.save(model.state_dict(),
                       f"{MODEL_DIR}/siamese_cva_en_iyi.pth")
            print(f"  -> en iyi model kaydedildi (hasar recall: {hasar_recall:.3f})")

    print(f"\n[bitti] en iyi hasar recall: {en_iyi_recall:.3f}")
    print(f"        model: {MODEL_DIR}/siamese_cva_en_iyi.pth")


if __name__ == "__main__":
    main()
