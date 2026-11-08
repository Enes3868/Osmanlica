from harfler import HARFLER, LAMELIF, ZWJ


def test_osmanli_alfabesi_tam():
    harfler = {h.harf for h in HARFLER}
    assert len(HARFLER) == 33 and len(harfler) == 33
    # Türkçeye özgü harfler dahil
    assert {"پ", "چ", "ژ", "گ", "ڭ"} <= harfler


def test_bicimler_zwj_ile_uretilir():
    be = next(h for h in HARFLER if h.harf == "ب")
    assert (be.basta, be.ortada, be.sonda) == ("ب" + ZWJ, ZWJ + "ب" + ZWJ, ZWJ + "ب")


def test_sola_baglanmayan_harfler():
    baglanmayan = {h.harf for h in HARFLER if not h.sola_baglanir}
    assert baglanmayan == {"ا", "د", "ذ", "ر", "ز", "ژ", "و"}
    dal = next(h for h in HARFLER if h.harf == "د")
    assert dal.basta == "د" and dal.ortada == ZWJ + "د"
    assert LAMELIF.ortada == ZWJ + "لا"


def test_harfler_sayfasi(istemci):
    html = istemci.get("/harfler").get_data(as_text=True)
    assert html.count('<td class="matbu"') == 34   # 33 harf + lamelif
    assert "Rik'a harfler" in html and "sağır kef" in html
    assert "/harfler" in istemci.get("/").get_data(as_text=True)  # ana sayfadan bağlantı
