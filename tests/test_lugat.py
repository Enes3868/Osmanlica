import random
import sqlite3

import ilerleme


def durum(bildi, zaman="2026-01-01"):
    return {"bildi": bildi, "zaman": zaman}


TUM = [f"k{i}" for i in range(20)]


def test_yeni_mod_yalnizca_gorulmemis_kelimeler():
    durumlar = {"k0": durum(1), "k1": durum(0)}
    secim = ilerleme.oturum_sec(TUM, durumlar, "yeni", rastgele=random.Random(1))
    assert len(secim) == 5 and not set(secim) & {"k0", "k1"}


def test_devam_bilinmeyenler_tekrar_ve_bir_eski_kelime():
    durumlar = {"k0": durum(0, "2026-01-03"), "k1": durum(0, "2026-01-02"),
                "k2": durum(1, "2026-01-01"), "k3": durum(1, "2026-01-05")}
    secim = ilerleme.oturum_sec(TUM, durumlar, "devam", onceki=["k0", "k1"], rastgele=random.Random(1))
    assert {"k0", "k1"} <= set(secim)          # bilinmeyenler geri geldi
    assert "k2" in secim and "k3" not in secim  # en uzun süredir görülmeyen bilinen kelime
    assert len(secim) == 5 and len(set(secim)) == 5


def test_devam_en_fazla_uc_bilinmeyen():
    durumlar = {f"k{i}": durum(0) for i in range(6)}
    secim = ilerleme.oturum_sec(TUM, durumlar, "devam", rastgele=random.Random(1))
    assert sum(1 for a in secim if a in durumlar) == 3


def test_yeni_kelime_bitince_eskilerden_tamamlanir():
    durumlar = {a: durum(1) for a in TUM[:18]}
    secim = ilerleme.oturum_sec(TUM, durumlar, "yeni", rastgele=random.Random(1))
    assert len(secim) == 5 and {"k18", "k19"} <= set(secim)


def test_cevaplar_silinmez_son_cevap_durumdur(tmp_path):
    b = ilerleme.baglan(tmp_path / "i.db")
    ilerleme.cevap_kaydet(b, "a|x", False)
    ilerleme.cevap_kaydet(b, "a|x", True)
    assert ilerleme.son_durumlar(b)["a|x"]["bildi"] == 1
    assert b.execute("SELECT COUNT(*) FROM lugat_cevaplari").fetchone()[0] == 2
    b.close()


def test_lugat_akisi_bes_kart_ve_kayit(istemci, tmp_path):
    html = istemci.get("/lugat").get_data(as_text=True)
    assert "01" in html and "05" in html and 'name="anahtar"' in html
    for i in range(5):
        with istemci.session_transaction() as s:
            anahtar = s["lugat"]["kartlar"][s["lugat"]["sira"]]
        r = istemci.post("/lugat/cevap", data={"anahtar": anahtar, "bildi": "1" if i % 2 else "0"})
    assert r.headers["Location"].endswith("/lugat/sonuc")
    sonuc = istemci.get("/lugat/sonuc").get_data(as_text=True)
    assert "2</strong> biliyorum" in sonuc and "3</strong> bilmiyorum" in sonuc
    # İlerleme kalıcı dosyaya yazıldı
    with sqlite3.connect(tmp_path / "ilerleme.db") as b:
        assert b.execute("SELECT COUNT(*) FROM lugat_cevaplari").fetchone()[0] == 5
    b.close()


def test_devam_et_bilinmeyenleri_geri_getirir(istemci):
    istemci.get("/lugat")
    with istemci.session_transaction() as s:
        kartlar = list(s["lugat"]["kartlar"])
    for a in kartlar:
        istemci.post("/lugat/cevap", data={"anahtar": a, "bildi": "0"})
    istemci.post("/lugat/yeni", data={"mod": "devam"})
    with istemci.session_transaction() as s:
        yeni = s["lugat"]["kartlar"]
    assert len(set(yeni) & set(kartlar)) == 3   # en çok 3 bilinmeyen geri gelir


def test_yanlis_kart_cevabi_yok_sayilir(istemci, tmp_path):
    istemci.get("/lugat")
    istemci.post("/lugat/cevap", data={"anahtar": "olmayan|x", "bildi": "1"})
    with istemci.session_transaction() as s:
        assert s["lugat"]["sira"] == 0
