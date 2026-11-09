"""Bir satırın doğru Latin harfli metnini kullanıcının yazdığıyla kelime kelime karşılaştırır.

Kelimeleri sırayla yan yana koymak yetmez: kullanıcı bir kelimeyi atlarsa sonraki bütün
kelimeler kayar. Bu yüzden iki kelime dizisi "hizalanır" (difflib.SequenceMatcher, `git diff`
ile aynı fikir): ortak kelimeler eşleştirilir, aradaki farklar yanlış / eksik / fazla diye ayrılır.
"""

from dataclasses import dataclass, field
import difflib

from checker import normallestir


def kelime_normal(kelime: str) -> str:
    """Karşılaştırma biçimi: Türkçe küçük harf, şapkasız, noktalamasız; tamlama çizgisi yok sayılır
    ("devlet-i" = "devleti")."""
    return normallestir(kelime).replace(" ", "")


def kelimeler(metin: str) -> list[str]:
    """Metni kelimelere böler; yalnızca noktalamadan oluşan parçaları atar."""
    return [k for k in metin.split() if kelime_normal(k)]


@dataclass
class Kelime:
    metin: str
    durum: str            # dogru | yanlis | eksik | fazla
    beklenen: str = ""    # yanlış ya da eksik kelimenin doğrusu


@dataclass
class Karsilastirma:
    dogru_metin: list[Kelime] = field(default_factory=list)   # doğru metnin kelimeleri
    cevap_metin: list[Kelime] = field(default_factory=list)   # kullanıcının kelimeleri (+ eksik yer tutucuları)
    dogru_sayisi: int = 0
    toplam: int = 0

    @property
    def yuzde(self) -> int:
        return round(100 * self.dogru_sayisi / self.toplam) if self.toplam else 100


def karsilastir(dogru: str, cevap: str) -> Karsilastirma:
    d, c = kelimeler(dogru), kelimeler(cevap)
    dn, cn = [kelime_normal(k) for k in d], [kelime_normal(k) for k in c]
    sonuc = Karsilastirma(toplam=len(d))
    for islem, d0, d1, c0, c1 in difflib.SequenceMatcher(None, dn, cn, autojunk=False).get_opcodes():
        if islem == "equal":
            sonuc.dogru_metin += [Kelime(k, "dogru") for k in d[d0:d1]]
            sonuc.cevap_metin += [Kelime(k, "dogru") for k in c[c0:c1]]
            sonuc.dogru_sayisi += d1 - d0
        elif islem == "replace":
            sonuc.dogru_metin += [Kelime(k, "yanlis") for k in d[d0:d1]]
            beklenen = d[d0:d1]
            for i, k in enumerate(c[c0:c1]):
                sonuc.cevap_metin.append(Kelime(k, "yanlis", beklenen[i] if i < len(beklenen) else ""))
            # Kullanıcı daha az kelime yazdıysa kalanlar eksiktir.
            sonuc.cevap_metin += [Kelime("…", "eksik", k) for k in beklenen[c1 - c0:]]
        elif islem == "delete":
            sonuc.dogru_metin += [Kelime(k, "eksik") for k in d[d0:d1]]
            sonuc.cevap_metin += [Kelime("…", "eksik", k) for k in d[d0:d1]]
        elif islem == "insert":
            sonuc.cevap_metin += [Kelime(k, "fazla") for k in c[c0:c1]]
    return sonuc
