# Osmanlıca Eğitim

Osmanlıca okuma pratiği ve eski Türkçe lügat çalışmak için kart tabanlı bir uygulama.

- **Osmanlıca okuma:** Kartta Arap harfleriyle yazılmış kelimeyi ya da ifadeyi okuyup Latin harfleriyle yazın. Uygulama doğru/yanlış olduğunu söyler, doğru okunuşu, diğer yazımları ve aynı yazılışla okunabilen başka kelimeleri gösterir.
- **Lügat:** Eski kelimelerin kartlarını okuyun; karta basınca kelimenin günümüzdeki biçimi ve anlamı açılır.
- Osmanlıca metin **matbu** (Amiri) ya da **rik'a** (Aref Ruqaa) yazıyla gösterilebilir.

## Veri

Sözlük verisi [Vikisözlük (Wiktionary)](https://en.wiktionary.org/wiki/Category:Ottoman_Turkish_language) Osmanlıca maddelerinden alınmıştır (yaklaşık 520 kelime ve 45 ifade). Arap harfli yazılışlar, okunuşlar ve günümüz biçimleri Vikisözlük'tendir.

> **Türkçe anlamlar, Vikisözlük'teki İngilizce anlamlardan yapay zekâ ile çevrilmiştir ve henüz kontrol edilmemiştir.** Uygulamada "AI çevirisi" olarak işaretlenir; İngilizce aslı da gösterilir.

Veri hattı:

```sh
python scripts/vikisozluk_indir.py   # ham veriyi data/ham/ klasörüne indirir (34 MB, Git'e eklenmez)
python scripts/vikisozluk_sec.py     # kelimeleri seçer → data/vikisozluk_secim.csv
# data/vikisozluk_anlamlar.csv: Türkçe anlamlar (çevirisi olmayan satır alınmaz)
python scripts/veritabani_olustur.py # → data/vikisozluk.sql
```

Uygulama `data/vikisozluk.sql` değiştiğinde veritabanını kendiliğinden yeniden oluşturur.

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

## Testler

```sh
.venv/bin/python -m pytest      # Windows: .venv\Scripts\python -m pytest
```

Testler `tests/veri/ornek_veri.sql` içindeki küçük örnek veriyle çalışır; ayrıca gerçek verinin şemaya uygun olduğunu denetler.

## Proje yapısı

| Yol | Görevi |
|---|---|
| `app.py` | Flask uygulaması: sayfalar ve veritabanı erişimi |
| `checker.py` | Cevap kontrolü (Türkçe büyük-küçük harf, şapka, kesme işareti, yazım çeşitleri, aynı yazılışlı kelimeler) |
| `data/sema.sql` | Veritabanı tabloları: `kaynaklar`, `kayitlar`, `okunuslar` |
| `data/vikisozluk*.{csv,sql}` | Sözlük verisi (CC BY-SA 4.0) |
| `scripts/` | Veriyi indirme, seçme ve SQL'e dönüştürme betikleri |
| `templates/`, `static/` | HTML şablonları, CSS ve yazı tipleri |
| `tests/` | Testler ve test verisi |

## Lisanslar

- **Kod:** MIT (`LICENSE`).
- **Sözlük verisi:** CC BY-SA 4.0, Wiktionary katkıcıları ve kaikki.org (`data/LICENSE`).
- **Yazı tipleri:** Amiri ve Aref Ruqaa, SIL Open Font License 1.1 (`static/fonts/OFL-*.txt`).
