"""Osmanlıca okuma ve lügat çalışma uygulaması (Flask)."""

import hashlib
import os
from pathlib import Path
import secrets
import sqlite3
import threading

from flask import (Flask, abort, g, make_response, redirect, render_template, request, send_from_directory,
                   session, url_for)

from checker import kontrol_et
import giris
from giris import aktif_kullanici, giris_gerekli
from harfler import HARFLER, LAMELIF
import ilerleme
from karsilastir import karsilastir
import kitap as kitaplar

KOK = Path(__file__).resolve().parent
VERI = KOK / "data"
YAZI_TIPLERI = ("matbu", "rika")
TURLER = {"kelime": "Tek kelime", "cumle": "Cümle / ifade"}

app = Flask(__name__)
app.config.update(
    SOZLUK_DB=VERI / "sozluk.db",
    # Veritabanı bu SQL dosyalarından (sırayla) oluşturulur.
    VERI_DOSYALARI=[VERI / "sema.sql", VERI / "vikisozluk.sql"],
    # Kullanıcının ilerlemesi: ayrı dosya, Git'e eklenmez, hiçbir kayıt silinmez.
    ILERLEME_DB=Path(app.instance_path) / "ilerleme.db",
    SESSION_COOKIE_SAMESITE="Lax",
    # "yerel": bilgisayarda tek kullanıcı, giriş yok. "site": Google ile giriş, herkesin ilerlemesi ayrı.
    CALISMA_MODU=os.environ.get("CALISMA_MODU", "yerel"),
    GOOGLE_CLIENT_ID=os.environ.get("GOOGLE_CLIENT_ID"),
    GOOGLE_CLIENT_SECRET=os.environ.get("GOOGLE_CLIENT_SECRET"),
    IZINLI_EPOSTALAR=os.environ.get("IZINLI_EPOSTALAR", ""),
    # Gizlilik sayfasında gösterilecek iletişim adresi (kodda/GitHub'da değil, sunucuda ayarlanır).
    ILETISIM_EPOSTA=os.environ.get("ILETISIM_EPOSTA", ""),
)

if app.config["CALISMA_MODU"] == "site":
    from werkzeug.middleware.proxy_fix import ProxyFix

    # alwaysdata uygulamanın önünde bir ara sunucu (proxy) çalıştırır: gerçek adres ve https
    # bilgisi başlıklarda gelir. Bunu okumazsak Google'a dönüş adresi http:// olarak oluşur.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    app.config.update(SESSION_COOKIE_SECURE=True, PREFERRED_URL_SCHEME="https")
    if not (app.config["GOOGLE_CLIENT_ID"] and app.config["GOOGLE_CLIENT_SECRET"]):
        raise RuntimeError("Site modunda GOOGLE_CLIENT_ID ve GOOGLE_CLIENT_SECRET ortam değişkenleri gerekli.")


def gizli_anahtar(klasor: Path) -> str:
    """Oturum çerezini imzalamak için anahtar: ilk açılışta üretilir, instance/ klasöründe saklanır."""
    dosya = klasor / "gizli_anahtar"
    if not dosya.exists():
        klasor.mkdir(parents=True, exist_ok=True)
        dosya.write_text(secrets.token_hex(32), encoding="utf-8")
    return dosya.read_text(encoding="utf-8").strip()


app.secret_key = os.environ.get("GIZLI_ANAHTAR") or gizli_anahtar(Path(app.instance_path))
giris.kur(app)


# ---------- Veritabanı ----------

def veri_surumu(dosyalar) -> str:
    """SQL dosyalarının içeriğinden bir parmak izi; veri değişince değişir."""
    h = hashlib.sha256()
    for d in dosyalar:
        h.update(Path(d).read_bytes())
    return h.hexdigest()


_hazirlama_kilidi = threading.Lock()


def sozluk_hazirla(yol: Path, dosyalar) -> None:
    """sozluk.db yoksa ya da veri dosyaları değiştiyse yeniden oluşturur."""
    # Sunucu istekleri aynı anda işleyebilir; veritabanını yalnızca bir iş parçacığı kursun.
    with _hazirlama_kilidi:
        _sozluk_hazirla(yol, dosyalar)


def _sozluk_hazirla(yol: Path, dosyalar) -> None:
    surum = veri_surumu(dosyalar)
    if yol.exists():
        with sqlite3.connect(yol) as b:
            try:
                mevcut = b.execute("SELECT deger FROM _ayarlar WHERE ad = 'veri_surumu'").fetchone()
            except sqlite3.DatabaseError:
                mevcut = None
        b.close()
        if mevcut and mevcut[0] == surum:
            return

    gecici = yol.with_suffix(f".{os.getpid()}.tmp")  # her süreç kendi geçici dosyasını kullanır
    gecici.unlink(missing_ok=True)
    b = sqlite3.connect(gecici)
    try:
        for d in dosyalar:
            b.executescript(Path(d).read_text(encoding="utf-8"))
        b.execute("CREATE TABLE _ayarlar (ad TEXT PRIMARY KEY, deger TEXT)")
        b.execute("INSERT INTO _ayarlar VALUES ('veri_surumu', ?)", (surum,))
        b.commit()
    finally:
        b.close()
    # Yarım kalmış bir dosya bırakmamak için önce geçici dosyaya yazıp sonra adlandırıyoruz.
    gecici.replace(yol)


def db() -> sqlite3.Connection:
    """İstek boyunca tek bir veritabanı bağlantısı kullanır."""
    if "db" not in g:
        yol = Path(app.config["SOZLUK_DB"])
        sozluk_hazirla(yol, app.config["VERI_DOSYALARI"])
        g.db = sqlite3.connect(yol)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def db_kapat(_hata):
    baglanti = g.pop("db", None)
    if baglanti is not None:
        baglanti.close()


def rastgele_kayit(tur: str, haric: int | None = None):
    return db().execute(
        "SELECT * FROM kayitlar WHERE tur = ? AND id != ? ORDER BY RANDOM() LIMIT 1",
        (tur, haric or -1),
    ).fetchone()


def kayit_getir(kayit_id: int):
    return db().execute("SELECT * FROM kayitlar WHERE id = ?", (kayit_id,)).fetchone()


def okunuslar(kayit_id: int) -> list[tuple[str, bool]]:
    satirlar = db().execute(
        "SELECT okunus, asil FROM okunuslar WHERE kayit_id = ? ORDER BY asil DESC, id",
        (kayit_id,),
    ).fetchall()
    return [(s["okunus"], bool(s["asil"])) for s in satirlar]


def esyazilislar(kayit) -> dict[str, str]:
    """Aynı Osmanlıca yazılışa sahip başka kelimeler: asıl okunuş → anlam."""
    satirlar = db().execute(
        """SELECT o.okunus, k.anlam FROM kayitlar k
           JOIN okunuslar o ON o.kayit_id = k.id AND o.asil = 1
           WHERE k.osmanlica = ? AND k.tur = ? AND k.id != ? ORDER BY k.id""",
        (kayit["osmanlica"], kayit["tur"], kayit["id"]),
    ).fetchall()
    return {s["okunus"]: s["anlam"] for s in satirlar}


# ---------- Yazı tipi seçimi (rik'a / matbu) ----------

@app.context_processor
def yazi_tipi():
    secim = request.cookies.get("yazi", "matbu")
    return {"yazi": secim if secim in YAZI_TIPLERI else "matbu"}


@app.route("/yazi/<tip>")
def yazi_sec(tip):
    if tip not in YAZI_TIPLERI:
        abort(404)
    # Yalnızca kendi sitemizin içindeki bir sayfaya geri dön.
    geri = request.args.get("geri", "/")
    if not geri.startswith("/") or geri.startswith("//"):
        geri = "/"
    cevap = make_response(redirect(geri))
    cevap.set_cookie("yazi", tip, max_age=60 * 60 * 24 * 365, samesite="Lax")
    return cevap


# ---------- Sayfalar ----------

@app.route("/")
def ana_sayfa():
    return render_template("index.html")


@app.route("/okuma")
def okuma_sec():
    return render_template("okuma_sec.html", turler=TURLER)


@app.route("/okuma/<tur>", methods=["GET", "POST"])
def okuma(tur):
    if tur not in TURLER:
        abort(404)

    if request.method == "POST":
        kayit = kayit_getir(request.form.get("kayit_id", type=int) or -1)
        if kayit is None or kayit["tur"] != tur:
            abort(400)
        cevap = request.form.get("cevap", "")
        diger = esyazilislar(kayit)
        sonuc = kontrol_et(cevap, okunuslar(kayit["id"]), list(diger))
        return render_template("okuma.html", tur=tur, tur_adi=TURLER[tur],
                               kayit=kayit, cevap=cevap, sonuc=sonuc, diger_anlamlar=diger)

    kayit = rastgele_kayit(tur, haric=request.args.get("onceki", type=int))
    if kayit is None:
        abort(404)
    return render_template("okuma.html", tur=tur, tur_adi=TURLER[tur], kayit=kayit)


# ---------- Lügat: tek tek kartlar, Biliyorum / Bilmiyorum ----------

def ilerleme_db() -> sqlite3.Connection:
    if "ilerleme" not in g:
        g.ilerleme = ilerleme.baglan(Path(app.config["ILERLEME_DB"]))
    return g.ilerleme


@app.teardown_appcontext
def ilerleme_kapat(_hata):
    b = g.pop("ilerleme", None)
    if b is not None:
        b.close()


def lugat_kaydi(anahtar: str):
    return db().execute("SELECT * FROM kayitlar WHERE anahtar = ? AND tur = 'kelime'", (anahtar,)).fetchone()


def yeni_lugat_oturumu(mod: str) -> None:
    """Oturumdaki kartlar imzalı çerezde (Flask session) tutulur; cevaplar ilerleme.db'ye yazılır."""
    tum = [s["anahtar"] for s in db().execute("SELECT anahtar FROM kayitlar WHERE tur = 'kelime'")]
    onceki = session.get("lugat", {})
    onceki_bilinmeyen = [a for a, bildi in onceki.get("sonuc", {}).items() if not bildi]
    kartlar = ilerleme.oturum_sec(tum, ilerleme.son_durumlar(ilerleme_db(), aktif_kullanici()), mod, onceki_bilinmeyen)
    session["lugat"] = {"kartlar": kartlar, "sira": 0, "sonuc": {}}


@app.route("/lugat")
@giris_gerekli
def lugat():
    oturum = session.get("lugat")
    if not oturum or oturum["sira"] >= len(oturum["kartlar"]):
        if oturum:  # bitmiş oturum: özet sayfası
            return redirect(url_for("lugat_sonuc"))
        yeni_lugat_oturumu("devam")
        oturum = session["lugat"]
    kayit = lugat_kaydi(oturum["kartlar"][oturum["sira"]])
    if kayit is None:  # veri değişmiş olabilir; yeni oturum başlat
        session.pop("lugat", None)
        return redirect(url_for("lugat"))
    return render_template(
        "lugat.html", kayit=kayit, sira=oturum["sira"] + 1, toplam=len(oturum["kartlar"]),
        okunus=next((o for o, a in okunuslar(kayit["id"]) if a), ""),
    )


@app.route("/lugat/cevap", methods=["POST"])
@giris_gerekli
def lugat_cevap():
    oturum = session.get("lugat")
    anahtar = request.form.get("anahtar", "")
    # Yalnızca sıradaki kart cevaplanabilir (eski bir sekmeden gelen çift gönderimi yok say).
    if not oturum or oturum["sira"] >= len(oturum["kartlar"]) or oturum["kartlar"][oturum["sira"]] != anahtar:
        return redirect(url_for("lugat"))
    bildi = request.form.get("bildi") == "1"
    ilerleme.cevap_kaydet(ilerleme_db(), anahtar, bildi, aktif_kullanici())
    oturum["sonuc"][anahtar] = bildi
    oturum["sira"] += 1
    session["lugat"] = oturum
    if oturum["sira"] >= len(oturum["kartlar"]):
        return redirect(url_for("lugat_sonuc"))
    return redirect(url_for("lugat"))


@app.route("/lugat/sonuc")
@giris_gerekli
def lugat_sonuc():
    oturum = session.get("lugat")
    if not oturum or oturum["sira"] < len(oturum["kartlar"]):
        return redirect(url_for("lugat"))
    kartlar = []
    for a in oturum["kartlar"]:
        k = lugat_kaydi(a)
        if k is not None:
            kartlar.append({"kayit": k, "bildi": oturum["sonuc"].get(a, False),
                            "okunus": a.split("|", 1)[1]})
    toplam = ilerleme_db().execute(
        "SELECT COUNT(DISTINCT anahtar) FROM lugat_cevaplari WHERE kullanici IS ?",
        (aktif_kullanici(),)).fetchone()[0]
    return render_template("lugat_sonuc.html", kartlar=kartlar, gorulen=toplam)


@app.route("/lugat/yeni", methods=["POST"])
@giris_gerekli
def lugat_yeni():
    mod = "yeni" if request.form.get("mod") == "yeni" else "devam"
    yeni_lugat_oturumu(mod)
    return redirect(url_for("lugat"))


# ---------- Kitap tercüme: sayfalar satır satır ----------

def kitap_veya_404(kod: str) -> dict:
    bilgi = kitaplar.kitap_bilgisi(kod)
    if bilgi is None:
        abort(404)
    return bilgi


def sayfa_veya_404(kod: str, sayfa: int):
    satirlar = kitaplar.sayfa_satirlari(kod, sayfa)
    if not satirlar:
        abort(404)
    return satirlar


@app.route("/kitap")
def kitap_listesi():
    return render_template("kitap_listesi.html", kitaplar=[
        dict(k, hazir=len(kitaplar.hazir_sayfalar(k["kod"])), toplam=len(kitaplar.tum_sayfalar(k["kod"])))
        for k in kitaplar.kitaplar()])


@app.route("/kitap/<kod>")
@giris_gerekli
def kitap_sayfalari(kod):
    bilgi = kitap_veya_404(kod)
    durumlar = ilerleme.sayfa_durumlari(ilerleme_db(), kod, aktif_kullanici())
    sayfalar = [{"pdf": n, "no": kitaplar.gorunen_no(kod, n), "durum": durumlar.get(n)}
                for n in kitaplar.hazir_sayfalar(kod)]
    return render_template("kitap_sayfalari.html", kitap=bilgi, kod=kod, sayfalar=sayfalar,
                           toplam=len(kitaplar.tum_sayfalar(kod)))


@app.route("/kitap/<kod>/resim/<int:sayfa>.jpg")
def kitap_resmi(kod, sayfa):
    kitap_veya_404(kod)
    return send_from_directory(kitaplar.KITAPLAR_KLASORU / kod / "sayfalar", f"s{sayfa:03d}.jpg",
                               max_age=60 * 60 * 24)


def satir_gorunumu(kod, sayfa, satir):
    """Satırı, üstünde ve altında biraz bağlamla gösteren pencere (oranlar CSS için yüzde).

    Otomatik bulunan satır sınırları her zaman kusursuz değil; pencere biraz geniş tutulur ve
    asıl satır vurgulanır, böylece sınır kaysa da satırın tamamı görünür."""
    genislik, yukseklik = kitaplar.sayfa_boyutu(kod, sayfa)
    boy = satir.y1 - satir.y0
    p0, p1 = max(0.0, satir.y0 - boy * 0.9), min(1.0, satir.y1 + boy * 0.9)
    pencere = p1 - p0
    return {"satir": satir, "resim": url_for("kitap_resmi", kod=kod, sayfa=sayfa),
            "oran": genislik / (pencere * yukseklik),
            "ust": p0 / pencere * 100,
            "vurgu_ust": (satir.y0 - p0) / pencere * 100,
            "vurgu_boy": boy / pencere * 100}


@app.route("/kitap/<kod>/<int:sayfa>")
@giris_gerekli
def kitap_calis(kod, sayfa):
    bilgi = kitap_veya_404(kod)
    satirlar = sayfa_veya_404(kod, sayfa)
    b = ilerleme_db()
    deneme = ilerleme.acik_deneme(b, kod, sayfa, aktif_kullanici())
    if deneme is None:
        if ilerleme.son_bitmis_deneme(b, kod, sayfa, aktif_kullanici()):
            return redirect(url_for("kitap_sonuc", kod=kod, sayfa=sayfa))
        deneme_id = ilerleme.deneme_baslat(b, kod, sayfa, aktif_kullanici())
    else:
        deneme_id = deneme["id"]
    cevaplar = ilerleme.satir_cevaplari(b, deneme_id)
    sira = next((s for s in satirlar if s.no not in cevaplar), None)
    if sira is None:  # bütün satırlar cevaplandı: sayfayı bitir
        sonuclar = [karsilastir(s.metin, cevaplar[s.no]) for s in satirlar]
        ilerleme.deneme_bitir(b, deneme_id, sum(k.dogru_sayisi for k in sonuclar), sum(k.toplam for k in sonuclar))
        return redirect(url_for("kitap_sonuc", kod=kod, sayfa=sayfa))
    return render_template("kitap_satir.html", kitap=bilgi, kod=kod, sayfa=sayfa,
                           no=kitaplar.gorunen_no(kod, sayfa), toplam=len(satirlar),
                           **satir_gorunumu(kod, sayfa, sira))


@app.route("/kitap/<kod>/<int:sayfa>/cevap", methods=["POST"])
@giris_gerekli
def kitap_cevap(kod, sayfa):
    bilgi = kitap_veya_404(kod)
    satirlar = sayfa_veya_404(kod, sayfa)
    b = ilerleme_db()
    deneme = ilerleme.acik_deneme(b, kod, sayfa, aktif_kullanici())
    no = request.form.get("satir", type=int)
    if deneme is None or no is None or not 1 <= no <= len(satirlar):
        return redirect(url_for("kitap_calis", kod=kod, sayfa=sayfa))
    cevaplar = ilerleme.satir_cevaplari(b, deneme["id"])
    beklenen = next((s.no for s in satirlar if s.no not in cevaplar), None)
    if no != beklenen:  # sayfa yenilendi ya da eski form: yalnızca sıradaki satır kaydedilir
        return redirect(url_for("kitap_calis", kod=kod, sayfa=sayfa))
    cevap = request.form.get("cevap", "").strip()
    ilerleme.satir_kaydet(b, deneme["id"], no, cevap)
    satir = satirlar[no - 1]
    return render_template("kitap_satir.html", kitap=bilgi, kod=kod, sayfa=sayfa,
                           no=kitaplar.gorunen_no(kod, sayfa), toplam=len(satirlar),
                           cevap=cevap, sonuc=karsilastir(satir.metin, cevap), son=(no == len(satirlar)),
                           **satir_gorunumu(kod, sayfa, satir))


@app.route("/kitap/<kod>/<int:sayfa>/sonuc")
@giris_gerekli
def kitap_sonuc(kod, sayfa):
    bilgi = kitap_veya_404(kod)
    satirlar = sayfa_veya_404(kod, sayfa)
    b = ilerleme_db()
    deneme = ilerleme.son_bitmis_deneme(b, kod, sayfa, aktif_kullanici())
    if deneme is None:
        return redirect(url_for("kitap_calis", kod=kod, sayfa=sayfa))
    cevaplar = ilerleme.satir_cevaplari(b, deneme["id"])
    satir_sonuclari = [{"satir": s, "sonuc": karsilastir(s.metin, cevaplar.get(s.no, ""))} for s in satirlar]
    hazir = kitaplar.hazir_sayfalar(kod)
    sonraki = next((n for n in hazir if n > sayfa), None)
    return render_template("kitap_sonuc.html", kitap=bilgi, kod=kod, sayfa=sayfa, deneme=deneme,
                           no=kitaplar.gorunen_no(kod, sayfa), satirlar=satir_sonuclari, sonraki=sonraki,
                           sonraki_no=kitaplar.gorunen_no(kod, sonraki) if sonraki else None,
                           yuzde=round(100 * deneme["dogru"] / deneme["toplam"]) if deneme["toplam"] else 100)


@app.route("/kitap/<kod>/<int:sayfa>/yeniden", methods=["POST"])
@giris_gerekli
def kitap_yeniden(kod, sayfa):
    kitap_veya_404(kod)
    sayfa_veya_404(kod, sayfa)
    b = ilerleme_db()
    if ilerleme.acik_deneme(b, kod, sayfa, aktif_kullanici()) is None:
        ilerleme.deneme_baslat(b, kod, sayfa, aktif_kullanici())
    return redirect(url_for("kitap_calis", kod=kod, sayfa=sayfa))


@app.route("/harfler")
def harfler():
    return render_template("harfler.html", harfler=HARFLER + [LAMELIF])


@app.route("/gizlilik")
def gizlilik():
    return render_template("gizlilik.html", iletisim=app.config["ILETISIM_EPOSTA"])


@app.route("/kaynaklar")
def kaynaklar():
    satirlar = db().execute(
        """SELECT k.*, COUNT(r.id) AS kayit_sayisi FROM kaynaklar k
           LEFT JOIN kayitlar r ON r.kaynak_id = k.id GROUP BY k.id ORDER BY k.id"""
    ).fetchall()
    return render_template("kaynaklar.html", kaynaklar=satirlar)


if __name__ == "__main__":
    # Yerel (masaüstü) çalıştırma: http://127.0.0.1:5000
    app.run(host="127.0.0.1", port=5000, debug=False)
