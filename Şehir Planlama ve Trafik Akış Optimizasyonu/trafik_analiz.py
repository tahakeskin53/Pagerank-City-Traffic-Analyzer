import numpy as np
import networkx as nx
import pandas as pd
import osmnx as ox

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
    "sakin": {},
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
                if isinstance(raw, list):
                    raw = raw[0]
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


def compute_all_slots(G, alpha=0.85):
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

        # Build personalization from in-edge weights so that nodes receiving
        # heavier traffic are seeded as more important in the PageRank.
        in_w = {}
        for (u, v, k), w in temporal.items():
            in_w[v] = in_w.get(v, 0) + w
        raw = {n: in_w.get(n, 1e-6) for n in G.nodes()}
        total = sum(raw.values())
        personalization = {n: v / total for n, v in raw.items()}

        try:
            scores = nx.pagerank(
                G, alpha=alpha, weight="trafik_agirlik",
                personalization=personalization, max_iter=1000, tol=1e-6
            )
        except nx.PowerIterationFailedConvergence:
            scores = nx.pagerank(
                G, alpha=alpha, weight="trafik_agirlik",
                personalization=personalization, max_iter=1000, tol=1e-4
            )
        results[dilim] = scores
    return results


def gini_coefficient(scores):
    arr = np.sort(np.array(list(scores.values()), dtype=float))
    n   = len(arr)
    idx = np.arange(1, n + 1)
    return float(
        (2 * np.sum(idx * arr) - (n + 1) * np.sum(arr))
        / (n * np.sum(arr) + 1e-12)
    )


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
