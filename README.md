# Osmanlıca Eğitim

Osmanlıca okuma pratiği ve eski Türkçe lügat çalışmak için kart tabanlı bir uygulama.

- **Osmanlıca okuma:** Kartta Arap harfleriyle yazılmış kelimeyi ya da cümleyi okuyup Latin harfleriyle yazın. Uygulama doğru/yanlış olduğunu söyler, doğru okunuşu ve kabul edilen diğer okunuşları gösterir.
- **Lügat:** Eski kelimelerin kartlarını okuyun, karta basınca günümüzdeki karşılığı açılır.
- Osmanlıca metin **matbu** (Amiri) ya da **rik'a** (Aref Ruqaa) yazıyla gösterilebilir.

> Şu anki veriler deneme amaçlı küçük bir **örnek veri setidir**. Gerçek kaynaklar, yeniden dağıtım lisansları doğrulandıktan sonra eklenecek.

## Bilgisayarınızda çalıştırma

Gereken: [Python 3.10 veya üstü](https://www.python.org/downloads/) ve Git. İnternet yalnızca kurulum sırasında gerekir.

Windows (PowerShell):

```powershell
git clone <depo-adresi> osmanlica-egitim
cd osmanlica-egitim
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python app.py
```

macOS / Linux:

```sh
git clone <depo-adresi> osmanlica-egitim
cd osmanlica-egitim
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python app.py
```

Sonra tarayıcıda <http://127.0.0.1:5000> adresini açın.

İlk açılışta `data/sozluk.db` dosyası `data/sema.sql` ve `data/ornek_veri.sql` dosyalarından otomatik oluşturulur. Veriyi değiştirdiyseniz bu `.db` dosyasını silip uygulamayı yeniden başlatın.

## Testler

```sh
.venv/bin/python -m pytest      # Windows: .venv\Scripts\python -m pytest
```

## Proje yapısı

| Yol | Görevi |
|---|---|
| `app.py` | Flask uygulaması: sayfalar ve veritabanı erişimi |
| `checker.py` | Cevap kontrolü (Türkçe büyük-küçük harf, şapka, birden çok okunuş) |
| `data/sema.sql` | Veritabanı tabloları: `kaynaklar`, `kayitlar`, `okunuslar` |
| `data/ornek_veri.sql` | Örnek kelimeler ve cümleler |
| `templates/` | HTML şablonları |
| `static/` | CSS ve yazı tipleri |
| `tests/` | Testler |

## Lisanslar

- Yazı tipleri: Amiri ve Aref Ruqaa, SIL Open Font License 1.1 (`static/fonts/OFL-*.txt`).
- Projenin kendi lisansı henüz seçilmedi.
