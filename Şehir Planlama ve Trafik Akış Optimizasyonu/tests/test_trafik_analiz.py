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


def test_impute_lanes_handles_list_lanes():
    G = make_test_graph()
    G[1][2][0]["lanes"] = ["2", "3"]
    G = impute_lanes(G)
    assert G[1][2][0]["lanes"] == 2  # takes first element


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
