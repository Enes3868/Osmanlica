"""Site modu: Google girişi ve kullanıcılar arası ilerleme ayrımı.

Google'a gerçekten bağlanılmaz; Authlib'in token alma adımı sahte cevapla değiştirilir.
"""

import sqlite3

import pytest

import app as uygulama
import giris


@pytest.fixture
def site(istemci, monkeypatch):
    monkeypatch.setitem(uygulama.app.config, "CALISMA_MODU", "site")
    monkeypatch.setitem(uygulama.app.config, "IZINLI_EPOSTALAR", "")
    return istemci


def google_donusu(monkeypatch, istemci, sub="111", eposta="ali@example.com", dogrulanmis=True, sonra="/lugat"):
    """Girişi baştan sona taklit eder: /giris/google → (Google) → /giris/donus."""
    monkeypatch.setattr(giris.oauth.google, "authorize_redirect", lambda adres: uygulama.app.redirect(adres))
    monkeypatch.setattr(giris.oauth.google, "authorize_access_token", lambda: {"userinfo": {
        "sub": sub, "email": eposta, "email_verified": dogrulanmis, "given_name": "Ali"}})
    istemci.get(f"/giris/google?sonra={sonra}")
    return istemci.get("/giris/donus")


def oturum_ac(istemci, sub, ad="Deneme"):
    with istemci.session_transaction() as s:
        s.clear()
        s["kullanici"] = {"id": sub, "ad": ad, "eposta": f"{sub}@example.com"}


def test_yerel_modda_giris_yok(istemci):
    assert istemci.get("/lugat").status_code == 200
    assert "Giriş yap" not in istemci.get("/").get_data(as_text=True)


def test_site_modunda_ilerleme_sayfalari_giris_ister(site):
    for adres in ("/lugat", "/kitap/fezleke"):
        r = site.get(adres)
        assert r.status_code == 302 and "/giris?sonra=" in r.headers["Location"]
    # İlerleme kaydetmeyen sayfalar açık
    for adres in ("/", "/okuma/kelime", "/harfler", "/kitap"):
        assert site.get(adres).status_code == 200


def test_google_ile_giris_ve_cikis(site, monkeypatch):
    r = google_donusu(monkeypatch, site)
    assert r.headers["Location"].endswith("/lugat")
    html = site.get("/").get_data(as_text=True)
    assert "Ali" in html and "Çıkış" in html
    assert site.get("/lugat").status_code == 200
    site.post("/cikis")
    assert site.get("/lugat").status_code == 302


def test_dogrulanmamis_eposta_reddedilir(site, monkeypatch):
    r = google_donusu(monkeypatch, site, dogrulanmis=False)
    assert "hata=dogrulanmamis" in r.headers["Location"]
    assert site.get("/lugat").status_code == 302


def test_izinli_eposta_listesi(site, monkeypatch):
    monkeypatch.setitem(uygulama.app.config, "IZINLI_EPOSTALAR", "anne@example.com, Ali@Example.com")
    assert google_donusu(monkeypatch, site, eposta="ali@example.com").headers["Location"].endswith("/lugat")
    site.post("/cikis")
    r = google_donusu(monkeypatch, site, sub="999", eposta="yabanci@example.com")
    assert "hata=izinsiz" in r.headers["Location"]


def test_giris_sonrasi_disari_yonlendirilmez(site, monkeypatch):
    r = google_donusu(monkeypatch, site, sonra="//kotu.site")
    assert r.headers["Location"] == "/"


def test_kullanicilarin_ilerlemesi_ayri(site, tmp_path):
    # Ali bir lügat oturumunu bitirir
    oturum_ac(site, "ali")
    site.get("/lugat")
    with site.session_transaction() as s:
        kartlar = list(s["lugat"]["kartlar"])
    for a in kartlar:
        site.post("/lugat/cevap", data={"anahtar": a, "bildi": "1"})
    # Ayşe kendi kitap sayfasını bitirmiş gibi görünmez, lügatte de 0 kelime çalışmıştır
    oturum_ac(site, "ayse")
    site.get("/lugat")
    with site.session_transaction() as s:
        assert s["lugat"]["sira"] == 0
    with sqlite3.connect(tmp_path / "ilerleme.db") as b:
        sayim = dict(b.execute("SELECT kullanici, COUNT(*) FROM lugat_cevaplari GROUP BY kullanici").fetchall())
    b.close()
    assert sayim == {"ali": 5}


def test_kitap_denemesi_kullaniciya_ait(site, tmp_path):
    import kitap
    sayfa = kitap.hazir_sayfalar("fezleke")[0]
    oturum_ac(site, "ali")
    site.get(f"/kitap/fezleke/{sayfa}")
    site.post(f"/kitap/fezleke/{sayfa}/cevap", data={"satir": 1, "cevap": "x"})
    oturum_ac(site, "ayse")
    html = site.get(f"/kitap/fezleke/{sayfa}").get_data(as_text=True)
    assert 'name="satir" value="1"' in html   # Ayşe kendi denemesine birinci satırdan başlar
    with sqlite3.connect(tmp_path / "ilerleme.db") as b:
        assert b.execute("SELECT COUNT(DISTINCT kullanici) FROM kitap_denemeleri").fetchone()[0] == 2
    b.close()


def test_gizlilik_sayfasi_herkese_acik(site, monkeypatch):
    monkeypatch.setitem(uygulama.app.config, "ILETISIM_EPOSTA", "iletisim@example.com")
    r = site.get("/gizlilik")
    html = r.get_data(as_text=True)
    assert r.status_code == 200 and "Gizlilik politikası" in html and "iletisim@example.com" in html
    assert "/gizlilik" in site.get("/").get_data(as_text=True)   # alt bilgide bağlantı
