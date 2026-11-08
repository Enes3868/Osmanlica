from checker import kontrol_et, normallestir

KATIP = [("kâtib", True), ("kâtip", False)]
KL = [("gel", True), ("gül", False), ("kül", False), ("kel", False)]


def test_birebir_dogru():
    s = kontrol_et("kâtib", KATIP)
    assert s.dogru and not s.yazim_farki


def test_sapkasiz_yazim_dogru_ama_isaretlenir():
    s = kontrol_et("katip", KATIP)
    assert s.dogru
    assert s.eslesen == "kâtip"
    assert s.yazim_farki


def test_buyuk_harf_turkce_kurali():
    assert normallestir("KATİP") == "katip"
    assert normallestir("IRMAK") == "ırmak"
    assert kontrol_et("İSTANBUL güzel bir şehirdir", [("İstanbul güzel bir şehirdir", True)]).dogru


def test_i_ve_ı_ayri_harfler():
    assert not kontrol_et("kil", [("kıl", True)]).dogru


def test_birden_cok_okunus_hepsi_dogru():
    for cevap in ["gel", "gül", "kül", "kel"]:
        assert kontrol_et(cevap, KL).dogru


def test_diger_okunuslar_listelenir():
    s = kontrol_et("gül", KL)
    assert s.asil == "gel"
    assert sorted(s.digerleri) == ["gel", "kel", "kül"]


def test_yanlis_cevap():
    s = kontrol_et("merhebe", [("merhaba", True)])
    assert not s.dogru
    assert s.asil == "merhaba"


def test_bos_cevap_yanlis():
    assert not kontrol_et("   ", [("su", True)]).dogru


def test_cumlede_noktalama_ve_bosluk_onemsiz():
    s = kontrol_et("  Ben  mektebe gidiyorum. ", [("ben mektebe gidiyorum", True)])
    assert s.dogru


def test_ayrik_yazilmis_sapka():
    # "a" + birleşik şapka (U+0302) da "â" gibi davranmalı
    assert kontrol_et("kâtib", KATIP).dogru
