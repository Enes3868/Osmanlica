"""Ham Vikisözlük verisinden uygulamaya alınacak kelimeleri ve cümleleri seçer.

Çıktı: data/vikisozluk_secim.csv  (her satır bir kayıt; Türkçe anlamı ayrı dosyadadır)

Seçim kuralları:
- Kelimeler: isim, sıfat, fiil, zarf; tek kelimelik yazılış; okunuşu (romanization) var;
  günümüz Türkçesinde karşılığı (descendant) var; eskimiş/biçim-göndermesi olmayan anlamı var.
- Aynı yazılış ve aynı asıl okunuşa sahip maddeler (ör. sıfat + isim) tek kayıtta birleşir.
  Aynı yazılışın farklı okunuşları ayrı kayıtlardır (gel / gül gibi farklı kelimeler).
- Cümleler: kaynak/yazar belirtilmeyen (editörlerin yazdığı) kısa örnek cümleler;
  telifli eserlerden alıntı olabilecek olanlar alınmaz.

Kullanım:  python scripts/vikisozluk_sec.py [--kelime 500] [--cumle 50]
"""

import argparse
import csv
import json
from pathlib import Path
import random
import re
import sys

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))
from checker import normallestir  # noqa: E402

HAM = KOK / "data" / "ham" / "vikisozluk-osmanlica.jsonl"
CIKTI = KOK / "data" / "vikisozluk_secim.csv"
TURLER = {"noun", "adj", "verb", "adv"}
ATLANAN_ETIKETLER = {"alt-of", "form-of", "alternative", "obsolete", "archaic", "historical",
                     "misspelling", "abbreviation", "letter", "morpheme"}
# Transliterasyondaki ayn/hemze işaretleri (ʼazîz → azîz). Türkçe kesme işareti (') korunur.
ISARETLER = re.compile("[ʼʻʾʿʹʽ]")
TOHUM = 20261108  # aynı seçim her çalıştırmada aynı çıksın


def temizle(metin: str) -> str:
    return " ".join(ISARETLER.sub("", metin).split())


def okunuslar(madde) -> list[str]:
    sonuc = []
    for f in madde.get("forms", []):
        if "romanization" in f.get("tags", []):
            o = temizle(f["form"])
            if o and o not in sonuc:
                sonuc.append(o)
    return sonuc


def anlamlar(madde) -> list[str]:
    sonuc = []
    for s in madde.get("senses", []):
        if ATLANAN_ETIKETLER & set(s.get("tags", [])):
            continue
        for g in s.get("glosses", []):
            if g not in sonuc:
                sonuc.append(g)
    return sonuc


def gunumuz(madde) -> str:
    for d in madde.get("descendants", []):
        if d.get("lang_code") == "tr" and d.get("word"):
            return d["word"]
    return ""


def kelime_kayitlari(maddeler):
    """Yazılış → [kayıt]; aynı asıl okunuşlu maddeler birleştirilir."""
    gruplar: dict[str, dict[str, dict]] = {}
    for m in maddeler:
        if m.get("pos") not in TURLER or " " in m["word"].strip():
            continue
        oks, ans, gun = okunuslar(m), anlamlar(m), gunumuz(m)
        if not (oks and ans and gun) or any(" " in o for o in oks):
            continue
        kayitlar = gruplar.setdefault(m["word"].strip(), {})
        k = kayitlar.setdefault(oks[0], {"okunuslar": [], "anlamlar": [], "gunumuz": gun})
        k["okunuslar"] += [o for o in oks if o not in k["okunuslar"]]
        k["anlamlar"] += [a for a in ans if a not in k["anlamlar"]]
    return gruplar


def cumleler(maddeler):
    gorulen, sonuc = set(), []
    for m in maddeler:
        for s in m.get("senses", []):
            for x in s.get("examples", []):
                metin, okunus, ing = (x.get(a, "").strip() for a in ("text", "roman", "english"))
                if x.get("ref") or not (metin and okunus and ing) or "\n" in metin:
                    continue
                okunus = temizle(okunus)
                kelime = len(okunus.split())
                # Arap harfli metin ile okunuşun kelime sayıları tutarlı olmalı (bozuk satırları ele).
                if not 2 <= kelime <= 8 or abs(len(metin.split()) - kelime) > 1:
                    continue
                if metin in gorulen:
                    continue
                gorulen.add(metin)
                sonuc.append({"osmanlica": metin, "okunuslar": [okunus], "anlamlar": [ing], "gunumuz": ""})
    return sonuc


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--kelime", type=int, default=500, help="seçilecek yazılış sayısı")
    p.add_argument("--cumle", type=int, default=50)
    a = p.parse_args()

    if not HAM.exists():
        sys.exit("Önce ham veriyi indirin: python scripts/vikisozluk_indir.py")
    maddeler = [json.loads(s) for s in HAM.open(encoding="utf-8")]

    rastgele = random.Random(TOHUM)
    gruplar = kelime_kayitlari(maddeler)
    # Önce bugün de aynı biçimde kullanılan kelimeler (okunuş ≈ günümüz biçimi): öğrenmeye daha elverişli.
    yasayan = [y for y, ks in gruplar.items()
               if any(normallestir(k["gunumuz"]) in map(normallestir, k["okunuslar"]) for k in ks.values())]
    diger = [y for y in gruplar if y not in set(yasayan)]
    rastgele.shuffle(yasayan)
    rastgele.shuffle(diger)
    secilen = sorted((yasayan + diger)[: a.kelime])

    cumle = cumleler(maddeler)
    rastgele.shuffle(cumle)
    cumle = sorted(cumle[: a.cumle], key=lambda c: c["osmanlica"])

    with CIKTI.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["anahtar", "tur", "osmanlica", "okunuslar", "gunumuz", "ingilizce"])
        for yazilis in secilen:
            for asil, k in gruplar[yazilis].items():
                w.writerow([f"{yazilis}|{asil}", "kelime", yazilis, "; ".join(k["okunuslar"]),
                            k["gunumuz"], " ¦ ".join(k["anlamlar"][:4])])
        for c in cumle:
            w.writerow([f"{c['osmanlica']}|{c['okunuslar'][0]}", "cumle", c["osmanlica"],
                        c["okunuslar"][0], "", c["anlamlar"][0]])
    print(f"{len(secilen)} yazılış, {len(cumle)} cümle → {CIKTI}")


if __name__ == "__main__":
    main()
