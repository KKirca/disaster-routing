"""
Faz 4 — Adim 1: xBD etiketlerinden kopru katmani girdi tablosunu uret.

K-18 sozlesmesi (revize):
    uid,lon,lat,footprint_wkt,area_m2,damage_class,confidence,source
    footprint_wkt: bina poligonu (WGS84). Mesafe hesabi centroid'den DEGIL
    poligondan yapilir — enkaz binanin merkezinden degil CEPHESINDEN dokulur.
    50x50 m bir binanin merkezi yoldan 51 m uzakta olabilir ama cephesi 26 m'de.
    area_m2: taban alani (EPSG:32614'te hesaplanir), enkaz hacmi vekili.
    Koordinat: WGS84 (EPSG:4326) — xBD'nin lng_lat blogu
    no-damage binalar DAHIL (yogunluk normalizasyonu icin)
    confidence: ground truth icin 1.0
    source: 'xbd_gt'

Neden ara tablo: Faz 4 ne .npz okur ne modeli cagirir. Girdisi sabit semali
bir CSV'dir. Boylece (a) sonuclar tekrarlanabilir, (b) rota hatasinin modelde
mi kopru katmaninda mi oldugu ayirt edilebilir, (c) ayni bolgede xbd_gt ve
model ciktisiyla iki kosu yapilip modelin hatasinin rotaya ne kadar yansidigi
olculebilir.

KULLANIM:
  cd ~/disaster-routing
  python scripts/phase4_build_damage_csv.py
"""

import csv
import glob
import json
import os
from collections import Counter

from shapely import wkt
from shapely.ops import transform
import pyproj

DISASTER = "mexico-earthquake"          # K-17
LABEL_GLOB = f"data/xbd/train/labels/{DISASTER}_*_post_disaster.json"
OUT_DIR = "data/damage"
OUT_CSV = f"{OUT_DIR}/{DISASTER}_xbd_gt.csv"

VALID = {"no-damage", "minor-damage", "major-damage", "destroyed"}
HEAVY = {"major-damage", "destroyed"}   # yol tikayabilecek siniflar
METRIC_CRS = "EPSG:32614"               # UTM 14N — alan hesabi icin

# Alan WGS84'te hesaplanamaz (derece^2 anlamsizdir); metrik projeksiyon sart.
_to_metric = pyproj.Transformer.from_crs(
    "EPSG:4326", METRIC_CRS, always_xy=True).transform


def main():
    files = sorted(glob.glob(LABEL_GLOB))
    if not files:
        raise SystemExit(f"Etiket dosyasi bulunamadi: {LABEL_GLOB}")

    rows = []
    skipped = Counter()

    for path in files:
        tile = os.path.basename(path).replace("_post_disaster.json", "")
        with open(path) as f:
            data = json.load(f)

        for ft in data["features"].get("lng_lat", []):
            props = ft.get("properties", {})
            cls = props.get("subtype")

            # un-classified ve etiketsiz kayitlar disarida: hasar bilgisi
            # olmayan bina skor hesabina katilamaz.
            if cls not in VALID:
                skipped[cls or "YOK"] += 1
                continue

            poly = wkt.loads(ft["wkt"])
            c = poly.centroid
            area = transform(_to_metric, poly).area
            rows.append({
                "uid": props.get("uid", ""),
                "lon": f"{c.x:.7f}",
                "lat": f"{c.y:.7f}",
                "footprint_wkt": poly.wkt,
                "area_m2": f"{area:.1f}",
                "damage_class": cls,
                "confidence": "1.0",
                "source": "xbd_gt",
                "tile": tile,
            })

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT_CSV, "w", newline="") as f:
        w = csv.DictWriter(
            f, fieldnames=["uid", "lon", "lat", "footprint_wkt", "area_m2",
                           "damage_class", "confidence", "source", "tile"])
        w.writeheader()
        w.writerows(rows)

    dist = Counter(r["damage_class"] for r in rows)
    heavy = sum(v for k, v in dist.items() if k in HEAVY)

    print(f"[karo]  {len(files)}")
    print(f"[bina]  {len(rows)} yazildi -> {OUT_CSV}")
    if skipped:
        print(f"[atlan] {sum(skipped.values())} kayit: "
              f"{dict(skipped)}")
    print("\n--- sinif dagilimi ---")
    for k in ["no-damage", "minor-damage", "major-damage", "destroyed"]:
        print(f"{dist.get(k, 0):7d}  {k}")
    print(f"\n[agir hasarli (major+destroyed)] {heavy}")

    ha = [float(r["area_m2"]) for r in rows if r["damage_class"] in HEAVY]
    if ha:
        ha.sort()
        print(f"[agir hasarli taban alani] min {ha[0]:.0f}  "
              f"medyan {ha[len(ha)//2]:.0f}  max {ha[-1]:.0f} m2")

    lons = [float(r["lon"]) for r in rows]
    lats = [float(r["lat"]) for r in rows]
    print(f"[kapsam] lon {min(lons):.4f}..{max(lons):.4f}  "
          f"lat {min(lats):.4f}..{max(lats):.4f}")


if __name__ == "__main__":
    main()
