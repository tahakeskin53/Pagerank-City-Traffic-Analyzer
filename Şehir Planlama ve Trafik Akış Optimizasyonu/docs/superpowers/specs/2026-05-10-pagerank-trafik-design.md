# PageRank Tabanlı Şehir Trafik Akış Optimizasyonu — Tasarım Belgesi

**Tarih:** 2026-05-10  
**Proje:** Şehir Planlama ve Trafik Akış Optimizasyonu  
**Amaç:** PageRank algoritmasını ders sunumu kapsamında şehir yol ağı üzerinde temsil etmek

---

## 1. Proje Amacı

Bu proje, PageRank algoritmasının gerçek dünya verisi üzerinde nasıl çalıştığını görsel olarak göstermek amacıyla geliştirilmektedir. Şehir yol ağındaki kavşaklar düğüm (node), yollar ise kenar (edge) olarak modellenmektedir. PageRank skoru, bir kavşağın trafik akışındaki "merkezi önem" düzeyini temsil eder — tıpkı web'deki bir sayfanın önemini ölçmesi gibi.

---

## 2. Hedef Konum

- **Şehir:** San Francisco, California, ABD
- **Mahalleler (seçilebilir 4 adet):**
  - Mission District
  - Castro
  - Haight-Ashbury
  - Noe Valley
- **Seçim mantığı:** Bu 4 mahalle birbirinden farklı sokak karakterine sahiptir. Mission düzensiz ve yoğun, Castro ızgara kırılımları içeren, Haight-Ashbury park kenarı nedeniyle organik, Noe Valley tepelik yapısıyla dead-end sokaklar barındırır. Bu çeşitlilik PageRank sonuçlarını karşılaştırmalı sunmak için idealdir.

---

## 3. Teknik Mimari

### Çıktı Formatı
Tek dosya Jupyter Notebook: `pagerank_trafik.ipynb`

### Kullanılan Kütüphaneler
| Kütüphane | Amaç |
|-----------|-------|
| `osmnx` | OpenStreetMap'ten gerçek yol ağı verisi çekme |
| `networkx` | Graf oluşturma ve PageRank hesaplama |
| `matplotlib` | Soyut graf görselleştirme (akademik katman) |
| `folium` | Gerçek harita üzerine PageRank bindirme |
| `ipywidgets` | Mahalle seçimi için interaktif dropdown |

### Proje Dosya Yapısı
```
📁 proje/
  📓 pagerank_trafik.ipynb   ← ana dosya
  📄 requirements.txt
  📄 README.md
  📁 data/                   ← offline mod için .graphml dosyaları
  📁 output/                 ← üretilen harita HTML dosyaları
```

---

## 4. Notebook Akışı (6 Bölüm)

### Bölüm 1 — Mahalle Seçimi
`ipywidgets.Dropdown` ile 4 mahalle listelenir. Seçim değiştiğinde sonraki hücreler tetiklenir.

```python
MAHALLELER = {
    "Mission District": "Mission District, San Francisco, CA, USA",
    "Castro":           "Castro, San Francisco, CA, USA",
    "Haight-Ashbury":   "Haight-Ashbury, San Francisco, CA, USA",
    "Noe Valley":       "Noe Valley, San Francisco, CA, USA",
}
```

### Bölüm 2 — Veri Çekme
```python
import osmnx as ox
G = ox.graph_from_place(secilen_mahalle, network_type="drive")
```
- `network_type="drive"`: Sadece araç trafiğine açık yollar dahil edilir.
- Graf doğrudan NetworkX `DiGraph` olarak döner (yönlü kenarlar, tek yönlü sokaklar dahil).
- Offline mod: İlk çalıştırmada `ox.save_graphml()` ile `data/<mahalle>.graphml` kaydedilir. Sonraki çalıştırmalarda dosya varsa internete bağlanmadan `ox.load_graphml()` ile yüklenir.

### Bölüm 3 — PageRank Hesaplama
```python
import networkx as nx
pagerank_scores = nx.pagerank(G, alpha=0.85, max_iter=100, tol=1e-6)
```
- **alpha=0.85**: Google'ın orijinal damping factor değeri. Sunum sırasında bu değer değiştirilerek algoritmanın davranışı canlı gözlemlenebilir.
- Sonuç: her düğüm için 0–1 arası skor.

### Bölüm 4 — Matplotlib Görselleştirme
- Düğüm rengi: PageRank skoruna göre renk haritası (yeşil → sarı → kırmızı).
- Düğüm boyutu: PageRank skoru ile orantılı.
- Kenar opaklığı: Düşük tutulur, düğümler ön plana çıkar.
- Başlık: Seçilen mahalle adı ve toplam düğüm/kenar sayısı.

### Bölüm 5 — Folium Harita
- Temel harita: OpenStreetMap tile'ları, mahalle merkezine odaklanmış.
- Her kavşak için `folium.CircleMarker`: yarıçap ve renk PageRank skoru ile orantılı.
- Top-10 kavşak için `folium.Popup`: kavşak koordinatları ve skor gösterilir.
- Çıktı: `output/pagerank_<mahalle>.html` — çift tıkla tarayıcıda açılır.

### Bölüm 6 — Analiz Çıktısı
- En yüksek PageRank skoruna sahip 10 kavşak tablo olarak listelenir.
- Kısa yorum: "Bu kavşaklar neden kritik?" sorusuna algoritma perspektifinden yanıt.

---

## 5. Hata Yönetimi

| Senaryo | Çözüm |
|---------|-------|
| İnternet bağlantısı yok | `data/` klasöründe önceden kaydedilmiş `.graphml` dosyası yüklenir |
| OSMnx mahalle adını tanımıyor | Tüm mahalle sorguları önceden test edilmiş, dropdown yalnızca doğrulanmış adları gösterir |
| Graf çok büyük (yavaş render) | Düğüm sayısı kontrolü yapılır; 2000+ düğümde kullanıcı uyarılır |

---

## 6. Kurulum

```bash
pip install -r requirements.txt
jupyter notebook pagerank_trafik.ipynb
```

**requirements.txt:**
```
osmnx
networkx
matplotlib
folium
ipywidgets
jupyter
```

---

## 7. Sunum Senaryosu

1. Notebook açık, Bölüm 1'de mahalle seçili (örn. Mission District).
2. "PageRank nedir?" açıklandıktan sonra Bölüm 3 çalıştırılır — algoritma canlı çalışıyor.
3. `alpha` değeri 0.85'ten 0.5'e değiştirilir, fark gösterilir.
4. Bölüm 4: Soyut graf görselleştirmesi — akademik anlatım.
5. Bölüm 5: Folium haritası tarayıcıda açılır — "Bu kırmızı nokta en kritik kavşak."
6. Farklı mahalle seçilerek karşılaştırma yapılır.

---

## 8. Kapsam Dışı

- Gerçek zamanlı trafik verisi entegrasyonu
- Makine öğrenmesi veya tahmin modelleri
- Mobil uygulama veya web deploy
- Kullanıcı hesabı / veritabanı
