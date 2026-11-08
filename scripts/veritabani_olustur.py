"""Seçim ve çeviri dosyalarından data/vikisozluk.sql dosyasını üretir.

Girdi:
  data/vikisozluk_secim.csv    — scripts/vikisozluk_sec.py çıktısı (Osmanlıca, okunuşlar, İngilizce anlam)
  data/vikisozluk_anlamlar.csv — Türkçe anlamlar (AI çevirisi). Çevirisi olmayan satır alınmaz;
                                 bu, uygun bulunmayan kelimeleri dışarıda bırakmanın yoludur.
Çıktı:
  data/vikisozluk.sql          — uygulamanın yüklediği veri (CC BY-SA 4.0)

Kullanım:  python scripts/veritabani_olustur.py
"""

import csv
from pathlib import Path

VERI = Path(__file__).resolve().parents[1] / "data"
KAYNAK_ID = 1


def sql(deger) -> str:
    if deger is None or deger == "":
        return "NULL"
    if isinstance(deger, int):
        return str(deger)
    return "'" + str(deger).replace("'", "''") + "'"


def main():
    with (VERI / "vikisozluk_anlamlar.csv").open(encoding="utf-8") as f:
        anlamlar = {s["anahtar"]: s["anlam"] for s in csv.DictReader(f)}
    with (VERI / "vikisozluk_secim.csv").open(encoding="utf-8") as f:
        secim = [s for s in csv.DictReader(f) if s["anahtar"] in anlamlar]

    satirlar = [
        "-- OTOMATİK ÜRETİLDİ: scripts/veritabani_olustur.py — elle düzenlemeyin.",
        "-- Kaynak: Vikisözlük (İngilizce Wiktionary, Osmanlıca maddeler), kaikki.org/wiktextract aracılığıyla.",
        "-- Lisans: CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0/).",
        "-- Türkçe anlamlar İngilizce anlamlardan AI ile çevrilmiştir ve kontrol edilmemiştir.",
        "",
        "INSERT INTO kaynaklar (id, ad, yazar, yil, lisans, url, notlar) VALUES (",
        f"    {KAYNAK_ID}, 'Vikisözlük (Wiktionary) — Osmanlıca', 'Wiktionary katkıcıları', 2024,",
        "    'CC BY-SA 4.0', 'https://en.wiktionary.org/wiki/Category:Ottoman_Turkish_language',",
        "    'kaikki.org verisi (2024-12-04 Wiktionary dökümü). Türkçe anlamlar AI çevirisidir.');",
        "",
    ]
    for kayit_id, s in enumerate(secim, start=1):
        okunuslar = [o.strip() for o in s["okunuslar"].split(";") if o.strip()]
        satirlar.append(
            "INSERT INTO kayitlar (id, anahtar, osmanlica, anlam, anlam_ai, anlam_ingilizce, gunumuz, koken, "
            "edebi, tur, kaynak_id) "
            f"VALUES ({kayit_id}, {sql(s['anahtar'])}, {sql(s['osmanlica'])},{sql(anlamlar[s['anahtar']])}, 1, "
            f"{sql(s['ingilizce'].replace(' ¦ ', '; '))}, {sql(s['gunumuz'])}, {sql(s.get('koken'))}, "
            f"{1 if s.get('edebi') == '1' else 0}, {sql(s['tur'])}, {KAYNAK_ID});"
        )
        for i, o in enumerate(okunuslar):
            satirlar.append(
                f"INSERT INTO okunuslar (kayit_id, okunus, asil) VALUES ({kayit_id}, {sql(o)}, {1 if i == 0 else 0});"
            )
    (VERI / "vikisozluk.sql").write_text("\n".join(satirlar) + "\n", encoding="utf-8")
    print(f"{len(secim)} kayıt → {VERI / 'vikisozluk.sql'}")


if __name__ == "__main__":
    main()
