-- TEST İÇİN ÖRNEK VERİ (uygulama bu dosyayı kullanmaz; testler kullanır)
-- Bu kayıtlar uygulamayı denemek için proje içinde elle yazılmıştır;
-- herhangi bir sözlükten kopyalanmamıştır. Gerçek kaynaklar lisansları
-- doğrulandıktan sonra eklenecektir.

INSERT INTO kaynaklar (id, ad, yazar, yil, lisans, notlar) VALUES
    (1, 'Örnek veri', 'osmanlica-egitim-ia projesi', 2026, 'Proje lisansı',
     'Deneme amaçlı elle yazılmış küçük veri seti.');

-- ---------- Kelimeler ----------
INSERT INTO kayitlar (id, osmanlica, anlam, tur, kaynak_id) VALUES
    (1,  'مرحبا',   'Selam; karşılaşınca söylenen iyi dilek sözü.', 'kelime', 1),
    (2,  'کتاب',    'Kitap.', 'kelime', 1),
    (3,  'کاتب',    'Yazı yazan kimse, yazıcı; kâtip.', 'kelime', 1),
    (4,  'کل',      'Gel (gelmek fiilinin emri).', 'kelime', 1),
    (5,  'قلم',     'Kalem; yazı yazma aracı.', 'kelime', 1),
    (6,  'اکمک',    'Ekmek.', 'kelime', 1),
    (7,  'صو',      'Su.', 'kelime', 1),
    (8,  'گوزل',    'Güzel.', 'kelime', 1),
    (9,  'یول',     'Yol.', 'kelime', 1),
    (10, 'باش',     'Baş, kafa.', 'kelime', 1),
    (11, 'گون',     'Gün.', 'kelime', 1),
    (12, 'اوطه',    'Oda.', 'kelime', 1),
    (13, 'دنیا',    'Dünya; yeryüzü.', 'kelime', 1),
    (14, 'علم',     'Bilgi, bilim (ilim); bayrak, sancak (alem).', 'kelime', 1),
    (15, 'مکتب',    'Okul.', 'kelime', 1),
    (16, 'مستقبل',  'Gelecek, ileride olacak olan zaman.', 'kelime', 1),
    (17, 'ماضی',    'Geçmiş, geçmiş zaman.', 'kelime', 1),
    (18, 'لسان',    'Dil (konuşulan dil).', 'kelime', 1),
    (19, 'معلم',    'Öğretmen.', 'kelime', 1),
    (20, 'طلبه',    'Öğrenciler; öğrenci.', 'kelime', 1),
    (21, 'وطن',     'Yurt, memleket.', 'kelime', 1),
    (22, 'حکمت',    'Bilgelik; bir şeyin gizli sebebi.', 'kelime', 1),
    (23, 'کتبخانه', 'Kütüphane.', 'kelime', 1),
    (24, 'ایام',    'Günler.', 'kelime', 1),
    (25, 'تحصیل',   'Öğrenim, okuyup öğrenme.', 'kelime', 1),
    (26, 'کل',      'Gül (çiçek).', 'kelime', 1),
    (27, 'کل',      'Kül.', 'kelime', 1),
    (28, 'کل',      'Kel, saçsız.', 'kelime', 1);

INSERT INTO okunuslar (kayit_id, okunus, asil) VALUES
    (1,  'merhaba', 1),
    (2,  'kitâb', 1),  (2,  'kitap', 0),
    (3,  'kâtib', 1),  (3,  'kâtip', 0),
    (4,  'gel', 1),    (26, 'gül', 1),   (27, 'kül', 1), (28, 'kel', 1),
    (5,  'kalem', 1),
    (6,  'ekmek', 1),
    (7,  'su', 1),
    (8,  'güzel', 1),
    (9,  'yol', 1),
    (10, 'baş', 1),
    (11, 'gün', 1),
    (12, 'oda', 1),
    (13, 'dünyâ', 1),
    (14, 'ilim', 1),   (14, 'ilm', 0),   (14, 'alem', 0),
    (15, 'mekteb', 1), (15, 'mektep', 0),
    (16, 'müstakbel', 1),
    (17, 'mâzî', 1),
    (18, 'lisân', 1),
    (19, 'muallim', 1),
    (20, 'talebe', 1),
    (21, 'vatan', 1),
    (22, 'hikmet', 1),
    (23, 'kütübhâne', 1), (23, 'kütüphane', 0),
    (24, 'eyyâm', 1),
    (25, 'tahsîl', 1);

-- ---------- Cümleler ----------
INSERT INTO kayitlar (id, osmanlica, anlam, tur, kaynak_id) VALUES
    (101, 'بن مکتبه گیدییورم',     'Ben okula gidiyorum.', 'cumle', 1),
    (102, 'بو کتاب چوق گوزل',      'Bu kitap çok güzel.', 'cumle', 1),
    (103, 'صباحلر خیرلی اولسون',   'Günaydın; sabahın hayırlı olsun.', 'cumle', 1),
    (104, 'استانبول گوزل بر شهردر', 'İstanbul güzel bir şehirdir.', 'cumle', 1);

INSERT INTO okunuslar (kayit_id, okunus, asil) VALUES
    (101, 'ben mektebe gidiyorum', 1),
    (102, 'bu kitâb çok güzel', 1), (102, 'bu kitap çok güzel', 0),
    (103, 'sabahlar hayırlı olsun', 1),
    (104, 'İstanbul güzel bir şehirdir', 1);
