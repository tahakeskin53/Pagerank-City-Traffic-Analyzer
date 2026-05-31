# Temporal Weighted PageRank — Tasarım Belgesi

**Tarih:** 2026-05-31  
**Proje:** Şehir Planlama ve Trafik Akış Optimizasyonu  
**Amaç:** Veri işleme karmaşıklığını artırmak — ağırlıklı ve zamana bağlı PageRank analizi

---

## 1. Motivasyon

Mevcut proje `nx.pagerank(G, alpha=0.85)` ile tüm yolları eşit ağırlıklı kabul ediyor. Gerçekte bir otoyol ile dar bir sokak aynı trafik kapasitesine sahip değil. Bu tasarım:

- OSM'den gerçek kenar özelliklerini çekerek ağırlıklı bir graf kurar
- Sabah rush, akşam rush ve sakin saat olmak üzere 3 zaman diliminde PageRank çalıştırır
- Kritik kavşakların gün içinde nasıl değiştiğini karşılaştırır

---

## 2. Veri Kaynakları

| Kaynak | Veri | Gerçek mi? |
|--------|------|-----------|
| OpenStreetMap (osmnx) | `maxspeed`, `lanes`, `highway` tipi, `length` | Gerçek |
| `ox.add_edge_speeds()` | Eksik `maxspeed` için yol tipine göre default | OSM tabanlı default |
| HCM (Highway Capacity Manual) | Zaman dilimi çarpanları | Literatür kaynağı |

---

## 3. Ön İşleme Pipeline'ı

### 3.1 Kenar Özelliği Çekme

```python
G = ox.add_edge_speeds(G)        # maxspeed eksikleri doldurur
G = ox.add_edge_travel_times(G)  # length/speed → travel_time
```

OSM'den çekilen ham özellikler: `speed_kph`, `lanes`, `highway`, `length`

### 3.2 Eksik Değer İmputation (lanes)

`lanes` özelliği OSM'de çoğu kenarda eksik. Yol tipine göre doldurulan değerler:

| Highway Tipi | Varsayılan lanes |
|---|---|
| motorway | 3 |
| trunk | 2 |
| primary | 2 |
| secondary | 2 |
| tertiary | 1 |
| residential | 1 |
| diğer | 1 |

### 3.3 Normalizasyon

Her özellik min-max normalizasyonu ile [0, 1] aralığına çekilir:

```
norm(x) = (x - x_min) / (x_max - x_min + ε)
```

### 3.4 Composite Ağırlık Formülü

```
w_base = 0.4 × norm(speed_kph) + 0.4 × norm(lanes) + 0.2 × norm(1 / length)
```

- `speed_kph`: yüksek hız → daha fazla trafik kapasitesi
- `lanes`: çok şerit → daha fazla akış
- `1/length`: kısa bağlantılar daha sık kullanılır (ters orantı)

---

## 4. Temporal Weighting (Zaman Dilimi Modeli)

### Zaman Dilimleri

| Dilim | Saat Aralığı | Tanım |
|---|---|---|
| `sabah_rush` | 07:00 – 09:00 | İşe gidiş yoğunluğu |
| `aksam_rush` | 17:00 – 19:00 | İş çıkışı yoğunluğu |
| `sakin` | diğer saatler | Normal akış |

### Yol Tipine Göre Çarpanlar

| Highway Tipi | sabah_rush | aksam_rush | sakin |
|---|---|---|---|
| motorway, trunk | 1.4 | 1.5 | 1.0 |
| primary, secondary | 1.3 | 1.4 | 1.0 |
| tertiary | 1.1 | 1.2 | 1.0 |
| residential, diğer | 0.8 | 0.9 | 1.0 |

**Kaynak:** TRB Highway Capacity Manual (HCM 7th ed.) peak hour factor standartları.

### Final Ağırlık

```
w_final(dilim) = w_base × çarpan(highway_tipi, dilim)
```

---

## 5. PageRank Hesaplama

Her zaman dilimi için ayrı PageRank çalıştırılır:

```python
for dilim in ["sabah_rush", "aksam_rush", "sakin"]:
    nx.set_edge_attributes(G, agirliklar[dilim], "trafik_agirlik")
    pr_sonuclar[dilim] = nx.pagerank(G, alpha=0.85, weight="trafik_agirlik")
```

---

## 6. Analiz Çıktıları

### 6.1 Rank Değişim Tablosu

Her dilim için top-10 kavşak listesi. Sabah kritik olan kavşağın akşam kaçıncı sıraya düştüğü gösterilir.

### 6.2 Dağılım İstatistikleri

Her dilim için PageRank dağılımının `gini katsayısı` hesaplanır:

```
Gini yüksek → trafik birkaç kavşakta toplanmış (tıkanıklık riski yüksek)
Gini düşük  → trafik dağınık (dengeli ağ)
```

### 6.3 Ortak Kritik Kavşaklar

3 dilimin kesişimi: her zaman diliminde top-10'da kalan "daima kritik" kavşaklar ayrıca işaretlenir.

---

## 7. Streamlit UI Değişiklikleri

- Sidebar'a **zaman dilimi radio butonu** eklenir (Sabah Rush / Akşam Rush / Sakin Saat)
- Seçilen dilime göre folium haritası yenilenir
- Metrik kartlara `Gini Katsayısı` eklenir
- Yeni sekme: `📊 Karşılaştırma` — 3 dilimi yan yana gösterir

---

## 8. Dosya Değişiklikleri

| Dosya | Değişiklik |
|---|---|
| `app.py` | Preprocessing, temporal weighting, yeni UI bileşenleri |
| `requirements.txt` | Değişiklik yok (tüm kütüphaneler mevcut) |

---

## 9. Rapor Bölüm Planı

| Bölüm | İçerik |
|---|---|
| Giriş | PageRank + trafik, neden dinamik analiz gerekli |
| Geçmiş Çalışmalar | Son 3 yılda PageRank + trafik üzerine 5 makale |
| Yöntem - Veri | OSM kenar özellikleri tablosu, imputation stratejisi |
| Yöntem - Algoritma | Composite ağırlık formülü, temporal multiplier tablosu |
| Sonuçlar | 3 dilim karşılaştırma tablosu, rank değişimleri, gini katsayıları |

---

## 10. Kapsam Dışı

- Gerçek zamanlı API entegrasyonu (TomTom, HERE)
- Makine öğrenmesi ile trafik tahmini
- Pedestrian / bisiklet ağı analizi
