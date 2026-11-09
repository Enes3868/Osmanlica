"""Fezleke PDF'inin sayfalarını resme çevirir ve her sayfadaki metin satırlarını bulur.

Bu betik yalnızca veri hazırlarken çalışır (uygulama çalışırken gerekmez).
Gerekenler: pip install pymupdf numpy pillow

Çıktı (data/kitaplar/fezleke/):
  sayfalar/sNNN.jpg   — sayfa resmi (gri tonlu)
  satirlar.json       — her sayfa için metin satırlarının dikey sınırları (resim yüksekliğine oranla)

Satır bulma: sayfa yatay olarak taranır, her piksel satırındaki "mürekkep" miktarı ölçülür;
mürekkepli bantlar satırlardır. Harf noktaları gibi ince bantlar en yakın satıra katılır.
Üstteki başlık (sayfa numarası ve kitap adı) çizginin üstünde kaldığı için atlanır.

Kullanım:  python scripts/fezleke_satirlar.py <pdf> [--ilk 4 --son 226] [--isaretli klasör]
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pymupdf
from PIL import Image, ImageDraw

KOK = Path(__file__).resolve().parents[1]
HEDEF = KOK / "data" / "kitaplar" / "fezleke"
DPI = 110


def sayfa_resmi(sayfa) -> Image.Image:
    pm = sayfa.get_pixmap(dpi=DPI, colorspace=pymupdf.csGRAY)
    return Image.frombytes("L", (pm.width, pm.height), pm.samples)


def egiklik(resim: Image.Image) -> float:
    """Taramanın eğiklik açısı (derece). Satırlar düz iken yatay mürekkep profili en "keskin" olur;
    küçük açılar denenip profil varyansının en büyük olduğu açı seçilir."""
    kucuk = resim.resize((resim.width // 3, resim.height // 3))
    a = np.asarray(kucuk, dtype=np.float32)
    murekkep = (a < np.percentile(a, 90) - 60).astype(np.float32)
    en_iyi, en_iyi_puan = 0.0, -1.0
    for aci in np.arange(-3, 3.01, 0.25):
        don = Image.fromarray((murekkep * 255).astype(np.uint8)).rotate(aci, resample=Image.BILINEAR)
        puan = float(np.asarray(don, dtype=np.float32).mean(axis=1).var())
        if puan > en_iyi_puan:
            en_iyi, en_iyi_puan = float(aci), puan
    return en_iyi


def duzelt(resim: Image.Image) -> Image.Image:
    """Belirgin eğik taramaları düzeltir; düz sayfalara dokunmaz (bulunan satırlar değişmesin)."""
    aci = egiklik(resim)
    if abs(aci) < 2:
        return resim
    kagit = int(np.percentile(np.asarray(resim), 90))
    return resim.rotate(aci, resample=Image.BICUBIC, fillcolor=kagit)


def satirlari_bul(resim: Image.Image) -> list[tuple[int, int]]:
    a = np.asarray(resim, dtype=np.float32)
    h, w = a.shape
    # Kâğıt rengi sayfadan sayfaya değişir: eşik, sayfanın kendi parlaklığına göre.
    kagit = np.percentile(a, 90)
    murekkep = a < kagit - 60
    # Kenar boşluklarını ve cilt gölgesini at. Cilt/sayfa kenarı neredeyse baştan sona koyu
    # (yoğunluk çok yüksek); metin sütunları orta yoğunlukta. İlk ve son metin sütunu arasını al
    # (kısa satırlar sağdan başladığı için sağ kenar kesilmemeli).
    sutun = murekkep.mean(axis=0)
    metin_sutunlari = np.where((sutun > 0.02) & (sutun < 0.45))[0]
    x0, x1 = (int(metin_sutunlari[0]), int(metin_sutunlari[-1]) + 1) if len(metin_sutunlari) else (0, w)
    satir = murekkep[:, x0:x1].mean(axis=1)
    # Başlık çizgisi: sayfanın üst kısmında, sütun boyunca uzanan yatay çizgi.
    # Çizgi ve üstündeki başlık (sayfa numarası, kitap/bab adı) satır sayılmaz.
    # Çizgi incedir (birkaç piksel); yoğun ama kalın bantlar metin satırıdır, çizgi sayılmaz.
    ust = int(h * 0.2)
    baslangic, y = 0, 0
    while y < ust:
        if satir[y] > 0.3:
            son = y
            while son + 1 < h and satir[son + 1] > 0.3:
                son += 1
            if son - y + 1 <= 6:
                baslangic = son + 2
                break
            y = son + 1
        else:
            y += 1
    satir = np.convolve(satir, np.ones(3) / 3, mode="same")
    # Düşük eşik: kısa (paragraf sonu) satırlar da az mürekkepli olsa yakalanmalı.
    esik = max(0.004, satir.max() * 0.02)
    bantlar, bas = [], None
    for y, v in enumerate(satir):
        if y < baslangic:
            continue
        if v > esik and bas is None:
            bas = y
        elif v <= esik and bas is not None:
            bantlar.append([bas, y])
            bas = None
    if bas is not None:
        bantlar.append([bas, h])
    if not bantlar:
        return []
    # Süs çizgileri (bölüm ayracı): ince ve çok yoğun bantlar satır değildir.
    bantlar = [b for b in bantlar if not (b[1] - b[0] <= 6 and satir[b[0]:b[1]].max() > 0.3)]
    # İnce bantları (nokta, hareke) komşu satıra kat.
    yukseklik = np.median([b1 - b0 for b0, b1 in bantlar])
    birlesik: list[list[int]] = []
    for b in bantlar:
        if birlesik and (b[1] - b[0] < yukseklik * 0.45 or b[0] - birlesik[-1][1] < 2):
            birlesik[-1][1] = b[1]
        else:
            birlesik.append(b)
    if len(birlesik) > 1 and birlesik[0][1] - birlesik[0][0] < yukseklik * 0.45:
        birlesik[1][0] = birlesik[0][0]
        birlesik.pop(0)
    # Birbirine değen satırlar tek bant olur: normalden çok yüksek bantları en az mürekkepli yerden böl.
    bolunmus: list[list[int]] = []
    for b0, b1 in birlesik:
        parcalar = [[b0, b1]]
        while parcalar[-1][1] - parcalar[-1][0] > yukseklik * 1.6:
            c0, c1 = parcalar.pop()
            kac = round((c1 - c0) / yukseklik)
            ara = satir[c0 + int(yukseklik * 0.6): c1 - int(yukseklik * 0.6)]
            if kac < 2 or len(ara) == 0:
                parcalar.append([c0, c1])
                break
            kes = c0 + int(yukseklik * 0.6) + int(np.argmin(ara))
            parcalar += [[c0, kes], [kes, c1]]
            parcalar.sort()
            if parcalar[-1][1] - parcalar[-1][0] <= yukseklik * 1.6:
                break
        bolunmus += parcalar
    birlesik = sorted(bolunmus)
    # Her satıra biraz pay bırak (harflerin kuyrukları kesilmesin).
    pay = int(yukseklik * 0.25)
    return [(max(0, b0 - pay), min(h, b1 + pay)) for b0, b1 in birlesik]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("pdf")
    p.add_argument("--ilk", type=int, default=4)
    p.add_argument("--son", type=int, default=226)
    p.add_argument("--isaretli", help="satır numaralı kontrol resimlerinin yazılacağı klasör")
    a = p.parse_args()

    d = pymupdf.open(a.pdf)
    (HEDEF / "sayfalar").mkdir(parents=True, exist_ok=True)
    json_yol = HEDEF / "satirlar.json"
    veri = json.loads(json_yol.read_text(encoding="utf-8")) if json_yol.exists() else {}
    for n in range(a.ilk, a.son + 1):
        resim = duzelt(sayfa_resmi(d[n - 1]))
        satirlar = satirlari_bul(resim)
        resim.save(HEDEF / "sayfalar" / f"s{n:03d}.jpg", quality=72, optimize=True)
        veri[str(n)] = {"genislik": resim.width, "yukseklik": resim.height,
                        "satirlar": [[round(y0 / resim.height, 5), round(y1 / resim.height, 5)]
                                     for y0, y1 in satirlar]}
        if a.isaretli:
            k = resim.convert("RGB")
            c = ImageDraw.Draw(k)
            for i, (y0, y1) in enumerate(satirlar, 1):
                c.rectangle([2, y0, k.width - 3, y1], outline=(220, 0, 0))
                c.text((6, y0 + 2), str(i), fill=(220, 0, 0))
            k.save(Path(a.isaretli) / f"isaretli_s{n:03d}.png")
        print(n, len(satirlar), "satır")
    json_yol.write_text(json.dumps(veri, ensure_ascii=False, indent=0, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    main()
