# Faz 2c — Kalibrasyon: Kuzey Turu Tamamlandı

**Tarih:** 2026-08-05
**Anotatör:** Kuzey
**Durum:** 1/2 anotatör tamamlandı. Cohen's kappa **hesaplanamadı** — Meyusun'un turu bekleniyor.

---

## 1. Bu faz ne için var?

Kahramanmaraş (Maxar) görüntülerinde **ground truth yok**. Orada modeli değerlendirmek için
bizim etiketlerimizi referans alacağız. Ama iki kişinin ürettiği etiketler birbirini
tutmuyorsa o referans değersizdir.

Faz 2c bunu ölçer: xBD'den seçilmiş, cevabı bilinen 100 örneği ikimiz de **birbirimizden
bağımsız** etiketleriz. Sonra iki şeye bakarız:

1. **Cohen's kappa** — ikimiz arasındaki şans-düzeltilmiş uyum → **hedef ≥ 0.60**
2. **Karışıklık matrisi** — hangi sınıf çiftlerinde karıştığımız → protokolün nerede
   eksik olduğunu söyler

Kappa 0.60'ın altındaysa Maxar verisine geçmiyoruz; önce protokolü düzeltip yeniden
ölçüyoruz. Bu keyfi bir eşik değil — kendi etiketlerimizi ground truth yerine
kullanabilmemizin ön koşulu.

Not: bu script'teki kappa **anotatörler arası** uyumdur, anotatör–xBD uyumu değil. Tek
dosyayla hesaplanmaz.

---

## 2. Bu push'ta ne var / ne yok?

```
data/labeling/
├── config.xml        ← Label Studio arayüzü + sınıf tanımları (= protokol)
└── tasks.json        ← 100 görev, DÜZELTİLMİŞ görüntü yollarıyla

scripts/
└── phase2c_calibration_set.py   ← DOC_ROOT hatası düzeltildi (bkz. 4.4)

reports/
└── phase2c_kuzey.txt ← phase2c_compare.py'nin ham çıktısı

.gitignore            ← satır içi yorum hatası düzeltildi (bkz. 2.1)
```

**Kasıtlı olarak repoda OLMAYANLAR:**

| Dosya | Neden |
|---|---|
| `data/labeling/calib/*.png` (200 dosya) | xBD türevi ham görüntü. Repo şişer. Script aynı `SEED=7` ile birebir aynısını üretir. |
| `data/labeling/ground_truth.csv` | **Cevap anahtarı.** Anotatör görürse kalibrasyon geçersiz olur. |
| `data/labeling/annotations_kuzey.json` | **Benim etiketlerim.** Meyusun görürse bağımsızlık bozulur, kappa yapay olarak şişer. Onun turu bitince karşılıklı paylaşılacak. |

Üçü de `.gitignore` ile engellendi ve `git check-ignore -v` ile doğrulandı. Yani bu bir
rica değil, mekanizma.

### 2.1 `.gitignore`'da bulunan hata (düzeltildi)

Eski hali şöyleydi:

```
data/labeling/ground_truth.csv  # GIZLI — anotatorler gormemeli
```

**Git `.gitignore` içinde satır içi yorum desteklemez.** Bu satırı yorum + desen olarak
değil, tamamı desen olan tek bir satır olarak okur — yani `ground_truth.csv  # GIZLI...`
adında bir dosya arar. Böyle bir dosya olmadığı için **kural hiçbir şeyi engellemiyordu.**
Aynı kusur `calib/` satırında da vardı.

Yani cevap anahtarı ve 200 PNG, fark edilmeseydi push'a girecekti. `#` yalnızca satırın
**başındaysa** yorumdur. Yorumlar kendi satırlarına taşındı.

Ders: `.gitignore`'a güvenme, `git check-ignore -v <dosya>` ile doğrula. Çıktı boşsa
dosya **engellenmiyor** demektir.

---

## 3. ⚠️ MEYUSUN — ETİKETLEMEDEN ÖNCE OKU

Kendi 100 etiketini bitirene kadar **şunlara bakma:**

1. `ground_truth.csv` — cevap anahtarı (repoda yok; script üretecek, **açma**)
2. Benim etiketlerim (repoda yok; sana turun bitmeden göndermeyeceğim)
3. Bu dokümanın **6. bölümü** — orada benim skorlarım ve karışıklık matrisim var.
   Hangi sınıfta hata yaptığımı bilmek seni etkiler.

Ölçtüğümüz şey "iki anotatör aynı protokolü uygulayınca aynı sonuca varıyor mu"
sorusudur. Bilgi sızıntısı kappa'yı yükseltir ama ölçümü anlamsızlaştırır.

**Turun bitmeden 6. ve 7. bölümü atla. Doğrudan 4. ve 5. bölümü uygula.**

---

## 4. Kurulum

### 4.1 Görüntüleri üret

Repoda PNG yok, kendi xBD kopyandan üreteceksin:

```bash
cd ~/disaster-routing
conda activate disaster
python scripts/phase2c_calibration_set.py
```

`data/labeling/calib/` altına 200 PNG (100 görev × pre/post), `tasks.json` ve
`ground_truth.csv` üretir. `SEED = 7` sabit olduğu için sende de birebir aynı 100 örnek
çıkar — bu, kappa'nın anlamlı olması için zorunlu.

**`ground_truth.csv`'yi açma.**

### 4.2 Label Studio'yu başlat

```bash
conda activate disaster
export LABEL_STUDIO_LOCAL_FILES_SERVING_ENABLED=true
export LABEL_STUDIO_LOCAL_FILES_DOCUMENT_ROOT=$HOME/disaster-routing
label-studio start
```

`DOCUMENT_ROOT` **proje kökü** olmalı, ev dizini değil. Sebebi 4.4'te.

### 4.3 Projeyi kur

1. Yeni proje: `Faz2c Kalibrasyon`
2. **Settings → Labeling Interface → Code** → `data/labeling/config.xml` içeriğini
   yapıştır → Save
3. **Settings → Cloud Storage → Add Source Storage**
   - Type: `Local files`
   - Path: `<proje kökü>/data/labeling/calib`
   - Save → **SYNC'E BASMA.**
     Sync, her PNG'yi ayrı görev sanıp 200 bozuk görev üretir ve pre/post eşleşmesini
     yok eder. Storage'ın durumunun "Failed" görünmesi normaldir — biz onu görev üretmek
     için değil, yalnızca dosya sunumunu yetkilendirmek için ekliyoruz.
4. **Import** → `data/labeling/tasks.json` → `Tasks: 100/100` görmelisin

### 4.4 Bende çıkan 404 hatası ve kök nedeni

Etiketleme ekranında görüntüler yüklenmiyordu:

```
There was an issue loading URL from $pre value
```

**Kök neden:** `phase2c_calibration_set.py` içinde

```python
DOC_ROOT = os.path.expanduser("~")     # → /home/<kullanici>
```

Script, Label Studio'nun belge kökünün **ev dizini** olduğunu varsayıyordu. Ben Label
Studio'yu `DOCUMENT_ROOT=/home/kuzey/disaster-routing` ile başlatmıştım.

Label Studio yolu şöyle çözer:

```
DOCUMENT_ROOT + "/" + <?d= parametresi>
```

`relpath(abs_pre, /home/kuzey)` → `disaster-routing/data/labeling/calib/...`
Label Studio bunu kendi köküne ekliyor →
`/home/kuzey/disaster-routing/disaster-routing/data/...` → **var olmayan yol.**

Kod hatası değil, iki bileşen arasında **sözleşme uyuşmazlığı**.

**Düzeltme (bu push'ta):**

```python
DOC_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
```

`__file__` script'in kendi yolu; iki `dirname` proje kökünü verir. Artık kullanıcı
adından bağımsız ve `DOCUMENT_ROOT` ayarıyla tutarlı.

**Neden ev dizinini kök yapmadık:** o çözüm de işe yarardı ama Label Studio'ya tüm ev
dizinini HTTP üzerinden sunma yetkisi verirdi. Erişimi proje ağacıyla sınırlamak doğru
olan.

**Doğrulama testi** — Label Studio oturumu açıkken tarayıcıda:

```
http://localhost:8080/data/local-files/?d=data/labeling/calib/task_0000_pre.png
```

Görüntü açılıyorsa yol çözümlemesi doğrudur.

**Uyarı:** Label Studio, import ettiği görevleri veritabanına kopyalar. `tasks.json`'ı
import ettikten sonra düzeltirsen mevcut görevleri **silip yeniden import** etmen gerekir;
diskteki dosyayı düzeltmek yetmez.

### 4.5 Export

Bitince: **Export → `JSON`** (JSON-MIN **değil**).

`phase2c_compare.py`, `item["data"]["task_id"]` ve `item["annotations"][0]["result"]`
iç içe yapısını okur. JSON-MIN bunu düzleştirir, script sıfır etiket okur ve sessizce
"bulunamadi" der.

İndirdiğin dosyayı şu isimle kaydet:

```
data/labeling/annotations_meyusun.json
```

İsim sözleşmelidir: script `annotations_*.json` glob'u ile arar, `annotations_` sonrasını
anotatör adı olarak rapora yazar.

**Bu dosya `.gitignore` ile engelli — push edemezsin, doğrusu da bu.** Turun bitince bana
haber ver, ikimiz de dosyalarımızı aynı anda karşılıklı gönderelim.

---

## 5. Etiketleme protokolü

- Sadece görüntünün **geometrik merkezindeki** binayı değerlendir. Kadrajdaki diğer
  binalar dikkate alınmaz.
- Klavye kısayolları `1`–`5`.
- `5` (`emin-degilim`) seçtiğinde not alanına **tek cümlelik gerekçe** yaz. Bu etiketler
  skorlamadan hariç tutulur, ama neden emin olamadığın protokol revizyonu için veridir.
- 100 görevi tek oturumda bitirme. Yorgunluk tutarlılığı düşürür ve doğrudan kappa'ya
  yansır. Ben ~4 oturumda bitirdim.

Sınıf tanımları `config.xml` içindeki `hint` alanlarındadır.

**Önemli:** Bu tanımların yetersiz olduğunu düşünüyorum (gerekçesi 6. bölümde). Yine de
**protokolü değiştirme, olduğu gibi uygula.** Sebep: kappa'nın anlamlı olması için ikimizin
aynı protokol altında etiketlemiş olması gerekir. Protokol revizyonu ölçümden sonra gelir;
şimdi değiştirirsek iki tur karşılaştırılamaz hale gelir.

---

## 6. ⛔ Kuzey turu sonuçları — kendi turun bitmeden okuma

Ham çıktı: `reports/phase2c_kuzey.txt`

```
degerlendirilen  : 90 / 100
'emin degilim'   : 10 (10%)
4-sinif dogruluk : 0.556
ikili (hasarli)  : recall 0.630 | precision 0.829
```

### Karışıklık matrisi (satır = xBD gerçek, sütun = Kuzey)

|              | no-damage | minor-damage | major-damage | destroyed | toplam |
|--------------|----------:|-------------:|-------------:|----------:|-------:|
| no-damage    |    **17** |            4 |            2 |         0 |     23 |
| minor-damage |        10 |        **7** |            4 |         0 |     21 |
| major-damage |        12 |            5 |        **3** |         2 |     22 |
| destroyed    |         0 |            0 |            1 |    **23** |     24 |

### Okuma

**Çalışan kısım:** `destroyed` 23/24, `no-damage` 17/23. Eksenin iki ucunu görüyorum.

**Çöken kısım:** `major-damage` satırı — 22 örneğin yalnızca **3**'ü doğru;
**12'sine `no-damage` dedim.** `minor-damage` satırında da 21 örneğin 10'una `no-damage`
dedim.

**Hatalar rastgele değil, tek yönlü:** hasarı sistematik olarak olduğundan hafif okuyorum.
Bu bir dikkat sorunu değil, **protokol sorunu**.

**Projeye etkisi:** `recall 0.630` — gerçekten hasarlı 54 binanın 20'sini kaçırmışım.
`precision 0.829` — "hasarlı" dediğimde genelde haklıyım. Bu asimetri kalibrasyon
açısından en kötü kombinasyon: temkinli değil, fazla iyimserim.

Rota planlama açısından `major-damage` binayı `no-damage` saymak, molozunu yola
dökebilecek bir binayı yok saymaktır; planlayıcı kapalı yolu açık kabul eder. Bu, Faz 1'de
düzelttiğimiz `edge_cost` hatasının veri katmanındaki eşdeğeridir — sistem hata vermez,
sadece sessizce geçilmez yoldan geçirir.

### Protokol kusuru teşhisi

`config.xml` hint'leri:

| Sınıf | Hint | Sorun |
|---|---|---|
| no-damage | "Yapisal degisiklik yok" | Neye göre "değişiklik"? Ölçüt yok. |
| minor-damage | "çatı **büyük ölçüde** yerinde" | "Büyük ölçüde" ölçülemez. |
| major-damage | "çatı **kısmen** çökmüş" | "Kısmen" ölçülemez. |
| destroyed | "Bina tamamen çökmüş / yerinde moloz" | Tek net (ikili) kriter. |

`destroyed`'in %96 doğru olması tesadüf değil: **tek ikili kriteri olan sınıf o.**
Diğer üçü sürekli bir eksen ("ne kadar çökmüş?") üzerinde sözel niteleyicilerle bölünmüş,
sayısal eşik yok. Eşiksiz sınıflandırıcı kararsızdır.

**İkinci kusur:** hiçbir hint `no-damage` ile `minor/major` arasında zorunlu bir ayırt
edici belirtmiyor. Emin olmadığımda "yapısal değişiklik yok" varsayılan davranışa
dönüşüyor — en yakın ve en masum sınıfa düşüyorum.

**Üçüncü kusur:** `<Choices toName="post">` — sınıflandırma yalnızca *sonra* görüntüsüne
bağlanmış. Ama karar bir **fark** kararıdır. Protokolde "önce ile sonrayı karşılaştır"
diyen tek bir talimat yok; header sadece "ORTADAKI binayi degerlendir" diyor.

Bunlar Meyusun'un turundan sonra revize edilecek.

---

## 7. Sıradaki adımlar

| # | İş | Kim |
|---|---|---|
| 1 | Hata analizi: xBD `major-damage` / Kuzey `no-damage` olan 12 görevin görsel incelemesi | Kuzey |
| 2 | Aynı 100 görevi bağımsız etiketle → `annotations_meyusun.json` | **Meyusun** |
| 3 | Dosyaları karşılıklı paylaş → `python scripts/phase2c_compare.py` → kappa | ikisi |
| 4 | κ ≥ 0.60 → Maxar/Kahramanmaraş verisine geç | ikisi |
| 5 | κ < 0.60 → protokolü ölçülebilir eşiklerle revize et → yeniden etiketle | ikisi |

Adım 1'in çıktısı (12 görüntüde xBD'nin gördüğü ama benim kaçırdığım görsel kanıt
tipleri) adım 5'in girdisidir. Kappa düşük çıkarsa protokolü havadan değil, bu somut
gözlemlerden türeteceğiz.

**Yüksek kappa tek başına yeterli değildir.** İkimiz de aynı yöne sistematik olarak
kayıyorsak kappa yüksek çıkar ama ortak körlüğü gizler. Bu yüzden kappa'nın yanında her
iki karışıklık matrisine de bakacağız.

---

## 8. Açık borçlar (Faz 2c dışı)

- `edge_cost` düzeltmesi ve `verify_phase1.py` yerel makineye aktarılacak — danışman
  toplantısından önce.
- `outputs/xbd_sample.png` git tarafından takip ediliyor, ama `.gitignore`'da `outputs/`
  yazıyor. Sebep: dosya kural yazılmadan **önce** commit'lenmiş; `.gitignore` yalnızca
  takip **edilmeyen** dosyalara uygulanır. Temizlenecek (`git rm --cached`).
- Faz 3 metodoloji sırası: CVA → Siamese CNN → foundation model backbone (ablation study).
  CVA ve Siamese birbirinin alternatifi değil: CVA eğitimsiz ikili değişim tespiti,
  Siamese 4-sınıf hasar sınıflandırması.
