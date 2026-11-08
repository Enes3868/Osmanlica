import pytest

import app as uygulama


@pytest.fixture
def istemci(tmp_path):
    # Her test kendi geçici veritabanını kullanır; gerçek data/sozluk.db'ye dokunmaz.
    uygulama.app.config.update(TESTING=True, SOZLUK_DB=tmp_path / "test.db")
    with uygulama.app.test_client() as c:
        yield c


def test_ana_sayfa_iki_mod(istemci):
    html = istemci.get("/").get_data(as_text=True)
    assert "Osmanlıca okuma" in html and "Lügat" in html


def test_okuma_karti_gelir(istemci):
    for tur in ("kelime", "cumle"):
        r = istemci.get(f"/okuma/{tur}")
        assert r.status_code == 200
        assert 'name="kayit_id"' in r.get_data(as_text=True)


def test_dogru_ve_yanlis_cevap(istemci):
    dogru = istemci.post("/okuma/kelime", data={"kayit_id": 1, "cevap": "Merhaba"})
    assert "Doğru!" in dogru.get_data(as_text=True)
    yanlis = istemci.post("/okuma/kelime", data={"kayit_id": 1, "cevap": "merhebe"})
    html = yanlis.get_data(as_text=True)
    assert "Yanlış." in html and "merhaba" in html


def test_birden_cok_okunus_sayfada(istemci):
    html = istemci.post("/okuma/kelime", data={"kayit_id": 4, "cevap": "gül"}).get_data(as_text=True)
    assert "Doğru!" in html and "kabul edilen diğer okunuşlar" in html


def test_tur_uyusmazligi_reddedilir(istemci):
    # Cümle kaydı kelime sayfasına gönderilemez.
    assert istemci.post("/okuma/kelime", data={"kayit_id": 101, "cevap": "x"}).status_code == 400


def test_lugat_kartlari(istemci):
    html = istemci.get("/lugat").get_data(as_text=True)
    assert html.count("<details") == 6


def test_yazi_secimi_cerez_ve_guvenli_yonlendirme(istemci):
    r = istemci.get("/yazi/rika?geri=/lugat")
    assert r.headers["Location"].endswith("/lugat")
    assert "yazi=rika" in r.headers["Set-Cookie"]
    # Başka bir siteye yönlendirme yapılmaz.
    assert istemci.get("/yazi/rika?geri=//kotu.site").headers["Location"].endswith("/")
