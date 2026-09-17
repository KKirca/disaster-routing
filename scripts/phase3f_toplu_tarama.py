"""
Faz 3f - 40 karoluk otomatik tarama: izgara-rota prototipinin genel
davranisini olcmek. Her karoda otomatik bas/hedef secimi + bina engeli
+ hasar maliyeti calistirilir, sonuclar ozetlenir.

KULLANIM:
  python scripts/phase3f_toplu_tarama.py --n 40
"""
import argparse
import glob
import os
import sys
import numpy as np
import torch
import networkx as nx
import segmentation_models_pytorch as smp
from PIL import Image

sys.path.insert(0, "scripts")
from phase3_siamese_cnn import SiameseCVA, SINIFLAR, cva_magnitude
from phase3e_gorsel_rota import (
    izgara_kur, bina_maskesi_hesapla, bina_ustu_kenarlari_kaldir,
    binalari_bul_ve_isaretle, hasarli_kume_bas_hedef, heuristic,
    SEG_MODEL_YOLU, CLS_MODEL_YOLU, PATCH_DIR, IMG_DIR,
)


def bir_karo_isle(karo, seg_model, cls_model, cihaz):
    """Bir karoyu isler, sonuc sozlugu doner (hata varsa 'hata' anahtari)."""
    try:
        pre = np.load(f"{PATCH_DIR}/{karo}_img.npy")
        post_yolu = f"{IMG_DIR}/EARTHQUAKE-TURKEY_{karo}_post_disaster.png"
        post = np.array(Image.open(post_yolu).convert("RGB")).astype("float32") / 255.0
        cva = cva_magnitude(pre * 255.0, post * 255.0)

        H, W = pre.shape[:2]
        G, satir, sutun = izgara_kur(H, W)
        ikili = bina_maskesi_hesapla(pre, seg_model, cihaz)
        G = bina_ustu_kenarlari_kaldir(G, ikili)

        binalar = binalari_bul_ve_isaretle(G, pre, post, cva, seg_model, cls_model, cihaz, ikili=ikili)
        hasarli_sayisi = sum(1 for b in binalar if b[3])

        if hasarli_sayisi == 0:
            return {"karo": karo, "durum": "hasar_yok", "hasarli_sayisi": 0}

        bas, hedef = hasarli_kume_bas_hedef(binalar, satir, sutun, G)

        try:
            maliyet_temiz = nx.astar_path_length(G, bas, hedef, heuristic=heuristic, weight="agirlik")
        except nx.NetworkXNoPath:
            return {"karo": karo, "durum": "yol_yok", "hasarli_sayisi": hasarli_sayisi}

        G_ref = bina_ustu_kenarlari_kaldir(izgara_kur(H, W)[0], ikili)
        maliyet_ref = nx.astar_path_length(G_ref, bas, hedef, heuristic=heuristic, weight="agirlik")

        fark = maliyet_temiz - maliyet_ref
        durum = "kacinma" if fark > 1 else "etkisiz"
        return {"karo": karo, "durum": durum, "hasarli_sayisi": hasarli_sayisi,
                "fark": round(fark, 1), "toplam_bina": len(binalar)}

    except Exception as e:
        return {"karo": karo, "durum": "hata", "detay": str(e)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=40)
    args = ap.parse_args()

    cihaz = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("[cihaz]", cihaz)

    seg_model = smp.Unet(encoder_name="resnet18", encoder_weights=None,
                         in_channels=3, classes=1).to(cihaz)
    seg_model.load_state_dict(torch.load(SEG_MODEL_YOLU, map_location=cihaz,
                                         weights_only=True))
    seg_model.eval()

    cls_model = SiameseCVA(n_sinif=len(SINIFLAR)).to(cihaz)
    cls_model.load_state_dict(torch.load(CLS_MODEL_YOLU, map_location=cihaz,
                                         weights_only=True))
    cls_model.eval()

    karolar = sorted(set(
        os.path.basename(f).replace("_img.npy", "")
        for f in glob.glob(f"{PATCH_DIR}/*_img.npy")
    ))[:args.n]
    print(f"[karo] {len(karolar)} karo taranacak\n")

    sonuclar = []
    for i, karo in enumerate(karolar, 1):
        r = bir_karo_isle(karo, seg_model, cls_model, cihaz)
        sonuclar.append(r)
        print(f"  {i:3d}/{len(karolar)}  {karo}  ->  {r['durum']}")

    print("\n--- OZET ---")
    from collections import Counter
    sayac = Counter(r["durum"] for r in sonuclar)
    for durum, sayi in sayac.most_common():
        print(f"  {sayi:3d}  {durum}")

    kacinma = [r for r in sonuclar if r["durum"] == "kacinma"]
    if kacinma:
        print("\n--- KACINMA GOZLENEN KAROLAR ---")
        for r in kacinma:
            print(f"  {r['karo']}  fark=+{r['fark']}  hasarli={r['hasarli_sayisi']}/{r['toplam_bina']}")

    hatalar = [r for r in sonuclar if r["durum"] == "hata"]
    if hatalar:
        print("\n--- HATALAR ---")
        for r in hatalar:
            print(f"  {r['karo']}  {r['detay']}")


if __name__ == "__main__":
    main()
