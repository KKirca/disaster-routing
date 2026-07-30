"""
Faz 2 — 2b: Copernicus EMSR648 vektor paketini INCELE.

Amac: indirdigimiz referans etiket paketini tanimak.
  - Pakette hangi shapefile'lar var, ne ise yariyorlar?
  - Geometri tipleri ne? (nokta / cizgi / alan)
  - Hasar kategorileri hangi sutunda ve hangi degerlerde?
  - Kac kayit var, dagilim nasil?

Bu bilgiler olmadan xBD ile sema eslemesi yapamayiz.

Calistirma:
    cd ~/disaster-routing
    conda activate disaster
    python scripts/inspect_emsr648.py
"""

import glob
import os

import geopandas as gpd
import matplotlib.pyplot as plt

SEARCH_DIR = "data/emsr648"

# Hasar derecesi tutmasi muhtemel sutun adlari (Copernicus surumlere gore degisir)
DAMAGE_HINTS = ["damage", "grading", "grade", "dmg", "notation", "obj_desc", "class"]


def find_files():
    shp = glob.glob(f"{SEARCH_DIR}/**/*.shp", recursive=True)
    gj = glob.glob(f"{SEARCH_DIR}/**/*.geojson", recursive=True)
    gpkg = glob.glob(f"{SEARCH_DIR}/**/*.gpkg", recursive=True)
    return sorted(shp + gj + gpkg)


def main():
    os.makedirs("outputs", exist_ok=True)

    files = find_files()
    if not files:
        raise SystemExit(
            f"{SEARCH_DIR} icinde .shp/.geojson/.gpkg bulunamadi.\n"
            "EMSR648 Vector Package'i indirip bu klasore actin mi?"
        )

    print(f"[paket] {len(files)} vektor dosyasi bulundu:\n")

    damage_layers = []   # hasar bilgisi tasiyan katmanlari topla

    for path in files:
        name = os.path.basename(path)
        try:
            gdf = gpd.read_file(path)
        except Exception as e:
            print(f"  ! {name}: okunamadi ({e})")
            continue

        geom_types = list(gdf.geom_type.dropna().unique())
        print(f"  {name}")
        print(f"      kayit : {len(gdf)}")
        print(f"      geom  : {geom_types}")
        print(f"      CRS   : {gdf.crs}")
        print(f"      sutun : {list(gdf.columns)}")

        # Hasar sutunu adayi var mi?
        cand = [c for c in gdf.columns
                if any(h in c.lower() for h in DAMAGE_HINTS)]
        for c in cand:
            vals = gdf[c].value_counts(dropna=False)
            if 1 < len(vals) <= 20:      # kategorik gorunuyorsa yazdir
                print(f"      --> '{c}' dagilimi:")
                for v, n in vals.items():
                    print(f"          {str(v):35s} {n}")
                damage_layers.append((name, path, gdf, c))
        print()

    if not damage_layers:
        print("[uyari] Hasar kategorisi tasiyan sutun otomatik bulunamadi.")
        print("        Yukaridaki sutun listelerine bak, dogru sutunu birlikte secelim.")
        return

    # --- Ciz: ilk hasar katmanini kategorilere gore renklendir ---
    name, path, gdf, col = damage_layers[0]
    print(f"[ciz] cizilen katman: {name}  (sutun: {col})")

    fig, ax = plt.subplots(figsize=(10, 10))
    gdf.plot(ax=ax, column=col, legend=True, markersize=6, cmap="RdYlGn_r",
             legend_kwds={"loc": "upper right", "fontsize": 8})
    ax.set_title(f"EMSR648 — {name}\nhasar kategorisi: {col}")
    ax.set_xlabel("boylam / x")
    ax.set_ylabel("enlem / y")
    fig.savefig("outputs/emsr648_sample.png", dpi=140, bbox_inches="tight")
    print("[ciz] kaydedildi: outputs/emsr648_sample.png")


if __name__ == "__main__":
    main()