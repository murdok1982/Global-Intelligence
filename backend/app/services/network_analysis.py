"""
Social Network Analysis (SNA) service for the Global Intelligence Platform.

Provides tools for building relationship graphs between countries,
organizations, and actors, computing centrality metrics, detecting
communities/blocs, and identifying key actors and chokepoints.

Implemented in pure Python with no external graph-library dependency.
"""

from __future__ import annotations

import heapq
import math
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Edge:
    source: str
    target: str
    weight: float = 1.0
    relationship_type: str = "alliance"
    metadata: dict[str, Any] = field(default_factory=dict)


class Graph:
    """Undirected weighted graph with adjacency-list storage."""

    def __init__(self) -> None:
        self._nodes: set[str] = set()
        self._adj: dict[str, dict[str, Edge]] = defaultdict(dict)
        self._edges: list[Edge] = []

    @property
    def nodes(self) -> set[str]:
        return set(self._nodes)

    @property
    def edges(self) -> list[Edge]:
        return list(self._edges)

    @property
    def node_count(self) -> int:
        return len(self._nodes)

    @property
    def edge_count(self) -> int:
        return len(self._edges)

    def add_node(self, node_id: str, **metadata: Any) -> None:
        self._nodes.add(node_id)
        if node_id not in self._adj:
            self._adj[node_id] = {}

    def add_edge(
        self,
        source: str,
        target: str,
        weight: float = 1.0,
        relationship_type: str = "alliance",
        **metadata: Any,
    ) -> None:
        self._nodes.add(source)
        self._nodes.add(target)
        edge = Edge(
            source=source,
            target=target,
            weight=weight,
            relationship_type=relationship_type,
            metadata=metadata,
        )
        self._adj[source][target] = edge
        self._adj[target][source] = edge
        self._edges.append(edge)

    def neighbors(self, node_id: str) -> dict[str, Edge]:
        return dict(self._adj.get(node_id, {}))

    def degree(self, node_id: str) -> int:
        return len(self._adj.get(node_id, {}))

    def weighted_degree(self, node_id: str) -> float:
        return sum(e.weight for e in self._adj.get(node_id, {}).values())

    def has_node(self, node_id: str) -> bool:
        return node_id in self._nodes

    def has_edge(self, source: str, target: str) -> bool:
        return target in self._adj.get(source, {})

    def get_edge(self, source: str, target: str) -> Optional[Edge]:
        return self._adj.get(source, {}).get(target)

    def total_weight(self) -> float:
        return sum(e.weight for e in self._edges)

    def subgraph(self, nodes: set[str]) -> Graph:
        g = Graph()
        for n in nodes:
            if n in self._nodes:
                g.add_node(n)
        for e in self._edges:
            if e.source in nodes and e.target in nodes:
                g.add_edge(
                    e.source,
                    e.target,
                    weight=e.weight,
                    relationship_type=e.relationship_type,
                    **e.metadata,
                )
        return g


def _dijkstra(graph: Graph, source: str) -> dict[str, float]:
    dist: dict[str, float] = {n: math.inf for n in graph.nodes}
    dist[source] = 0.0
    pq: list[tuple[float, str]] = [(0.0, source)]
    visited: set[str] = set()

    while pq:
        d, u = heapq.heappop(pq)
        if u in visited:
            continue
        visited.add(u)
        for v, edge in graph.neighbors(u).items():
            w = edge.weight if edge.weight > 0 else 1e-9
            if d + w < dist[v]:
                dist[v] = d + w
                heapq.heappush(pq, (dist[v], v))

    return dist


def _bfs_shortest_paths(
    graph: Graph, source: str
) -> tuple[dict[str, float], dict[str, list[str]]]:
    dist: dict[str, float] = {source: 0.0}
    predecessors: dict[str, list[str]] = {n: [] for n in graph.nodes}
    queue: deque[str] = deque([source])
    order: list[str] = []

    while queue:
        u = queue.popleft()
        order.append(u)
        for v, edge in graph.neighbors(u).items():
            w = 1.0 / edge.weight if edge.weight > 0 else 1e9
            new_dist = dist[u] + w
            if v not in dist:
                dist[v] = new_dist
                predecessors[v].append(u)
                queue.append(v)
            elif abs(new_dist - dist[v]) < 1e-12:
                predecessors[v].append(u)

    return dist, predecessors


def _brandes_betweenness(graph: Graph) -> dict[str, float]:
    betweenness: dict[str, float] = {n: 0.0 for n in graph.nodes}

    for s in graph.nodes:
        stack: list[str] = []
        predecessors: dict[str, list[str]] = {n: [] for n in graph.nodes}
        sigma: dict[str, int] = {n: 0 for n in graph.nodes}
        sigma[s] = 1
        dist: dict[str, float] = {s: 0.0}
        queue: deque[str] = deque([s])

        while queue:
            u = queue.popleft()
            stack.append(u)
            for v, edge in graph.neighbors(u).items():
                w = 1.0 / edge.weight if edge.weight > 0 else 1e9
                path_len = dist[u] + w
                if v not in dist:
                    dist[v] = path_len
                    queue.append(v)
                if abs(path_len - dist[v]) < 1e-12:
                    sigma[v] += sigma[u]
                    predecessors[v].append(u)

        delta: dict[str, float] = {n: 0.0 for n in graph.nodes}
        while stack:
            w = stack.pop()
            for v in predecessors[w]:
                if sigma[w] > 0:
                    delta[v] += (sigma[v] / sigma[w]) * (1.0 + delta[w])
            if w != s:
                betweenness[w] += delta[w]

    n = graph.node_count
    if n > 2:
        scale = 1.0 / ((n - 1) * (n - 2))
        for node in betweenness:
            betweenness[node] *= scale

    return betweenness


def degree_centrality(graph: Graph) -> dict[str, float]:
    n = graph.node_count
    if n <= 1:
        return {node: 0.0 for node in graph.nodes}
    denom = n - 1
    return {node: graph.degree(node) / denom for node in graph.nodes}


def weighted_degree_centrality(graph: Graph) -> dict[str, float]:
    total = graph.total_weight()
    if total == 0:
        return {node: 0.0 for node in graph.nodes}
    return {node: graph.weighted_degree(node) / total for node in graph.nodes}


def betweenness_centrality(graph: Graph) -> dict[str, float]:
    return _brandes_betweenness(graph)


def closeness_centrality(graph: Graph) -> dict[str, float]:
    result: dict[str, float] = {}
    n = graph.node_count

    for node in graph.nodes:
        distances = _dijkstra(graph, node)
        reachable = [d for n2, d in distances.items() if n2 != node and d < math.inf]
        if not reachable:
            result[node] = 0.0
            continue
        total_dist = sum(reachable)
        num_reachable = len(reachable)
        if total_dist > 0:
            result[node] = (num_reachable / total_dist) * (num_reachable / (n - 1))
        else:
            result[node] = 0.0

    return result


def clustering_coefficient(graph: Graph) -> dict[str, float]:
    result: dict[str, float] = {}

    for node in graph.nodes:
        nbrs = set(graph.neighbors(node).keys())
        k = len(nbrs)
        if k < 2:
            result[node] = 0.0
            continue
        triangles = 0
        nbr_list = list(nbrs)
        for i in range(len(nbr_list)):
            for j in range(i + 1, len(nbr_list)):
                if graph.has_edge(nbr_list[i], nbr_list[j]):
                    triangles += 1
        result[node] = (2.0 * triangles) / (k * (k - 1))

    return result


def average_clustering(graph: Graph) -> float:
    cc = clustering_coefficient(graph)
    if not cc:
        return 0.0
    return sum(cc.values()) / len(cc)


def _modularity(graph: Graph, communities: dict[str, int]) -> float:
    m = graph.total_weight()
    if m == 0:
        return 0.0

    q = 0.0
    for e in graph.edges:
        if communities.get(e.source) == communities.get(e.target):
            ki = graph.weighted_degree(e.source)
            kj = graph.weighted_degree(e.target)
            q += e.weight - (ki * kj) / (2.0 * m)

    return q / m


def detect_communities(graph: Graph, max_iterations: int = 50) -> dict[str, int]:
    communities: dict[str, int] = {node: i for i, node in enumerate(sorted(graph.nodes))}
    m = graph.total_weight()
    if m == 0:
        return communities

    for _ in range(max_iterations):
        improved = False
        for node in graph.nodes:
            current_comm = communities[node]
            neighbor_comms: dict[int, float] = defaultdict(float)

            for nbr, edge in graph.neighbors(node).items():
                neighbor_comms[communities[nbr]] += edge.weight

            if not neighbor_comms:
                continue

            ki = graph.weighted_degree(node)
            best_comm = current_comm
            best_gain = 0.0

            for comm, w_in in neighbor_comms.items():
                if comm == current_comm:
                    continue
                sigma_tot_current = sum(
                    graph.weighted_degree(n)
                    for n in graph.nodes
                    if communities[n] == current_comm and n != node
                )
                sigma_tot_target = sum(
                    graph.weighted_degree(n)
                    for n in graph.nodes
                    if communities[n] == comm
                )

                ki_in_current = sum(
                    edge.weight
                    for nbr, edge in graph.neighbors(node).items()
                    if communities[nbr] == current_comm
                )
                ki_in_target = w_in

                remove_cost = -(ki_in_current - ki * sigma_tot_current / (2.0 * m)) / m
                add_gain = (ki_in_target - ki * sigma_tot_target / (2.0 * m)) / m
                gain = remove_cost + add_gain

                if gain > best_gain:
                    best_gain = gain
                    best_comm = comm

            if best_comm != current_comm and best_gain > 0:
                communities[node] = best_comm
                improved = True

        if not improved:
            break

    labels = sorted(set(communities.values()))
    remap = {old: new for new, old in enumerate(labels)}
    return {node: remap[c] for node, c in communities.items()}


def detect_communities_label_propagation(
    graph: Graph, max_iterations: int = 100
) -> dict[str, int]:
    communities: dict[str, int] = {node: i for i, node in enumerate(sorted(graph.nodes))}

    for _ in range(max_iterations):
        changed = False
        for node in graph.nodes:
            nbr_weights: dict[int, float] = defaultdict(float)
            for nbr, edge in graph.neighbors(node).items():
                nbr_weights[communities[nbr]] += edge.weight

            if not nbr_weights:
                continue

            max_w = max(nbr_weights.values())
            best_comms = [c for c, w in nbr_weights.items() if abs(w - max_w) < 1e-12]
            new_comm = min(best_comms)

            if communities[node] != new_comm:
                communities[node] = new_comm
                changed = True

        if not changed:
            break

    labels = sorted(set(communities.values()))
    remap = {old: new for new, old in enumerate(labels)}
    return {node: remap[c] for node, c in communities.items()}


def compute_centrality(graph: Graph) -> dict[str, dict[str, float]]:
    return {
        "degree": degree_centrality(graph),
        "weighted_degree": weighted_degree_centrality(graph),
        "betweenness": betweenness_centrality(graph),
        "closeness": closeness_centrality(graph),
        "clustering": clustering_coefficient(graph),
    }


def find_key_actors(graph: Graph, top_n: int = 10) -> list[dict[str, Any]]:
    centrality = compute_centrality(graph)
    actors: list[dict[str, Any]] = []

    for node in graph.nodes:
        composite = (
            centrality["degree"].get(node, 0.0) * 0.25
            + centrality["betweenness"].get(node, 0.0) * 0.35
            + centrality["closeness"].get(node, 0.0) * 0.25
            + centrality["clustering"].get(node, 0.0) * 0.15
        )
        actors.append(
            {
                "node": node,
                "composite_score": round(composite, 6),
                "degree_centrality": round(centrality["degree"].get(node, 0.0), 6),
                "betweenness_centrality": round(
                    centrality["betweenness"].get(node, 0.0), 6
                ),
                "closeness_centrality": round(
                    centrality["closeness"].get(node, 0.0), 6
                ),
                "clustering_coefficient": round(
                    centrality["clustering"].get(node, 0.0), 6
                ),
                "degree": graph.degree(node),
                "weighted_degree": round(graph.weighted_degree(node), 4),
            }
        )

    actors.sort(key=lambda a: a["composite_score"], reverse=True)
    return actors[:top_n]


def find_chokepoints(graph: Graph, top_n: int = 5) -> list[dict[str, Any]]:
    bc = betweenness_centrality(graph)
    ranked = sorted(bc.items(), key=lambda x: x[1], reverse=True)
    return [
        {
            "node": node,
            "betweenness_centrality": round(score, 6),
            "degree": graph.degree(node),
            "role": "bridge" if graph.degree(node) >= 3 else "peripheral_bridge",
        }
        for node, score in ranked[:top_n]
    ]


ALLIANCE_DATA: dict[str, dict[str, Any]] = {
    "NATO": {
        "full_name": "North Atlantic Treaty Organization",
        "type": "military_alliance",
        "founded": 1949,
        "members": [
            "US", "UK", "FR", "DE", "IT", "CA", "NL", "BE", "LU", "NO",
            "DK", "IS", "PT", "ES", "GR", "TR", "PL", "HU", "CZ", "SK",
            "RO", "BG", "EE", "LV", "LT", "SI", "HR", "AL", "ME", "MK",
            "FI", "SE",
        ],
    },
    "CSTO": {
        "full_name": "Collective Security Treaty Organization",
        "type": "military_alliance",
        "founded": 1992,
        "members": ["RU", "BY", "KZ", "KG", "TJ", "AM"],
    },
    "AUKUS": {
        "full_name": "Australia-United Kingdom-United States Security Partnership",
        "type": "security_pact",
        "founded": 2021,
        "members": ["AU", "UK", "US"],
    },
    "SCO": {
        "full_name": "Shanghai Cooperation Organisation",
        "type": "political_economic_security",
        "founded": 2001,
        "members": ["CN", "RU", "KZ", "KG", "TJ", "UZ", "IN", "PK", "IR"],
    },
    "BRICS": {
        "full_name": "BRICS Group of Emerging Economies",
        "type": "economic_bloc",
        "founded": 2009,
        "members": ["BR", "RU", "IN", "CN", "ZA", "EG", "ET", "AE", "IR", "SA"],
    },
    "EU": {
        "full_name": "European Union",
        "type": "political_economic_union",
        "founded": 1993,
        "members": [
            "DE", "FR", "IT", "ES", "NL", "BE", "LU", "DK", "IE", "GR",
            "PT", "AT", "FI", "SE", "PL", "HU", "CZ", "SK", "SI", "HR",
            "RO", "BG", "EE", "LV", "LT", "CY", "MT",
        ],
    },
    "ASEAN": {
        "full_name": "Association of Southeast Asian Nations",
        "type": "regional_bloc",
        "founded": 1967,
        "members": ["ID", "MY", "PH", "SG", "TH", "BN", "VN", "LA", "MM", "KH"],
    },
}


ALLIANCE_WEIGHTS: dict[str, float] = {
    "NATO": 1.0,
    "CSTO": 0.85,
    "AUKUS": 0.95,
    "SCO": 0.6,
    "BRICS": 0.5,
    "EU": 0.9,
    "ASEAN": 0.55,
}


def build_alliance_graph(
    alliances: Optional[list[dict[str, Any]]] = None,
) -> Graph:
    graph = Graph()
    source_data = alliances if alliances is not None else list(ALLIANCE_DATA.values())

    for alliance in source_data:
        name = alliance.get("name", alliance.get("full_name", "Unknown"))
        alliance_type = alliance.get("type", "alliance")
        members = alliance.get("members", [])
        weight = alliance.get("weight", ALLIANCE_WEIGHTS.get(name, 0.5))

        for member in members:
            if not graph.has_node(member):
                graph.add_node(member, type="country")

        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                src, tgt = members[i], members[j]
                if graph.has_edge(src, tgt):
                    existing = graph.get_edge(src, tgt)
                    if existing:
                        existing.weight = min(existing.weight + weight * 0.3, 2.0)
                else:
                    graph.add_edge(
                        src,
                        tgt,
                        weight=weight,
                        relationship_type=alliance_type,
                        alliance=name,
                    )

    return graph


def build_custom_graph(
    relationships: list[dict[str, Any]],
) -> Graph:
    graph = Graph()

    for rel in relationships:
        source = rel["source"]
        target = rel["target"]
        weight = rel.get("weight", 1.0)
        rel_type = rel.get("type", "unknown")

        if not graph.has_node(source):
            graph.add_node(source, **rel.get("source_meta", {}))
        if not graph.has_node(target):
            graph.add_node(target, **rel.get("target_meta", {}))

        graph.add_edge(source, target, weight=weight, relationship_type=rel_type)

    return graph


def community_summary(
    graph: Graph, communities: dict[str, int]
) -> list[dict[str, Any]]:
    groups: dict[int, list[str]] = defaultdict(list)
    for node, comm in communities.items():
        groups[comm].append(node)

    result: list[dict[str, Any]] = []
    for comm_id, members in sorted(groups.items()):
        sub = graph.subgraph(set(members))
        result.append(
            {
                "community_id": comm_id,
                "size": len(members),
                "members": sorted(members),
                "internal_edges": sub.edge_count,
                "internal_weight": round(sub.total_weight(), 4),
                "density": round(
                    (2.0 * sub.edge_count) / (len(members) * (len(members) - 1))
                    if len(members) > 1
                    else 0.0,
                    6,
                ),
            }
        )

    return result


def cross_community_links(
    graph: Graph, communities: dict[str, int]
) -> list[dict[str, Any]]:
    links: list[dict[str, Any]] = []

    for edge in graph.edges:
        c_src = communities.get(edge.source)
        c_tgt = communities.get(edge.target)
        if c_src is not None and c_tgt is not None and c_src != c_tgt:
            links.append(
                {
                    "source": edge.source,
                    "target": edge.target,
                    "source_community": c_src,
                    "target_community": c_tgt,
                    "weight": edge.weight,
                    "relationship_type": edge.relationship_type,
                }
            )

    links.sort(key=lambda x: x["weight"], reverse=True)
    return links


__all__ = [
    "Graph",
    "Edge",
    "ALLIANCE_DATA",
    "build_alliance_graph",
    "build_custom_graph",
    "compute_centrality",
    "detect_communities",
    "detect_communities_label_propagation",
    "find_key_actors",
    "find_chokepoints",
    "community_summary",
    "cross_community_links",
    "degree_centrality",
    "weighted_degree_centrality",
    "betweenness_centrality",
    "closeness_centrality",
    "clustering_coefficient",
    "average_clustering",
]
