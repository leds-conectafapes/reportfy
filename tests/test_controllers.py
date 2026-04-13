"""Integration-style tests for Controller classes (no real GitHub API calls)."""
from __future__ import annotations

import os
import tempfile

import pandas as pd
import pytest

from reportfy.controllers.collaboration_controller import CollaborationController
from reportfy.controllers.developer_controller import DeveloperController
from reportfy.controllers.organization_controller import OrganizationController
from reportfy.controllers.repository_controller import RepositoryController
from reportfy.controllers.team_controller import TeamController
from reportfy.core.config import ReportConfig


@pytest.fixture
def tmp_config(tmp_path):
    """ReportConfig pointing to a fresh temporary directory."""
    return ReportConfig(
        github_token="test-token",
        repository="leds-conectafapes/planner",
        output_dir=str(tmp_path),
        monte_carlo_simulations=10,
    )


class TestOrganizationController:
    """Tests for OrganizationController.run()."""

    def test_run_creates_report_file(self, tmp_config, issues_df):
        controller = OrganizationController(tmp_config, issues_df)
        path = controller.run()
        assert os.path.exists(path)
        assert path.endswith("organization_stats.md")

    def test_run_file_contains_expected_content(self, tmp_config, issues_df):
        controller = OrganizationController(tmp_config, issues_df)
        path = controller.run()
        content = open(path).read()
        assert "Estatísticas GitHub" in content


class TestRepositoryController:
    """Tests for RepositoryController.run()."""

    def test_run_creates_report_file(self, tmp_config, issues_df):
        controller = RepositoryController(tmp_config, issues_df)
        path = controller.run()
        assert os.path.exists(path)
        assert path.endswith("repository_stats.md")


class TestDeveloperController:
    """Tests for DeveloperController.run()."""

    def test_run_creates_summary_and_individual_files(self, tmp_config, issues_df):
        controller = DeveloperController(tmp_config, issues_df)
        summary_path = controller.run()
        assert os.path.exists(summary_path)
        # At least one individual developer file should exist
        dev_dir = os.path.join(tmp_config.output_dir, "developers")
        md_files = [f for f in os.listdir(dev_dir) if f.endswith(".md")]
        assert len(md_files) > 0


class TestTeamController:
    """Tests for TeamController.run()."""

    def test_run_with_empty_members_creates_summary(self, tmp_config, issues_df):
        empty_members = pd.DataFrame()
        controller = TeamController(tmp_config, issues_df, empty_members)
        summary_path = controller.run()
        assert os.path.exists(summary_path)


class TestCollaborationController:
    """Tests for CollaborationController.run()."""

    def test_run_creates_collaboration_report(self, tmp_config, issues_df):
        controller = CollaborationController(tmp_config, issues_df)
        path = controller.run()
        assert os.path.exists(path)
        assert path.endswith("collaboration_report.md")

    def test_run_file_contains_network_metrics(self, tmp_config, issues_df):
        controller = CollaborationController(tmp_config, issues_df)
        path = controller.run()
        content = open(path).read()
        assert "Métricas da Rede" in content
