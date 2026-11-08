"""Osmanlıca okuma ve lügat çalışma uygulaması (Flask)."""

import hashlib
import os
from pathlib import Path
import sqlite3
import threading

from flask import Flask, abort, g, make_response, redirect, render_template, request

from checker import kontrol_et
from harfler import HARFLER, LAMELIF

KOK = Path(__file__).resolve().parent
VERI = KOK / "data"
YAZI_TIPLERI = ("matbu", "rika")
TURLER = {"kelime": "Tek kelime", "cumle": "Cümle / ifade"}

app = Flask(__name__)
app.config.update(
    SOZLUK_DB=VERI / "sozluk.db",
    # Veritabanı bu SQL dosyalarından (sırayla) oluşturulur.
    VERI_DOSYALARI=[VERI / "sema.sql", VERI / "vikisozluk.sql"],
)


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


@app.route("/harfler")
def harfler():
    return render_template("harfler.html", harfler=HARFLER + [LAMELIF])


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
