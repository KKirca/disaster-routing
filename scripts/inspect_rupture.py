"""
Faz 1 — Gercek veri, Adim B: Fay ruptur verisini INCELE (henuz entegre etme).

Amac: indirdigimiz geoJSON'i tanimak.
  - Koordinat sistemi (CRS) ne? OSMnx grafi EPSG:4326 (lat/lon) kullanir;
    ruptur verisi de ayni mi, farkli mi?
  - Kac cizgi (feature) var?
  - Cografi sinirlar (bounds) nerede? Yani hat harita uzerinde nerede?

Calistirma:
    cd ~/disaster-routing
    conda activate disaster
    python scripts/inspect_rupture.py
"""

import glob
import geopandas as gpd
import matplotlib.pyplot as plt

# data/ icindeki ilk .geojson dosyasini otomatik bul.
# Eger .shp indirdiysen, asagidaki pattern'i "data/*.shp" yap.
candidates = glob.glob("data/*.geojson") + glob.glob("data/*.json")
if not candidates:
    raise SystemExit(
        "data/ icinde .geojson bulunamadi. "
        "Dosyayi indirip data/ klasorune koydun mu? "
        "(.shp indirdiysen script'teki glob desenini 'data/*.shp' yap.)"
    )

path = candidates[0]
print(f"[dosya] okunuyor: {path}")

gdf = gpd.read_file(path)

# --- Temel bilgiler ---
print(f"[CRS ] koordinat sistemi: {gdf.crs}")
print(f"[adet] feature (cizgi) sayisi: {len(gdf)}")
print(f"[tip ] geometri tipleri: {gdf.geom_type.unique()}")
print(f"[alan] sinirlar (minx, miny, maxx, maxy):\n       {gdf.total_bounds}")
print(f"[stun] oznitelik sutunlari: {list(gdf.columns)}")

# --- Gorsel: rupturu tek basina ciz ---
fig, ax = plt.subplots(figsize=(8, 8))
gdf.plot(ax=ax, color="red", linewidth=1)
ax.set_title("Fay ruptur hatti (ham veri)")
ax.set_xlabel("boylam (lon)")
ax.set_ylabel("enlem (lat)")
fig.savefig("outputs/rupture_raw.png", dpi=150, bbox_inches="tight")
print("[ciz ] kaydedildi: outputs/rupture_raw.png")