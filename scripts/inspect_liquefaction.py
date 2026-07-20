"""
Faz 1 — Likefaksiyon, Adim B: Raster (GeoTIFF) verisini INCELE.

Amac: indirdigimiz likefaksiyon olasilik rasterini tanimak.
  - Kac bant, kac satir/sutun (izgara boyutu)?
  - CRS ne? (grafimiz EPSG:4326)
  - Deger araligi ne? (olasilik bekliyoruz: 0-1)
  - Cografi olarak nerede? (bounds)
  - Gorsel: sicaklik haritasi gibi ciz.

Calistirma:
    cd ~/disaster-routing
    conda activate disaster
    python scripts/inspect_liquefaction.py
"""

import glob
import numpy as np
import rasterio
import matplotlib.pyplot as plt

# data/ icindeki .tif dosyalarini bul.
tifs = glob.glob("data/*.tif") + glob.glob("data/*.tiff")
if not tifs:
    raise SystemExit(
        "data/ icinde .tif bulunamadi. Ground Failure paketini indirip "
        "likefaksiyon GeoTIFF'ini data/ klasorune koydun mu?"
    )

# Birden fazla tif varsa (likefaksiyon + heyelan), adinda 'liq' geceni sec.
liq = [t for t in tifs if "liq" in t.lower()]
path = liq[0] if liq else tifs[0]
print(f"[dosya] bulunan tif'ler: {tifs}")
print(f"[dosya] secilen: {path}")

with rasterio.open(path) as src:
    print(f"[CRS ] koordinat sistemi: {src.crs}")
    print(f"[boyut] (satir, sutun): {src.shape}")
    print(f"[bant] bant sayisi: {src.count}")
    print(f"[coz ] piksel cozunurlugu: {src.res}")
    print(f"[alan] sinirlar: {src.bounds}")
    print(f"[nodata] nodata degeri: {src.nodata}")
    band = src.read(1).astype("float32")   # ilk bandi oku
    nodata = src.nodata

# nodata hucrelerini NaN yap ki istatistigi bozmasin
if nodata is not None:
    band[band == nodata] = np.nan

print(f"[deger] min={np.nanmin(band):.4f}, max={np.nanmax(band):.4f}, "
      f"ortalama={np.nanmean(band):.4f}")

# Gorsel: olasilik haritasi (sicaklik haritasi gibi)
plt.figure(figsize=(9, 7))
plt.imshow(band, cmap="viridis")
plt.colorbar(label="likefaksiyon olasiligi")
plt.title("Likefaksiyon olasilik rasteri (ham veri)")
plt.savefig("outputs/liquefaction_raw.png", dpi=150, bbox_inches="tight")
print("[ciz ] kaydedildi: outputs/liquefaction_raw.png")