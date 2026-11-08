"""Vikisözlük (İngilizce Wiktionary) Osmanlıca verisini indirir.

Veri: kaikki.org'un wiktextract ile hazırladığı JSONL dosyası.
Lisans: CC BY-SA 4.0 (Wiktionary içeriği). Ham dosya büyük olduğu için Git'e eklenmez.

Kullanım:  python scripts/vikisozluk_indir.py
"""

from pathlib import Path
import shutil
import urllib.request

URL = "https://kaikki.org/dictionary/Ottoman%20Turkish/kaikki.org-dictionary-OttomanTurkish.jsonl"
HEDEF = Path(__file__).resolve().parents[1] / "data" / "ham" / "vikisozluk-osmanlica.jsonl"


def main():
    HEDEF.parent.mkdir(parents=True, exist_ok=True)
    gecici = HEDEF.with_suffix(".indiriliyor")
    istek = urllib.request.Request(URL, headers={"User-Agent": "osmanlica-egitim/0.1"})
    with urllib.request.urlopen(istek, timeout=120) as cevap, gecici.open("wb") as dosya:
        shutil.copyfileobj(cevap, dosya)
    gecici.replace(HEDEF)
    print(f"İndirildi: {HEDEF} ({HEDEF.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
