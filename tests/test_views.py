"""Unit tests for View classes — verifies markdown output and chart generation."""
from __future__ import annotations

import os
import tempfile

import pytest

from reportfy.models.collaboration import CollaborationModel
from reportfy.models.developer import DeveloperModel
from reportfy.models.organization import OrganizationModel
from reportfy.models.repository import RepositoryModel
from reportfy.models.team import TeamModel
from reportfy.views.collaboration_view import CollaborationView
from reportfy.views.developer_view import DeveloperView
from reportfy.views.organization_view import OrganizationView
from reportfy.views.repository_view import RepositoryView
from reportfy.views.team_view import TeamView


@pytest.fixture
def tmp_dir():
    """Create and yield a temporary output directory for each test."""
    with tempfile.TemporaryDirectory() as d:
        yield d


class TestOrganizationView:
    """Tests for OrganizationView."""

    def test_render_returns_markdown_string(self, sample_issues, tmp_dir):
        model = OrganizationModel(sample_issues, simulations=10)
        view = OrganizationView(model, tmp_dir)
        result = view.render()
        assert isinstance(result, str)
        assert "# Estatísticas GitHub" in result

    def test_render_contains_stats_table(self, sample_issues, tmp_dir):
        model = OrganizationModel(sample_issues, simulations=10)
        view = OrganizationView(model, tmp_dir)
        result = view.render()
        assert "Fechadas" in result
        assert "Total" in result

    def test_save_charts_creates_files(self, sample_issues, tmp_dir):
        model = OrganizationModel(sample_issues, simulations=10)
        view = OrganizationView(model, tmp_dir)
        charts = view.save_charts()
        for name, path in charts.items():
            if path:
                assert os.path.exists(path), f"Chart not found: {path}"


class TestRepositoryView:
    """Tests for RepositoryView."""

    def test_render_contains_repo_name(self, sample_issues, tmp_dir):
        model = RepositoryModel(sample_issues, simulations=10)
        view = RepositoryView(model, tmp_dir)
        result = view.render()
        assert "leds-conectafapes/planner" in result

    def test_render_contains_summary_section(self, sample_issues, tmp_dir):
        model = RepositoryModel(sample_issues, simulations=10)
        view = RepositoryView(model, tmp_dir)
        result = view.render()
        assert "Resumo Geral" in result


class TestDeveloperView:
    """Tests for DeveloperView."""

    def test_render_index_contains_all_devs(self, sample_issues, tmp_dir):
        model = DeveloperModel(sample_issues)
        view = DeveloperView(model, tmp_dir)
        result = view.render()
        for login in model.developer_logins():
            assert login in result

    def test_render_developer_contains_login(self, sample_issues, tmp_dir):
        model = DeveloperModel(sample_issues)
        view = DeveloperView(model, tmp_dir)
        stats = model.compute_stats("alice")
        result = view.render_developer(stats)
        assert "alice" in result

    def test_save_all_creates_md_files(self, sample_issues, tmp_dir):
        model = DeveloperModel(sample_issues)
        view = DeveloperView(model, tmp_dir)
        view.save_all_developer_reports()
        dev_dir = os.path.join(tmp_dir, "developers")
        for login in model.developer_logins():
            assert os.path.exists(os.path.join(dev_dir, f"{login}.md"))


class TestCollaborationView:
    """Tests for CollaborationView."""

    def test_render_contains_metrics_header(self, sample_issues, tmp_dir):
        model = CollaborationModel(sample_issues)
        view = CollaborationView(model, tmp_dir)
        result = view.render()
        assert "Métricas da Rede" in result

    def test_render_contains_community_section(self, sample_issues, tmp_dir):
        model = CollaborationModel(sample_issues)
        view = CollaborationView(model, tmp_dir)
        result = view.render()
        assert "Comunidades" in result
