"""
Faz 2c — Adim 1: ANOTATOR KALIBRASYON SETI.

FIKIR: Turkiye verisine gecmeden once, dogru cevabi BILDIGIMIZ xBD
karolariyla kendinizi olcun. Boylece:
  - Her anotatorun uzman etiketiyle uyumu olculur
  - Iki anotatorun birbiriyle uyumu (Cohen's kappa) olculur
  - Protokol belirsizlikleri gercek orneklerle netlesir

Turkiye'de dogru cevap YOK — orada urettiginiz etiket ground truth olacak.
Kalibre olmadan uretirseniz hatanizi olcemezsiniz.

CIKTI:
  data/labeling/calib/          -> pre/post yama PNG'leri
  data/labeling/tasks.json      -> Label Studio'ya import edilecek gorevler
  data/labeling/config.xml      -> Label Studio etiketleme arayuzu tanimi
  data/labeling/ground_truth.csv-> GIZLI dogru cevaplar (anotatorlere VERME)

Calistirma:
    cd ~/disaster-routing
    conda activate disaster
    python scripts/phase2c_calibration_set.py
"""

import csv
import glob
import json
import os
import random

import matplotlib.pyplot as plt
import numpy as np
from shapely import wkt

# ---------------------------------------------------------------------------
# Ayarlar
# ---------------------------------------------------------------------------
N_PER_CLASS = 25         # her hasar sinifindan kac ornek (toplam ~100)
PATCH = 160              # yama kenari — etiketleyene baglam versin diye biraz genis
SEED = 7
CLASSES = ["no-damage", "minor-damage", "major-damage", "destroyed"]
# Label Studio belge koku = proje koku. LABEL_STUDIO_LOCAL_FILES_DOCUMENT_ROOT bu yola esit olmali.
DOC_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

OUT_DIR = "data/labeling"
IMG_DIR = f"{OUT_DIR}/calib"


def crop_centered(img, cx, cy, size):
    h, w = img.shape[:2]
    half = size // 2
    x0, y0 = int(cx) - half, int(cy) - half
    out = np.zeros((size, size, 3), dtype=img.dtype)
    sx0, sy0 = max(x0, 0), max(y0, 0)
    sx1, sy1 = min(x0 + size, w), min(y0 + size, h)
    if sx1 <= sx0 or sy1 <= sy0:
        return out
    out[sy0 - y0:sy1 - y0, sx0 - x0:sx1 - x0] = img[sy0:sy1, sx0:sx1]
    return out


def load_rgb(path):
    img = plt.imread(path)[:, :, :3]
    if img.max() <= 1.0:
        img = img * 255.0
    return img.astype("uint8")


def main():
    os.makedirs(IMG_DIR, exist_ok=True)
    rng = random.Random(SEED)

    # --- 1) Tum karolardan aday binalari topla (goruntu yuklemeden) ---
    paths = sorted(glob.glob("data/**/labels/*_post_disaster.json", recursive=True))
    if not paths:
        raise SystemExit("xBD etiketleri bulunamadi.")
    rng.shuffle(paths)

    pool = {c: [] for c in CLASSES}
    for p in paths:
        with open(p) as f:
            feats = json.load(f)["features"]["xy"]
        for j, ft in enumerate(feats):
            st = ft["properties"].get("subtype")
            if st in pool and len(pool[st]) < N_PER_CLASS * 4:
                pool[st].append((p, j, ft["wkt"]))
        if all(len(v) >= N_PER_CLASS * 4 for v in pool.values()):
            break

    print("[havuz] toplanan aday sayilari:")
    for c in CLASSES:
        print(f"        {c:15s} {len(pool[c])}")

    # --- 2) Her siniftan esit sayida sec, sonra KARISTIR ---
    chosen = []
    for c in CLASSES:
        if len(pool[c]) < N_PER_CLASS:
            print(f"[uyari] '{c}' icin yeterli ornek yok "
                  f"({len(pool[c])} < {N_PER_CLASS}) — hepsi kullanilacak.")
        chosen += [(c, *x) for x in rng.sample(pool[c], min(N_PER_CLASS, len(pool[c])))]
    rng.shuffle(chosen)   # sinif sirasi ipucu vermesin
    print(f"\n[secim] toplam gorev: {len(chosen)}")

    # --- 3) Yamalari kes ve kaydet ---
    tasks, truth = [], []
    cache = {}
    for i, (cls, post_json, j, wkt_str) in enumerate(chosen):
        post_p = post_json.replace("labels", "images").replace(".json", ".png")
        pre_p = post_p.replace("post_disaster", "pre_disaster")
        if not (os.path.exists(pre_p) and os.path.exists(post_p)):
            continue

        if post_json not in cache:
            cache = {post_json: (load_rgb(pre_p), load_rgb(post_p))}  # tek karo tut
        pre_img, post_img = cache[post_json]

        c = wkt.loads(wkt_str).centroid
        tid = f"task_{i:04d}"
        pre_rel = f"{IMG_DIR}/{tid}_pre.png"
        post_rel = f"{IMG_DIR}/{tid}_post.png"
        plt.imsave(pre_rel, crop_centered(pre_img, c.x, c.y, PATCH))
        plt.imsave(post_rel, crop_centered(post_img, c.x, c.y, PATCH))

        # Label Studio yerel dosya URL'i (DOC_ROOT'a gore goreli yol)
        abs_pre = os.path.abspath(pre_rel)
        abs_post = os.path.abspath(post_rel)
        url_pre = "/data/local-files/?d=" + os.path.relpath(abs_pre, DOC_ROOT)
        url_post = "/data/local-files/?d=" + os.path.relpath(abs_post, DOC_ROOT)

        tasks.append({"id": i, "data": {"task_id": tid,
                                        "pre": url_pre, "post": url_post}})
        truth.append({"task_id": tid, "true_class": cls,
                      "source_tile": os.path.basename(post_json),
                      "building_index": j})

    # --- 4) Gorev dosyasi ---
    with open(f"{OUT_DIR}/tasks.json", "w") as f:
        json.dump(tasks, f, indent=1)

    # --- 5) GIZLI dogru cevaplar ---
    with open(f"{OUT_DIR}/ground_truth.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["task_id", "true_class",
                                          "source_tile", "building_index"])
        w.writeheader()
        w.writerows(truth)

    # --- 6) Label Studio arayuz konfigu ---
    config = """<View>
  <Header value="Deprem oncesi (sol) ve sonrasi (sag) — ORTADAKI binayi degerlendir"/>
  <View style="display: flex">
    <View style="flex: 50%"><Header value="ONCE"/><Image name="pre" value="$pre" zoom="true"/></View>
    <View style="flex: 50%"><Header value="SONRA"/><Image name="post" value="$post" zoom="true"/></View>
  </View>
  <Choices name="damage" toName="post" choice="single" showInLine="false" required="true">
    <Choice value="no-damage"    hint="Yapisal degisiklik yok"/>
    <Choice value="minor-damage" hint="Kismi hasar izi, cati buyuk olcude yerinde"/>
    <Choice value="major-damage" hint="Belirgin yapisal hasar, cati kismen cokmus"/>
    <Choice value="destroyed"    hint="Bina tamamen cokmus / yerinde moloz"/>
    <Choice value="emin-degilim" hint="Karar veremiyorum"/>
  </Choices>
  <TextArea name="note" toName="post" placeholder="Not (opsiyonel)" rows="2" editable="true"/>
</View>
"""
    with open(f"{OUT_DIR}/config.xml", "w") as f:
        f.write(config)

    print(f"\n[kaydet] {OUT_DIR}/tasks.json          ({len(tasks)} gorev)")
    print(f"[kaydet] {OUT_DIR}/config.xml")
    print(f"[kaydet] {OUT_DIR}/ground_truth.csv   <-- ANOTATORLERE VERME")
    print(f"[kaydet] {IMG_DIR}/  ({2*len(tasks)} PNG)")
    print("\nSinif dagilimi (gizli):")
    from collections import Counter
    for c, n in Counter(t["true_class"] for t in truth).items():
        print(f"   {c:15s} {n}")


if __name__ == "__main__":
    main()