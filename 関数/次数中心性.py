from collections import defaultdict
from typing import Dict, Hashable, List, Tuple

def degree_centrality(
    edges: List[Tuple[Hashable, Hashable]],
) -> Dict[Hashable, float]:
    """
    無向・非重み付きグラフの次数中心性を計算します。
    定義は NetworkX の networkx.degree_centrality(G) と同じで、
    各ノード v について centrality(v) = degree(v) / (n - 1) を返します。
    ここで n はノード数、degree(v) は無向グラフの次数です。

    入力:
        edges: [("A","B"), ("A","C"), ...] のエッジ列（無向）
               自己ループ (u,u) は無視。重複エッジは1本として扱います。

    返り値:
        {ノード: 次数中心性} の辞書
    """
    # 隣接集合（自己ループ除外、重複エッジは集合で吸収）
    adj: Dict[Hashable, set] = defaultdict(set)
    for u, v in edges:
        if u == v:
            continue
        adj[u].add(v)
        adj[v].add(u)

    nodes = list(adj.keys())
    n = len(nodes)

    # ノードが 0 または 1 の場合は 0 を返す（NetworkX と同じ扱い）
    if n <= 1:
        return {v: 0.0 for v in nodes}

    # degree(v) / (n-1)
    denom = float(n - 1)
    return {v: len(adj[v]) / denom for v in nodes}


#テスト用入力値--------------------------------------------------------------------------------------------------------------------------------
edges = [
    ("A","B"), ("A","C"), ("A","D"), ("A","E"), ("A","F"),
    ("B","G"),
    ("C","H"), ("H","I"),
    ("D","J"), ("J","K"),
    ("E","L"), ("L","M"),
    ("F","N"),
    ("H","O"),
    ("K","P"),
    ("M","Q"),
    ("N","R"),
    ("J","S"),
    ("G","T"),
]

#--------------------------------------------------------------------------------------------------------------------------------
result = degree_centrality(edges)
print(1, result)


#--------------------------------------------------------------------------------------------------------------------------------
import networkx as nx
G = nx.Graph()
G.add_edges_from(edges)
res = nx.degree_centrality(G)
print(2, res)

#--------------------------------------------------------------------------------------------------------------------------------
nx.draw(G, with_labels=True)
