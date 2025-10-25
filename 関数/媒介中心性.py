from collections import deque, defaultdict
from typing import List, Tuple, Dict, Hashable

def betweenness_centrality(
    edges: List[Tuple[Hashable, Hashable]],
    normalized: bool = True,
) -> Dict[Hashable, float]:
    """
    無向・非重み付きグラフにおける媒介中心性（Betweenness Centrality）を Brandes 法で計算します。
    NetworkX の nx.betweenness_centrality と同じ定義（normalized=True, endpoints=False 相当）です。

    Parameters
    ----------
    edges : list of tuple
        [("A","B"), ("A","C"), ("B","C"), ...] のような無向エッジ列。
        自己ループ (u,u) は無視します。多重辺は1本として扱います。
    normalized : bool, default=True
        NetworkX と同様の規則で正規化します（無向：係数 2/((n-1)(n-2))）。

    Returns
    -------
    dict
        各ノードをキー、媒介中心性を値とする辞書。
    """
    # --- グラフ（隣接集合）を構築（自己ループ除外、重複エッジは集合で1本に） ---
    adj: Dict[Hashable, set] = defaultdict(set)
    for u, v in edges:
        if u == v:
            continue  # 自己ループは媒介中心性に影響しないため無視
        adj[u].add(v)
        adj[v].add(u)

    nodes = list(adj.keys())
    n = len(nodes)
    # 孤立点を扱いたい場合はここで別途 nodes に追加してください
    # （本関数はエッジ列のみを前提 -> エッジに出現しない孤立点は対象外）

    # ノードが2以下なら全ノードの中心性は0
    if n <= 2:
        return {v: 0.0 for v in nodes}

    # --- Brandes（無向・非重み付き） ---
    Cb: Dict[Hashable, float] = {v: 0.0 for v in nodes}

    for s in nodes:
        # 前向き探索（最短路数 sigma、距離 dist、直前ノード集合 P、訪問順 S）
        S: List[Hashable] = []
        P: Dict[Hashable, List[Hashable]] = {v: [] for v in nodes}
        sigma: Dict[Hashable, float] = {v: 0.0 for v in nodes}
        dist: Dict[Hashable, int] = {v: -1 for v in nodes}

        sigma[s] = 1.0
        dist[s] = 0

        Q = deque([s])
        while Q:
            v = Q.popleft()
            S.append(v)
            dv = dist[v] + 1
            for w in adj[v]:
                if dist[w] < 0:
                    dist[w] = dv
                    Q.append(w)
                if dist[w] == dv:
                    sigma[w] += sigma[v]
                    P[w].append(v)

        # 依存度の逆伝播
        delta: Dict[Hashable, float] = {v: 0.0 for v in nodes}
        while S:
            w = S.pop()
            sw = sigma[w]
            if sw != 0.0:  # 連結でない場合の防御
                coeff = (1.0 + delta[w]) / sw
                for v in P[w]:
                    delta[v] += sigma[v] * coeff
            if w != s:
                Cb[w] += delta[w]

    # 無向グラフは「両方向で二重に数えている」ため 2 で割る
    for v in Cb:
        Cb[v] /= 2.0

    # 正規化（NetworkX と同じ規則）
    if normalized:
        # 無向：係数 = 2 / ((n-1)(n-2))
        scale = 0.0
        if n > 2:
            scale = 2.0 / ((n - 1) * (n - 2))
        if scale != 0.0:
            for v in Cb:
                Cb[v] *= scale

    return Cb





#--------------------------------------------------------------------------------------------------------------------------------
edges1 = [
    ("A", "B"), ("A", "C"), ("B", "C"), ("B", "D"), ("C", "E"), ("D", "E"),
    ("F", "G"), ("F", "H"), ("G", "H"), ("G", "I"), ("H", "J"), ("I", "J"),
    ("K", "L"), ("K", "M"), ("L", "M"), ("L", "N"), ("M", "O"), ("N", "O"),
    ("E", "F"), ("J", "K"),
    ("A", "P"), ("C", "Q"), ("L", "R"), ("N", "S"),
    ]
print('networkxを使用しない場合', betweenness_centrality(edges1))


#--------------------------------------------------------------------------------------------------------------------------------
import networkx as nx
G = nx.Graph(edges1)
nx.draw(G, with_labels=True)  # ラベルをTrueにして番号の可視化

print('networkxを使用した場合　', nx.betweenness_centrality(G))

#--------------------------------------------------------------------------------------------------------------------------------
#Output
#{'A': 0.11111111111111112, 'B': 0.0196078431372549, 'C': 0.3235294117647059, 'D': 0.042483660130718956, 'E': 0.477124183006536, 'F': 0.5032679738562091, 'G': 0.05555555555555556, 'H': 0.4444444444444445, 'I': 0.026143790849673203, 'J': 0.5065359477124183, 'K': 0.47058823529411764, 'L': 0.28758169934640526, 'M': 0.09150326797385622, 'N': 0.11764705882352941, 'O': 0.006535947712418301, 'P': 0.0, 'Q': 0.0, 'R': 0.0, 'S': 0.0}
