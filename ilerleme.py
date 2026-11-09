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

-- Kitap tercüme: her sayfa çalışması bir "deneme"dir; satır cevapları denemeye bağlıdır.
CREATE TABLE IF NOT EXISTS kitap_denemeleri (
    id         INTEGER PRIMARY KEY,
    kullanici  TEXT,
    kitap      TEXT NOT NULL,
    sayfa      INTEGER NOT NULL,     -- PDF sayfa numarası
    basladi    TEXT NOT NULL,
    bitti      TEXT,                 -- NULL: devam ediyor
    dogru      INTEGER,              -- bitince: doğru kelime sayısı
    toplam     INTEGER               -- bitince: doğru metindeki kelime sayısı
);
CREATE TABLE IF NOT EXISTS kitap_satir_cevaplari (
    id         INTEGER PRIMARY KEY,
    deneme_id  INTEGER NOT NULL REFERENCES kitap_denemeleri(id),
    satir      INTEGER NOT NULL,     -- 1'den başlar
    cevap      TEXT NOT NULL,
    zaman      TEXT NOT NULL,
    UNIQUE (deneme_id, satir)
);
"""


def _simdi() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def acik_deneme(b, kitap: str, sayfa: int, kullanici: str | None = None):
    return b.execute(
        """SELECT * FROM kitap_denemeleri WHERE kullanici IS ? AND kitap = ? AND sayfa = ? AND bitti IS NULL
           ORDER BY id DESC LIMIT 1""", (kullanici, kitap, sayfa)).fetchone()


def deneme_baslat(b, kitap: str, sayfa: int, kullanici: str | None = None) -> int:
    imlec = b.execute("INSERT INTO kitap_denemeleri (kullanici, kitap, sayfa, basladi) VALUES (?, ?, ?, ?)",
                      (kullanici, kitap, sayfa, _simdi()))
    b.commit()
    return imlec.lastrowid


def satir_cevaplari(b, deneme_id: int) -> dict[int, str]:
    return {s["satir"]: s["cevap"] for s in
            b.execute("SELECT satir, cevap FROM kitap_satir_cevaplari WHERE deneme_id = ?", (deneme_id,))}


def satir_kaydet(b, deneme_id: int, satir: int, cevap: str) -> None:
    b.execute("INSERT INTO kitap_satir_cevaplari (deneme_id, satir, cevap, zaman) VALUES (?, ?, ?, ?)",
              (deneme_id, satir, cevap, _simdi()))
    b.commit()


def deneme_bitir(b, deneme_id: int, dogru: int, toplam: int) -> None:
    b.execute("UPDATE kitap_denemeleri SET bitti = ?, dogru = ?, toplam = ? WHERE id = ? AND bitti IS NULL",
              (_simdi(), dogru, toplam, deneme_id))
    b.commit()


def son_bitmis_deneme(b, kitap: str, sayfa: int, kullanici: str | None = None):
    return b.execute(
        """SELECT * FROM kitap_denemeleri WHERE kullanici IS ? AND kitap = ? AND sayfa = ? AND bitti IS NOT NULL
           ORDER BY id DESC LIMIT 1""", (kullanici, kitap, sayfa)).fetchone()


def sayfa_durumlari(b, kitap: str, kullanici: str | None = None) -> dict[int, dict]:
    """sayfa → {"bitti": kaç kez bitirildi, "en_iyi": en iyi yüzde, "devam": açık deneme var mı}"""
    sonuc: dict[int, dict] = {}
    for s in b.execute("SELECT sayfa, bitti, dogru, toplam FROM kitap_denemeleri WHERE kullanici IS ? AND kitap = ?",
                       (kullanici, kitap)):
        d = sonuc.setdefault(s["sayfa"], {"bitti": 0, "en_iyi": None, "devam": False})
        if s["bitti"]:
            d["bitti"] += 1
            yuzde = round(100 * s["dogru"] / s["toplam"]) if s["toplam"] else 100
            d["en_iyi"] = max(d["en_iyi"] or 0, yuzde)
        else:
            d["devam"] = True
    return sonuc


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
