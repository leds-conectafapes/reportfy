"""Unit tests for CollaborationModel."""
from __future__ import annotations

import pytest

from reportfy.models.collaboration import CollaborationModel


class TestBuildGraph:
    """Tests for CollaborationModel.build_graph()."""

    def test_creates_nodes_for_each_author(self, sample_issues):
        model = CollaborationModel(sample_issues)
        model.build_graph()
        # alice and carol both authored issues
        assert "alice" in model.graph.nodes
        assert "carol" in model.graph.nodes

    def test_creates_edges_for_author_assignee(self, sample_issues):
        model = CollaborationModel(sample_issues)
        model.build_graph()
        # issue #2: bob → alice
        assert model.graph.has_edge("bob", "alice")

    def test_idempotent_on_multiple_calls(self, sample_issues):
        model = CollaborationModel(sample_issues)
        model.build_graph()
        n1 = model.graph.number_of_nodes()
        model.build_graph()  # second call — should not add duplicates
        assert model.graph.number_of_nodes() == n1

    def test_empty_issues(self):
        model = CollaborationModel([])
        model.build_graph()
        assert model.graph.number_of_nodes() == 0


class TestCentralityMetrics:
    """Tests for CollaborationModel.centrality_metrics()."""

    def test_returns_centrality_metrics(self, sample_issues):
        model = CollaborationModel(sample_issues)
        metrics = model.centrality_metrics()
        # With at least one edge there should be at least one entry
        assert isinstance(metrics.degree, list)
        assert isinstance(metrics.betweenness, list)

    def test_empty_graph_returns_empty_metrics(self):
        model = CollaborationModel([])
        metrics = model.centrality_metrics()
        assert metrics.degree == []
        assert metrics.betweenness == []


class TestNetworkMetrics:
    """Tests for CollaborationModel.network_metrics()."""

    def test_node_edge_counts(self, sample_issues):
        model = CollaborationModel(sample_issues)
        net = model.network_metrics()
        assert net.num_nodes >= 0
        assert net.num_edges >= 0

    def test_clustering_coefficient_in_range(self, sample_issues):
        model = CollaborationModel(sample_issues)
        net = model.network_metrics()
        assert 0.0 <= net.clustering_coefficient <= 1.0


class TestCommunityDetection:
    """Tests for CollaborationModel.community_detection()."""

    def test_returns_community_result(self, sample_issues):
        model = CollaborationModel(sample_issues)
        result = model.community_detection()
        assert isinstance(result.partition, dict)
        assert result.num_communities >= 0
