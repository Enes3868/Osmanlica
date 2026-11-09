import sqlite3

import pytest

from karsilastir import karsilastir, kelime_normal
import kitap


# ---------- Kelime kelime karşılaştırma ----------

def test_birebir_dogru():
    k = karsilastir("Osmân Gâzî bu târîhden", "osman gazi bu tarihden")
    assert k.dogru_sayisi == k.toplam == 4
    assert all(w.durum == "dogru" for w in k.cevap_metin)


def test_tamlama_cizgisi_ve_noktalama_onemsiz():
    assert kelime_normal("Devlet-i") == kelime_normal("devleti")
    k = karsilastir("Târîh-i Devlet-i Osmâniye.", "tarihi devleti osmaniye")
    assert k.dogru_sayisi == 3


def test_atlanan_kelime_sonrakileri_kaydirmaz():
    k = karsilastir("vezir sahib tedbir devşirme usulünü", "vezir devşirme usulünü")
    assert k.dogru_sayisi == 3
    assert [w.durum for w in k.dogru_metin] == ["dogru", "eksik", "eksik", "dogru", "dogru"]
    eksikler = [w.beklenen for w in k.cevap_metin if w.durum == "eksik"]
    assert eksikler == ["sahib", "tedbir"]


def test_yanlis_ve_fazla_kelime():
    k = karsilastir("bir kat daha", "bir kere daha fazla")
    durumlar = [(w.metin, w.durum) for w in k.cevap_metin]
    assert ("kere", "yanlis") in durumlar and ("fazla", "fazla") in durumlar
    assert next(w for w in k.cevap_metin if w.metin == "kere").beklenen == "kat"
    assert k.dogru_sayisi == 2 and k.toplam == 3


def test_bos_cevap():
    k = karsilastir("olunur", "")
    assert k.dogru_sayisi == 0 and k.yuzde == 0
    assert k.cevap_metin[0].durum == "eksik"


# ---------- Kitap verisi ----------

def test_hazir_sayfalarin_metni_bantlarla_uyumlu():
    """Her metin dosyasında bant sayısı kadar satır olmalı (yoksa satırlar kayar)."""
    hazir = kitap.hazir_sayfalar("fezleke")
    assert hazir, "en az bir sayfa hazır olmalı"
    for n in hazir:
        satirlar = kitap.sayfa_satirlari("fezleke", n)   # uyumsuzlukta ValueError fırlatır
        assert satirlar and all(s.metin and s.metin not in "+-" for s in satirlar)
        assert all(0 <= s.y0 < s.y1 <= 1 for s in satirlar)


def test_birlestirme_ve_atlama(tmp_path, monkeypatch):
    klasor = tmp_path / "deneme"
    (klasor / "metin").mkdir(parents=True)
    (klasor / "kitap.json").write_text('{"ad": "D", "ilk_pdf_sayfasi": 1}', encoding="utf-8")
    (klasor / "satirlar.json").write_text(
        '{"1": {"genislik": 10, "yukseklik": 10, "satirlar": [[0, 0.1], [0.1, 0.2], [0.2, 0.3], [0.3, 0.4]]}}',
        encoding="utf-8")
    (klasor / "metin" / "s001.txt").write_text("# not\n-\nbir\n+\niki\n", encoding="utf-8")
    monkeypatch.setattr(kitap, "KITAPLAR_KLASORU", tmp_path)
    kitap._bantlar.cache_clear()
    try:
        s = kitap.sayfa_satirlari("deneme", 1)
        assert [(x.metin, x.y0, x.y1) for x in s] == [("bir", 0.1, 0.3), ("iki", 0.3, 0.4)]
    finally:
        kitap._bantlar.cache_clear()


def test_kitap_kodu_klasor_disina_cikamaz():
    assert kitap.kitap_bilgisi("..") is None
    assert kitap.kitap_bilgisi("../data") is None


# ---------- Sayfa akışı ----------

@pytest.fixture
def ilk_sayfa():
    return kitap.hazir_sayfalar("fezleke")[0]


def test_ana_sayfada_kitap_tercume_ilk_sirada(istemci):
    html = istemci.get("/").get_data(as_text=True)
    assert html.index("Kitap tercüme") < html.index("Osmanlıca okuma")


def test_sayfa_listesi_ve_resim(istemci, ilk_sayfa):
    assert "Fezleke" in istemci.get("/kitap").get_data(as_text=True)
    html = istemci.get("/kitap/fezleke").get_data(as_text=True)
    assert f"/kitap/fezleke/{ilk_sayfa}" in html
    r = istemci.get(f"/kitap/fezleke/resim/{ilk_sayfa}.jpg")
    assert r.status_code == 200 and r.mimetype == "image/jpeg"
    assert istemci.get("/kitap/yok").status_code == 404


def test_satir_satir_akis_ve_degerlendirme(istemci, ilk_sayfa, tmp_path):
    satirlar = kitap.sayfa_satirlari("fezleke", ilk_sayfa)
    html = istemci.get(f"/kitap/fezleke/{ilk_sayfa}").get_data(as_text=True)
    assert 'name="satir" value="1"' in html
    for s in satirlar:
        cevap = s.metin if s.no == 1 else "yanlış"
        r = istemci.post(f"/kitap/fezleke/{ilk_sayfa}/cevap", data={"satir": s.no, "cevap": cevap})
        assert "Doğrusu" in r.get_data(as_text=True)
    # Son satırdan sonra değerlendirme
    r = istemci.get(f"/kitap/fezleke/{ilk_sayfa}")
    assert r.headers["Location"].endswith(f"/kitap/fezleke/{ilk_sayfa}/sonuc")
    sonuc = istemci.get(r.headers["Location"]).get_data(as_text=True)
    assert "tamamlandı" in sonuc and "kk-yanlis" in sonuc
    # Sayfa listesinde bitti olarak görünür
    assert "✓" in istemci.get("/kitap/fezleke").get_data(as_text=True)
    with sqlite3.connect(tmp_path / "ilerleme.db") as b:
        assert b.execute("SELECT COUNT(*) FROM kitap_satir_cevaplari").fetchone()[0] == len(satirlar)
    b.close()


def test_sira_disi_satir_kaydedilmez(istemci, ilk_sayfa, tmp_path):
    istemci.get(f"/kitap/fezleke/{ilk_sayfa}")
    istemci.post(f"/kitap/fezleke/{ilk_sayfa}/cevap", data={"satir": 3, "cevap": "x"})
    with sqlite3.connect(tmp_path / "ilerleme.db") as b:
        assert b.execute("SELECT COUNT(*) FROM kitap_satir_cevaplari").fetchone()[0] == 0
    b.close()


def test_sayfa_tekrar_yapilabilir(istemci, ilk_sayfa):
    istemci.get(f"/kitap/fezleke/{ilk_sayfa}")          # deneme başlar
    for s in kitap.sayfa_satirlari("fezleke", ilk_sayfa):
        istemci.post(f"/kitap/fezleke/{ilk_sayfa}/cevap", data={"satir": s.no, "cevap": s.metin})
    istemci.get(f"/kitap/fezleke/{ilk_sayfa}")          # bitir
    istemci.post(f"/kitap/fezleke/{ilk_sayfa}/yeniden")
    html = istemci.get(f"/kitap/fezleke/{ilk_sayfa}").get_data(as_text=True)
    assert 'name="satir" value="1"' in html             # yeni deneme baştan başlar


def test_kitapta_sapkasiz_yazim_dogru():
    k = karsilastir("Sultân-ı müşârün-ileyh vâlî", "sultanı müşarünileyh vali")
    assert k.dogru_sayisi == k.toplam == 3
