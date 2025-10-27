from collections import deque, defaultdict
from typing import List, Tuple, Dict, Hashable

def closeness_centrality(
    edges: List[Tuple[Hashable, Hashable]],
    wf_improved: bool = True,
) -> Dict[Hashable, float]:
    """
    無向・非重み付きグラフにおける近接中心性（closeness centrality）を計算します。
    NetworkX の networkx.closeness_centrality(G, wf_improved=True) と同じ定義です。

    Parameters
    ----------
    edges : list of tuple
        [("A","B"), ("A","C"), ("B","C"), ...] のような無向エッジ列。
        自己ループ (u,u) は無視、重複エッジは1本として扱います。
    wf_improved : bool, default=True
        NetworkX と同じ補正（Wasserman & Faust 改良）を適用します。
        到達可能ノード数が全体より少ない場合に (reachable-1)/(N-1) を掛けます。

    Returns
    -------
    dict
        各ノード -> 近接中心性
    """
    # --- グラフ（隣接集合）を構築 ---
    adj: Dict[Hashable, set] = defaultdict(set)
    for u, v in edges:
        if u == v:
            continue  # 自己ループは中心性に影響しないため除外
        adj[u].add(v)
        adj[v].add(u)

    nodes = list(adj.keys())
    N = len(nodes)
    if N == 0:
        return {}

    # --- 各ノード s から BFS で最短距離を合計 ---
    def bfs_sum_dist(start):
        dist = {start: 0}
        q = deque([start])
        while q:
            x = q.popleft()
            for y in adj[x]:
                if y not in dist:
                    dist[y] = dist[x] + 1
                    q.append(y)
        # 自分以外への距離の総和
        total = sum(d for n, d in dist.items() if n != start)
        reachable = len(dist)  # 自分を含む到達可能ノード数
        return total, reachable

    C = {}
    for s in nodes:
        total_dist, reachable = bfs_sum_dist(s)

        # 孤立ノード、到達先が自分だけ、または距離総和ゼロ（N=1）のときは0
        if reachable <= 1 or total_dist == 0:
            C[s] = 0.0
            continue

        # 基本形： (reachable-1) / sum_dist
        score = (reachable - 1) / total_dist

        # 改良補正（wf_improved=True）
        if wf_improved and N > 1:
            score *= (reachable - 1) / (N - 1)

        C[s] = float(score)

    return C


# ---- ここから下は動作テスト（直接実行時のみ） ----
edges = [
    ("A", "B"), ("A", "C"), ("B", "C"), ("B", "D"), ("C", "E"), ("D", "E"),
    ("F", "G"), ("F", "H"), ("G", "H"), ("G", "I"), ("H", "J"), ("I", "J"),
    ("K", "L"), ("K", "M"), ("L", "M"), ("L", "N"), ("M", "O"), ("N", "O"),
    ("E", "F"), ("J", "K"),
    ("A", "P"), ("C", "Q"), ("L", "R"), ("N", "S"),
    ]

#--------------------------------------------------------------------------------------------------------------------------------
result = closeness_centrality(edges, wf_improved=True)
print(result)

#--------------------------------------------------------------------------------------------------------------------------------
G = nx.Graph()
G.add_edges_from(edges)
# NetworkX 既定は wf_improved=True
res = nx.closeness_centrality(G, wf_improved=True)
print(res)
