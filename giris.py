"""Google ile giriş — yalnızca site modunda (CALISMA_MODU=site).

Yerel modda (bilgisayarda çalıştırınca) giriş yoktur; bilgisayarın sahibi tek kullanıcıdır.
Sitede her kullanıcının ilerlemesi Google'ın verdiği değişmez kimliğe ("sub") bağlanır;
e-posta adresi değişebileceği için kimlik olarak kullanılmaz.

Gerekli ayarlar (sunucuda ortam değişkeni olarak, koda ya da GitHub'a yazılmaz):
  GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET — Google Cloud Console'daki OAuth istemcisi
  IZINLI_EPOSTALAR (isteğe bağlı)        — virgülle ayrılmış liste; boşsa her Google hesabı girebilir
"""

from functools import wraps

from authlib.integrations.flask_client import OAuth
from flask import Blueprint, current_app, redirect, render_template, request, session, url_for

oauth = OAuth()
oauth.register(
    name="google",
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)
bp = Blueprint("giris", __name__)


def site_modu() -> bool:
    return current_app.config.get("CALISMA_MODU") == "site"


def aktif_kullanici() -> str | None:
    """İlerleme kayıtlarının bağlanacağı kimlik. Yerel modda None (tek kullanıcı)."""
    if not site_modu():
        return None
    k = session.get("kullanici")
    return k["id"] if k else None


def giris_gerekli(gorunum):
    """Site modunda giriş yapılmamışsa giriş sayfasına yönlendirir; yerel modda etkisizdir."""
    @wraps(gorunum)
    def sarmal(*args, **kwargs):
        if site_modu() and not session.get("kullanici"):
            return redirect(url_for("giris.giris", sonra=request.full_path))
        return gorunum(*args, **kwargs)
    return sarmal


def guvenli_hedef(adres: str | None) -> str:
    """Girişten sonra yalnızca kendi sitemizin içindeki bir sayfaya dönülür."""
    if not adres or not adres.startswith("/") or adres.startswith("//") or "\\" in adres:
        return "/"
    return adres


def izinli_mi(eposta: str) -> bool:
    liste = [e.strip().lower() for e in current_app.config.get("IZINLI_EPOSTALAR", "").split(",") if e.strip()]
    return not liste or eposta.lower() in liste


@bp.route("/giris")
def giris():
    if not site_modu():
        return redirect("/")
    return render_template("giris.html", sonra=guvenli_hedef(request.args.get("sonra")),
                           hata=request.args.get("hata"))


@bp.route("/giris/google")
def google():
    if not site_modu():
        return redirect("/")
    session["giris_sonra"] = guvenli_hedef(request.args.get("sonra"))
    return oauth.google.authorize_redirect(url_for("giris.donus", _external=True))


@bp.route("/giris/donus")
def donus():
    if not site_modu():
        return redirect("/")
    try:
        token = oauth.google.authorize_access_token()
    except Exception:  # kullanıcı vazgeçti, süre doldu ya da durum (state) tutmadı
        current_app.logger.warning("Google girişi tamamlanamadı", exc_info=True)
        return redirect(url_for("giris.giris", hata="tamamlanamadi"))
    bilgi = token.get("userinfo") or {}
    eposta = bilgi.get("email", "")
    if not bilgi.get("sub") or not bilgi.get("email_verified"):
        return redirect(url_for("giris.giris", hata="dogrulanmamis"))
    if not izinli_mi(eposta):
        return redirect(url_for("giris.giris", hata="izinsiz"))
    sonra = guvenli_hedef(session.pop("giris_sonra", "/"))
    # Önceki oturumdan hiçbir şey taşınmasın (başka birinin lügat oturumu gibi).
    session.clear()
    session.permanent = True
    session["kullanici"] = {"id": bilgi["sub"], "ad": bilgi.get("given_name") or bilgi.get("name") or eposta,
                            "eposta": eposta}
    return redirect(sonra)


@bp.route("/cikis", methods=["POST"])
def cikis():
    session.clear()
    return redirect("/")


def kur(app) -> None:
    oauth.init_app(app)
    app.register_blueprint(bp)

    @app.context_processor
    def kullanici_bilgisi():
        return {"site_modu": site_modu(), "giris_yapan": session.get("kullanici")}
