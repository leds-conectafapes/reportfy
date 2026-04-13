"""Unit tests for DeveloperModel."""
from __future__ import annotations

import pytest

from reportfy.models.developer import DeveloperModel


class TestDeveloperLogins:
    """Tests for DeveloperModel.developer_logins()."""

    def test_returns_sorted_unique_logins(self, sample_issues):
        model = DeveloperModel(sample_issues)
        logins = model.developer_logins()
        assert logins == sorted(set(logins))
        assert "alice" in logins
        assert "bob" in logins
        assert "carol" in logins

    def test_empty_issues_returns_empty(self):
        model = DeveloperModel([])
        assert model.developer_logins() == []


class TestIssuesFor:
    """Tests for DeveloperModel.issues_for()."""

    def test_returns_only_authors_issues(self, sample_issues):
        model = DeveloperModel(sample_issues)
        alice_issues = model.issues_for("alice")
        assert all(i.author_login == "alice" for i in alice_issues)
        assert len(alice_issues) == 2  # issues #1 and #3

    def test_unknown_login_returns_empty(self, sample_issues):
        model = DeveloperModel(sample_issues)
        assert model.issues_for("nobody") == []


class TestComputeStats:
    """Tests for DeveloperModel.compute_stats()."""

    def test_alice_stats(self, sample_issues):
        model = DeveloperModel(sample_issues)
        stats = model.compute_stats("alice")
        assert stats.login == "alice"
        assert stats.total == 2
        assert stats.closed_count == 1   # issue #1
        assert stats.open_count == 1     # issue #3
        assert stats.closed_pct == 50.0

    def test_throughput_df_has_expected_columns(self, sample_issues):
        model = DeveloperModel(sample_issues)
        stats = model.compute_stats("alice")
        assert "Prometido (Criadas)" in stats.throughput_df.columns
        assert "Realizado (Fechadas)" in stats.throughput_df.columns
