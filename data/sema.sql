-- Sözlük veritabanının yapısı (şema).
-- İçerik ayrı dosyalardadır (data/vikisozluk.sql; testlerde tests/veri/ornek_veri.sql).

-- Kelimelerin ve cümlelerin geldiği kaynaklar.
-- Bir kaynakta çok kayıt olabilir (bire-çok ilişki).
CREATE TABLE IF NOT EXISTS kaynaklar (
    id      INTEGER PRIMARY KEY,
    ad      TEXT NOT NULL,          -- ör. "Vikisözlük (Wiktionary)"
    yazar   TEXT,
    yil     INTEGER,
    lisans  TEXT NOT NULL,          -- yeniden dağıtım izni: "CC BY-SA 4.0", "Kamu malı" ...
    url     TEXT,
    notlar  TEXT
);

-- Her kart bir kayıttır: tek kelime ya da bir cümle/ifade.
-- Aynı Osmanlıca yazılışın farklı okunuşları (gel / gül) ayrı kayıtlardır.
CREATE TABLE IF NOT EXISTS kayitlar (
    id               INTEGER PRIMARY KEY,
    anahtar          TEXT UNIQUE,     -- kalıcı kimlik "yazılış|asıl okunuş"; ilerleme kaydı buna bağlanır
                                      -- (id veri yeniden üretilince değişebilir, anahtar değişmez)
    osmanlica        TEXT NOT NULL,   -- Arap harfli yazılış (Unicode). Rik'a/matbu farkı yazı tipiyle gelir.
    anlam            TEXT NOT NULL,   -- Türkçe anlam (lügat modu)
    anlam_ai         INTEGER NOT NULL DEFAULT 0 CHECK (anlam_ai IN (0, 1)),  -- 1: AI çevirisi, kontrol edilmedi
    anlam_ingilizce  TEXT,            -- kaynaktaki asıl anlam (çeviri yapıldıysa)
    gunumuz          TEXT,            -- kelimenin günümüz Türkçesindeki biçimi (ör. عزیز → aziz)
    koken            TEXT,            -- 'ar' (Arapça), 'fa' (Farsça) ya da NULL
    edebi            INTEGER NOT NULL DEFAULT 0 CHECK (edebi IN (0, 1)),  -- edebi dil kelimesi
    tur              TEXT NOT NULL CHECK (tur IN ('kelime', 'cumle')),
    kaynak_id        INTEGER NOT NULL REFERENCES kaynaklar(id)
);

CREATE INDEX IF NOT EXISTS kayitlar_osmanlica ON kayitlar(osmanlica);

-- Bir kaydın kabul edilen Latin harfli okunuşları (yazım çeşitleri: kitâb / kitap).
-- Her kaydın tam olarak bir "asıl" okunuşu vardır; ekranda o gösterilir.
CREATE TABLE IF NOT EXISTS okunuslar (
    id         INTEGER PRIMARY KEY,
    kayit_id   INTEGER NOT NULL REFERENCES kayitlar(id),
    okunus     TEXT NOT NULL,
    asil       INTEGER NOT NULL DEFAULT 0 CHECK (asil IN (0, 1))
);

CREATE INDEX IF NOT EXISTS okunuslar_kayit ON okunuslar(kayit_id);
