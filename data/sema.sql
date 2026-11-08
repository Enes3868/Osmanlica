-- Sözlük veritabanının yapısı (şema).
-- Bu dosya tabloları tanımlar; içerik ornek_veri.sql dosyasındadır.

-- Kelimelerin ve cümlelerin geldiği kitaplar/kaynaklar.
-- Bir kaynakta çok kayıt olabilir (bire-çok ilişki).
CREATE TABLE IF NOT EXISTS kaynaklar (
    id      INTEGER PRIMARY KEY,
    ad      TEXT NOT NULL,          -- ör. "Kāmûs-ı Türkî"
    yazar   TEXT,
    yil     INTEGER,
    lisans  TEXT NOT NULL,          -- yeniden dağıtım izni: "Kamu malı", "CC BY 4.0" ...
    notlar  TEXT
);

-- Her kart bir kayıttır: tek kelime ya da bir cümle.
CREATE TABLE IF NOT EXISTS kayitlar (
    id         INTEGER PRIMARY KEY,
    osmanlica  TEXT NOT NULL,       -- Arap harfli yazılış (Unicode). Rik'a/matbu farkı yazı tipiyle gelir.
    anlam      TEXT NOT NULL,       -- günümüz Türkçesiyle karşılığı (lügat modu)
    tur        TEXT NOT NULL CHECK (tur IN ('kelime', 'cumle')),
    kaynak_id  INTEGER NOT NULL REFERENCES kaynaklar(id)
);

-- Bir kaydın kabul edilen Latin harfli okunuşları.
-- Bir kaydın birden çok okunuşu olabilir (ör. کل: gel, gül, kül, kel).
-- Her kaydın tam olarak bir "asıl" okunuşu vardır; ekranda o gösterilir.
CREATE TABLE IF NOT EXISTS okunuslar (
    id         INTEGER PRIMARY KEY,
    kayit_id   INTEGER NOT NULL REFERENCES kayitlar(id),
    okunus     TEXT NOT NULL,
    asil       INTEGER NOT NULL DEFAULT 0 CHECK (asil IN (0, 1))
);

CREATE INDEX IF NOT EXISTS okunuslar_kayit ON okunuslar(kayit_id);
