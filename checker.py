"""Kullanıcının yazdığı okunuşu kabul edilen okunuşlarla karşılaştırır.

Kurallar (onaylanan tasarım):
- Büyük-küçük harf farkı önemsizdir; Türkçe kuralı kullanılır (I→ı, İ→i).
- ı ile i ayrı harflerdir ("kıl" ≠ "kil").
- Şapka farkı hata değildir (â→a, î→i, û→u); ekranda doğru yazım gösterilir.
- Noktalama ve fazla boşluklar önemsizdir (cümleler için).
- Bir kaydın birden çok geçerli okunuşu olabilir; hepsi doğru sayılır.
"""

from dataclasses import dataclass, field
import unicodedata

SAPKALAR = str.maketrans({"â": "a", "î": "i", "û": "u"})


def turkce_kucuk_harf(metin: str) -> str:
    # Python'un lower() fonksiyonu "I"yı "i" yapar; Türkçede "ı" olmalı.
    # "İ" de lower() ile "i" + birleşik nokta olur; önce kendimiz çeviririz.
    return metin.replace("I", "ı").replace("İ", "i").lower()


def normallestir(metin: str) -> str:
    """Karşılaştırma için metni sadeleştirir."""
    # NFC: "a" + birleşik şapka gibi ayrık yazılmış harfleri tek harfe birleştirir.
    metin = unicodedata.normalize("NFC", metin)
    metin = turkce_kucuk_harf(metin).translate(SAPKALAR)
    # Harf ve rakam dışındaki her şeyi (noktalama, kesme işareti) boşluğa çevir.
    metin = "".join(h if h.isalnum() else " " for h in metin)
    return " ".join(metin.split())


@dataclass
class Sonuc:
    dogru: bool
    asil: str                      # ekranda gösterilecek doğru yazım
    eslesen: str | None = None     # kullanıcının cevabının eşleştiği okunuş
    digerleri: list[str] = field(default_factory=list)  # diğer geçerli okunuşlar
    yazim_farki: bool = False      # doğru, ama yazımı gösterilen biçimden farklı


def kontrol_et(cevap: str, okunuslar: list[tuple[str, bool]]) -> Sonuc:
    """okunuslar: (okunuş, asıl_mı) çiftleri. Tam olarak birinin asıl olması beklenir."""
    asil = next((o for o, a in okunuslar if a), okunuslar[0][0])
    tum = [o for o, _ in okunuslar]
    aranan = normallestir(cevap)

    eslesen = None
    if aranan:
        eslesen = next((o for o in tum if normallestir(o) == aranan), None)

    if eslesen is None:
        return Sonuc(dogru=False, asil=asil, digerleri=[o for o in tum if o != asil])

    yazim_farki = unicodedata.normalize("NFC", cevap.strip()) != eslesen
    return Sonuc(
        dogru=True,
        asil=asil,
        eslesen=eslesen,
        digerleri=[o for o in tum if o != eslesen],
        yazim_farki=yazim_farki,
    )
