"""
Faz 2c — Adim 2: Anotator etiketlerini xBD ile KARSILASTIR.

Uc soruyu cevaplar:
  1. Her anotator uzman etiketiyle ne kadar uyusuyor? (dogruluk)
  2. Anotatorler birbiriyle ne kadar uyusuyor? (Cohen's kappa)
  3. HANGI sinif ciftlerinde karisiyoruz? (karisiklik matrisi)

Ucuncusu en degerlisi: protokolun nerede eksik oldugunu soyler.

KULLANIM:
  Label Studio'dan JSON export al, su isimle kaydet:
      data/labeling/annotations_<isim>.json
  Sonra:
      cd ~/disaster-routing
      python scripts/phase2c_compare.py
"""

import glob
import json
import os
from collections import Counter, defaultdict

import numpy as np

CLASSES = ["no-damage", "minor-damage", "major-damage", "destroyed"]
UNSURE = "emin-degilim"
DIR = "data/labeling"


# ---------------------------------------------------------------------------
# Label Studio JSON export'unu oku
# ---------------------------------------------------------------------------
def load_annotations(path):
    """{task_id: secilen_sinif} sozlugu dondurur."""
    with open(path) as f:
        data = json.load(f)
    out = {}
    for item in data:
        tid = item.get("data", {}).get("task_id")
        anns = item.get("annotations") or []
        if not tid or not anns:
            continue
        for res in anns[0].get("result", []):
            if res.get("type") == "choices":
                choices = res.get("value", {}).get("choices", [])
                if choices:
                    out[tid] = choices[0]
                break
    return out


def load_truth(path):
    import csv
    with open(path) as f:
        return {r["task_id"]: r["true_class"] for r in csv.DictReader(f)}


# ---------------------------------------------------------------------------
# Metrikler
# ---------------------------------------------------------------------------
def cohens_kappa(a, b, labels):
    """Iki etiketleyici arasi sans-duzeltilmis uyum."""
    n = len(a)
    if n == 0:
        return float("nan")
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum((ca[l] / n) * (cb[l] / n) for l in labels)
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")


def confusion(true, pred, labels):
    idx = {l: i for i, l in enumerate(labels)}
    m = np.zeros((len(labels), len(labels)), dtype=int)
    for t, p in zip(true, pred):
        if t in idx and p in idx:
            m[idx[t]][idx[p]] += 1
    return m


def print_matrix(m, labels, title):
    print(f"\n{title}")
    w = max(len(l) for l in labels) + 2
    print(" " * w + "".join(f"{l[:12]:>14s}" for l in labels))
    for i, l in enumerate(labels):
        print(f"{l:<{w}s}" + "".join(f"{m[i][j]:14d}" for j in range(len(labels))))
    print("  (satir = gercek / xBD, sutun = anotator)")


# ---------------------------------------------------------------------------
def main():
    truth = load_truth(f"{DIR}/ground_truth.csv")
    files = sorted(glob.glob(f"{DIR}/annotations_*.json"))
    if not files:
        raise SystemExit(
            f"{DIR}/annotations_*.json bulunamadi.\n"
            "Label Studio'dan JSON export alip bu isimle kaydettin mi?"
        )

    anns = {}
    for p in files:
        name = os.path.basename(p).replace("annotations_", "").replace(".json", "")
        anns[name] = load_annotations(p)
        print(f"[oku] {name}: {len(anns[name])} etiket")

    print(f"[oku] ground truth: {len(truth)} gorev\n")
    print("=" * 60)

    # --- 1) Her anotator vs xBD ---
    for name, a in anns.items():
        common = [t for t in truth if t in a]
        unsure = [t for t in common if a[t] == UNSURE]
        scored = [t for t in common if a[t] != UNSURE]

        y_true = [truth[t] for t in scored]
        y_pred = [a[t] for t in scored]
        acc = np.mean([t == p for t, p in zip(y_true, y_pred)]) if scored else 0

        # Ikili gorunum: hasarli (major/destroyed) vs degil — projenin asil kararı
        dmg = {"major-damage", "destroyed"}
        bt = [t in dmg for t in y_true]
        bp = [p in dmg for p in y_pred]
        tp = sum(t and p for t, p in zip(bt, bp))
        fn = sum(t and not p for t, p in zip(bt, bp))
        fp = sum((not t) and p for t, p in zip(bt, bp))
        rec = tp / max(tp + fn, 1)
        prec = tp / max(tp + fp, 1)

        print(f"\n### {name} — xBD ile karsilastirma")
        print(f"  degerlendirilen  : {len(scored)} / {len(common)}")
        print(f"  'emin degilim'   : {len(unsure)} ({100*len(unsure)/max(len(common),1):.0f}%)")
        print(f"  4-sinif dogruluk : {acc:.3f}")
        print(f"  ikili (hasarli)  : recall {rec:.3f} | precision {prec:.3f}")
        print_matrix(confusion(y_true, y_pred, CLASSES), CLASSES,
                     f"Karisiklik matrisi — {name}")

    # --- 2) Anotatorler arasi uyum ---
    names = list(anns)
    if len(names) >= 2:
        print("\n" + "=" * 60)
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                a, b = anns[names[i]], anns[names[j]]
                common = [t for t in a if t in b
                          and a[t] != UNSURE and b[t] != UNSURE]
                la = [a[t] for t in common]
                lb = [b[t] for t in common]
                agree = np.mean([x == y for x, y in zip(la, lb)]) if common else 0
                k = cohens_kappa(la, lb, CLASSES)
                print(f"\n### {names[i]} vs {names[j]}")
                print(f"  ortak gorev    : {len(common)}")
                print(f"  ham uyum       : {agree:.3f}")
                print(f"  Cohen's kappa  : {k:.3f}   "
                      f"({'zayif' if k < 0.4 else 'orta' if k < 0.6 else 'iyi' if k < 0.8 else 'cok iyi'})")

        # --- 3) Tartisilacak ornekler ---
        a, b = anns[names[0]], anns[names[1]]
        both_wrong, disagree = [], []
        for t in truth:
            if t not in a or t not in b:
                continue
            if a[t] == b[t] and a[t] != truth[t] and a[t] != UNSURE:
                both_wrong.append((t, truth[t], a[t]))
            elif a[t] != b[t]:
                disagree.append((t, truth[t], a[t], b[t]))

        print("\n" + "=" * 60)
        print(f"\n### IKINIZ DE xBD'YE TERS DUSTUNUZ ({len(both_wrong)} ornek)")
        print("    -> protokol eksigi VEYA xBD etiketi tartismali. Bunlari tartis.")
        for t, tr, pred in both_wrong[:15]:
            print(f"    {t}: xBD={tr:15s} ikiniz={pred}")

        print(f"\n### BIRBIRINIZLE ANLASAMADINIZ ({len(disagree)} ornek)")
        print("    -> sinif tanimlari net degil. Bunlari tartis.")
        for t, tr, pa, pb in disagree[:15]:
            print(f"    {t}: xBD={tr:15s} {names[0]}={pa:15s} {names[1]}={pb}")
    else:
        print("\n[not] Ikinci anotator dosyasi yok — kappa hesaplanmadi.")


if __name__ == "__main__":
    main()