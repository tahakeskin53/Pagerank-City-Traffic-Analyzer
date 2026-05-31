import streamlit as st
import osmnx as ox
import networkx as nx
import folium
import numpy as np
import os
import warnings
warnings.filterwarnings("ignore")
from trafik_analiz import compute_all_slots, gini_coefficient, compute_rank_table

# ── SAYFA YAPLANDIRMASI ──────────────────────────────────────────────────────
st.set_page_config(
    page_title="PageRank Trafik Analizi",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── ÖZEL STILLER ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.main-header {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    padding: 2rem 2.5rem;
    border-radius: 16px;
    margin-bottom: 1.5rem;
    color: white;
}
.main-header h1 { font-size: 2rem; font-weight: 700; margin: 0 0 0.3rem 0; }
.main-header p  { font-size: 1rem; margin: 0; opacity: 0.8; }

.metric-card {
    background: linear-gradient(135deg, #1e3a5f, #16213e);
    border-radius: 12px;
    padding: 1.2rem 1.5rem;
    color: white;
    text-align: center;
    border: 1px solid rgba(255,255,255,0.1);
}
.metric-card .label { font-size: 0.8rem; opacity: 0.7; text-transform: uppercase; letter-spacing: 1px; }
.metric-card .value { font-size: 1.8rem; font-weight: 700; margin-top: 0.3rem; }
.metric-card .sub   { font-size: 0.75rem; opacity: 0.6; margin-top: 0.2rem; }

.info-box {
    background: rgba(99, 179, 237, 0.1);
    border-left: 4px solid #63b3ed;
    border-radius: 8px;
    padding: 1rem 1.2rem;
    margin: 1rem 0;
    color: #bee3f8;
    font-size: 0.9rem;
}

.top10-row {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 0.6rem 1rem;
    border-radius: 8px;
    margin-bottom: 0.4rem;
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.06);
    color: white;
}
.top10-rank { font-weight: 700; font-size: 1.1rem; width: 2rem; }
.top10-bar-wrap { flex: 1; background: rgba(255,255,255,0.1); border-radius: 4px; height: 8px; }
.top10-bar { height: 8px; border-radius: 4px; }
.top10-score { font-size: 0.8rem; opacity: 0.7; width: 8rem; text-align: right; }

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0d1117 0%, #161b22 100%);
}
[data-testid="stSidebar"] * { color: #e6edf3 !important; }

div[data-testid="stButton"] button {
    background: linear-gradient(135deg, #0f3460, #533483);
    color: white;
    border: none;
    border-radius: 10px;
    font-weight: 600;
    font-size: 1rem;
    padding: 0.6rem 0;
    width: 100%;
    cursor: pointer;
    transition: opacity 0.2s;
}
div[data-testid="stButton"] button:hover { opacity: 0.85; }

.stSlider > div > div > div { background: #0f3460 !important; }
</style>
""", unsafe_allow_html=True)

# ── VERİ ─────────────────────────────────────────────────────────────────────
MAHALLELER = {
    "Mission District": (37.7599, -122.4148),
    "Castro":           (37.7609, -122.4350),
    "Haight-Ashbury":   (37.7692, -122.4481),
    "Noe Valley":       (37.7502, -122.4337),
    "Brisbane":         (37.6797, -122.3999),
}
DIST = 800  # metre yarıçap

os.makedirs("data",   exist_ok=True)
os.makedirs("output", exist_ok=True)

# ── YARDIMCI FONKSİYONLAR ────────────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def graf_yukle(mahalle_adi: str, koordinat: tuple):
    cache = f"data/{mahalle_adi.replace(' ', '')}.graphml"
    if os.path.exists(cache):
        try:
            G = ox.load_graphml(cache)
            # Gerçek OSMnx verisini doğrula — sahte cache dosyasını reddet
            sample = list(G.nodes(data=True))[0][1]
            if "osmid" not in sample and "x" not in sample:
                raise ValueError("Geçersiz cache")
        except Exception:
            os.remove(cache)
            G = ox.graph_from_point(koordinat, dist=DIST, network_type="drive")
            ox.save_graphml(G, cache)
    else:
        G = ox.graph_from_point(koordinat, dist=DIST, network_type="drive")
        ox.save_graphml(G, cache)
    return G

@st.cache_data(show_spinner=False)
def tum_slotlar_hesapla(_G, mahalle_adi: str, alpha: float):
    return compute_all_slots(_G, alpha=alpha)

def skor_renk(norm: float) -> str:
    r = int(255 * norm)
    g = int(255 * (1 - norm))
    return f"#{r:02x}{g:02x}00"

def folium_harita_olustur(G, pr_scores: dict) -> str:
    node_data = dict(G.nodes(data=True))
    scores    = list(pr_scores.values())
    mn, mx    = min(scores), max(scores)
    denom     = mx - mn + 1e-12

    lat_vals = [d["y"] for d in node_data.values()]
    lon_vals = [d["x"] for d in node_data.values()]

    harita = folium.Map(
        location=[np.mean(lat_vals), np.mean(lon_vals)],
        zoom_start=15,
        tiles="CartoDB dark_matter",
    )

    # Top-10 skor eşiği
    top10_list_sorted = sorted(pr_scores.items(), key=lambda x: x[1], reverse=True)[:10]
    top10_nodes = {n: i+1 for i, (n, _) in enumerate(top10_list_sorted)}

    # Yol kenarları — belirgin çizgi
    for u, v, data in G.edges(data=True):
        if "geometry" in data:
            coords = [(p[1], p[0]) for p in data["geometry"].coords]
        else:
            coords = [
                (node_data[u]["y"], node_data[u]["x"]),
                (node_data[v]["y"], node_data[v]["x"]),
            ]
        folium.PolyLine(
            coords, color="#5b8dd9", weight=2.2, opacity=0.75
        ).add_to(harita)

    # Genel kavşak noktaları (top 10 hariç)
    for node, score in pr_scores.items():
        if node in top10_nodes:
            continue
        norm  = (score - mn) / denom
        renk  = skor_renk(norm)
        popup = (
            f"<div style='font-family:Inter,sans-serif;font-size:13px;padding:6px;'>"
            f"<b>PageRank:</b> {score:.7f}<br>"
            f"<b>Konum:</b> {node_data[node]['y']:.5f}, {node_data[node]['x']:.5f}"
            f"</div>"
        )
        folium.CircleMarker(
            location=[node_data[node]["y"], node_data[node]["x"]],
            radius=3 + norm * 10,
            color="transparent",
            fill=True,
            fill_color=renk,
            fill_opacity=0.85,
            popup=folium.Popup(popup, max_width=220),
            tooltip=f"PR: {score:.6f}",
        ).add_to(harita)

    # Ping animasyonu CSS — bir kez eklenir
    ping_css = """
    <style>
    @keyframes ping {
        0%   { transform: scale(1);   opacity: 0.9; }
        70%  { transform: scale(2.8); opacity: 0.3; }
        100% { transform: scale(3.2); opacity: 0;   }
    }
    @keyframes pulse-core {
        0%, 100% { transform: scale(1);    box-shadow: 0 0 0   0 rgba(255,80,80,0.6); }
        50%       { transform: scale(1.12); box-shadow: 0 0 10px 4px rgba(255,80,80,0.4); }
    }
    .ping-ring {
        position: absolute;
        width: 28px; height: 28px;
        border-radius: 50%;
        background: rgba(255, 80, 80, 0.45);
        top: -14px; left: -14px;
        animation: ping 1.6s ease-out infinite;
    }
    .ping-ring-2 {
        position: absolute;
        width: 28px; height: 28px;
        border-radius: 50%;
        background: rgba(255, 80, 80, 0.25);
        top: -14px; left: -14px;
        animation: ping 1.6s ease-out 0.5s infinite;
    }
    .ping-core {
        position: absolute;
        width: 14px; height: 14px;
        border-radius: 50%;
        background: #ff3232;
        border: 2.5px solid #ffffff;
        top: -7px; left: -7px;
        z-index: 10;
        animation: pulse-core 1.6s ease-in-out infinite;
    }
    .ping-label {
        position: absolute;
        top: -30px; left: -12px;
        background: rgba(0,0,0,0.82);
        color: #fff;
        font-size: 11px;
        font-weight: 700;
        font-family: Inter, sans-serif;
        padding: 2px 6px;
        border-radius: 6px;
        white-space: nowrap;
        border: 1px solid rgba(255,80,80,0.6);
        z-index: 11;
    }
    </style>
    """
    harita.get_root().html.add_child(folium.Element(ping_css))

    # Top-10 ping işaretçileri
    for node, rank in top10_nodes.items():
        score = pr_scores[node]
        lat   = node_data[node]["y"]
        lon   = node_data[node]["x"]
        medal = ["🥇","🥈","🥉"][rank-1] if rank <= 3 else f"#{rank}"

        ping_html = f"""
        <div style="position:relative;">
          <div class="ping-ring"></div>
          <div class="ping-ring-2"></div>
          <div class="ping-core"></div>
          <div class="ping-label">{medal}</div>
        </div>
        """

        popup_html = (
            f"<div style='font-family:Inter,sans-serif;font-size:13px;"
            f"padding:10px;min-width:180px;'>"
            f"<div style='font-size:1.4rem;margin-bottom:6px;'>{medal} <b>TOP {rank} KAVŞAK</b></div>"
            f"<div style='color:#ff4444;font-size:1rem;font-weight:700;margin-bottom:8px;'>"
            f"PageRank: {score:.7f}</div>"
            f"<div style='font-size:0.8rem;color:#888;'>"
            f"{lat:.5f}, {lon:.5f}</div>"
            f"</div>"
        )

        folium.Marker(
            location=[lat, lon],
            icon=folium.DivIcon(
                html=ping_html,
                icon_size=(0, 0),
                icon_anchor=(0, 0),
            ),
            popup=folium.Popup(popup_html, max_width=250),
            tooltip=f"{medal} Kritik kavşak — PR: {score:.6f}",
        ).add_to(harita)

    # ── Leaflet map değişken adı (flyTo için gerekli) ──
    map_var = harita.get_name()

    # ── Top 10 panel satırları ──
    top10_rows_html = ""

    for node, rank in top10_nodes.items():
        score  = pr_scores[node]
        lat    = node_data[node]["y"]
        lon    = node_data[node]["x"]
        norm   = (score - mn) / denom
        bar_w  = int(norm * 100)
        r_c    = int(255 * norm); g_c = int(255 * (1 - norm))
        bar_cl = f"#{r_c:02x}{g_c:02x}00"
        medal  = ["🥇","🥈","🥉"][rank-1] if rank <= 3 else f"#{rank}"

        top10_rows_html += f"""
        <div onclick="flyToKavsak({lat},{lon},{rank})"
             onmouseover="this.style.background='rgba(255,255,255,0.07)'"
             onmouseout="this.style.background='transparent'"
             style="display:flex;align-items:center;gap:12px;
                    padding:10px 12px;border-radius:8px;margin-bottom:6px;
                    cursor:pointer;transition:background 0.18s;
                    border:1px solid rgba(255,255,255,0.08);">
          <div style="font-size:1.3rem;width:30px;text-align:center;flex-shrink:0;">{medal}</div>
          <div style="flex:1;min-width:0;">
            <div style="font-size:0.82rem;color:#bbb;margin-bottom:6px;
                        white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
                        letter-spacing:0.3px;">
              {lat:.4f}, {lon:.4f}
            </div>
            <div style="background:rgba(255,255,255,0.12);border-radius:4px;height:7px;">
              <div style="width:{bar_w}%;height:7px;border-radius:4px;background:{bar_cl};"></div>
            </div>
          </div>
          <div style="font-size:0.82rem;color:#e0e0e0;font-weight:600;
                      white-space:nowrap;flex-shrink:0;letter-spacing:0.3px;">
            {score:.6f}
          </div>
        </div>"""

    # ── Efsane ──
    legend_html = """
    <div style="position:absolute;bottom:25px;left:10px;z-index:1000;
                background:rgba(13,17,23,0.92);padding:12px 16px;
                border-radius:12px;border:1px solid rgba(255,255,255,0.13);
                font-family:Inter,sans-serif;font-size:11.5px;color:#e6edf3;line-height:2;">
      <b style="font-size:12.5px;">PageRank Skoru</b><br>
      <span style="color:#ff4444;">●</span> Yüksek — Kritik kavşak<br>
      <span style="color:#ffaa00;">●</span> Orta — Bağlantı noktası<br>
      <span style="color:#44ff44;">●</span> Düşük — Yerel yol<br>
      <span style="color:#ff3232;font-size:13px;">⊙</span> Ping — Top 10 kavşak
    </div>"""

    # ── Top 10 panel + flyTo script (aynı iframe içinde) ──
    panel_and_script = f"""
    <div id="top10-panel" style="
        position:absolute;top:10px;right:10px;width:300px;
        background:rgba(13,17,23,0.95);border-radius:14px;
        border:1px solid rgba(255,255,255,0.14);
        font-family:Inter,sans-serif;color:#e6edf3;
        z-index:1000;padding:16px;
        max-height:88%;overflow-y:auto;
        box-shadow:0 8px 32px rgba(0,0,0,0.6);">
      <div style="font-size:15px;font-weight:700;margin-bottom:12px;
                  border-bottom:1px solid rgba(255,255,255,0.12);padding-bottom:10px;">
        🏆 Top 10 Kritik Kavşak
        <div style="font-size:11px;font-weight:400;color:#888;margin-top:4px;">
          Tıkla → haritada göster
        </div>
      </div>
      {top10_rows_html}
    </div>

    <script>
    function flyToKavsak(lat, lon, rank) {{
        var map = window['{map_var}'];
        if (!map) return;

        // Haritayı o konuma uçur
        map.flyTo([lat, lon], 18, {{animate: true, duration: 1.1}});

        // Kırmızı parlayan halka efekti
        var outer = L.circle([lat, lon], {{
            color: '#ff3232', fillColor: '#ff5555',
            fillOpacity: 0.35, radius: 50, weight: 2.5
        }}).addTo(map);

        var inner = L.circle([lat, lon], {{
            color: '#ffffff', fillColor: '#ff3232',
            fillOpacity: 0.8, radius: 12, weight: 2
        }}).addTo(map);

        // 2.5 saniye sonra efekti kaldır
        setTimeout(function() {{
            map.removeLayer(outer);
            map.removeLayer(inner);
        }}, 2500);
    }}
    </script>
    """

    harita.get_root().html.add_child(folium.Element(legend_html))
    harita.get_root().html.add_child(folium.Element(panel_and_script))
    return harita._repr_html_()

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🗺️ PageRank Analizi")
    st.markdown("---")

    secilen_adi = st.selectbox(
        "Mahalle Seç",
        options=list(MAHALLELER.keys()),
        help="San Francisco'dan 4 farklı mahalle",
    )

    st.markdown("---")

    alpha = st.slider(
        "Damping Factor (α)",
        min_value=0.50,
        max_value=0.99,
        value=0.85,
        step=0.01,
        help="Google'ın orijinal değeri: 0.85\nDüşürünce dağılım düzleşir, yükseltince uç değerler belirginleşir.",
    )

    st.markdown(
        f"<div class='info-box'>α = <b>{alpha}</b><br>"
        f"Sürücünün komşu kavşağa geçme (yolu takip etme) olasılığı: <b>%{int(alpha*100)}</b><br>"
        f"Rastgele ışınlanma olasılığı: <b>%{round((1-alpha)*100, 1)}</b></div>",
        unsafe_allow_html=True,
    )

    st.markdown("---")
    secilen_dilim = st.radio(
        "Zaman Dilimi",
        options=["sabah_rush", "aksam_rush", "sakin"],
        format_func=lambda x: {
            "sabah_rush": "🌅 Sabah Rush (07-09)",
            "aksam_rush": "🌆 Akşam Rush (17-19)",
            "sakin":      "🌙 Sakin Saat",
        }[x],
    )
    st.markdown(
        "<div style='font-size:0.78rem;opacity:0.5;margin-top:0.3rem;'>"
        "Çarpanlar: TRB Highway Capacity Manual</div>",
        unsafe_allow_html=True,
    )
    st.markdown("---")
    analiz_btn = st.button("🔍  Analiz Et", use_container_width=True)
    if analiz_btn:
        st.session_state["analiz_yapildi"] = True

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        "<div style='font-size:0.75rem;opacity:0.4;text-align:center;'>"
        "Veri: OpenStreetMap · NetworkX PageRank</div>",
        unsafe_allow_html=True,
    )

# ── ANA ALAN ──────────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
  <h1>🗺️ PageRank Tabanlı Trafik Analizi</h1>
  <p>San Francisco yol ağında en kritik kavşakları belirle — Google'ın PageRank algoritmasıyla</p>
</div>
""", unsafe_allow_html=True)

if not st.session_state.get("analiz_yapildi", False):
    st.markdown("""
    <div style="text-align:center;padding:4rem 2rem;color:rgba(255,255,255,0.3);">
      <div style="font-size:5rem;">🏙️</div>
      <div style="font-size:1.2rem;margin-top:1rem;">Sol panelden mahalle seç ve <b>Analiz Et</b>'e bas</div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ── ANALİZ ───────────────────────────────────────────────────────────────────
secilen_koordinat = MAHALLELER[secilen_adi]

with st.spinner(f"🌐 {secilen_adi} yol ağı yükleniyor..."):
    G = graf_yukle(secilen_adi, secilen_koordinat)

with st.spinner("⚙️ 3 zaman dilimi için PageRank hesaplanıyor..."):
    pr_sonuclar = tum_slotlar_hesapla(G, secilen_adi, alpha)
pr = pr_sonuclar[secilen_dilim]

scores    = list(pr.values())
node_data = dict(G.nodes(data=True))
gini = gini_coefficient(pr)

# ── METRİKLER ────────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown(f"""
    <div class="metric-card">
      <div class="label">Toplam Kavşak</div>
      <div class="value">{len(G.nodes):,}</div>
      <div class="sub">düğüm</div>
    </div>""", unsafe_allow_html=True)

with c2:
    st.markdown(f"""
    <div class="metric-card">
      <div class="label">Toplam Yol</div>
      <div class="value">{len(G.edges):,}</div>
      <div class="sub">kenar</div>
    </div>""", unsafe_allow_html=True)

with c3:
    st.markdown(f"""
    <div class="metric-card">
      <div class="label">Max PageRank</div>
      <div class="value">{max(scores):.5f}</div>
      <div class="sub">en kritik kavşak</div>
    </div>""", unsafe_allow_html=True)

with c4:
    st.markdown(f"""
    <div class="metric-card">
      <div class="label">Gini Katsayısı</div>
      <div class="value">{gini:.3f}</div>
      <div class="sub">trafik yoğunlaşması</div>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── HARİTA (Top 10 panel içinde gömülü) ──────────────────────────────────────
dilim_etiket = {"sabah_rush": "🌅 Sabah Rush", "aksam_rush": "🌆 Akşam Rush", "sakin": "🌙 Sakin Saat"}

tab_harita, tab_karsilastirma = st.tabs(["🗺️ Harita", "📊 Dilim Karşılaştırması"])

with tab_harita:
    st.markdown(f"### 🗺️ {secilen_adi} — {dilim_etiket[secilen_dilim]}")
    st.markdown(
        "<div style='font-size:0.85rem;opacity:0.6;margin-bottom:0.8rem;'>"
        "Kırmızı/büyük noktalar = kritik kavşaklar · "
        "Sağdaki listeden tıkla → haritada uç · Noktalara tıkla → skor bilgisi</div>",
        unsafe_allow_html=True,
    )
    with st.spinner("🗺️ Harita oluşturuluyor..."):
        harita_html = folium_harita_olustur(G, pr)
    st.components.v1.html(harita_html, height=600, scrolling=False)

with tab_karsilastirma:
    st.markdown("### 📊 Zaman Dilimi Karşılaştırması")
    st.markdown(
        "<div style='font-size:0.85rem;opacity:0.6;margin-bottom:1rem;'>"
        "Top-10 kritik kavşakların 3 zaman dilimindeki sıralama değişimi. "
        "'&gt;10' = o dilimde ilk 10 dışında.</div>",
        unsafe_allow_html=True,
    )

    gcols = st.columns(3)
    for col, dilim in zip(gcols, ["sabah_rush", "aksam_rush", "sakin"]):
        g = gini_coefficient(pr_sonuclar[dilim])
        etiket = dilim_etiket[dilim]
        with col:
            st.markdown(f"""
            <div class="metric-card">
              <div class="label">{etiket}</div>
              <div class="value">{g:.3f}</div>
              <div class="sub">Gini katsayısı</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    rank_df = compute_rank_table(pr_sonuclar)
    rank_df = rank_df.rename(columns={
        "node": "Kavşak ID",
        "sabah_rush": "🌅 Sabah",
        "aksam_rush": "🌆 Akşam",
        "sakin": "🌙 Sakin",
    })
    st.dataframe(
        rank_df,
        use_container_width=True,
        hide_index=True,
    )

    st.markdown(
        "<div style='font-size:0.78rem;opacity:0.5;margin-top:0.5rem;'>"
        "Çarpan kaynağı: TRB Highway Capacity Manual (HCM 7th ed.)</div>",
        unsafe_allow_html=True,
    )

# ── ALGORİTMA AÇIKLAMASI ─────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
with st.expander("📐 Algoritma Açıklaması — Bu kavşaklar neden kritik?"):
    st.markdown(f"""
PageRank algoritması, bir kavşağa gelen yol sayısını ve o yollara ulaşan diğer kavşakların
önemini **birlikte** değerlendirir. Tıpkı web'de çok sayıda önemli sayfanın link verdiği
bir sayfanın yüksek PageRank alması gibi, çok sayıda önemli yolun kesiştiği kavşaklar da
yüksek skor alır.

**Matris formülasyonu:**

$$PR(u) = \\frac{{1-\\alpha}}{{N}} + \\alpha \\sum_{{v \\in B_u}} \\frac{{PR(v)}}{{L(v)}}$$

- $\\alpha = {alpha}$ → Damping factor: sürücünün mevcut kavşaktan gerçek bir yolu takip etme olasılığı (Google orijinal: 0.85)
- $1-\\alpha = {round(1-alpha, 2)}$ → Rastgele ışınlanma: sürücünün ağdaki herhangi bir kavşağa atlaması
- $N = {len(G.nodes)}$ → Toplam düğüm (kavşak) sayısı
- $B_u$ → $u$ kavşağına giren yolların kümesi
- $L(v)$ → $v$ kavşağından çıkan yol sayısı

**Trafik planlamasındaki önemi:** Yüksek skorlu kavşaklar, trafik yoğunluğunun en kritik
aktarım noktalarıdır — yeni sinyalizasyon, genişletme veya alternatif güzergah
planlamalarında öncelikli değerlendirilmesi gereken noktalardır.
    """)
