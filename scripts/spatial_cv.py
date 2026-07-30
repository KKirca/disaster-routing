"""
Faz 2 — 2d: Spatial Cross-Validation bolunmeleri.

PROBLEM: Karolari rastgele egitim/test diye bolersen, komsu karolar
ikisine dagilir. Komsu karo = ayni mahalle, ayni yikim orugusu, ayni
uydu gecisi. Model onu "ogrenmis" degil "tanimis" olur -> data leakage.

COZUM: Bolmeyi COGRAFYAYA gore yap.
  1. Her karonun koordinatini bul (etiket JSON'undaki lng_lat'ten).
  2. Haritayi ~BLOCK_DEG buyuklugunde bloklara bol.
  3. Bir blogun TUM karolari ayni fold'a gitsin.

Ayrica rastgele bolmenin ne kadar sizdirdigini SAYISAL olarak gosterir.

Calistirma:
    cd ~/disaster-routing
    conda activate disaster
    python scripts/spatial_cv.py
"""

import glob
import json
import math
import os
import random
from collections import Counter, defaultdict

import matplotlib.pyplot as plt
import numpy as np
from shapely import wkt

# ---------------------------------------------------------------------------
# Ayarlar
# ---------------------------------------------------------------------------
BLOCK_DEG = 0.05   # blok kenari (derece). ~5.5 km. Karo ~0.5 km oldugu icin
                   # bir blok ~10x10 karo alir. Buyutursen daha guvenli ama
                   # daha az blok kalir (fold'lar dengesizlesir).
K = 5              # fold sayisi
SEED = 42          # tekrarlanabilirlik
VIZ_DISASTER = "palu-tsunami"   # haritada gosterilecek olay

OUT = "outputs/spatial_cv.png"


# ---------------------------------------------------------------------------
# 1) Her karonun koordinatini ve hasar bilgisini cikar
# ---------------------------------------------------------------------------
def tile_info(path):
    """Bir post_disaster etiketinden karo merkezini ve hasar sayilarini cikarir."""
    with open(path) as f:
        d = json.load(f)

    feats = d["features"].get("lng_lat", [])
    if not feats:
        return None   # binasiz karo — koordinat cikaramayiz, atla

    polys = [wkt.loads(ft["wkt"]) for ft in feats]
    lon = float(np.mean([p.centroid.x for p in polys]))
    lat = float(np.mean([p.centroid.y for p in polys]))

    sub = Counter(ft["properties"].get("subtype", "un-classified") for ft in feats)
    damaged = sub.get("major-damage", 0) + sub.get("destroyed", 0)

    return {
        "path": path,
        "name": os.path.basename(path),
        "disaster": os.path.basename(path).split("_")[0],
        "lon": lon,
        "lat": lat,
        "n_buildings": len(feats),
        "n_damaged": damaged,
    }


def block_of(tile):
    """Karonun ait oldugu blogun (i, j) kimligi."""
    return (math.floor(tile["lon"] / BLOCK_DEG),
            math.floor(tile["lat"] / BLOCK_DEG))


# ---------------------------------------------------------------------------
# 2) Bloklari fold'lara ata
# ---------------------------------------------------------------------------
def assign_folds(tiles, k, seed):
    """Blok bazinda fold atamasi: bir blogun tum karolari ayni fold'a."""
    blocks = defaultdict(list)
    for t in tiles:
        blocks[block_of(t)].append(t)

    keys = sorted(blocks.keys())          # deterministik baslangic
    random.Random(seed).shuffle(keys)     # sonra tohumlu karistirma

    for idx, key in enumerate(keys):
        fold = idx % k
        for t in blocks[key]:
            t["fold_block"] = fold
    return blocks


def assign_random_folds(tiles, k, seed):
    """Karsilastirma icin: KARO bazinda rastgele atama (sizdiran yontem)."""
    rng = random.Random(seed + 1)
    for t in tiles:
        t["fold_random"] = rng.randrange(k)


# ---------------------------------------------------------------------------
# 3) Sizinti olcumu: bir blok kac farkli fold'a bolunmus?
# ---------------------------------------------------------------------------
def leakage_report(blocks, key):
    split_blocks = 0
    for tiles_in_block in blocks.values():
        folds = {t[key] for t in tiles_in_block}
        if len(folds) > 1:
            split_blocks += 1
    total = len(blocks)
    pct = 100.0 * split_blocks / total if total else 0.0
    return split_blocks, total, pct


# ---------------------------------------------------------------------------
# Ana akis
# ---------------------------------------------------------------------------
def main():
    os.makedirs("outputs", exist_ok=True)

    paths = glob.glob("data/**/labels/*_post_disaster.json", recursive=True)
    if not paths:
        raise SystemExit("post_disaster .json bulunamadi.")
    print(f"[tara] {len(paths)} karo etiketi taraniyor...")

    tiles = [t for t in (tile_info(p) for p in paths) if t is not None]
    print(f"[karo] koordinati cikarilan: {len(tiles)} "
          f"(binasiz/atlanan: {len(paths) - len(tiles)})")

    # Olay bazinda ozet — leave-disaster-out icin hangi olaylar var?
    by_dis = defaultdict(lambda: {"tiles": 0, "damaged": 0})
    for t in tiles:
        by_dis[t["disaster"]]["tiles"] += 1
        by_dis[t["disaster"]]["damaged"] += t["n_damaged"]
    print("\n[olay] afet bazinda dagilim (leave-disaster-out adaylari):")
    for dis, s in sorted(by_dis.items(), key=lambda x: -x[1]["damaged"]):
        print(f"       {dis:28s} {s['tiles']:5d} karo, {s['damaged']:7d} agir/yikik bina")

    # Fold atamalari
    blocks = assign_folds(tiles, K, SEED)
    assign_random_folds(tiles, K, SEED)
    print(f"\n[blok] {len(blocks)} mekansal blok olustu (BLOCK_DEG={BLOCK_DEG})")

    # Fold dengesi
    print(f"\n[fold] blok-bazli bolme ({K} fold):")
    for f in range(K):
        sel = [t for t in tiles if t["fold_block"] == f]
        dmg = sum(t["n_damaged"] for t in sel)
        dis = len({t["disaster"] for t in sel})
        print(f"       fold {f}: {len(sel):5d} karo, {dmg:7d} agir/yikik bina, {dis} olay")

    # SIZINTI KARSILASTIRMASI
    sb_b, tot, pct_b = leakage_report(blocks, "fold_block")
    sb_r, _, pct_r = leakage_report(blocks, "fold_random")
    print("\n[SIZINTI] ayni blok kac kez birden fazla fold'a bolunmus?")
    print(f"       blok-bazli bolme : {sb_b:5d} / {tot} blok  ({pct_b:.1f}%)")
    print(f"       rastgele bolme   : {sb_r:5d} / {tot} blok  ({pct_r:.1f}%)  <-- sizinti")

    # --- Gorsel: bir olayin karolari, fold'a gore renkli ---
    sel = [t for t in tiles if t["disaster"] == VIZ_DISASTER]
    if not sel:
        print(f"\n[ciz] '{VIZ_DISASTER}' bulunamadi, cizim atlandi.")
        return

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    for ax, key, title in [
        (ax1, "fold_random", "RASTGELE bolme (sizdirir)"),
        (ax2, "fold_block", f"BLOK bazli bolme (~{BLOCK_DEG}°)"),
    ]:
        lons = [t["lon"] for t in sel]
        lats = [t["lat"] for t in sel]
        cols = [t[key] for t in sel]
        sc = ax.scatter(lons, lats, c=cols, cmap="tab10", s=45,
                        vmin=0, vmax=K - 1, edgecolors="k", linewidths=0.3)
        ax.set_title(f"{VIZ_DISASTER}\n{title}")
        ax.set_xlabel("boylam")
        ax.set_ylabel("enlem")
        ax.set_aspect("equal", adjustable="datalim")

    fig.colorbar(sc, ax=ax2, label="fold")
    fig.tight_layout()
    fig.savefig(OUT, dpi=140, bbox_inches="tight")
    print(f"\n[ciz] kaydedildi: {OUT}")


if __name__ == "__main__":
    main()