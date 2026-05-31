# Temporal Weighted PageRank — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** OSM kenar özelliklerinden composite ağırlık hesaplayıp sabah rush / akşam rush / sakin olmak üzere 3 zaman diliminde ağırlıklı PageRank çalıştırmak ve sonuçları Streamlit'te karşılaştırmalı göstermek.

**Architecture:** Saf hesaplama fonksiyonları `trafik_analiz.py` adlı yeni bir modüle taşınır (test edilebilir), `app.py` sadece UI katmanı olarak kalır. `tum_slotlar_hesapla` Streamlit cache ile sarılır — kullanıcı zaman dilimi değiştirdiğinde hesaplama tekrar koşmaz, sadece önbellekten alınan sonuç değişir.

**Tech Stack:** Python 3.x, osmnx, networkx, streamlit, folium, numpy, pandas, pytest

---

## Dosya Haritası

| Dosya | Değişiklik |
|-------|-----------|
| `trafik_analiz.py` | YENİ — saf hesaplama modülü |
| `tests/test_trafik_analiz.py` | YENİ — unit testler |
| `app.py` | GÜNCELLEME — yeni modülü entegre et, UI ekle |

Çalışma dizini her komut için:
`cd "Şehir Planlama ve Trafik Akış Optimizasyonu"`

---

### Task 1: Lane İmputation — Test + Implementasyon

**Files:**
- Create: `tests/__init__.py` (boş)
- Create: `tests/test_trafik_analiz.py`
- Create: `trafik_analiz.py`

- [ ] **Step 1: Test dosyasını oluştur**

`tests/__init__.py` → boş dosya.

`tests/test_trafik_analiz.py`:
```python
import pytest
import networkx as nx
from trafik_analiz import (
    impute_lanes, compute_base_weights,
    apply_temporal_weights, compute_all_slots,
    gini_coefficient, compute_rank_table,
    LANE_DEFAULTS, TEMPORAL_MULTIPLIERS,
)


def make_test_graph():
    G = nx.MultiDiGraph()
    G.add_node(1, x=-122.41, y=37.76)
    G.add_node(2, x=-122.42, y=37.77)
    G.add_node(3, x=-122.43, y=37.78)
    G.add_edge(1, 2, 0, highway="primary",     length=200.0, speed_kph=50.0)
    G.add_edge(2, 3, 0, highway="residential", length=100.0, speed_kph=30.0)
    G.add_edge(3, 1, 0, highway="motorway",    length=500.0, speed_kph=100.0)
    return G


# ── Lane imputation ───────────────────────────────────────────────────────────

def test_impute_lanes_fills_missing_primary():
    G = make_test_graph()
    G = impute_lanes(G)
    assert G[1][2][0]["lanes"] == LANE_DEFAULTS["primary"]  # 2


def test_impute_lanes_fills_missing_residential():
    G = make_test_graph()
    G = impute_lanes(G)
    assert G[2][3][0]["lanes"] == LANE_DEFAULTS["residential"]  # 1


def test_impute_lanes_fills_missing_motorway():
    G = make_test_graph()
    G = impute_lanes(G)
    assert G[3][1][0]["lanes"] == LANE_DEFAULTS["motorway"]  # 3


def test_impute_lanes_keeps_existing_value():
    G = make_test_graph()
    G[1][2][0]["lanes"] = 4
    G = impute_lanes(G)
    assert G[1][2][0]["lanes"] == 4


def test_impute_lanes_converts_string_to_int():
    G = make_test_graph()
    G[1][2][0]["lanes"] = "3"
    G = impute_lanes(G)
    assert G[1][2][0]["lanes"] == 3


# ── Base weights ──────────────────────────────────────────────────────────────

def test_compute_base_weights_covers_all_edges():
    G = make_test_graph()
    G = impute_lanes(G)
    weights = compute_base_weights(G)
    assert len(weights) == 3


def test_compute_base_weights_all_non_negative():
    G = make_test_graph()
    G = impute_lanes(G)
    weights = compute_base_weights(G)
    assert all(w >= 0 for w in weights.values())


def test_compute_base_weights_motorway_heavier_than_residential():
    G = make_test_graph()
    G = impute_lanes(G)
    weights = compute_base_weights(G)
    # motorway (3→1): speed=100, lanes=3 vs residential (2→3): speed=30, lanes=1
    assert weights[(3, 1, 0)] > weights[(2, 3, 0)]


# ── Temporal weights ──────────────────────────────────────────────────────────

def _edge_highway_map(G):
    return {
        (u, v, k): d.get("highway", "unclassified")
        for u, v, k, d in G.edges(keys=True, data=True)
    }


def test_sabah_rush_increases_primary_over_sakin():
    G = make_test_graph()
    G = impute_lanes(G)
    base = compute_base_weights(G)
    ehm  = _edge_highway_map(G)
    rush  = apply_temporal_weights(base, ehm, "sabah_rush")
    sakin = apply_temporal_weights(base, ehm, "sakin")
    assert rush[(1, 2, 0)] > sakin[(1, 2, 0)]


def test_sabah_rush_reduces_residential_vs_sakin():
    G = make_test_graph()
    G = impute_lanes(G)
    base = compute_base_weights(G)
    ehm  = _edge_highway_map(G)
    rush  = apply_temporal_weights(base, ehm, "sabah_rush")
    sakin = apply_temporal_weights(base, ehm, "sakin")
    assert rush[(2, 3, 0)] < sakin[(2, 3, 0)]


def test_sakin_equals_base():
    G = make_test_graph()
    G = impute_lanes(G)
    base  = compute_base_weights(G)
    ehm   = _edge_highway_map(G)
    sakin = apply_temporal_weights(base, ehm, "sakin")
    for key in base:
        assert abs(sakin[key] - base[key]) < 1e-10


# ── All-slots PageRank ────────────────────────────────────────────────────────

def test_compute_all_slots_returns_three_keys():
    G = make_test_graph()
    results = compute_all_slots(G)
    assert set(results.keys()) == {"sabah_rush", "aksam_rush", "sakin"}


def test_compute_all_slots_scores_cover_all_nodes():
    G = make_test_graph()
    results = compute_all_slots(G)
    for scores in results.values():
        assert set(scores.keys()) == {1, 2, 3}


def test_compute_all_slots_scores_sum_to_one():
    G = make_test_graph()
    results = compute_all_slots(G)
    for dilim, scores in results.items():
        assert abs(sum(scores.values()) - 1.0) < 1e-6, f"{dilim} scores don't sum to 1"


def test_compute_all_slots_sabah_differs_from_sakin():
    G = make_test_graph()
    results = compute_all_slots(G)
    assert results["sabah_rush"] != results["sakin"]


# ── Gini coefficient ──────────────────────────────────────────────────────────

def test_gini_uniform_is_near_zero():
    scores = {i: 1.0 / 10 for i in range(10)}
    assert gini_coefficient(scores) < 0.05


def test_gini_concentrated_is_high():
    scores = {0: 1.0}
    scores.update({i: 0.0001 for i in range(1, 10)})
    assert gini_coefficient(scores) > 0.8


def test_gini_between_zero_and_one():
    G = make_test_graph()
    results = compute_all_slots(G)
    for scores in results.values():
        g = gini_coefficient(scores)
        assert 0.0 <= g <= 1.0


# ── Rank table ────────────────────────────────────────────────────────────────

def test_rank_table_has_required_columns():
    G = make_test_graph()
    results = compute_all_slots(G)
    df = compute_rank_table(results)
    assert {"node", "sabah_rush", "aksam_rush", "sakin"}.issubset(df.columns)


def test_rank_table_not_empty():
    G = make_test_graph()
    results = compute_all_slots(G)
    df = compute_rank_table(results)
    assert len(df) > 0
```

- [ ] **Step 2: Testlerin import hatası verdiğini doğrula**

```
pytest tests/test_trafik_analiz.py -v 2>&1 | head -20
```

Beklenen çıktı: `ModuleNotFoundError: No module named 'trafik_analiz'`

- [ ] **Step 3: `trafik_analiz.py` oluştur — sadece lane imputation**

`trafik_analiz.py`:
```python
import numpy as np
import networkx as nx
import pandas as pd

LANE_DEFAULTS = {
    "motorway": 3, "motorway_link": 2,
    "trunk": 2, "trunk_link": 2,
    "primary": 2, "primary_link": 2,
    "secondary": 2, "secondary_link": 1,
    "tertiary": 1, "tertiary_link": 1,
    "residential": 1, "living_street": 1,
    "unclassified": 1, "service": 1,
}

TEMPORAL_MULTIPLIERS = {
    "sabah_rush": {
        "motorway": 1.4, "motorway_link": 1.4,
        "trunk": 1.4, "trunk_link": 1.4,
        "primary": 1.3, "primary_link": 1.3,
        "secondary": 1.3, "secondary_link": 1.3,
        "tertiary": 1.1, "tertiary_link": 1.1,
        "residential": 0.8, "living_street": 0.8,
        "unclassified": 0.9, "service": 0.8,
    },
    "aksam_rush": {
        "motorway": 1.5, "motorway_link": 1.5,
        "trunk": 1.5, "trunk_link": 1.5,
        "primary": 1.4, "primary_link": 1.4,
        "secondary": 1.4, "secondary_link": 1.4,
        "tertiary": 1.2, "tertiary_link": 1.2,
        "residential": 0.9, "living_street": 0.9,
        "unclassified": 1.0, "service": 0.9,
    },
    "sakin": {},  # tüm çarpanlar 1.0 (varsayılan)
}


def impute_lanes(G):
    for u, v, k, data in G.edges(keys=True, data=True):
        raw = data.get("lanes")
        if raw is None:
            highway = data.get("highway", "unclassified")
            if isinstance(highway, list):
                highway = highway[0]
            G[u][v][k]["lanes"] = LANE_DEFAULTS.get(highway, 1)
        else:
            try:
                G[u][v][k]["lanes"] = int(raw)
            except (ValueError, TypeError):
                highway = data.get("highway", "unclassified")
                if isinstance(highway, list):
                    highway = highway[0]
                G[u][v][k]["lanes"] = LANE_DEFAULTS.get(highway, 1)
    return G


def _normalize(values):
    arr = np.array(values, dtype=float)
    mn, mx = arr.min(), arr.max()
    return (arr - mn) / (mx - mn + 1e-12)


def compute_base_weights(G):
    raise NotImplementedError


def apply_temporal_weights(base_weights, edge_highway_map, dilim):
    raise NotImplementedError


def compute_all_slots(G, alpha=0.85):
    raise NotImplementedError


def gini_coefficient(scores):
    raise NotImplementedError


def compute_rank_table(pr_results):
    raise NotImplementedError
```

- [ ] **Step 4: Lane imputation testlerini çalıştır**

```
pytest tests/test_trafik_analiz.py -k "impute" -v
```

Beklenen: 5 test PASS, diğerleri NotImplementedError ile FAIL.

- [ ] **Step 5: Commit**

```bash
git add trafik_analiz.py tests/__init__.py tests/test_trafik_analiz.py
git commit -m "feat: add trafik_analiz module with lane imputation + full test suite"
```

---

### Task 2: Base Weight Hesaplama

**Files:**
- Modify: `trafik_analiz.py` — `compute_base_weights` implement et

- [ ] **Step 1: `compute_base_weights` testlerinin FAIL verdiğini kontrol et**

```
pytest tests/test_trafik_analiz.py -k "base_weight" -v
```

Beklenen: 3 test FAIL (NotImplementedError).

- [ ] **Step 2: `compute_base_weights` implement et**

`trafik_analiz.py` içindeki `compute_base_weights` fonksiyonunu değiştir:

```python
def compute_base_weights(G):
    edges = list(G.edges(keys=True, data=True))
    speeds  = [float(d.get("speed_kph", 30.0)) for _, _, _, d in edges]
    lanes   = [float(d.get("lanes", 1))         for _, _, _, d in edges]
    lengths = [float(d.get("length", 100.0))    for _, _, _, d in edges]

    norm_speed      = _normalize(speeds)
    norm_lanes      = _normalize(lanes)
    norm_inv_length = _normalize([1.0 / l for l in lengths])

    weights = {}
    for i, (u, v, k, _) in enumerate(edges):
        weights[(u, v, k)] = (
            0.4 * norm_speed[i] +
            0.4 * norm_lanes[i] +
            0.2 * norm_inv_length[i]
        )
    return weights
```

- [ ] **Step 3: Testleri çalıştır**

```
pytest tests/test_trafik_analiz.py -k "base_weight" -v
```

Beklenen: 3 test PASS.

- [ ] **Step 4: Commit**

```bash
git add trafik_analiz.py
git commit -m "feat: implement composite base weight computation"
```

---

### Task 3: Temporal Weight Çarpanları

**Files:**
- Modify: `trafik_analiz.py` — `apply_temporal_weights` implement et

- [ ] **Step 1: Testlerin FAIL verdiğini doğrula**

```
pytest tests/test_trafik_analiz.py -k "temporal or sakin or sabah or aksam" -v
```

Beklenen: 3 test FAIL (NotImplementedError).

- [ ] **Step 2: `apply_temporal_weights` implement et**

```python
def apply_temporal_weights(base_weights, edge_highway_map, dilim):
    multipliers = TEMPORAL_MULTIPLIERS.get(dilim, {})
    result = {}
    for (u, v, k), w in base_weights.items():
        highway = edge_highway_map.get((u, v, k), "unclassified")
        if isinstance(highway, list):
            highway = highway[0]
        mult = multipliers.get(highway, 1.0)
        result[(u, v, k)] = w * mult
    return result
```

- [ ] **Step 3: Testleri çalıştır**

```
pytest tests/test_trafik_analiz.py -k "temporal or sakin or sabah or aksam" -v
```

Beklenen: 3 test PASS.

- [ ] **Step 4: Commit**

```bash
git add trafik_analiz.py
git commit -m "feat: implement temporal weight multipliers (HCM peak hour factors)"
```

---

### Task 4: compute_all_slots

**Files:**
- Modify: `trafik_analiz.py` — `compute_all_slots` implement et

- [ ] **Step 1: Testlerin FAIL verdiğini doğrula**

```
pytest tests/test_trafik_analiz.py -k "all_slots" -v
```

Beklenen: 4 test FAIL.

- [ ] **Step 2: `compute_all_slots` implement et**

`trafik_analiz.py` dosyasının başına ekle:
```python
import osmnx as ox
```

`compute_all_slots` fonksiyonunu değiştir:
```python
def compute_all_slots(G, alpha=0.85):
    # ox.add_edge_speeds sadece speed_kph yoksa çalışır (testlerde atlanır)
    edges_data = [d for _, _, d in G.edges(data=True)]
    if not any("speed_kph" in d for d in edges_data):
        G = ox.add_edge_speeds(G)

    G = impute_lanes(G)
    base_weights = compute_base_weights(G)

    edge_highway_map = {
        (u, v, k): d.get("highway", "unclassified")
        for u, v, k, d in G.edges(keys=True, data=True)
    }

    results = {}
    for dilim in ["sabah_rush", "aksam_rush", "sakin"]:
        temporal = apply_temporal_weights(base_weights, edge_highway_map, dilim)
        for (u, v, k), w in temporal.items():
            G[u][v][k]["trafik_agirlik"] = w
        try:
            scores = nx.pagerank(
                G, alpha=alpha, weight="trafik_agirlik", max_iter=1000, tol=1e-6
            )
        except nx.PowerIterationFailedConvergence:
            scores = nx.pagerank(
                G, alpha=alpha, weight="trafik_agirlik", max_iter=1000, tol=1e-4
            )
        results[dilim] = scores
    return results
```

- [ ] **Step 3: Testleri çalıştır**

```
pytest tests/test_trafik_analiz.py -k "all_slots" -v
```

Beklenen: 4 test PASS.

- [ ] **Step 4: Commit**

```bash
git add trafik_analiz.py
git commit -m "feat: implement compute_all_slots with 3-slot weighted PageRank"
```

---

### Task 5: Gini Katsayısı + Rank Tablosu

**Files:**
- Modify: `trafik_analiz.py` — `gini_coefficient` ve `compute_rank_table` implement et

- [ ] **Step 1: Testlerin FAIL verdiğini doğrula**

```
pytest tests/test_trafik_analiz.py -k "gini or rank" -v
```

Beklenen: 5 test FAIL.

- [ ] **Step 2: `gini_coefficient` implement et**

```python
def gini_coefficient(scores):
    arr = np.sort(np.array(list(scores.values()), dtype=float))
    n   = len(arr)
    idx = np.arange(1, n + 1)
    return float(
        (2 * np.sum(idx * arr) - (n + 1) * np.sum(arr))
        / (n * np.sum(arr) + 1e-12)
    )
```

- [ ] **Step 3: `compute_rank_table` implement et**

```python
def compute_rank_table(pr_results):
    slot_ranks = {}
    for dilim, scores in pr_results.items():
        top10 = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:10]
        slot_ranks[dilim] = {node: rank + 1 for rank, (node, _) in enumerate(top10)}

    all_nodes = set()
    for ranks in slot_ranks.values():
        all_nodes.update(ranks.keys())

    rows = []
    for node in all_nodes:
        row = {"node": node}
        for dilim in ["sabah_rush", "aksam_rush", "sakin"]:
            row[dilim] = slot_ranks[dilim].get(node, ">10")
        rows.append(row)

    df = pd.DataFrame(rows)
    df = df.sort_values(
        "sabah_rush",
        key=lambda col: col.map(lambda v: v if isinstance(v, int) else 99),
    )
    return df.reset_index(drop=True)
```

- [ ] **Step 4: Tüm testleri çalıştır**

```
pytest tests/test_trafik_analiz.py -v
```

Beklenen: tüm testler PASS (en az 24 test).

- [ ] **Step 5: Commit**

```bash
git add trafik_analiz.py
git commit -m "feat: add gini coefficient and rank comparison table"
```

---

### Task 6: app.py — Backend Entegrasyonu

**Files:**
- Modify: `app.py`

- [ ] **Step 1: Import ekle**

`app.py` dosyasında `import warnings` satırının hemen altına ekle:

```python
from trafik_analiz import compute_all_slots, gini_coefficient, compute_rank_table
```

- [ ] **Step 2: `pagerank_hesapla` fonksiyonunu `tum_slotlar_hesapla` ile değiştir**

Şu kodu:
```python
@st.cache_data(show_spinner=False)
def pagerank_hesapla(_G, mahalle_adi: str, alpha: float):
    # α yükseldikçe yakınsama daha fazla iterasyon gerektirir;
    # max_iter=1000 ve toleransı biraz gevşeterek hata önlenir.
    try:
        return nx.pagerank(_G, alpha=alpha, max_iter=1000, tol=1e-6)
    except nx.PowerIterationFailedConvergence:
        # Yine de yakınsamazsa toleransı gevşet
        return nx.pagerank(_G, alpha=alpha, max_iter=1000, tol=1e-4)
```

Şununla değiştir:
```python
@st.cache_data(show_spinner=False)
def tum_slotlar_hesapla(_G, mahalle_adi: str, alpha: float):
    return compute_all_slots(_G, alpha=alpha)
```

- [ ] **Step 3: Analiz bölümünde PageRank çağrısını güncelle**

Şu kodu:
```python
with st.spinner("⚙️ PageRank hesaplanıyor..."):
    pr = pagerank_hesapla(G, secilen_adi, alpha)
```

Şununla değiştir:
```python
with st.spinner("⚙️ 3 zaman dilimi için PageRank hesaplanıyor..."):
    pr_sonuclar = tum_slotlar_hesapla(G, secilen_adi, alpha)
pr = pr_sonuclar[secilen_dilim]
```

Not: `secilen_dilim` Task 7'de sidebar'a eklenecek. Bu adımda geçici olarak sabit kodla:
```python
secilen_dilim = "sabah_rush"  # Task 7'de sidebar'a taşınacak
```

Bu satırı `pr = pr_sonuclar[secilen_dilim]` satırının hemen üstüne koy.

- [ ] **Step 4: `scores` ve `node_data` satırlarının hâlâ çalıştığını doğrula**

Şu satırların değişmediğinden emin ol (app.py ~line 464):
```python
scores    = list(pr.values())
node_data = dict(G.nodes(data=True))
```

Bu satırlar `pr` değişkenini kullanıyor — değişmedi, çalışmaya devam eder.

- [ ] **Step 5: Uygulamayı çalıştır ve temel işlevselliği doğrula**

```
streamlit run app.py
```

Tarayıcıda: mahalle seç → Analiz Et → harita görünmeli. Terminal'de hata olmamalı.

- [ ] **Step 6: Commit**

```bash
git add app.py
git commit -m "feat: replace pagerank_hesapla with 3-slot tum_slotlar_hesapla"
```

---

### Task 7: app.py — Sidebar Zaman Dilimi + Gini Metrik

**Files:**
- Modify: `app.py`

- [ ] **Step 1: Sidebar'a zaman dilimi radio butonu ekle**

Sidebar bloğunda (`with st.sidebar:` içinde), `analiz_btn = st.button(...)` satırından ÖNCE şunu ekle:

```python
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
```

- [ ] **Step 2: Sabit kodlanmış `secilen_dilim = "sabah_rush"` satırını sil**

Task 6'da geçici olarak eklenen şu satırı `app.py`'den kaldır:
```python
secilen_dilim = "sabah_rush"  # Task 7'de sidebar'a taşınacak
```

- [ ] **Step 3: Session state ile analiz durumunu koru**

Radio buton değiştiğinde sayfa yeniden render olur ve `analiz_btn` False döner. Bunu önlemek için session state kullan.

Sidebar'da `analiz_btn` satırından sonra şunu ekle:
```python
    if analiz_btn:
        st.session_state["analiz_yapildi"] = True
```

Ana alandaki şu kodu:
```python
if not analiz_btn:
    st.markdown("""
    <div style="text-align:center;padding:4rem 2rem;color:rgba(255,255,255,0.3);">
      <div style="font-size:5rem;">🏙️</div>
      <div style="font-size:1.2rem;margin-top:1rem;">Sol panelden mahalle seç ve <b>Analiz Et</b>'e bas</div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()
```

Şununla değiştir:
```python
if not st.session_state.get("analiz_yapildi", False):
    st.markdown("""
    <div style="text-align:center;padding:4rem 2rem;color:rgba(255,255,255,0.3);">
      <div style="font-size:5rem;">🏙️</div>
      <div style="font-size:1.2rem;margin-top:1rem;">Sol panelden mahalle seç ve <b>Analiz Et</b>'e bas</div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()
```

- [ ] **Step 4: Gini metrik kartı ekle**

`scores = list(pr.values())` satırından sonra şunu ekle:
```python
gini = gini_coefficient(pr)
```

4. metrik kartı (`c4`, Damping Factor) şununla değiştir:
```python
with c4:
    st.markdown(f"""
    <div class="metric-card">
      <div class="label">Gini Katsayısı</div>
      <div class="value">{gini:.3f}</div>
      <div class="sub">trafik yoğunlaşması</div>
    </div>""", unsafe_allow_html=True)
```

- [ ] **Step 5: Harita başlığına seçili dilimi ekle**

Şu satırı:
```python
st.markdown(f"### 🗺️ {secilen_adi} — PageRank Haritası")
```

Şununla değiştir:
```python
dilim_etiket = {"sabah_rush": "🌅 Sabah Rush", "aksam_rush": "🌆 Akşam Rush", "sakin": "🌙 Sakin Saat"}
st.markdown(f"### 🗺️ {secilen_adi} — {dilim_etiket[secilen_dilim]}")
```

- [ ] **Step 6: Uygulamayı çalıştır ve radio butonun çalıştığını doğrula**

```
streamlit run app.py
```

- Analiz Et'e bas → harita görünmeli
- Radio buton değiştir → harita yenilenmeli (hata olmadan)
- Gini kartı güncel dilim için değer göstermeli

- [ ] **Step 7: Commit**

```bash
git add app.py
git commit -m "feat: add time slot radio button, gini metric, session state persistence"
```

---

### Task 8: app.py — Karşılaştırma Sekmesi

**Files:**
- Modify: `app.py`

- [ ] **Step 1: Harita bölümünü sekmelere taşı**

Şu kodu:
```python
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
```

Şununla değiştir:
```python
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

    # Gini karşılaştırma satırı
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

    # Rank tablosu
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
```

- [ ] **Step 2: Uygulamayı çalıştır ve sekmeleri doğrula**

```
streamlit run app.py
```

Kontrol listesi:
- [ ] "Harita" sekmesi önceki gibi çalışıyor
- [ ] "Dilim Karşılaştırması" sekmesinde 3 Gini kartı görünüyor
- [ ] Rank tablosu dolu ve `>10` değerleri var
- [ ] Radio butonla dilim değiştirince harita sekmesi güncelleniyor

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "feat: add comparison tab with gini cards and rank change table"
```

---

## Son Doğrulama

- [ ] Tüm unit testleri çalıştır: `pytest tests/test_trafik_analiz.py -v`
- [ ] Uygulamayı baştan sona test et: her mahalle + her zaman dilimi
- [ ] Terminal'de kırmızı hata yok

---

## Rapor İçin Hazır Materyaller

| Bölüm | İçerik |
|-------|--------|
| Veri seti | OSM kenar özellikleri tablosu: `speed_kph`, `lanes`, `highway`, `length` |
| Ön işleme | `impute_lanes` imputation tablosu + `_normalize` formülü |
| Yöntem | Composite ağırlık formülü + `TEMPORAL_MULTIPLIERS` tablosu |
| Algoritmalar | Ağırlıklı PageRank formülü + 3-slot karşılaştırma |
| Sonuçlar | Gini katsayıları tablosu + rank değişim tablosu ekran görüntüsü |
