"""
Faz 2 — 2a: xBD veri setine BAK (tek bir pre/post cifti).

Amac: xBD'nin yapisini somutlastirmak.
  - pre ve post goruntuleri nasil gorunuyor?
  - Bina poligonlari ve dort seviyeli hasar skalasi neye benziyor?
  - Bu ornekte her hasar sinifindan kac bina var?

xBD etiket JSON yapisi (post_disaster):
  features -> xy -> [ { "wkt": "POLYGON(...)", "properties": {"subtype": "..."} }, ... ]
  subtype degerleri: no-damage / minor-damage / major-damage / destroyed / un-classified
  ("xy" piksel koordinati; goruntunun uzerine dogrudan cizilir.)

Calistirma:
    cd ~/disaster-routing
    conda activate disaster
    python scripts/inspect_xbd.py
"""

import glob
import json
import os
from collections import Counter

import matplotlib.pyplot as plt
from shapely import wkt

# Hasar sinifi -> renk
COLORS = {
    "no-damage": "lime",
    "minor-damage": "yellow",
    "major-damage": "orange",
    "destroyed": "red",
    "un-classified": "gray",
}

# data/ altinda bir post_disaster etiketi bul (recursive).
labels = glob.glob("data/**/labels/*_post_disaster.json", recursive=True)
if not labels:
    raise SystemExit(
        "post_disaster .json bulunamadi. xBD'yi indirip data/xbd/ altina "
        "cikardin mi? (yapi: .../labels/*_post_disaster.json)"
    )

post_json = labels[0]
print(f"[ornek] secilen etiket: {post_json}")

# Etiket yolundan goruntu yollarini turet.
post_img = post_json.replace("labels", "images").replace(".json", ".png")
pre_img = post_img.replace("post_disaster", "pre_disaster")

# Etiketi oku.
with open(post_json) as f:
    data = json.load(f)
features = data["features"]["xy"]

# Hasar sinifi sayimlari.
counts = Counter(feat["properties"].get("subtype", "un-classified") for feat in features)
print("[hasar] bina sayilari:")
for k, v in counts.items():
    print(f"        {k}: {v}")
print(f"[toplam] {len(features)} bina")

# --- Ciz: pre (sol) + post (sag, poligonlarla) ---
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))

ax1.imshow(plt.imread(pre_img))
ax1.set_title("Deprem ONCESI (pre)")
ax1.axis("off")

ax2.imshow(plt.imread(post_img))
ax2.set_title("Deprem SONRASI (post) + hasar poligonlari")
ax2.axis("off")

for feat in features:
    poly = wkt.loads(feat["wkt"])
    subtype = feat["properties"].get("subtype", "un-classified")
    color = COLORS.get(subtype, "gray")
    xs, ys = poly.exterior.xy
    ax2.fill(xs, ys, facecolor=color, edgecolor=color, alpha=0.45, linewidth=0.5)

# Renk aciklamasi (legend)
from matplotlib.patches import Patch
legend = [Patch(facecolor=c, label=k) for k, c in COLORS.items()]
ax2.legend(handles=legend, loc="upper right", fontsize=8)

fig.savefig("outputs/xbd_sample.png", dpi=120, bbox_inches="tight")
print("[ciz] kaydedildi: outputs/xbd_sample.png")