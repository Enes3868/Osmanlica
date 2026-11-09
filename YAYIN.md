# Siteyi yayına alma (alwaysdata + Google ile giriş)

Uygulama iki modda çalışır:

| Mod | Nerede | Giriş | İlerleme |
|---|---|---|---|
| `yerel` (varsayılan) | Kendi bilgisayarınızda `python app.py` | Yok | Tek kişi |
| `site` | Sunucuda (alwaysdata) | Google ile giriş | Her kullanıcının ayrı |

Site modu **ortam değişkenleriyle** açılır. Google anahtarları ve gizli anahtar koda ya da GitHub'a
**asla** yazılmaz; yalnızca alwaysdata panelindeki site ayarlarına girilir.

> Not: alwaysdata ve Google panellerindeki menü adları zamanla değişebilir; aşağıdaki adlar yol göstermek içindir.

---

## 1. Google'da OAuth istemcisi oluşturma

1. <https://console.cloud.google.com> adresine kendi Google hesabınızla girin ve yeni bir proje oluşturun (ör. "Osmanlica").
2. **APIs & Services → OAuth consent screen** (Google Auth Platform):
   - Kullanıcı türü: **External**.
   - Uygulama adı (ör. "Osmanlıca Eğitim"), destek e-postası ve geliştirici e-postası: kendi adresiniz.
   - Kapsamlar (scopes): `openid`, `email`, `profile` yeterlidir (bunlar "hassas" değildir).
   - **Test users** bölümüne giriş yapacak kişilerin Gmail adreslerini ekleyin. Uygulama "Testing" durumunda
     kaldıkça yalnızca bu kişiler girebilir (en çok 100 kişi) — aile ve arkadaşlar için yeterli ve güvenli.
3. **APIs & Services → Credentials → Create credentials → OAuth client ID**:
   - Uygulama türü: **Web application**.
   - **Authorized redirect URIs**: `https://HESAP.alwaysdata.net/giris/donus`
     (`HESAP` yerine alwaysdata hesap adınız; kendi alan adınızı kullanırsanız o adres).
4. Oluşan **Client ID** ve **Client secret** değerlerini bir kenara not edin. Bunları kimseyle paylaşmayın.

## 2. alwaysdata'da kurulum

### 2a. Kodu sunucuya çekme (SSH)

alwaysdata panelinde **Remote access → SSH** bölümünden SSH erişimini açın, sonra kendi bilgisayarınızın
terminalinden bağlanın (`ssh HESAP@ssh-HESAP.alwaysdata.net`) ve şunları çalıştırın:

```sh
git clone https://github.com/Enes3868/Osmanlica.git ~/osmanlica
cd ~/osmanlica
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Bir de gizli anahtar üretin ve not edin (oturum çerezlerini imzalamak için):

```sh
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### 2b. Siteyi oluşturma

Panelde **Web → Sites → Add a site**:

| Alan | Değer |
|---|---|
| Adresler | `HESAP.alwaysdata.net` |
| Tür (Type) | **Python WSGI** |
| Application path | `/home/HESAP/osmanlica/wsgi.py` |
| Working directory | `/home/HESAP/osmanlica` |
| Virtualenv directory | `/home/HESAP/osmanlica/.venv` |
| Environment (ortam değişkenleri) | aşağıdaki tablo |

Ortam değişkenleri (her biri ayrı satır, `AD=değer`):

| Değişken | Değer |
|---|---|
| `CALISMA_MODU` | `site` |
| `GOOGLE_CLIENT_ID` | 1. adımdaki Client ID |
| `GOOGLE_CLIENT_SECRET` | 1. adımdaki Client secret |
| `GIZLI_ANAHTAR` | 2a'da ürettiğiniz uzun rastgele metin |
| `IZINLI_EPOSTALAR` | (isteğe bağlı) `anne@gmail.com,ali@gmail.com` — boşsa her Google hesabı girebilir |

Sitenin **SSL / HTTPS** ayarında "Force HTTPS" (HTTPS'e yönlendir) açık olsun. Kaydedip siteyi yeniden başlatın.

### 2c. Deneme

`https://HESAP.alwaysdata.net` adresini açın, **Lügat**'e tıklayın: Google giriş sayfasına yönlendirilmelisiniz.
Giriş yaptıktan sonra sağ üstte adınız görünür.

Sorun olursa: panelde sitenin **Logs** bölümüne bakın. "Site modunda GOOGLE_CLIENT_ID ... gerekli" hatası
ortam değişkenlerinin girilmediğini, Google'ın `redirect_uri_mismatch` hatası ise 1.3'teki adresin
sitenin adresiyle birebir aynı olmadığını gösterir.

## 3. Güncelleme

GitHub'a yeni bir sürüm gönderildikten sonra sunucuda:

```sh
cd ~/osmanlica
git pull
.venv/bin/pip install -r requirements.txt
```

ve panelden siteyi yeniden başlatın.

## 4. Kullanıcı verisi

Kullanıcıların ilerlemesi sunucuda `~/osmanlica/instance/ilerleme.db` dosyasındadır. Bu dosya GitHub'a
gitmez ve `git pull` ile silinmez. Ara sıra yedeğini alın:

```sh
cp ~/osmanlica/instance/ilerleme.db ~/ilerleme-yedek-$(date +%F).db
```
