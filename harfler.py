"""Osmanlı alfabesindeki harfler ("Rik'a harfler" sayfası için).

Bu içerik sabit ve yalnızca gösterim amaçlı olduğu için veritabanında değil burada durur.

Harflerin başta / ortada / sonda biçimleri ayrıca saklanmaz: tarayıcı, harfin yanına görünmez
"sıfır genişlikli birleştirici" (ZWJ, U+200D) konunca bağlı biçimi kendisi çizer.
"""

from dataclasses import dataclass

ZWJ = "‍"


@dataclass(frozen=True)
class Harf:
    harf: str            # tek başına yazılış (Unicode)
    ad: str              # harfin adı
    latin: str           # Latin harfli karşılık(lar)ı
    sola_baglanir: bool = True  # sonraki harfe bağlanır mı? (ا د ذ ر ز ژ و bağlanmaz)
    not_: str = ""

    @property
    def tek(self) -> str:
        return self.harf

    @property
    def basta(self) -> str:
        # Sola bağlanmayan harfin "baş" biçimi, tek başına biçimiyle aynıdır.
        return self.harf + ZWJ if self.sola_baglanir else self.harf

    @property
    def ortada(self) -> str:
        return ZWJ + self.harf + ZWJ if self.sola_baglanir else ZWJ + self.harf

    @property
    def sonda(self) -> str:
        return ZWJ + self.harf


HARFLER: list[Harf] = [
    Harf("ا", "elif", "a, e", False, "Kelime başında ünlüyü taşır."),
    Harf("ب", "be", "b"),
    Harf("پ", "pe", "p", not_="Türkçe ve Farsça kelimelerde."),
    Harf("ت", "te", "t"),
    Harf("ث", "se", "s", not_="Arapça kelimelerde."),
    Harf("ج", "cim", "c"),
    Harf("چ", "çim", "ç", not_="Türkçe ve Farsça kelimelerde."),
    Harf("ح", "ha (hâ-yı hutti)", "h"),
    Harf("خ", "hı", "h (hı)"),
    Harf("د", "dal", "d", False),
    Harf("ذ", "zel", "z", False),
    Harf("ر", "re", "r", False),
    Harf("ز", "ze", "z", False),
    Harf("ژ", "je", "j", False, "Farsça ve Fransızca kelimelerde."),
    Harf("س", "sin", "s"),
    Harf("ش", "şın", "ş"),
    Harf("ص", "sad", "s"),
    Harf("ض", "dad", "d, z"),
    Harf("ط", "tı", "t"),
    Harf("ظ", "zı", "z"),
    Harf("ع", "ayın", "ʿ (boğaz sesi)"),
    Harf("غ", "gayın", "ğ, g"),
    Harf("ف", "fe", "f"),
    Harf("ق", "kaf", "k (kalın)"),
    Harf("ك", "kef", "k, g, ğ, n", not_="Türkçe kelimelerde g, ğ ve n sesini de gösterir."),
    Harf("گ", "gef", "g"),
    Harf("ڭ", "nef (sağır kef)", "n (genizden)", not_="Ör. deñiz (deniz)."),
    Harf("ل", "lam", "l"),
    Harf("م", "mim", "m"),
    Harf("ن", "nun", "n"),
    Harf("و", "vav", "v, o, ö, u, ü", False),
    Harf("ه", "he (hâ-yı resmiyye)", "h, e, a", not_="Kelime sonunda çoğunlukla e/a sesini gösterir."),
    Harf("ی", "ye", "y, ı, i"),
]

# Lam ile elif yan yana gelince özel bir bitişik biçim (lamelif) alır.
LAMELIF = Harf("لا", "lamelif", "la", False, "Lam + elif'in bitişik yazılışı.")
