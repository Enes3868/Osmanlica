"""Kitap tercüme bölümünün verisi: kitaplar, sayfa resimleri, satırlar ve doğru metinler.

Her kitap data/kitaplar/<kod>/ klasöründedir:
  kitap.json        — ad, yazar, yıl, lisans, kaynak
  sayfalar/sNNN.jpg — sayfa resimleri (NNN = PDF sayfa numarası)
  satirlar.json     — scripts/fezleke_satirlar.py'nin bulduğu satır bantları (resme oranla y0, y1)
  metin/sNNN.txt    — doğru Latin harfli metin; bulunan her bant için bir satır:
                        metin  → bu bandın okunuşu
                        -      → bu bant atlanır (sayfa başlığı, süs)
                        +      → bu bant bir önceki satıra eklenir (otomatik bulma bir satırı böldüyse)
                      "#" ile başlayan satırlar açıklamadır ve sayılmaz.
Metin dosyası olan sayfalar çalışmaya hazırdır.
"""

from dataclasses import dataclass
from functools import lru_cache
import json
from pathlib import Path

KITAPLAR_KLASORU = Path(__file__).resolve().parent / "data" / "kitaplar"


@dataclass(frozen=True)
class Satir:
    no: int          # 1'den başlar
    y0: float        # resim yüksekliğine oranla
    y1: float
    metin: str


@lru_cache(maxsize=None)
def kitap_bilgisi(kod: str) -> dict | None:
    yol = KITAPLAR_KLASORU / kod / "kitap.json"
    if not yol.is_file() or "/" in kod or "\\" in kod or kod.startswith("."):
        return None
    return json.loads(yol.read_text(encoding="utf-8"))


def kitaplar() -> list[dict]:
    return [dict(kitap_bilgisi(p.name), kod=p.name)
            for p in sorted(KITAPLAR_KLASORU.iterdir()) if kitap_bilgisi(p.name)]


@lru_cache(maxsize=None)
def _bantlar(kod: str) -> dict:
    return json.loads((KITAPLAR_KLASORU / kod / "satirlar.json").read_text(encoding="utf-8"))


def metin_satirlari(yol: Path) -> list[str]:
    return [s.rstrip() for s in yol.read_text(encoding="utf-8").splitlines()
            if s.strip() and not s.lstrip().startswith("#")]


def sayfa_satirlari(kod: str, pdf_sayfa: int) -> list[Satir] | None:
    """Sayfanın çalışılacak satırları; metni hazır değilse None."""
    yol = KITAPLAR_KLASORU / kod / "metin" / f"s{pdf_sayfa:03d}.txt"
    bilgi = _bantlar(kod).get(str(pdf_sayfa))
    if not yol.is_file() or bilgi is None:
        return None
    bantlar, metinler = bilgi["satirlar"], metin_satirlari(yol)
    if len(bantlar) != len(metinler):
        raise ValueError(f"{yol.name}: {len(bantlar)} bant var ama {len(metinler)} metin satırı var")
    satirlar: list[list] = []
    for (y0, y1), m in zip(bantlar, metinler):
        if m == "-":
            continue
        if m == "+":
            if satirlar:
                satirlar[-1][1] = y1
            continue
        satirlar.append([y0, y1, m])
    return [Satir(i, y0, y1, m) for i, (y0, y1, m) in enumerate(satirlar, 1)]


def sayfa_boyutu(kod: str, pdf_sayfa: int) -> tuple[int, int]:
    b = _bantlar(kod)[str(pdf_sayfa)]
    return b["genislik"], b["yukseklik"]


def tum_sayfalar(kod: str) -> list[int]:
    return sorted(int(n) for n in _bantlar(kod))


def hazir_sayfalar(kod: str) -> list[int]:
    klasor = KITAPLAR_KLASORU / kod / "metin"
    return sorted(int(p.stem[1:]) for p in klasor.glob("s*.txt")) if klasor.is_dir() else []


def gorunen_no(kod: str, pdf_sayfa: int) -> int:
    """Kullanıcıya gösterilen sıra numarası (1'den başlar)."""
    return pdf_sayfa - kitap_bilgisi(kod).get("ilk_pdf_sayfasi", 1) + 1
