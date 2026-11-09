# Fezleke metinleri

Her `sNNN.txt` dosyası, PDF'in NNN numaralı sayfasının Latin harfli okunuşudur.

**Bu metinler Claude (yapay zekâ) tarafından sayfa resimlerinden okunmuştur ve bir insan
tarafından kontrol edilmemiştir.** Hatalı okumalar olabilir; düzeltmeler doğrudan bu
dosyalara yapılabilir.

## Biçim

Dosyadaki her satır, `../satirlar.json` içinde o sayfa için otomatik bulunmuş bir "bant"a karşılık gelir
(sırayla). Bant sayısı ile satır sayısı eşit olmalıdır.

| Satır | Anlamı |
|---|---|
| metin | Bu bandın okunuşu |
| `-` | Bu bant atlanır (sayfa başlığı, süs çizgisi, yarım kalmış bant) |
| `+` | Bu bant bir önceki satıra eklenir (otomatik bulma bir satırı ikiye böldüyse) |
| `# ...` | Açıklama; sayılmaz |

## Okuma kuralları

- Günümüz Türk alfabesi; uzun ünlüler için şapka (â, î, û) kullanılır ama karşılaştırmada önemsizdir.
- Tamlamalar çizgiyle yazılır: `Devlet-i Osmâniye`, `hazret-i pâdişâhî` (karşılaştırmada "devleti" de doğru sayılır).
- Ayın ve hemze için kesme işareti: `ta'dîl`, `şürû'` (karşılaştırmada önemsizdir).
- Osmanlı rakamları Batı rakamlarıyla yazılır: `٦٩٩` → `699`.
- Kelimeler kitaptaki imlaya göre okunur (ör. `olmağla`, `olunmuşdur`), günümüz imlasına çevrilmez.
