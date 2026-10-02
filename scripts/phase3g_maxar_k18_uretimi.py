"""
Faz 3g - Maxar goruntusunden K-18 formatinda CSV uretimi.

Model 1 (bina tespiti) + Model 2 (hasar siniflandirma), coğrafi
referansli bir Maxar patch'ine uygulanir. Sonuc, Faz 4'un bekledigi
K-18 semasinda bir CSV olur: uid, lon, lat, footprint_wkt, area_m2,
damage_class, confidence, source.

Bu, K-27'nin coğrafi referans sorununu COZER - EBD_TR yerine
coğrafi referansli Maxar kullanilir.

KULLANIM:
  python scripts/phase3g_maxar_k18_uretimi.py
"""
import csv
import numpy as np
import rasterio
import torch
import segmentation_models_pytorch as smp
from scipy import ndimage
import sys

sys.path.insert(0, "scripts")
from phase3_siamese_cnn import SiameseCVA, SINIFLAR, cva_magnitude
from phase3e_gorsel_rota import SEG_MODEL_YOLU, CLS_MODEL_YOLU, kirp, PATCH

MAXAR_PRE = "data/maxar/pre/10300100E18A1000_37_031133031121_10300100E18A1000.tif"
MAXAR_POST_DIR = "data/maxar/post"
PENCERE_X, PENCERE_Y = 14336, 10240
PENCERE_BOYUT = 512
MIN_ALAN = 20
HASAR_ESIGI = 0.7
CIKTI_CSV = "outputs/phase3g_maxar_hasar.csv"


def post_dosyasini_bul(pre_yolu):
    """Pre dosyasinin karo ID'sine gore eslesen post dosyasini bulur."""
    import glob
    import os
    karo_id = os.path.basename(pre_yolu).split("_")[2]
    adaylar = glob.glob(f"{MAXAR_POST_DIR}/*{karo_id}*.tif")
    if not adaylar:
        raise FileNotFoundError(f"Karo {karo_id} icin post goruntu bulunamadi")
    return adaylar[0]


def main():
    cihaz = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("[cihaz]", cihaz)

    post_yolu = post_dosyasini_bul(MAXAR_PRE)
    print("[post]", post_yolu)

    pencere = rasterio.windows.Window(PENCERE_X, PENCERE_Y, PENCERE_BOYUT, PENCERE_BOYUT)
    with rasterio.open(MAXAR_PRE) as src:
        pre_data = src.read([1, 2, 3], window=pencere)
        patch_transform = src.window_transform(pencere)
        crs = src.crs
        piksel_boyu = src.res[0]  # metre/piksel

    with rasterio.open(post_yolu) as src:
        post_data = src.read([1, 2, 3], window=pencere)

    pre = np.moveaxis(pre_data, 0, -1).astype("float32") / 255.0
    post = np.moveaxis(post_data, 0, -1).astype("float32") / 255.0
    cva = cva_magnitude(pre * 255.0, post * 255.0)

    print("[koordinat] CRS:", crs, " piksel boyu:", round(piksel_boyu, 2), "m")

    seg_model = smp.Unet(encoder_name="resnet18", encoder_weights=None,
                         in_channels=3, classes=1).to(cihaz)
    seg_model.load_state_dict(torch.load(SEG_MODEL_YOLU, map_location=cihaz,
                                         weights_only=True))
    seg_model.eval()

    cls_model = SiameseCVA(n_sinif=len(SINIFLAR)).to(cihaz)
    cls_model.load_state_dict(torch.load(CLS_MODEL_YOLU, map_location=cihaz,
                                         weights_only=True))
    cls_model.eval()

    with torch.no_grad():
        pre_t = torch.from_numpy(pre.transpose(2, 0, 1)).float().unsqueeze(0).to(cihaz)
        seg_tahmin = torch.sigmoid(seg_model(pre_t)).cpu().numpy()[0, 0]

    ikili = seg_tahmin > 0.5
    etiketli, n = ndimage.label(ikili)
    print(f"[model 1] {n} bina bulundu")

    satirlar = []
    for i in range(1, n + 1):
        bilesen = (etiketli == i)
        alan_px = bilesen.sum()
        if alan_px < MIN_ALAN:
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
            pre_tp = torch.from_numpy(pre_p.transpose(2, 0, 1)).float().unsqueeze(0).to(cihaz)
            post_tp = torch.from_numpy(post_p.transpose(2, 0, 1)).float().unsqueeze(0).to(cihaz)
            cva_tp = torch.from_numpy(cva_p[None]).float().unsqueeze(0).to(cihaz)
            cikti = cls_model(pre_tp, post_tp, cva_tp)
            olasiliklar = torch.softmax(cikti, dim=1)[0]
            hasar_olasilik = olasiliklar[1:].sum().item()
            if hasar_olasilik > HASAR_ESIGI:
                sinif_idx = int(olasiliklar[1:].argmax().item()) + 1
            else:
                sinif_idx = 0
            guven = olasiliklar[sinif_idx].item()

        # Piksel -> coğrafi koordinat (K-18 semasi icin lon/lat gerekir,
        # burada UTM/EPSG:32637 veriyoruz - Faz 4'un projeksiyon
        # beklentisiyle karsilastirilip gerekirse WGS84'e cevrilecek)
        utm_x, utm_y = patch_transform * (cx, cy)
        alan_m2 = alan_px * (piksel_boyu ** 2)

        satirlar.append({
            "uid": f"maxar_031303_{i:04d}",
            "lon": round(utm_x, 2),
            "lat": round(utm_y, 2),
            "footprint_wkt": f"POINT({utm_x:.2f} {utm_y:.2f})",
            "area_m2": round(alan_m2, 1),
            "damage_class": SINIFLAR[sinif_idx],
            "confidence": round(guven, 3),
            "source": "model_v1",
        })

    print(f"[model 2] {len(satirlar)} bina siniflandirildi")

    import os
    os.makedirs("outputs", exist_ok=True)
    with open(CIKTI_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["uid", "lon", "lat", "footprint_wkt",
                                          "area_m2", "damage_class", "confidence", "source"])
        w.writeheader()
        w.writerows(satirlar)

    print(f"\n[kaydedildi] {CIKTI_CSV}")
    print(f"[not] CRS={crs} (UTM/metre, WGS84 lon/lat degil - Faz 4 ile karsilastirilirken donusum gerekebilir)")


if __name__ == "__main__":
    main()
