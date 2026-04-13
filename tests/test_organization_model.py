"""Unit tests for OrganizationModel."""
from __future__ import annotations

import pytest

from reportfy.models.organization import OrganizationModel


class TestComputeStats:
    """Tests for OrganizationModel.compute_stats()."""

    def test_counts_open_and_closed(self, sample_issues):
        # sample_issues has 3 from planner (2 closed, 1 open) + 1 from other-repo (closed)
        model = OrganizationModel(sample_issues)
        stats = model.compute_stats()
        assert stats["total"] == 4
        assert stats["closed"] == 3
        assert stats["open"] == 1
        assert stats["percent_closed"] == 75.0

    def test_empty_issues(self):
        model = OrganizationModel([])
        stats = model.compute_stats()
        assert stats["total"] == 0
        assert stats["percent_closed"] == 0.0


class TestComputeBiweeklyDelivery:
    """Tests for OrganizationModel.compute_biweekly_delivery()."""

    def test_returns_dataframe_with_expected_columns(self, sample_issues):
        model = OrganizationModel(sample_issues)
        df = model.compute_biweekly_delivery()
        for col in ("period", "promised", "delivered", "percent_completed"):
            assert col in df.columns

    def test_promised_gte_delivered(self, sample_issues):
        model = OrganizationModel(sample_issues)
        df = model.compute_biweekly_delivery()
        assert (df["promised"] >= df["delivered"]).all()


class TestRunMonteCarlo:
    """Tests for OrganizationModel.run_monte_carlo()."""

    def test_returns_monte_carlo_result(self, sample_issues):
        model = OrganizationModel(sample_issues, simulations=20)
        result = model.run_monte_carlo()
        assert result.velocity_mean >= 0
        assert result.velocity_p10 <= result.velocity_p50 <= result.velocity_p90

    def test_returns_complete_when_no_remaining_work(self):
        from reportfy.models.issue import IssueModel
        from datetime import datetime, timezone
        # All issues closed
        issues = [
            IssueModel(
                number=i, title=f"Issue {i}", state="closed",
                repository="org/repo", html_url=f"https://github.com/org/repo/issues/{i}",
                created_at=datetime(2024, 1, i, tzinfo=timezone.utc),
                closed_at=datetime(2024, 1, i + 1, tzinfo=timezone.utc),
                author_login="dev", assignee_login=None, assignee_logins=[],
            )
            for i in range(1, 6)
        ]
        model = OrganizationModel(issues, simulations=20)
        result = model.run_monte_carlo()
        assert result.is_complete
