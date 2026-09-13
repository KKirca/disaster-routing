"""
Faz 3c - Kopru scripti: Model 1 (segmentasyon) + Model 2 (siniflandirma).

Akis:
  1. Model 1, PRE goruntuden bina konumlarini bulur (segmentasyon)
  2. Her bina konumu icin, PRE ve POST goruntuden 64x64 patch kesilir
  3. Model 2, bu patch cifti + CVA ile hasar sinifi tahmin eder

KULLANIM:
  python scripts/phase3c_kopru.py --karo 000042
"""
import argparse
import numpy as np
import torch
import segmentation_models_pytorch as smp
from scipy import ndimage

import sys
sys.path.insert(0, "scripts")
from phase3_siamese_cnn import SiameseCVA, SINIFLAR, cva_magnitude

SEG_MODEL_YOLU = "models/seg_unet_en_iyi.pth"
CLS_MODEL_YOLU = "models/siamese_cva_en_iyi.pth"
PATCH_DIR = "data/seg_turkey_patches"
PATCH = 64
MIN_ALAN = 20
HASAR_ESIGI = 0.7


def kirp(img, cx, cy, patch=PATCH):
    h, w = img.shape[:2]
    r = patch // 2
    x0 = int(max(0, min(cx - r, w - patch)))
    y0 = int(max(0, min(cy - r, h - patch)))
    return img[y0:y0+patch, x0:x0+patch]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--karo", type=str, required=True)
    ap.add_argument("--esik", type=float, default=0.5)
    args = ap.parse_args()

    cihaz = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("[cihaz]", cihaz)

    seg_model = smp.Unet(encoder_name="resnet18", encoder_weights=None,
                         in_channels=3, classes=1).to(cihaz)
    seg_model.load_state_dict(torch.load(SEG_MODEL_YOLU, map_location=cihaz,
                                         weights_only=True))
    seg_model.eval()
    print("[model 1] segmentasyon yuklendi")

    cls_model = SiameseCVA(n_sinif=len(SINIFLAR)).to(cihaz)
    cls_model.load_state_dict(torch.load(CLS_MODEL_YOLU, map_location=cihaz,
                                         weights_only=True))
    cls_model.eval()
    print("[model 2] siniflandirma yuklendi")

    pre = np.load(f"{PATCH_DIR}/{args.karo}_img.npy")
    from PIL import Image
    post_yolu = f"data/ebd_turkey/EARTHQUAKE-TURKEY/images/EARTHQUAKE-TURKEY_{args.karo}_post_disaster.png"
    post = np.array(Image.open(post_yolu).convert("RGB")).astype("float32") / 255.0
    cva = cva_magnitude(pre * 255.0, post * 255.0)

    print(f"[goruntu] {args.karo}  pre={pre.shape}  post={post.shape}")

    with torch.no_grad():
        pre_t = torch.from_numpy(pre.transpose(2,0,1)).float().unsqueeze(0).to(cihaz)
        seg_tahmin = torch.sigmoid(seg_model(pre_t)).cpu().numpy()[0,0]

    ikili = seg_tahmin > args.esik
    etiketli, n = ndimage.label(ikili)
    print(f"[model 1] {n} bina bulundu (esik={args.esik})")

    sonuclar = []
    for i in range(1, n+1):
        bilesen = (etiketli == i)
        alan = bilesen.sum()
        if alan < MIN_ALAN:
            continue
        ys, xs = np.where(bilesen)
        cy, cx = ys.mean(), xs.mean()

        pre_p = kirp(pre, cx, cy)
        post_p = kirp(post, cx, cy)
        cva_p = kirp(cva, cx, cy)
        if pre_p.shape[:2] != (PATCH, PATCH):
            continue
        cva_p = cva_p / (cva_p.max() + 1e-8)

        with torch.no_grad():
            pre_tp = torch.from_numpy(pre_p.transpose(2,0,1)).float().unsqueeze(0).to(cihaz)
            post_tp = torch.from_numpy(post_p.transpose(2,0,1)).float().unsqueeze(0).to(cihaz)
            cva_tp = torch.from_numpy(cva_p[None]).float().unsqueeze(0).to(cihaz)
            cikti = cls_model(pre_tp, post_tp, cva_tp)
            olasiliklar = torch.softmax(cikti, dim=1)[0]
            # K-26: hasar esigi. argmax yerine, hasarli siniflarin (1,2,3)
            # toplam olasiligi HASAR_ESIGI ustundeyse hasarli sayilir.
            # 0.5 varsayilaniyla model her binayi hasarli goruyordu
            # (no-damage recall 0.039); 0.7 ile dengeli sonuc (0.684 / 0.740).
            hasar_olasilik = olasiliklar[1:].sum().item()
            if hasar_olasilik > HASAR_ESIGI:
                tahmin_idx = int(olasiliklar[1:].argmax().item()) + 1
            else:
                tahmin_idx = 0
            olasilik = olasiliklar[tahmin_idx].item()

        sonuclar.append({
            "cx": round(cx, 1), "cy": round(cy, 1), "alan_px": int(alan),
            "sinif": SINIFLAR[tahmin_idx], "guven": round(olasilik, 3),
        })

    print(f"\n[model 2] {len(sonuclar)} bina siniflandirildi")
    print(f"\n{'x':>7s} {'y':>7s} {'alan':>7s}  sinif             guven")
    for s in sonuclar:
        print(f"{s['cx']:7.1f} {s['cy']:7.1f} {s['alan_px']:7d}  {s['sinif']:16s} {s['guven']:.3f}")


if __name__ == "__main__":
    main()
