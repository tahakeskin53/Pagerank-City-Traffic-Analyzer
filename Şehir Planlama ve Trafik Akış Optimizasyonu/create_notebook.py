"""
create_notebook.py
Çalıştır: python create_notebook.py
Çıktı:    pagerank_trafik.ipynb
"""

import nbformat as nbf

nb = nbf.v4.new_notebook()
nb.metadata["kernelspec"] = {
    "display_name": "Python 3",
    "language": "python",
    "name": "python3",
}
nb.metadata["language_info"] = {"name": "python", "version": "3.10.0"}

cells = []

# ── BAŞLIK ──────────────────────────────────────────────────────────────────
cells.append(nbf.v4.new_markdown_cell("""# 🗺️ PageRank Tabanlı Şehir Trafik Analizi
## San Francisco Yol Ağı Üzerinde PageRank Görselleştirmesi

**Amaç:** Şehir kavşaklarını düğüm, yolları kenar olarak modelleyerek
PageRank algoritmasının en kritik kavşakları nasıl belirlediğini göstermek.

> 💡 **Sunum notu:** PageRank, web sayfalarının önemini ölçmek için Google
> tarafından geliştirilen algoritmadır. Burada aynı mantığı şehir yol ağına uyguluyoruz.
> Çok sayıda yolun kesiştiği kavşaklar yüksek PageRank skoru alır.
"""))

# ── IMPORTS ─────────────────────────────────────────────────────────────────
cells.append(nbf.v4.new_code_cell("""\
import os
import warnings
warnings.filterwarnings("ignore")

import osmnx as ox
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import folium
import ipywidgets as widgets
from IPython.display import display, HTML
import numpy as np

# Klasörleri oluştur
os.makedirs("data", exist_ok=True)
os.makedirs("output", exist_ok=True)

print("✅ Tüm kütüphaneler yüklendi.")
"""))

# ── BÖLÜM 1: MAHALlE SEÇİMİ ────────────────────────────────────────────────
cells.append(nbf.v4.new_markdown_cell("""---
## 📍 Bölüm 1 — Mahalle Seçimi

Aşağıdaki dropdown'dan analiz yapmak istediğin mahalleyi seç.
Her mahallenin sokak karakteri farklıdır — PageRank sonuçları da farklılaşacak.
"""))

cells.append(nbf.v4.new_code_cell("""\
MAHALLELER = {
    "Mission District": "Mission District, San Francisco, CA, USA",
    "Castro":           "Castro, San Francisco, CA, USA",
    "Haight-Ashbury":   "Haight-Ashbury, San Francisco, CA, USA",
    "Noe Valley":       "Noe Valley, San Francisco, CA, USA",
}

mahalle_widget = widgets.Dropdown(
    options=list(MAHALLELER.keys()),
    value="Mission District",
    description="Mahalle:",
    style={"description_width": "initial"},
    layout=widgets.Layout(width="300px"),
)

display(mahalle_widget)
print("⬆️  Mahalleyi seçtikten sonra aşağıdaki hücreleri sırayla çalıştır.")
"""))

# ── BÖLÜM 2: VERİ ÇEKME ─────────────────────────────────────────────────────
cells.append(nbf.v4.new_markdown_cell("""---
## 🌐 Bölüm 2 — Yol Ağı Verisi Çekme

Seçilen mahallenin gerçek yol ağı OpenStreetMap'ten indirilir.
**İlk çalıştırma** internet gerektirir (~10-30 saniye).
**Sonraki çalıştırmalar** disk cache kullanır, internet gerekmez.
"""))

cells.append(nbf.v4.new_code_cell("""\
secilen_mahalle_adi = mahalle_widget.value
secilen_mahalle_sorgu = MAHALLELER[secilen_mahalle_adi]
cache_dosya = f"data/{secilen_mahalle_adi.replace(' ', '')}.graphml"

if os.path.exists(cache_dosya):
    print(f"📂 Cache bulundu: {cache_dosya} — diskten yükleniyor...")
    G = ox.load_graphml(cache_dosya)
else:
    print(f"🌐 İnternet'ten indiriliyor: {secilen_mahalle_sorgu}")
    G = ox.graph_from_place(secilen_mahalle_sorgu, network_type="drive")
    ox.save_graphml(G, cache_dosya)
    print(f"💾 Cache'e kaydedildi: {cache_dosya}")

node_count = len(G.nodes)
edge_count = len(G.edges)

print(f"\\n✅ Graf yüklendi: {secilen_mahalle_adi}")
print(f"   Düğüm (kavşak) sayısı : {node_count}")
print(f"   Kenar (yol) sayısı    : {edge_count}")

if node_count > 2000:
    print(f"\\n⚠️  Uyarı: {node_count} düğüm — görselleştirme yavaş olabilir.")
"""))

# ── BÖLÜM 3: PAGERANK ───────────────────────────────────────────────────────
cells.append(nbf.v4.new_markdown_cell("""---
## 📐 Bölüm 3 — PageRank Hesaplama

PageRank algoritması şehir yol ağına uygulanıyor.

**Parametreler:**
- `alpha = 0.85` → Damping factor. Google'ın orijinal değeri.
  *Bir sürücünün mevcut kavşaktan rastgele bir yola geçme olasılığı: %85*
- `max_iter = 100` → Maksimum iterasyon sayısı (yakınsama için)
- `tol = 1e-6` → Yakınsama toleransı

> 💡 **Dene:** `alpha` değerini 0.5 yapıp hücreyi yeniden çalıştır.
> Sonuçların nasıl değiştiğini gözlemle.
"""))

cells.append(nbf.v4.new_code_cell("""\
# ── Parametre (değiştirilebilir) ──────────────────────────────
alpha = 0.85
max_iter = 100
tol = 1e-6
# ──────────────────────────────────────────────────────────────

pagerank_scores = nx.pagerank(G, alpha=alpha, max_iter=max_iter, tol=tol)

scores = list(pagerank_scores.values())
print(f"✅ PageRank hesaplandı (alpha={alpha})")
print(f"   Min skor : {min(scores):.6f}")
print(f"   Max skor : {max(scores):.6f}")
print(f"   Ort skor : {np.mean(scores):.6f}")
print(f"   Toplam   : {sum(scores):.4f}  (her zaman ~1.0 olmalı)")
"""))

# ── BÖLÜM 4: MATPLOTLİB ─────────────────────────────────────────────────────
cells.append(nbf.v4.new_markdown_cell("""---
## 🎨 Bölüm 4 — Akademik Graf Görselleştirmesi

PageRank skorları renk ve boyutla kodlanmış soyut graf görünümü.
**Kırmızı/büyük** düğümler = yüksek PageRank = kritik kavşaklar.
"""))

cells.append(nbf.v4.new_code_cell("""\
fig, ax = plt.subplots(figsize=(12, 10))

# Düğüm renklerini ve boyutlarını PageRank'e göre hesapla
node_list   = list(G.nodes())
score_array = np.array([pagerank_scores[n] for n in node_list])
score_norm  = (score_array - score_array.min()) / (score_array.max() - score_array.min() + 1e-12)

colormap   = cm.get_cmap("RdYlGn_r")          # yeşil→sarı→kırmızı
node_colors = [colormap(s) for s in score_norm]
node_sizes  = 20 + score_norm * 200            # 20–220 piksel arası

# Graf pozisyonları (coğrafi koordinatlar)
pos = {node: (data["x"], data["y"]) for node, data in G.nodes(data=True)}

nx.draw_networkx_edges(
    G, pos, ax=ax,
    edge_color="gray", alpha=0.25, width=0.5, arrows=False
)
nx.draw_networkx_nodes(
    G, pos, ax=ax,
    nodelist=node_list,
    node_color=node_colors,
    node_size=node_sizes,
)

# Renk çubuğu (colorbar)
sm = plt.cm.ScalarMappable(cmap=colormap, norm=plt.Normalize(vmin=0, vmax=1))
sm.set_array([])
cbar = fig.colorbar(sm, ax=ax, shrink=0.6, pad=0.02)
cbar.set_label("PageRank Skoru (normalleştirilmiş)", fontsize=11)

ax.set_title(
    f"PageRank — {secilen_mahalle_adi}\\n"
    f"{node_count} kavşak · {edge_count} yol segmenti · α={alpha}",
    fontsize=14, fontweight="bold"
)
ax.axis("off")
plt.tight_layout()
plt.show()
print("✅ Matplotlib görselleştirmesi tamamlandı.")
"""))

# ── BÖLÜM 5: FOLİUM HARİTA ──────────────────────────────────────────────────
cells.append(nbf.v4.new_markdown_cell("""---
## 🗺️ Bölüm 5 — İnteraktif Harita (Folium)

Aynı PageRank sonuçları gerçek San Francisco haritasına bindiriliyor.
Çıktı dosyası `output/` klasörüne kaydedilir — çift tıkla tarayıcıda aç.
"""))

cells.append(nbf.v4.new_code_cell("""\
def pagerank_renk(normalized_score):
    \"\"\"0-1 arası skoru yeşil→sarı→kırmızı hex rengine çevirir.\"\"\"
    r = int(255 * normalized_score)
    g = int(255 * (1 - normalized_score))
    return f"#{r:02x}{g:02x}00"

# Harita merkezi (mahallenin coğrafi ortası)
node_data  = dict(G.nodes(data=True))
lat_values = [d["y"] for d in node_data.values()]
lon_values = [d["x"] for d in node_data.values()]
merkez_lat = np.mean(lat_values)
merkez_lon = np.mean(lon_values)

harita = folium.Map(location=[merkez_lat, merkez_lon], zoom_start=15,
                    tiles="OpenStreetMap")

# Yol kenarlarını çiz
for u, v, data in G.edges(data=True):
    if "geometry" in data:
        coords = [(p[1], p[0]) for p in data["geometry"].coords]
    else:
        coords = [
            (node_data[u]["y"], node_data[u]["x"]),
            (node_data[v]["y"], node_data[v]["x"]),
        ]
    folium.PolyLine(coords, color="#888888", weight=1.5, opacity=0.4).add_to(harita)

# Kavşakları PageRank skoruyla çiz
top10_esik = sorted(pagerank_scores.values(), reverse=True)[9]

for node, score in pagerank_scores.items():
    norm  = (score - min(scores)) / (max(scores) - min(scores) + 1e-12)
    renk  = pagerank_renk(norm)
    yaricap = 4 + norm * 12
    popup_text = (
        f"<b>PageRank Skoru:</b> {score:.6f}<br>"
        f"<b>Konum:</b> {node_data[node]['y']:.5f}, {node_data[node]['x']:.5f}"
    )
    if score >= top10_esik:
        popup_text = "⭐ <b>TOP 10 KAVŞAK</b><br>" + popup_text
        yaricap += 4

    folium.CircleMarker(
        location=[node_data[node]["y"], node_data[node]["x"]],
        radius=yaricap,
        color=renk,
        fill=True,
        fill_color=renk,
        fill_opacity=0.8,
        popup=folium.Popup(popup_text, max_width=250),
    ).add_to(harita)

# Efsane (legend)
legend_html = \"\"\"
<div style="position:fixed;bottom:30px;left:30px;z-index:1000;
            background:white;padding:12px;border-radius:8px;
            border:2px solid #aaa;font-size:13px;line-height:1.8;">
  <b>PageRank Skoru</b><br>
  <span style="color:#ff0000">● Yüksek</span> — Kritik kavşak<br>
  <span style="color:#ffaa00">● Orta</span>   — Bağlantı noktası<br>
  <span style="color:#00ff00">● Düşük</span>  — Yerel yol<br>
  ⭐ = Top 10 kavşak
</div>
\"\"\"
harita.get_root().html.add_child(folium.Element(legend_html))

# Kaydet
mahalle_dosya_adi = secilen_mahalle_adi.replace(" ", "")
cikti_dosya = f"output/pagerank_{mahalle_dosya_adi}.html"
harita.save(cikti_dosya)

display(HTML(f'<a href="{cikti_dosya}" target="_blank">🗺️ Haritayı aç: {cikti_dosya}</a>'))
print(f"\\n✅ Folium haritası kaydedildi: {cikti_dosya}")
"""))

# ── BÖLÜM 6: ANALİZ ÇIKTISI ─────────────────────────────────────────────────
cells.append(nbf.v4.new_markdown_cell("""---
## 📊 Bölüm 6 — Analiz Çıktısı

En yüksek PageRank skoruna sahip 10 kavşak ve algoritmik yorum.
"""))

cells.append(nbf.v4.new_code_cell("""\
# Top-10 kavşakları sırala
top10 = sorted(pagerank_scores.items(), key=lambda x: x[1], reverse=True)[:10]

print(f"{'Sıra':<5} {'Düğüm ID':<15} {'PageRank Skoru':<18} {'Konum (lat, lon)'}")
print("-" * 70)
for i, (node, score) in enumerate(top10, 1):
    lat = node_data[node]["y"]
    lon = node_data[node]["x"]
    print(f"{i:<5} {str(node):<15} {score:<18.8f} ({lat:.5f}, {lon:.5f})")

print(f\"\"\"
──────────────────────────────────────────────────────────────────────
🔍 Algoritma Yorumu — {secilen_mahalle_adi}

Bu kavşaklar neden kritik?

PageRank algoritması, bir kavşağa gelen yol sayısını ve o yollara ulaşan
diğer kavşakların önemini birlikte değerlendirir. Tıpkı web'de çok sayıda
önemli sayfanın link verdiği bir sayfanın yüksek PageRank alması gibi,
çok sayıda önemli yolun kesiştiği kavşaklar da yüksek skor alır.

• Damping factor (α={alpha}): Her iterasyonda sürücünün %{int(alpha*100)}'lük
  olasılıkla mevcut kavşaktan rastgele bir yola geçtiği varsayılır.
  Kalan %{int((1-alpha)*100)}'lik olasılıkla ağın herhangi bir noktasına ışınlanır.

• Yüksek skorlu kavşaklar trafik planlamasında öncelikli genişletme,
  yeni güzergah veya sinyalizasyon noktaları olarak değerlendirilebilir.
\"\"\")
"""))

# ── NOTEBOOK YAZI ───────────────────────────────────────────────────────────
nb.cells = cells

output_path = "pagerank_trafik.ipynb"
with open(output_path, "w", encoding="utf-8") as f:
    nbf.write(nb, f)

print(f"✅ Notebook oluşturuldu: {output_path}")
print(f"   Hücre sayısı: {len(cells)}")
print(f"\nBaşlatmak için:\n  jupyter notebook {output_path}")
