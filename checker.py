"""Kullanıcının yazdığı okunuşu kabul edilen okunuşlarla karşılaştırır.

Kurallar (onaylanan tasarım):
- Büyük-küçük harf farkı önemsizdir; Türkçe kuralı kullanılır (I→ı, İ→i).
- ı ile i ayrı harflerdir ("kıl" ≠ "kil").
- Şapka ve diğer okuma işaretleri hata değildir (â→a, î→i, û→u, ā→a, ṭ→t, ḱ→k ...);
  ekranda doğru yazım gösterilir. Yalnızca Türk alfabesinin kendi harfleri (ç ğ ı ö ş ü) korunur.
- Noktalama, kesme işareti ve fazla boşluklar önemsizdir (cümleler için).
- Aynı yazılışın birden çok geçerli okunuşu olabilir; hepsi doğru sayılır:
    * yazım çeşitleri: aynı kelimenin farklı yazımları (kitâb / kitap)
    * farklı kelimeler: aynı harflerle yazılan başka kelimeler (gel / gül)
"""

from dataclasses import dataclass, field
import unicodedata

TURK_HARFLERI = set("abcçdefgğhıijklmnoöprsştuüvyzqwx")
KESME_ISARETLERI = {"'", "’", "‘", "`", "´"}


def isaretsiz(harf: str) -> str:
    """Türk alfabesinde olmayan işaretli harfi yalın hâline indirir (â→a, ṭ→t, ḱ→k).
    Ayın/hemze gibi işaret harfleri (ʿ ʾ ʼ) ve kesme işaretleri tamamen düşer."""
    if harf in TURK_HARFLERI or not harf.isalpha():
        return "" if harf in KESME_ISARETLERI else harf
    if unicodedata.category(harf) == "Lm":   # ʿ ʾ ʼ ʻ gibi değiştirici harfler
        return ""
    yalin = "".join(c for c in unicodedata.normalize("NFD", harf) if not unicodedata.combining(c))
    return yalin


def turkce_kucuk_harf(metin: str) -> str:
    # Python'un lower() fonksiyonu "I"yı "i" yapar; Türkçede "ı" olmalı.
    # "İ" de lower() ile "i" + birleşik nokta olur; önce kendimiz çeviririz.
    return metin.replace("I", "ı").replace("İ", "i").lower()


def normallestir(metin: str) -> str:
    """Karşılaştırma için metni sadeleştirir."""
    # NFC: "a" + birleşik şapka gibi ayrık yazılmış harfleri tek harfe birleştirir.
    metin = unicodedata.normalize("NFC", metin)
    metin = "".join(isaretsiz(h) for h in turkce_kucuk_harf(metin))
    # Harf ve rakam dışındaki her şeyi (noktalama, tire) boşluğa çevir.
    metin = "".join(h if h.isalnum() else " " for h in metin)
    return " ".join(metin.split())


def yazim_bicimi(metin: str) -> str:
    """"Yazımı şöyledir" uyarısı için karşılaştırma: büyük-küçük harf, noktalama ve boşluk farkı
    yazım farkı sayılmaz ("Şerif" ile "şerif" aynı); şapka ve kesme işareti farkı sayılır
    ("şerif" yazana "şerîf" gösterilir)."""
    metin = turkce_kucuk_harf(unicodedata.normalize("NFC", metin))
    metin = "".join(h if h.isalnum() or h in KESME_ISARETLERI else " " for h in metin)
    return " ".join(metin.split())


@dataclass
class Sonuc:
    dogru: bool
    asil: str                       # kartın kelimesinin ekranda gösterilecek doğru yazımı
    eslesen: str | None = None      # kullanıcının cevabının eşleştiği okunuş
    yazim_farki: bool = False       # doğru, ama yazımı gösterilen biçimden farklı
    farkli_kelime: bool = False     # doğru, ama aynı yazılışlı başka bir kelime olarak okudu
    cesitler: list[str] = field(default_factory=list)          # kartın kelimesinin diğer yazımları
    farkli_kelimeler: list[str] = field(default_factory=list)  # aynı yazılışın diğer kelimeleri


def kontrol_et(cevap: str, okunuslar: list[tuple[str, bool]],
               farkli_kelimeler: list[str] | None = None) -> Sonuc:
    """okunuslar: kartın kelimesinin (okunuş, asıl_mı) çiftleri; tam olarak biri asıl olmalı.
    farkli_kelimeler: aynı Osmanlıca yazılışa sahip başka kelimelerin asıl okunuşları."""
    farkli_kelimeler = farkli_kelimeler or []
    asil = next((o for o, a in okunuslar if a), okunuslar[0][0])
    kendi = [o for o, _ in okunuslar]
    aranan = normallestir(cevap)

    def bul(liste):
        return next((o for o in liste if normallestir(o) == aranan), None) if aranan else None

    eslesen = bul(kendi)
    farkli = False
    if eslesen is None:
        eslesen = bul(farkli_kelimeler)
        farkli = eslesen is not None

    if eslesen is None:
        return Sonuc(dogru=False, asil=asil, cesitler=[o for o in kendi if o != asil],
                     farkli_kelimeler=farkli_kelimeler)

    return Sonuc(
        dogru=True,
        asil=asil,
        eslesen=eslesen,
        yazim_farki=yazim_bicimi(cevap) != yazim_bicimi(eslesen),
        farkli_kelime=farkli,
        # Başka kelime olarak okuduysa kartın asıl okunuşu zaten ayrıca gösterilir.
        cesitler=[o for o in kendi if o != eslesen and not (farkli and o == asil)],
        farkli_kelimeler=[o for o in farkli_kelimeler if o != eslesen],
    )
