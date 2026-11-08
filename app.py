"""Osmanlıca okuma ve lügat çalışma uygulaması (Flask)."""

from pathlib import Path
import sqlite3

from flask import Flask, abort, g, make_response, redirect, render_template, request, url_for

from checker import kontrol_et

KOK = Path(__file__).resolve().parent
VERI = KOK / "data"
SOZLUK_DB = VERI / "sozluk.db"
YAZI_TIPLERI = ("matbu", "rika")
TURLER = {"kelime": "Tek kelime", "cumle": "Cümle"}

app = Flask(__name__)


# ---------- Veritabanı ----------

def sozluk_olustur(yol: Path = SOZLUK_DB) -> None:
    """sozluk.db yoksa şema ve örnek veriden oluşturur."""
    if yol.exists():
        return
    gecici = yol.with_suffix(".tmp")
    gecici.unlink(missing_ok=True)
    with sqlite3.connect(gecici) as baglanti:
        baglanti.executescript((VERI / "sema.sql").read_text(encoding="utf-8"))
        baglanti.executescript((VERI / "ornek_veri.sql").read_text(encoding="utf-8"))
    baglanti.close()
    # Yarım kalmış bir dosya bırakmamak için önce geçici dosyaya yazıp sonra adlandırıyoruz.
    gecici.replace(yol)


def db() -> sqlite3.Connection:
    """İstek boyunca tek bir veritabanı bağlantısı kullanır."""
    if "db" not in g:
        sozluk_olustur(app.config.get("SOZLUK_DB", SOZLUK_DB))
        g.db = sqlite3.connect(app.config.get("SOZLUK_DB", SOZLUK_DB))
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
        sonuc = kontrol_et(cevap, okunuslar(kayit["id"]))
        return render_template("okuma.html", tur=tur, tur_adi=TURLER[tur],
                               kayit=kayit, cevap=cevap, sonuc=sonuc)

    kayit = rastgele_kayit(tur, haric=request.args.get("onceki", type=int))
    if kayit is None:
        abort(404)
    return render_template("okuma.html", tur=tur, tur_adi=TURLER[tur], kayit=kayit)


@app.route("/lugat")
def lugat():
    kayitlar = db().execute(
        "SELECT * FROM kayitlar WHERE tur = 'kelime' ORDER BY RANDOM() LIMIT 6"
    ).fetchall()
    kartlar = [
        {"kayit": k, "okunus": next((o for o, a in okunuslar(k["id"]) if a), "")}
        for k in kayitlar
    ]
    return render_template("lugat.html", kartlar=kartlar)


if __name__ == "__main__":
    # Yerel (masaüstü) çalıştırma: http://127.0.0.1:5000
    app.run(host="127.0.0.1", port=5000, debug=False)
