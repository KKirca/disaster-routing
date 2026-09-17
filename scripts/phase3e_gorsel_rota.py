"""
Faz 3e - Koordinatsiz gosterim: goruntu ici basit yol izgarasi + Model 1+2.

EBD_TR karosundan basit bir izgara yol agi kurar (gercek sokak degil,
piksel bazli izgara), Model 1+2'nin bina/hasar tahminini bu izgaraya
baglar, A* ile rota hesaplar. Amac: hasarli binadan kacinan rota
mantiginin coğrafi koordinat olmadan da calistigini gostermek.

KULLANIM:
  python scripts/phase3e_gorsel_rota.py --karo 000237
"""
import argparse
import numpy as np
import torch
import networkx as nx
import segmentation_models_pytorch as smp
from scipy import ndimage

import sys
sys.path.insert(0, "scripts")
from phase3_siamese_cnn import SiameseCVA, SINIFLAR, cva_magnitude

SEG_MODEL_YOLU = "models/seg_unet_en_iyi.pth"
CLS_MODEL_YOLU = "models/siamese_cva_en_iyi.pth"
PATCH_DIR = "data/seg_turkey_patches"
IMG_DIR = "data/ebd_turkey/EARTHQUAKE-TURKEY/images"
PATCH = 64
MIN_ALAN = 20
HASAR_ESIGI = 0.7
IZGARA_ADIM = 16   # her 16 pikselde bir dugum (K-37: 32den daha az parcalanma sagladi)


def kirp(img, cx, cy, patch=PATCH):
    h, w = img.shape[:2]
    r = patch // 2
    x0 = int(max(0, min(cx - r, w - patch)))
    y0 = int(max(0, min(cy - r, h - patch)))
    return img[y0:y0+patch, x0:x0+patch]


def heuristic(a, b):
    return ((a[0]-b[0])**2 + (a[1]-b[1])**2) ** 0.5 * IZGARA_ADIM


def izgara_kur(H, W, adim=IZGARA_ADIM):
    """
    Goruntu boyutunda basit bir izgara grafi kurar.
    Her dugum (i,j) piksel konumuna karsilik gelir, komsu dugumlere
    (yatay/dikey) baglidir. Kenar agirligi = piksel mesafesi (varsayilan).
    """
    G = nx.Graph()
    satir = H // adim
    sutun = W // adim
    for i in range(satir):
        for j in range(sutun):
            G.add_node((i, j), x=j*adim + adim//2, y=i*adim + adim//2)
    for i in range(satir):
        for j in range(sutun):
            if j + 1 < sutun:
                G.add_edge((i, j), (i, j+1), agirlik=float(adim), hasar_puan=0.0)
            if i + 1 < satir:
                G.add_edge((i, j), (i+1, j), agirlik=float(adim), hasar_puan=0.0)
    return G, satir, sutun


def bina_maskesi_hesapla(pre, seg_model, cihaz):
    """Model 1'i calistirir, ikili bina maskesini dondurur (True = bina).
    Hem hasar siniflandirmasi hem de kenar-yasaklama tarafindan kullanilir
    - tek gecis, tek kaynak; iki yerde ayri segmentasyon calistirmak
    tutarsizlik riski tasir."""
    with torch.no_grad():
        pre_t = torch.from_numpy(pre.transpose(2,0,1)).float().unsqueeze(0).to(cihaz)
        seg_tahmin = torch.sigmoid(seg_model(pre_t)).cpu().numpy()[0,0]
    return seg_tahmin > 0.5


def binalari_bul_ve_isaretle(G, pre, post, cva, seg_model, cls_model, cihaz, adim=IZGARA_ADIM, ikili=None):
    """Model 1 ile binalari bulur, Model 2 ile hasar tahmin eder, en yakin
    izgara kenarina hasar puani ekler (K-19 mantiginin basitlestirilmisi:
    hasarli bina neresi ise oradaki yol kenari pahalanir)."""
    if ikili is None:
        ikili = bina_maskesi_hesapla(pre, seg_model, cihaz)

    etiketli, n = ndimage.label(ikili)
    print(f"[model 1] {n} bina bulundu")

    binalar = []
    for i in range(1, n + 1):
        bilesen = (etiketli == i)
        alan = bilesen.sum()
        if alan < MIN_ALAN:
            continue
        ys, xs = np.where(bilesen)
        cy, cx = ys.mean(), xs.mean()

        pre_p = kirp(pre, cx, cy)
        post_p = kirp(post, cx, cy)
        cva_p = kirp(cva, cx, cy)
        if pre_p.shape[:2] != (PATCH, PATCH):
            continue
        cva_p = cva_p / (cva_p.max() + 1e-8)

        with torch.no_grad():
            pre_tp = torch.from_numpy(pre_p.transpose(2,0,1)).float().unsqueeze(0).to(cihaz)
            post_tp = torch.from_numpy(post_p.transpose(2,0,1)).float().unsqueeze(0).to(cihaz)
            cva_tp = torch.from_numpy(cva_p[None]).float().unsqueeze(0).to(cihaz)
            cikti = cls_model(pre_tp, post_tp, cva_tp)
            olasiliklar = torch.softmax(cikti, dim=1)[0]
            hasar_olasilik = olasiliklar[1:].sum().item()
            hasarli = hasar_olasilik > HASAR_ESIGI

        binalar.append((cx, cy, hasar_olasilik, hasarli))

        if hasarli:
            i_izgara = int(cy // adim)
            j_izgara = int(cx // adim)
            for (u, v) in G.edges():
                for dugum in (u, v):
                    if dugum == (i_izgara, j_izgara):
                        eski = G[u][v]["hasar_puan"]
                        G[u][v]["hasar_puan"] = max(eski, hasar_olasilik)
                        G[u][v]["agirlik"] = float(IZGARA_ADIM) * (1 + 5 * hasar_olasilik)

    hasarli_sayisi = sum(1 for b in binalar if b[3])
    print(f"[model 2] {len(binalar)} bina siniflandirildi, {hasarli_sayisi} hasarli")
    return binalar

def bina_ustu_kenarlari_kaldir(G, ikili):
    """Grid kenarlarindan bina ustunden gecenleri siler (hard constraint).
    Kenar boyunca birden fazla nokta orneklenir; herhangi biri bina
    pikseline denk gelirse kenar silinir - supheli durumda kisitlama
    yonunde hata yapilir (K-16 ile ayni ilke: emin degilken kapat, ac ma)."""
    H, W = ikili.shape
    silinecek = []
    for (u, v) in G.edges():
        x0, y0 = G.nodes[u]["x"], G.nodes[u]["y"]
        x1, y1 = G.nodes[v]["x"], G.nodes[v]["y"]
        n_ornek = 8
        bina_uzerinde = False
        for t in range(n_ornek + 1):
            oran = t / n_ornek
            x = int(round(x0 + (x1 - x0) * oran))
            y = int(round(y0 + (y1 - y0) * oran))
            x = min(max(x, 0), W - 1)
            y = min(max(y, 0), H - 1)
            if ikili[y, x]:
                bina_uzerinde = True
                break
        if bina_uzerinde:
            silinecek.append((u, v))

    G.remove_edges_from(silinecek)
    print(f"[bina engeli] {len(silinecek)} kenar bina ustunden gectigi icin silindi")
    return G



def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--karo", type=str, required=True)
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

    pre = np.load(f"{PATCH_DIR}/{args.karo}_img.npy")
    from PIL import Image
    post_yolu = f"{IMG_DIR}/EARTHQUAKE-TURKEY_{args.karo}_post_disaster.png"
    post = np.array(Image.open(post_yolu).convert("RGB")).astype("float32") / 255.0
    cva = cva_magnitude(pre * 255.0, post * 255.0)

    H, W = pre.shape[:2]
    G, satir, sutun = izgara_kur(H, W)
    print(f"[izgara] {satir}x{sutun} dugum, adim={IZGARA_ADIM}px")

    ikili = bina_maskesi_hesapla(pre, seg_model, cihaz)
    G = bina_ustu_kenarlari_kaldir(G, ikili)

    binalar = binalari_bul_ve_isaretle(G, pre, post, cva, seg_model, cls_model, cihaz, ikili=ikili)

    bas, hedef = hasarli_kume_bas_hedef(binalar, satir, sutun, G)

    try:
        yol_temiz = nx.astar_path(G, bas, hedef, heuristic=heuristic, weight="agirlik")
        maliyet_temiz = nx.astar_path_length(G, bas, hedef, heuristic=heuristic, weight="agirlik")
    except nx.NetworkXNoPath:
        yol_temiz, maliyet_temiz = None, None

    # Referans: hasarsiz izgara (agirlik = duz adim), ayni bina engeliyle
    G_ref = bina_ustu_kenarlari_kaldir(izgara_kur(H, W)[0], ikili)
    yol_ref = nx.astar_path(G_ref, bas, hedef, heuristic=heuristic, weight="agirlik")
    maliyet_ref = nx.astar_path_length(G_ref, bas, hedef, heuristic=heuristic, weight="agirlik")

    print(f"\n[rota - hasarsiz izgara] {len(yol_ref)} dugum, maliyet={maliyet_ref:.0f}")
    if yol_temiz:
        print(f"[rota - hasar dikkate alinarak] {len(yol_temiz)} dugum, maliyet={maliyet_temiz:.0f}")
        fark = maliyet_temiz - maliyet_ref
        print(f"  fark: +{fark:.0f} ({'sapti' if fark > 1 else 'degismedi'})")
    else:
        print("[rota - hasar dikkate alinarak] ULASILAMIYOR")

    # Gorsellestirme
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(16, 8))
    for ax, yol, baslik in [(axes[0], yol_ref, "Hasar Yok (referans)"),
                             (axes[1], yol_temiz, "Hasar Dikkate Alindi")]:
        ax.imshow(post)
        for cx, cy, olasilik, hasarli in binalar:
            renk = "red" if hasarli else "lime"
            ax.plot(cx, cy, "o", color=renk, markersize=6, alpha=0.7)
        if yol:
            xs = [G.nodes[n]["x"] for n in yol]
            ys = [G.nodes[n]["y"] for n in yol]
            ax.plot(xs, ys, "b-", linewidth=3)
        ax.set_title(baslik)
        ax.axis("off")

    fig.suptitle(f"Karo {args.karo} — koordinatsiz izgara rota gosterimi")
    fig.tight_layout()
    import os
    os.makedirs("outputs", exist_ok=True)
    cikti = f"outputs/phase3e_{args.karo}.png"
    fig.savefig(cikti, dpi=110, bbox_inches="tight")
    plt.close(fig)
    print(f"\n[kaydedildi] {cikti}")


def hasarli_kume_bas_hedef(binalar, satir, sutun, G, adim=IZGARA_ADIM):
    """
    Hasarli binalarin bounding box'ini bulur, kumenin uzun eksenine gore
    karsit iki ucuna (pay ile disarida) izgara dugumu atar.

    Varsayim: hasarli binalar tek, yaklasik disbukey bir kume olusturur.
    Kume dagitik/coklu ise (iki ayri bolge) bu yontem yaniltici sonuc verir -
    cikti gorseli incelenmeden guvenilmemeli.

    Bulunan (i,j) bina ustune veya grafikten silinmis (izole) bir duguma
    denk gelebilir - bu durumda G uzerinde en yakin gecerli (derece>0)
    duguma kaydirilir; asla geometrik hesaba kor korune guvenilmez.

    Donus: (bas, hedef) -> ikisi de (i, j) izgara dugumu.
    """
    hasarlilar = [(cx, cy) for cx, cy, _, hasarli in binalar if hasarli]
    if not hasarlilar:
        raise ValueError(
            "Hasarli bina bulunamadi; otomatik nokta secimi icin "
            "en az bir hasarli bina gerekli."
        )

    pay = adim * 2

    if len(hasarlilar) == 1:
        cx, cy = hasarlilar[0]
        bas_x, bas_y = cx - pay, cy
        hedef_x, hedef_y = cx + pay, cy
        aciklama = f"tek bina ({cx:.0f},{cy:.0f}) etrafinda"
    else:
        en_uzak_cift, en_mesafe_kare = None, -1
        for i in range(len(hasarlilar)):
            for j in range(i + 1, len(hasarlilar)):
                x1, y1 = hasarlilar[i]
                x2, y2 = hasarlilar[j]
                d = (x1 - x2) ** 2 + (y1 - y2) ** 2
                if d > en_mesafe_kare:
                    en_mesafe_kare, en_uzak_cift = d, (hasarlilar[i], hasarlilar[j])
        (x1, y1), (x2, y2) = en_uzak_cift
        dx, dy = x2 - x1, y2 - y1
        uzunluk = (dx ** 2 + dy ** 2) ** 0.5
        oran = pay / uzunluk if uzunluk > 0 else 0
        bas_x, bas_y = x1 - dx * oran, y1 - dy * oran
        hedef_x, hedef_y = x2 + dx * oran, y2 + dy * oran
        aciklama = (f"en uzak cift ({x1:.0f},{y1:.0f})-({x2:.0f},{y2:.0f}), "
                    f"mesafe={uzunluk:.0f}px")

    def piksel_to_dugum(x, y):
        i = int(min(max(y // adim, 0), satir - 1))
        j = int(min(max(x // adim, 0), sutun - 1))
        return (i, j)

    import networkx as nx
    bilesenler = list(nx.connected_components(G))
    if not bilesenler:
        raise ValueError("Grafikte hic bagli bilesen yok.")
    ana_govde = max(bilesenler, key=len)

    def en_yakin_gecerli_dugum(dugum):
        if dugum in ana_govde:
            return dugum
        i0, j0 = dugum
        en_yakin, en_kisa = None, None
        for n in ana_govde:
            i1, j1 = n
            d = (i1 - i0) ** 2 + (j1 - j0) ** 2
            if en_kisa is None or d < en_kisa:
                en_kisa, en_yakin = d, n
        return en_yakin

    bas_ham = piksel_to_dugum(bas_x, bas_y)
    hedef_ham = piksel_to_dugum(hedef_x, hedef_y)
    bas = en_yakin_gecerli_dugum(bas_ham)
    hedef = en_yakin_gecerli_dugum(hedef_ham)

    if bas != bas_ham:
        print(f"[nokta duzeltme] bas {bas_ham} gecersizdi, en yakina kaydirildi: {bas}")
    if hedef != hedef_ham:
        print(f"[nokta duzeltme] hedef {hedef_ham} gecersizdi, en yakina kaydirildi: {hedef}")

    if bas == hedef:
        raise ValueError(
            f"Bas ve hedef ayni duguma dusuyor: {bas}. "
            "Izgara adimini veya pay degerini gozden gecir."
        )

    print(f"[otomatik nokta] bas={bas} hedef={hedef} ({aciklama})")

    return bas, hedef


if __name__ == "__main__":
    main()
