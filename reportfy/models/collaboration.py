"""CollaborationModel — NetworkX-based developer collaboration graph."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import networkx as nx

from reportfy.models.issue import IssueModel


@dataclass
class CentralityMetrics:
    """Top-N developers by each centrality measure."""

    degree: list[tuple[str, float]] = field(default_factory=list)
    betweenness: list[tuple[str, float]] = field(default_factory=list)
    closeness: list[tuple[str, float]] = field(default_factory=list)
    eigenvector: list[tuple[str, float]] = field(default_factory=list)


@dataclass
class NetworkMetrics:
    """High-level graph statistics."""

    num_nodes: int = 0
    num_edges: int = 0
    avg_path_length: Optional[float] = None
    diameter: Optional[int] = None
    clustering_coefficient: float = 0.0
    global_efficiency: float = 0.0
    sigma: Optional[float] = None  # small-world index


@dataclass
class CommunityResult:
    """Community detection output."""

    partition: dict[str, int] = field(default_factory=dict)   # node → community_id
    modularity: float = 0.0
    num_communities: int = 0


class CollaborationModel:
    """
    Builds a directed collaboration graph where edges represent author→assignee
    relationships weighted by co-occurrence count.

    Uses NetworkX for centrality, path analysis, and community detection.
    """

    TOP_N = 5   # number of top developers to highlight per metric

    def __init__(self, issues: list[IssueModel]):
        """
        Args:
            issues: Full parsed issue list used to construct the graph.
        """
        self.issues = issues
        self.graph: nx.DiGraph = nx.DiGraph()
        self.undirected: nx.Graph = nx.Graph()
        self._built = False

    # ------------------------------------------------------------------
    # Factory helpers for temporal slicing
    # ------------------------------------------------------------------

    @classmethod
    def for_period(
        cls,
        issues: list[IssueModel],
        start: datetime,
        end: datetime,
    ) -> "CollaborationModel":
        """Return a CollaborationModel containing only issues within [start, end)."""
        filtered = [
            i for i in issues
            if i.created_at is not None and start <= i.created_at < end
        ]
        return cls(filtered)

    @classmethod
    def months_with_issues(cls, issues: list[IssueModel]) -> list[tuple[int, int]]:
        """Return sorted list of (year, month) tuples that have at least one issue."""
        seen: set[tuple[int, int]] = set()
        for i in issues:
            if i.created_at is not None:
                seen.add((i.created_at.year, i.created_at.month))
        return sorted(seen)

    @classmethod
    def weeks_in_month(cls, year: int, month: int) -> list[tuple[datetime, datetime]]:
        """
        Return ISO-week windows that overlap with the given calendar month.

        Each tuple is (week_start Monday, week_end exclusive Monday).
        """
        import pandas as pd

        month_start = pd.Timestamp(year=year, month=month, day=1)
        month_end = (month_start + pd.offsets.MonthEnd(1)).normalize() + pd.Timedelta(days=1)

        # Walk week by week
        windows: list[tuple[datetime, datetime]] = []
        cursor = month_start - pd.Timedelta(days=month_start.weekday())  # Monday of first week
        while cursor < month_end:
            week_end = cursor + pd.Timedelta(weeks=1)
            # Only include weeks that have days within the month
            overlap_start = max(cursor, month_start)
            overlap_end = min(week_end, month_end)
            if overlap_start < overlap_end:
                windows.append((cursor.to_pydatetime(), week_end.to_pydatetime()))
            cursor = week_end
        return windows

    # ------------------------------------------------------------------
    # Graph construction
    # ------------------------------------------------------------------

    def build_graph(self) -> None:
        """Populate self.graph from the issue list (idempotent)."""
        if self._built:
            return

        for issue in self.issues:
            author = issue.author_login
            if not author:
                continue
            self.graph.add_node(author)
            for assignee in issue.all_assignees:
                if assignee and assignee != author:
                    if self.graph.has_edge(author, assignee):
                        self.graph[author][assignee]["weight"] += 1
                    else:
                        self.graph.add_edge(author, assignee, weight=1)

        self.undirected = self.graph.to_undirected()
        self._built = True

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def centrality_metrics(self) -> CentralityMetrics:
        """Compute degree, betweenness, closeness, and eigenvector centrality."""
        self.build_graph()
        g = self.undirected
        n = g.number_of_nodes()
        if n == 0:
            return CentralityMetrics()

        def _top(scores: dict) -> list[tuple[str, float]]:
            return sorted(scores.items(), key=lambda x: x[1], reverse=True)[: self.TOP_N]

        degree = nx.degree_centrality(g)
        betweenness = nx.betweenness_centrality(g)
        closeness = nx.closeness_centrality(g)

        try:
            eigenvector = nx.eigenvector_centrality(g, max_iter=1000)
        except nx.PowerIterationFailedConvergence:
            eigenvector = {node: 0.0 for node in g.nodes()}

        return CentralityMetrics(
            degree=_top(degree),
            betweenness=_top(betweenness),
            closeness=_top(closeness),
            eigenvector=_top(eigenvector),
        )

    def network_metrics(self) -> NetworkMetrics:
        """Compute path length, diameter, clustering, and small-world index."""
        self.build_graph()
        g = self.undirected
        n = g.number_of_nodes()
        if n == 0:
            return NetworkMetrics()

        metrics = NetworkMetrics(
            num_nodes=n,
            num_edges=g.number_of_edges(),
            clustering_coefficient=nx.average_clustering(g),
            global_efficiency=nx.global_efficiency(g),
        )

        # Path metrics require a connected graph
        if nx.is_connected(g):
            metrics.avg_path_length = nx.average_shortest_path_length(g)
            metrics.diameter = nx.diameter(g)
        else:
            # Use the largest connected component
            largest_cc = max(nx.connected_components(g), key=len)
            sub = g.subgraph(largest_cc)
            if len(sub) > 1:
                metrics.avg_path_length = nx.average_shortest_path_length(sub)
                metrics.diameter = nx.diameter(sub)

        # Small-world index sigma  (σ = (C/C_rand) / (L/L_rand))
        if n > 2 and g.number_of_edges() > 0:
            try:
                sigma = nx.sigma(g, niter=100, nrand=10)
                metrics.sigma = round(sigma, 4)
            except Exception:
                pass

        return metrics

    def community_detection(self) -> CommunityResult:
        """Detect communities via greedy modularity maximisation."""
        self.build_graph()
        g = self.undirected
        if g.number_of_nodes() == 0:
            return CommunityResult()

        try:
            communities = nx.community.greedy_modularity_communities(g)
            partition: dict[str, int] = {}
            for idx, community in enumerate(communities):
                for node in community:
                    partition[node] = idx
            modularity = nx.community.modularity(g, communities)
            return CommunityResult(
                partition=partition,
                modularity=round(modularity, 4),
                num_communities=len(communities),
            )
        except Exception:
            return CommunityResult()
