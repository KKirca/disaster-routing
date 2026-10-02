"""
Faz 3i - Maxar'dan K-18 CSV uretimi (v2, phase3g'nin yerine).

phase3g'nin sorunlari ve bu surumdeki karsiliklari:
  * footprint POINT + UTM        -> poligon (rasterio.features.shapes), WGS84
  * lon/lat aslinda UTM metre    -> pyproj ile EPSG:4326 + assertion
  * uid'de kodlanmis karo no     -> dosya adindan turetilen karo no
  * nodata kontrolu yok          -> nodata'li pencere atlanir
  * tek sabit pencere (5 bina)   -> phase3h CSV'sinden bbox ile secilen pencereler
  * guven sutunu aldatici        -> hasar_olasilik sutunu eklendi (K-26 esigi bununla)

Girdi : outputs/phase3h_kentsel_pencereler.csv (phase3h_kentsel_tarama.py uretir)
Cikti : outputs/phase3i_kilis_k18.csv
        K-18 sutunlari + hasar_olasilik, pencere_kenari, tile

SINIRLAR (bilinen):
  * Bitisik nizam bloklar Model 1'de tek bilesen olabilir -> area_m2 sismesi.
  * 64x64 (~20 m) patch, buyuk birlesik blok icin yetersiz.
  * Pencere kenarina degen bilesenler parcali olabilir (pencere_kenari=1).

KULLANIM (proje kokunden):
  python scripts/phase3i_k18_uretimi.py
  python scripts/phase3i_k18_uretimi.py --bbox 37.09 36.70 37.14 36.735
  python scripts/phase3i_k18_uretimi.py --max-pencere 50     # hizli deneme
"""
import argparse
import csv
import os
import random
import sys
from collections import Counter

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pyproj
import rasterio
import segmentation_models_pytorch as smp
import torch
from rasterio.features import shapes
from rasterio.windows import Window
from scipy import ndimage
from shapely import wkt as swkt
from shapely.geometry import shape
from shapely.ops import transform as shp_transform

sys.path.insert(0, "scripts")
from phase3_siamese_cnn import SiameseCVA, SINIFLAR, cva_magnitude
from phase3e_gorsel_rota import SEG_MODEL_YOLU, CLS_MODEL_YOLU, kirp, PATCH
from phase3c_kopru import HASAR_ESIGI                      # tek kaynak (K-26)
from phase3h_kentsel_tarama import (karo_dosyasi, nodata_orani, PRE_DIR,
                                    POST_DIR, PENCERE, MIN_ALAN, SEG_ESIK)

GIRDI_CSV = "outputs/phase3h_kentsel_pencereler.csv"
CIKTI_CSV = "outputs/phase3i_kilis_k18.csv"
VARSAYILAN_BBOX = (37.09, 36.70, 37.14, 36.735)   # lon_min lat_min lon_max lat_max
MAX_NODATA = 0.02
SADELESTIRME_M = 0.25      # poligon sadelestirme toleransi (metre)
SUTUNLAR = ["uid", "lon", "lat", "footprint_wkt", "area_m2", "damage_class",
            "confidence", "source", "hasar_olasilik", "pencere_kenari", "tile"]


def pencereleri_sec(bbox, min_bina, max_pencere):
    lon0, lat0, lon1, lat1 = bbox
    secilen = []
    with open(GIRDI_CSV) as f:
        for r in csv.DictReader(f):
            lon, lat = float(r["lon"]), float(r["lat"])
            if lon0 <= lon <= lon1 and lat0 <= lat <= lat1 and int(r["bina"]) >= min_bina:
                secilen.append({"karo": r["karo"], "x": int(r["x"]), "y": int(r["y"])})
    secilen.sort(key=lambda s: (s["karo"], s["y"], s["x"]))
    if max_pencere:
        secilen = secilen[:max_pencere]
    return secilen


def modelleri_yukle(cihaz):
    seg = smp.Unet(encoder_name="resnet18", encoder_weights=None,
                   in_channels=3, classes=1).to(cihaz)
    seg.load_state_dict(torch.load(SEG_MODEL_YOLU, map_location=cihaz, weights_only=True))
    seg.eval()
    cls = SiameseCVA(n_sinif=len(SINIFLAR)).to(cihaz)
    cls.load_state_dict(torch.load(CLS_MODEL_YOLU, map_location=cihaz, weights_only=True))
    cls.eval()
    return seg, cls


def siniflandir(cls_model, pre_l, post_l, cva_l, cihaz):
    """Patch listelerini toplu siniflandirir. Donus: (N, 4) olasiliklar."""
    cikti = []
    for i in range(0, len(pre_l), 256):
        s = slice(i, i + 256)
        pre_t = torch.from_numpy(np.stack(pre_l[s]).transpose(0, 3, 1, 2)).float().to(cihaz)
        post_t = torch.from_numpy(np.stack(post_l[s]).transpose(0, 3, 1, 2)).float().to(cihaz)
        cva_t = torch.from_numpy(np.stack(cva_l[s])[:, None]).float().to(cihaz)
        with torch.no_grad():
            cikti.append(torch.softmax(cls_model(pre_t, post_t, cva_t), dim=1).cpu().numpy())
    return np.concatenate(cikti) if cikti else np.zeros((0, len(SINIFLAR)))


BLUR_SIGMA = 0.0     # main() --blur ile ayarlar
KESKINLIK = []       # (pre, post) Laplace varyansi, pencere basina


def keskinlik(u8):
    """Keskinlik olcusu: gri goruntunun Laplace varyansi (buyuk = keskin)."""
    gri = u8.astype("float32").mean(axis=0)
    return float(ndimage.laplace(gri).var())


def sigma_sec(pencereler, n=20, adaylar=(0.5, 0.6, 0.7, 0.8, 0.9, 1.0)):
    """POST'u Gauss ile bulaniklastirip POST/PRE keskinlik oranini 1'e en yakin
    getiren sigma'yi secer.

    OLCUT KESKINLIK ORANIDIR, MODEL CIKTISI DEGIL: sigma'yi hasar oranina bakarak
    secmek dairesel olurdu (sonucu istedigimiz yone ceker). Burada hedef tek ve
    onceden belli: iki goruntunun keskinligi esit olsun.
    """
    adim = max(1, len(pencereler) // n)
    ornek = pencereler[::adim][:n]
    oranlar = {s: [] for s in adaylar}
    acik = {}
    try:
        for p in ornek:
            karo = p["karo"]
            if karo not in acik:
                acik[karo] = (rasterio.open(karo_dosyasi(PRE_DIR, karo)),
                              rasterio.open(karo_dosyasi(POST_DIR, karo)))
            sp, so = acik[karo]
            w = Window(p["x"], p["y"], PENCERE, PENCERE)
            pre = sp.read([1, 2, 3], window=w)
            post = so.read([1, 2, 3], window=w)
            kp = keskinlik(pre)
            for s in adaylar:
                bl = ndimage.gaussian_filter(post.astype("float32"), sigma=(0, s, s))
                oranlar[s].append(keskinlik(bl) / max(kp, 1e-6))
    finally:
        for a, b in acik.values():
            a.close()
            b.close()
    medyan = {s: float(np.median(v)) for s, v in oranlar.items()}
    for s, m in medyan.items():
        print(f"  sigma={s:.1f}  POST/PRE keskinlik orani (medyan) = {m:.2f}")
    return min(medyan, key=lambda s: abs(np.log(medyan[s])))


def lut_hesapla(sp, so, adim=16):
    """Karo bazinda post -> pre histogram eslemesi (quantile mapping), bant basina LUT.

    NEDEN KARO BAZINDA: pencere bazinda eslersek penceredeki gercek hasar da
    histogrami degistirir ve eslemeyle silinir. Karo olceginde (yuzlerce hektar)
    hasarli alan orani kucuktur, esleme yalnizca radyometrik farki yakalar.
    adim=16: 17408 px karoyu 1088 px'e indirgeyerek istatistik alir.
    """
    h, w = sp.height // adim, sp.width // adim
    pre = sp.read([1, 2, 3], out_shape=(3, h, w))
    post = so.read([1, 2, 3], out_shape=(3, h, w))
    gecerli = (pre.max(axis=0) > 0) & (post.max(axis=0) > 0)
    lut = np.zeros((3, 256), dtype=np.uint8)
    for b in range(3):
        p = np.sort(post[b][gecerli])
        q = np.sort(pre[b][gecerli])
        cdf_v = np.searchsorted(p, np.arange(256), side="right") / len(p)
        lut[b] = np.quantile(q, np.clip(cdf_v, 0, 1)).round().clip(0, 255)
    return lut


def ornek_sayfasi(ornekler, dosya, n=24):
    """Rastgele major/destroyed binalar icin PRE|POST kirpinti sayfasi (gorsel hakem)."""
    if not ornekler:
        return
    secim = random.Random(42).sample(ornekler, min(n, len(ornekler)))
    sut = 4
    sat = int(np.ceil(len(secim) / sut))
    fig, ax = plt.subplots(sat, sut, figsize=(sut * 4.2, sat * 2.3))
    ax = np.atleast_1d(ax).ravel()
    for a in ax:
        a.axis("off")
    for a, (sinif, p, img) in zip(ax, secim):
        a.imshow(np.clip(img, 0, 1))
        a.set_title(f"{sinif}  p={p:.2f}   (sol PRE | sag POST)", fontsize=8)
    fig.tight_layout()
    fig.savefig(dosya, dpi=80)
    plt.close(fig)


def pencere_isle(sp, so, tr, karo, x, y, seg_model, cls_model, cihaz,
                 lut=None, ornekler=None):
    w = Window(x, y, PENCERE, PENCERE)
    pre_u8 = sp.read([1, 2, 3], window=w)
    post_u8 = so.read([1, 2, 3], window=w)
    if nodata_orani(pre_u8) > MAX_NODATA or nodata_orani(post_u8) > MAX_NODATA:
        return None   # nodata -> atla
    KESKINLIK.append((keskinlik(pre_u8), keskinlik(post_u8)))   # esleme/bulaniklastirmadan ONCE
    if lut is not None:   # nodata kontrolunden SONRA esle (0 degeri LUT'a girmesin)
        post_u8 = np.stack([lut[b][post_u8[b]] for b in range(3)])
    if BLUR_SIGMA > 0:    # post'u pre'nin keskinligine yaklastir (test)
        post_u8 = ndimage.gaussian_filter(
            post_u8.astype("float32"), sigma=(0, BLUR_SIGMA, BLUR_SIGMA)
        ).round().clip(0, 255).astype("uint8")

    pre = np.moveaxis(pre_u8, 0, -1).astype("float32") / 255.0
    post = np.moveaxis(post_u8, 0, -1).astype("float32") / 255.0
    cva = cva_magnitude(pre * 255.0, post * 255.0)

    with torch.no_grad():
        t = torch.from_numpy(pre.transpose(2, 0, 1)).float().unsqueeze(0).to(cihaz)
        maske = torch.sigmoid(seg_model(t)).cpu().numpy()[0, 0] > SEG_ESIK
    etiketli, n = ndimage.label(maske)

    bilesenler, pre_l, post_l, cva_l, kirpinti_l = [], [], [], [], []
    for i in range(1, n + 1):
        b = etiketli == i
        if b.sum() < MIN_ALAN:
            continue
        ys, xs = np.where(b)
        cy, cx = ys.mean(), xs.mean()
        pre_p, post_p, cva_p = kirp(pre, cx, cy), kirp(post, cx, cy), kirp(cva, cx, cy)
        if pre_p.shape[:2] != (PATCH, PATCH):
            continue
        cva_p = cva_p / (cva_p.max() + 1e-8)
        kenar = int(ys.min() == 0 or xs.min() == 0 or
                    ys.max() == PENCERE - 1 or xs.max() == PENCERE - 1)
        bilesenler.append((i, kenar))
        pre_l.append(pre_p); post_l.append(post_p); cva_l.append(cva_p)
        kirpinti_l.append(np.concatenate([pre_p, post_p], axis=1))
    if not bilesenler:
        return []

    olas = siniflandir(cls_model, pre_l, post_l, cva_l, cihaz)

    # poligonlar (UTM, metre) -> id'ye gore
    pencere_tf = sp.window_transform(w)
    poligon = {}
    for geom, val in shapes(etiketli.astype("int32"), mask=etiketli > 0,
                            transform=pencere_tf, connectivity=4):
        poligon[int(val)] = shape(geom)

    satirlar = []
    for (i, kenar), p, kirpinti in zip(bilesenler, olas, kirpinti_l):
        g_utm = poligon.get(i)
        if g_utm is None or g_utm.is_empty:
            continue
        g_utm = g_utm.simplify(SADELESTIRME_M, preserve_topology=True)
        if g_utm.geom_type != "Polygon" or g_utm.is_empty:
            continue
        alan_m2 = g_utm.area
        g_wgs = shp_transform(tr.transform, g_utm)
        c = g_wgs.centroid

        hasar_olasilik = float(p[1:].sum())
        if hasar_olasilik > HASAR_ESIGI:               # K-26
            idx = int(p[1:].argmax()) + 1
        else:
            idx = 0
        if ornekler is not None and idx >= 2 and len(ornekler) < 400:
            ornekler.append((SINIFLAR[idx], hasar_olasilik, kirpinti))
        satirlar.append({
            "uid": f"{karo}_{x}_{y}_{i:03d}",
            "lon": round(c.x, 7), "lat": round(c.y, 7),
            "footprint_wkt": swkt.dumps(g_wgs, rounding_precision=7),
            "area_m2": round(alan_m2, 1),
            "damage_class": SINIFLAR[idx],
            "confidence": round(float(p[idx]), 3),
            "source": "model_v1",
            "hasar_olasilik": round(hasar_olasilik, 3),
            "pencere_kenari": kenar,
            "tile": karo,
        })
    return satirlar


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bbox", type=float, nargs=4, default=VARSAYILAN_BBOX,
                    metavar=("LON_MIN", "LAT_MIN", "LON_MAX", "LAT_MAX"))
    ap.add_argument("--min-bina", type=int, default=20)
    ap.add_argument("--max-pencere", type=int, default=0, help="0 = sinirsiz")
    ap.add_argument("--esle", action="store_true",
                    help="post'u karo bazinda pre histogramina esle (radyometri testi)")
    ap.add_argument("--blur", default="0",
                    help="post'a Gauss sigma (piksel) ya da 'auto': keskinlik eslemesiyle sec")
    args = ap.parse_args()
    global BLUR_SIGMA

    pencereler = pencereleri_sec(args.bbox, args.min_bina, args.max_pencere)
    print(f"[secim] {len(pencereler)} pencere (bbox={args.bbox}, min_bina={args.min_bina})")
    if not pencereler:
        sys.exit("Pencere yok: bbox ya da --min-bina degerini gevset")

    if args.blur == "auto":
        print("[blur] sigma keskinlik eslemesiyle seciliyor:")
        BLUR_SIGMA = sigma_sec(pencereler)
        print(f"[blur] secilen sigma = {BLUR_SIGMA}")
    else:
        BLUR_SIGMA = float(args.blur)
    etiket = ("_esle" if args.esle else "") + (f"_blur{BLUR_SIGMA:g}" if BLUR_SIGMA > 0 else "")
    cikti_csv = CIKTI_CSV.replace(".csv", f"{etiket}.csv")

    cihaz = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    seg_model, cls_model = modelleri_yukle(cihaz)

    tumu, atlanan, ornekler = [], 0, []
    karolar = sorted({p["karo"] for p in pencereler})
    for karo in karolar:
        pre_yol, post_yol = karo_dosyasi(PRE_DIR, karo), karo_dosyasi(POST_DIR, karo)
        with rasterio.open(pre_yol) as sp, rasterio.open(post_yol) as so:
            tr = pyproj.Transformer.from_crs(sp.crs, "EPSG:4326", always_xy=True)
            lut = lut_hesapla(sp, so) if args.esle else None
            if lut is not None:
                print(f"  {karo}: histogram LUT hesaplandi")
            liste = [p for p in pencereler if p["karo"] == karo]
            for k, p in enumerate(liste, 1):
                s = pencere_isle(sp, so, tr, karo, p["x"], p["y"],
                                 seg_model, cls_model, cihaz,
                                 lut=lut, ornekler=ornekler)
                if s is None:
                    atlanan += 1
                else:
                    tumu += s
                if k % 25 == 0 or k == len(liste):
                    print(f"  {karo}: {k}/{len(liste)} pencere, {len(tumu)} bina")

    if not tumu:
        sys.exit("Hic bina uretilmedi")

    # koordinat assertion'lari: WGS84 derece olmak ZORUNDA, bbox civarinda olmali
    lons = np.array([r["lon"] for r in tumu]); lats = np.array([r["lat"] for r in tumu])
    assert (np.abs(lons) <= 180).all() and (np.abs(lats) <= 90).all(), "lon/lat derece degil"
    tol = 0.01
    assert lons.min() >= args.bbox[0] - tol and lons.max() <= args.bbox[2] + tol, "lon bbox disinda"
    assert lats.min() >= args.bbox[1] - tol and lats.max() <= args.bbox[3] + tol, "lat bbox disinda"

    os.makedirs("outputs", exist_ok=True)
    with open(cikti_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=SUTUNLAR)
        w.writeheader()
        w.writerows(tumu)

    sayfa = f"outputs/phase3i_hasarli_ornek{etiket}.png"
    ornek_sayfasi(ornekler, sayfa)

    sayac = Counter(r["damage_class"] for r in tumu)
    ho = np.array([r["hasar_olasilik"] for r in tumu])
    print(f"\n[kaydedildi] {cikti_csv}  ({len(tumu)} bina, {atlanan} pencere nodata ile atlandi)")
    print(f"[gorsel hakem] {sayfa}  (rastgele major/destroyed ornekleri)")
    print(f"[bbox] lon {lons.min():.4f}..{lons.max():.4f}  lat {lats.min():.4f}..{lats.max():.4f}")
    if KESKINLIK:
        oran = np.array([q / max(p, 1e-6) for p, q in KESKINLIK])
        print(f"[keskinlik] POST/PRE Laplace-varyans orani: medyan {np.median(oran):.2f}, "
              f"pencerelerin %{100 * (oran > 1).mean():.0f}'inde POST daha keskin")
    print("\n--- sinif dagilimi (K-26 esigi 0.7) ---")
    for s in SINIFLAR:
        print(f"  {s:14s} {sayac[s]:6d}  {100 * sayac[s] / len(tumu):5.1f}%")
    print("\n--- hasar_olasilik dagilimi ---")
    for lo, hi in [(0, .1), (.1, .3), (.3, .5), (.5, .7), (.7, .9), (.9, 1.01)]:
        n = int(((ho >= lo) & (ho < hi)).sum())
        print(f"  {lo:.1f}-{min(hi, 1):.1f}  {n:6d}  {100 * n / len(ho):5.1f}%")


if __name__ == "__main__":
    main()
