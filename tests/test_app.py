from pathlib import Path
import sqlite3

import pytest

import app as uygulama

TESTLER = Path(__file__).resolve().parent
VERI = TESTLER.parent / "data"


@pytest.fixture
def istemci(tmp_path):
    # Testler kendi küçük örnek verisini ve geçici veritabanını kullanır; data/sozluk.db'ye dokunmaz.
    uygulama.app.config.update(
        TESTING=True,
        SOZLUK_DB=tmp_path / "test.db",
        VERI_DOSYALARI=[VERI / "sema.sql", TESTLER / "veri" / "ornek_veri.sql"],
    )
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


def test_ayni_yazilisli_baska_kelime_dogru_ve_anlami_gosterilir(istemci):
    # کل kaydı 4 = "gel"; aynı yazılışlı "gül" ayrı bir kayıt.
    html = istemci.post("/okuma/kelime", data={"kayit_id": 4, "cevap": "gül"}).get_data(as_text=True)
    assert "Doğru!" in html
    assert "Gül (çiçek)" in html            # okuduğu kelimenin anlamı
    assert "Kartın kelimesi: <strong>gel</strong>" in html


def test_yazim_cesitleri_ayri_gosterilir(istemci):
    html = istemci.post("/okuma/kelime", data={"kayit_id": 2, "cevap": "kitap"}).get_data(as_text=True)
    assert "Diğer yazımları" in html and "başka kelimeler" not in html


def test_tur_uyusmazligi_reddedilir(istemci):
    # Cümle kaydı kelime sayfasına gönderilemez.
    assert istemci.post("/okuma/kelime", data={"kayit_id": 101, "cevap": "x"}).status_code == 400


def test_lugat_kartlari(istemci):
    html = istemci.get("/lugat").get_data(as_text=True)
    assert html.count("<details") == 6


def test_kaynaklar_sayfasi(istemci):
    html = istemci.get("/kaynaklar").get_data(as_text=True)
    assert "Örnek veri" in html and "CC BY-SA 4.0" in html


def test_yazi_secimi_cerez_ve_guvenli_yonlendirme(istemci):
    r = istemci.get("/yazi/rika?geri=/lugat")
    assert r.headers["Location"].endswith("/lugat")
    assert "yazi=rika" in r.headers["Set-Cookie"]
    # Başka bir siteye yönlendirme yapılmaz.
    assert istemci.get("/yazi/rika?geri=//kotu.site").headers["Location"].endswith("/")


def test_veri_degisince_veritabani_yenilenir(tmp_path):
    db = tmp_path / "s.db"
    sema = VERI / "sema.sql"
    v1 = tmp_path / "v1.sql"
    v1.write_text("INSERT INTO kaynaklar (id, ad, lisans) VALUES (1, 'A', 'x');", encoding="utf-8")
    uygulama.sozluk_hazirla(db, [sema, v1])
    v1.write_text("INSERT INTO kaynaklar (id, ad, lisans) VALUES (1, 'B', 'x');", encoding="utf-8")
    uygulama.sozluk_hazirla(db, [sema, v1])
    with sqlite3.connect(db) as b:
        assert b.execute("SELECT ad FROM kaynaklar").fetchone()[0] == "B"
    b.close()


def test_gercek_veri_yuklenir_ve_tutarli(tmp_path):
    """data/vikisozluk.sql şemaya uyuyor; her kaydın tam bir asıl okunuşu ve lisansı var."""
    db = tmp_path / "gercek.db"
    uygulama.sozluk_hazirla(db, [VERI / "sema.sql", VERI / "vikisozluk.sql"])
    with sqlite3.connect(db) as b:
        assert b.execute("SELECT COUNT(*) FROM kayitlar WHERE tur='kelime'").fetchone()[0] > 400
        assert b.execute("SELECT COUNT(*) FROM kayitlar WHERE tur='cumle'").fetchone()[0] > 30
        asilsiz = b.execute(
            "SELECT COUNT(*) FROM kayitlar k WHERE (SELECT COUNT(*) FROM okunuslar o "
            "WHERE o.kayit_id = k.id AND o.asil = 1) != 1").fetchone()[0]
        assert asilsiz == 0
        assert b.execute("SELECT lisans FROM kaynaklar").fetchall() == [("CC BY-SA 4.0",)]
    b.close()
