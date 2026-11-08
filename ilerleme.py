"""Kullanıcının ilerleme kaydı (lügat kartlarına verilen "Biliyorum / Bilmiyorum" cevapları).

Sözlük verisinden ayrı bir SQLite dosyasında tutulur (instance/ilerleme.db) ve Git'e eklenmez.
Kayıtlar hiç silinmez: her cevap yeni bir satır olarak eklenir; bir kelimenin "durumu"
ona verilen son cevaptır. Kelimeler kalıcı anahtarlarıyla ("yazılış|asıl okunuş") saklanır,
böylece sözlük verisi yeniden üretilse de ilerleme kaybolmaz.

İleride sitede birden çok kullanıcı olunca `kullanici` sütunu dolacak; yerelde boştur (NULL).
"""

from datetime import datetime, timezone
from pathlib import Path
import random
import sqlite3

OTURUM_BOYU = 5
EN_FAZLA_TEKRAR = 3   # bir oturuma geri gelen "bilmiyorum" kartı sayısı (en çok)
ESKI_TEKRAR = 1       # bir oturuma tekrar için alınan "biliyorum" kartı sayısı

SEMA = """
CREATE TABLE IF NOT EXISTS lugat_cevaplari (
    id         INTEGER PRIMARY KEY,
    kullanici  TEXT,                -- yerelde NULL; sitede Google kullanıcı kimliği olacak
    anahtar    TEXT NOT NULL,       -- kelimenin kalıcı anahtarı
    bildi      INTEGER NOT NULL CHECK (bildi IN (0, 1)),
    zaman      TEXT NOT NULL        -- UTC, ISO 8601
);
CREATE INDEX IF NOT EXISTS lugat_cevaplari_anahtar ON lugat_cevaplari(kullanici, anahtar);
"""


def baglan(yol: Path) -> sqlite3.Connection:
    yol.parent.mkdir(parents=True, exist_ok=True)
    b = sqlite3.connect(yol)
    b.row_factory = sqlite3.Row
    b.executescript(SEMA)
    return b


def cevap_kaydet(b: sqlite3.Connection, anahtar: str, bildi: bool, kullanici: str | None = None) -> None:
    b.execute(
        "INSERT INTO lugat_cevaplari (kullanici, anahtar, bildi, zaman) VALUES (?, ?, ?, ?)",
        (kullanici, anahtar, int(bildi), datetime.now(timezone.utc).isoformat(timespec="seconds")),
    )
    b.commit()


def son_durumlar(b: sqlite3.Connection, kullanici: str | None = None) -> dict[str, sqlite3.Row]:
    """anahtar → son cevap (bildi, zaman). Hiç cevaplanmamış kelimeler sözlükte yer almaz."""
    satirlar = b.execute(
        """SELECT anahtar, bildi, zaman FROM lugat_cevaplari c
           WHERE kullanici IS ? AND id = (SELECT MAX(id) FROM lugat_cevaplari
                                          WHERE anahtar = c.anahtar AND kullanici IS ?)""",
        (kullanici, kullanici),
    ).fetchall()
    return {s["anahtar"]: s for s in satirlar}


def oturum_sec(tum_anahtarlar: list[str], durumlar: dict, mod: str,
               onceki: list[str] | None = None, rastgele: random.Random | None = None) -> list[str]:
    """Bir sonraki oturumun kartlarını seçer.

    mod "yeni":  yalnızca hiç görülmemiş kelimeler.
    mod "devam": önce "bilmiyorum" denen kelimeler (önceki oturumdakiler önde, en çok 3),
                 sonra en uzun süredir görülmeyen 1 "biliyorum" kelimesi (tekrar),
                 kalan yerler yeni kelimelerle dolar.
    Yeterli kelime yoksa diğer gruplardan tamamlanır.
    """
    r = rastgele or random.Random()
    onceki = onceki or []
    yeni = [a for a in tum_anahtarlar if a not in durumlar]
    r.shuffle(yeni)
    bilinmeyen = [a for a, d in durumlar.items() if not d["bildi"]]
    bilinen = sorted((a for a, d in durumlar.items() if d["bildi"]), key=lambda a: durumlar[a]["zaman"])

    secim: list[str] = []

    def ekle(adaylar, sayi):
        for a in adaylar:
            if len(secim) >= OTURUM_BOYU or sayi <= 0:
                return
            if a not in secim:
                secim.append(a)
                sayi -= 1

    if mod == "devam":
        bilinmeyen.sort(key=lambda a: (a not in onceki, durumlar[a]["zaman"]))
        ekle(bilinmeyen, EN_FAZLA_TEKRAR)
        ekle(bilinen, ESKI_TEKRAR)
    ekle(yeni, OTURUM_BOYU)
    # Yeni kelime kalmadıysa eskilerden tamamla.
    ekle(bilinmeyen, OTURUM_BOYU)
    ekle(bilinen, OTURUM_BOYU)
    r.shuffle(secim)
    return secim
