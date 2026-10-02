"""
Faz 3h - Maxar karolarinda kentsel pencere taramasi.

AMAC: phase3g tek bir sabit pencere (kirsal, ust 1/3 nodata) ile 5 binalik CSV
uretti. Burada pre+post'u eslesen karolar 512x512 pencerelerle taranir, nodata
olan pencereler elenir, Model 1 ile bina sayilir, en yogun pencereler siralanir.

NEDEN NODATA ELENIR: bir goruntude 0, digerinde dolu piksel varsa CVA orada
maksimuma cikar ve Model 2 bunu "hasar" okur. Nodata'li pencerede hasar
tahmini yapmak olcum degil artefakttir.

KULLANIM (proje kokunden):
  python scripts/phase3h_kentsel_tarama.py
  python scripts/phase3h_kentsel_tarama.py --karolar 031133031130 031133031132
  python scripts/phase3h_kentsel_tarama.py --stride 256 --min-bina 15

CIKTI:
  outputs/phase3h_kentsel_pencereler.csv   tum kabul edilen pencereler, bina sayisina gore
  outputs/phase3h_onizleme_1..3.png        en yogun 3 pencere (pre | pre+maske | post)
"""
import argparse
import csv
import glob
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import rasterio
import segmentation_models_pytorch as smp
import torch
from rasterio.warp import transform as warp_transform
from rasterio.windows import Window
from scipy import ndimage

sys.path.insert(0, "scripts")
from phase3e_gorsel_rota import SEG_MODEL_YOLU

PRE_DIR = "data/maxar/pre"
POST_DIR = "data/maxar/post"
PENCERE = 512
MIN_ALAN = 20        # piksel; phase3c/3g ile ayni
SEG_ESIK = 0.5       # phase3c/3g ile ayni
BATCH = 16
CIKTI_CSV = "outputs/phase3h_kentsel_pencereler.csv"


def karo_dosyasi(klasor, karo):
    adaylar = glob.glob(f"{klasor}/*_{karo}_*.tif")
    if not adaylar:
        raise FileNotFoundError(f"{klasor} icinde karo {karo} yok")
    return adaylar[0]


def nodata_orani(arr):
    """arr: (bant, y, x). Tum bantlari 0 olan piksel orani."""
    return float((arr == 0).all(axis=0).mean())


def model_yukle(cihaz):
    m = smp.Unet(encoder_name="resnet18", encoder_weights=None,
                 in_channels=3, classes=1).to(cihaz)
    m.load_state_dict(torch.load(SEG_MODEL_YOLU, map_location=cihaz,
                                 weights_only=True))
    m.eval()
    return m


def segmente_et(model, pre_listesi, cihaz):
    """pre_listesi: [(3,H,W) uint8]. Donus: [(H,W) bool maske]."""
    x = np.stack(pre_listesi).astype("float32") / 255.0
    with torch.no_grad():
        t = torch.from_numpy(x).to(cihaz)
        p = torch.sigmoid(model(t)).cpu().numpy()[:, 0]
    return p > SEG_ESIK


def bina_say(maske):
    etiketli, n = ndimage.label(maske)
    if n == 0:
        return 0
    alanlar = ndimage.sum(maske, etiketli, index=range(1, n + 1))
    return int((np.asarray(alanlar) >= MIN_ALAN).sum())


def tara_karo(karo, model, cihaz, stride, max_nodata):
    pre_yol = karo_dosyasi(PRE_DIR, karo)
    post_yol = karo_dosyasi(POST_DIR, karo)
    sonuc = []
    toplam = elenen = 0

    with rasterio.open(pre_yol) as sp, rasterio.open(post_yol) as so:
        if (sp.width, sp.height) != (so.width, so.height):
            raise ValueError(f"{karo}: pre/post boyutlari farkli")
        if sp.transform != so.transform:
            print(f"  [uyari] {karo}: pre/post transform farkli, hizalama dogrulanmali")

        bekleyen = []   # (x, y, pre_arr, nd_pre, nd_post)

        def bosalt():
            if not bekleyen:
                return
            maskeler = segmente_et(model, [b[2] for b in bekleyen], cihaz)
            for (x, y, _, ndp, ndq), mask in zip(bekleyen, maskeler):
                cx, cy = sp.transform * (x + PENCERE / 2, y + PENCERE / 2)
                lon, lat = warp_transform(sp.crs, "EPSG:4326", [cx], [cy])
                sonuc.append({
                    "karo": karo, "x": x, "y": y,
                    "bina": bina_say(mask),
                    "bina_alan_orani": round(float(mask.mean()), 3),
                    "nodata_pre": round(ndp, 4), "nodata_post": round(ndq, 4),
                    "lon": round(lon[0], 5), "lat": round(lat[0], 5),
                })
            bekleyen.clear()

        for y in range(0, sp.height - PENCERE + 1, stride):
            for x in range(0, sp.width - PENCERE + 1, stride):
                toplam += 1
                w = Window(x, y, PENCERE, PENCERE)
                pre = sp.read([1, 2, 3], window=w)
                ndp = nodata_orani(pre)
                if ndp > max_nodata:
                    elenen += 1
                    continue
                post = so.read([1, 2, 3], window=w)
                ndq = nodata_orani(post)
                if ndq > max_nodata:
                    elenen += 1
                    continue
                bekleyen.append((x, y, pre, ndp, ndq))
                if len(bekleyen) >= BATCH:
                    bosalt()
        bosalt()

    print(f"  {karo}: {toplam} pencere, {elenen} nodata nedeniyle elendi, "
          f"{len(sonuc)} kabul")
    return sonuc, pre_yol, post_yol


def onizleme(satir, pre_yol, post_yol, model, cihaz, dosya):
    w = Window(satir["x"], satir["y"], PENCERE, PENCERE)
    with rasterio.open(pre_yol) as sp:
        pre = sp.read([1, 2, 3], window=w)
    with rasterio.open(post_yol) as so:
        post = so.read([1, 2, 3], window=w)
    maske = segmente_et(model, [pre], cihaz)[0]

    fig, ax = plt.subplots(1, 3, figsize=(18, 6))
    ax[0].imshow(np.moveaxis(pre, 0, -1)); ax[0].set_title("PRE")
    ax[1].imshow(np.moveaxis(pre, 0, -1))
    ax[1].contour(maske, levels=[0.5], colors="red", linewidths=0.8)
    ax[1].set_title(f"PRE + Model 1 maske ({satir['bina']} bina)")
    ax[2].imshow(np.moveaxis(post, 0, -1)); ax[2].set_title("POST")
    for a in ax:
        a.axis("off")
    fig.suptitle(f"{satir['karo']} x={satir['x']} y={satir['y']}  "
                 f"lon={satir['lon']} lat={satir['lat']}")
    fig.tight_layout()
    fig.savefig(dosya, dpi=90)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--karolar", nargs="+",
                    default=["031133031130", "031133031132"],
                    help="pre+post'u eslesen karo ID'leri")
    ap.add_argument("--stride", type=int, default=512)
    ap.add_argument("--max-nodata", type=float, default=0.02)
    ap.add_argument("--min-bina", type=int, default=1,
                    help="CSV'ye yazilacak en az bina sayisi")
    args = ap.parse_args()

    cihaz = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("[cihaz]", cihaz)
    model = model_yukle(cihaz)

    hepsi = []
    yollar = {}
    for karo in args.karolar:
        print(f"[tarama] {karo}")
        sonuc, pre_yol, post_yol = tara_karo(karo, model, cihaz,
                                             args.stride, args.max_nodata)
        hepsi += sonuc
        yollar[karo] = (pre_yol, post_yol)

    hepsi = [s for s in hepsi if s["bina"] >= args.min_bina]
    hepsi.sort(key=lambda s: -s["bina"])

    os.makedirs("outputs", exist_ok=True)
    if hepsi:
        with open(CIKTI_CSV, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(hepsi[0].keys()))
            w.writeheader()
            w.writerows(hepsi)
        print(f"\n[kaydedildi] {CIKTI_CSV}  ({len(hepsi)} pencere)")
    else:
        print("\n[sonuc] hicbir pencerede bina bulunamadi")
        return

    print(f"\n{'karo':14s} {'x':>6s} {'y':>6s} {'bina':>5s} {'alan%':>6s} "
          f"{'nd_pre':>7s} {'nd_post':>8s}  lon, lat")
    for s in hepsi[:10]:
        print(f"{s['karo']:14s} {s['x']:6d} {s['y']:6d} {s['bina']:5d} "
              f"{100 * s['bina_alan_orani']:6.1f} {s['nodata_pre']:7.4f} "
              f"{s['nodata_post']:8.4f}  {s['lon']}, {s['lat']}")

    for i, s in enumerate(hepsi[:3], 1):
        pre_yol, post_yol = yollar[s["karo"]]
        dosya = f"outputs/phase3h_onizleme_{i}.png"
        onizleme(s, pre_yol, post_yol, model, cihaz, dosya)
        print(f"[onizleme] {dosya}")


if __name__ == "__main__":
    main()
