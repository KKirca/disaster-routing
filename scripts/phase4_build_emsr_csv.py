"""
Faz 4 — Kahramanmars transferi: EMSR648 -> K-18 CSV donusumu.

EMSR648 sema esmesi (K-21):
  Destroyed         -> destroyed        (confidence=1.0)
  Damaged           -> major-damage     (confidence=1.0)
  No visible damage -> no-damage        (confidence=1.0)
  Possibly damaged  -> possibly-damaged (confidence=0.0)

minor-damage EMSR648'de karsilıksız: K-19'daki 0.15 agirligi bu kosuda
devreye girmez. Formul calisir ama bir bileseni olu kalir (tezde belirtilecek).

Cikti: data/damage/kahramanmaras_emsr648.csv  (K-18 semasi)

NOT: LC_ALL=C ile calistirin.
KULLANIM:
  LC_ALL=C python scripts/phase4_build_emsr_csv.py
"""
import csv, os, glob
import geopandas as gpd
from shapely.ops import transform
import pyproj

AOI = "AOI17"
EMSR_DIR = "data/emsr648"
OUT_CSV = "data/damage/kahramanmaras_emsr648.csv"
METRIC_CRS = "EPSG:32637"   # UTM 37N — Kahramanmaras

ESLESME = {
    "Destroyed":          ("destroyed",         1.0),
    "Damaged":            ("major-damage",       1.0),
    "No visible damage":  ("no-damage",          1.0),
    "Possibly damaged":   ("possibly-damaged",   0.0),
}

_to_metric = pyproj.Transformer.from_crs(
    "EPSG:4326", METRIC_CRS, always_xy=True).transform


def main():
    pattern = f"{EMSR_DIR}/*{AOI}*/*_builtUpA_*.shp"
    dosyalar = sorted(glob.glob(pattern))
    if not dosyalar:
        raise SystemExit(f"Shapefile bulunamadi: {pattern}")

    gdf = gpd.read_file(dosyalar[0])
    print(f"[okuma] {dosyalar[0].split('/')[-1]}")
    print(f"        {len(gdf)} bina, CRS: {gdf.crs}")

    os.makedirs("data/damage", exist_ok=True)
    satirlar = []
    sayac = {k: 0 for k in list(ESLESME.values()) + [("atildi", 0)]}

    for i, row in gdf.iterrows():
        dmg_gra = row.get("damage_gra", "")
        if dmg_gra not in ESLESME:
            sayac[("atildi", 0)] = sayac.get(("atildi", 0), 0) + 1
            continue

        damage_class, confidence = ESLESME[dmg_gra]
        poly_wgs = row.geometry
        if poly_wgs is None:
            continue

        c = poly_wgs.centroid
        poly_m = transform(_to_metric, poly_wgs)
        area = poly_m.area

        uid = str(row.get("or_src_id", f"emsr_{i}"))
        satirlar.append({
            "uid":           uid,
            "lon":           f"{c.x:.7f}",
            "lat":           f"{c.y:.7f}",
            "footprint_wkt": poly_wgs.wkt,
            "area_m2":       f"{area:.1f}",
            "damage_class":  damage_class,
            "confidence":    confidence,
            "source":        "emsr648",
            "tile":          AOI,
        })
        sayac[(damage_class, confidence)] = \
            sayac.get((damage_class, confidence), 0) + 1

    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "uid", "lon", "lat", "footprint_wkt", "area_m2",
            "damage_class", "confidence", "source", "tile"])
        w.writeheader()
        w.writerows(satirlar)

    print(f"\n[cikti] {OUT_CSV}  ({len(satirlar)} kayit)")
    print("\n--- sinif dagilimi ---")
    for (cls, conf), n in sorted(sayac.items(), key=lambda x: -x[1]):
        if n > 0:
            print(f"  {n:5d}  {cls}  (conf={conf})")

    agir = sum(n for (cls, _), n in sayac.items()
               if cls in ("destroyed", "major-damage"))
    belirsiz = sayac.get(("possibly-damaged", 0.0), 0)
    print(f"\n[ozet] agir hasarli: {agir}  belirsiz: {belirsiz}  "
          f"toplam: {len(satirlar)}")


if __name__ == "__main__":
    main()
