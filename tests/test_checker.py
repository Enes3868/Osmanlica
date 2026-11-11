from checker import kontrol_et, normallestir

KATIP = [("kâtib", True), ("kâtip", False)]
GEL = [("gel", True)]
GEL_DIGERLERI = ["gül", "kül", "kel"]


def test_birebir_dogru():
    s = kontrol_et("kâtib", KATIP)
    assert s.dogru and not s.yazim_farki


def test_sapkasiz_yazim_dogru_ama_isaretlenir():
    s = kontrol_et("katip", KATIP)
    assert s.dogru
    assert s.eslesen == "kâtip"
    assert s.yazim_farki
    assert s.cesitler == ["kâtib"]


def test_buyuk_harf_turkce_kurali():
    assert normallestir("KATİP") == "katip"
    assert normallestir("IRMAK") == "ırmak"
    assert kontrol_et("İSTANBUL güzel bir şehirdir", [("İstanbul güzel bir şehirdir", True)]).dogru


def test_i_ve_ı_ayri_harfler():
    assert not kontrol_et("kil", [("kıl", True)]).dogru


def test_farkli_kelime_olarak_okumak_dogru_sayilir():
    s = kontrol_et("gül", GEL, GEL_DIGERLERI)
    assert s.dogru and s.farkli_kelime
    assert s.asil == "gel"
    assert sorted(s.farkli_kelimeler) == ["kel", "kül"]
    assert s.cesitler == []  # "gel" kartın kelimesi olarak zaten gösteriliyor


def test_kartin_kelimesi_farkli_kelime_sayilmaz():
    s = kontrol_et("gel", GEL, GEL_DIGERLERI)
    assert s.dogru and not s.farkli_kelime
    assert s.farkli_kelimeler == GEL_DIGERLERI


def test_yanlis_cevap():
    s = kontrol_et("merhebe", [("merhaba", True)])
    assert not s.dogru
    assert s.asil == "merhaba"


def test_bos_cevap_yanlis():
    assert not kontrol_et("   ", [("su", True)]).dogru


def test_cumlede_noktalama_ve_bosluk_onemsiz():
    assert kontrol_et("  Ben  mektebe gidiyorum. ", [("ben mektebe gidiyorum", True)]).dogru


def test_kesme_isareti_onemsiz():
    # Vikisözlük okunuşlarında kesme işareti olabilir: ba's, rahmetü'llâhi
    assert kontrol_et("bas", [("ba's", True)]).dogru
    assert kontrol_et("rahmetullahi aleyh", [("rahmetü'llâhi aleyh", True)]).dogru is False
    assert kontrol_et("rahmetüllahi aleyh", [("rahmetü'llâhi aleyh", True)]).dogru


def test_ayrik_yazilmis_sapka():
    # "a" + birleşik şapka (U+0302) da "â" gibi davranmalı
    assert kontrol_et("kâtib", KATIP).dogru


def test_diger_okuma_isaretleri_de_onemsiz():
    # Vikisözlük okunuşlarında şapka dışında işaretler de var: ā, ṭ, ḱ, ʾ
    assert kontrol_et("mahkum", [("mahḱum", True)]).dogru
    assert kontrol_et("valide-i sultan", [("vâlide-i sulṭân", True)]).dogru
    assert kontrol_et("lutfi", [("luṭfī", True)]).dogru
    assert normallestir("ʾazîz") == "aziz"


def test_turk_harfleri_korunur():
    # İşaretleri atarken Türk alfabesinin kendi harfleri bozulmamalı
    assert normallestir("Çöğüş ŞIK") == "çöğüş şık"
    assert not kontrol_et("cok", [("çok", True)]).dogru
    assert not kontrol_et("gul", [("gül", True)]).dogru


def test_buyuk_harf_yazim_farki_sayilmaz():
    # "Şerif" ile "şerif" aynı yazımdır; "Yazımı: şerif" uyarısı gösterilmemeli
    s = kontrol_et("Şerif", [("şerif", True)])
    assert s.dogru and not s.yazim_farki
    assert not kontrol_et("İSTANBUL", [("İstanbul", True)]).yazim_farki
    assert not kontrol_et(" şerif. ", [("şerif", True)]).yazim_farki
    # Şapka farkı ise bilgi olarak gösterilmeye devam eder
    assert kontrol_et("Katip", [("kâtip", True)]).yazim_farki
