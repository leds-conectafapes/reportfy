"""Shared pytest fixtures for the Reportfy test suite."""
from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
import pytest

from reportfy.core.config import ReportConfig
from reportfy.models.issue import IssueModel


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _dt(year: int, month: int, day: int) -> datetime:
    return datetime(year, month, day, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Config fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def config() -> ReportConfig:
    """Minimal ReportConfig for unit tests (no real tokens needed)."""
    return ReportConfig(
        github_token="test-token",
        repository="leds-conectafapes/planner",
        output_dir="/tmp/reportfy_test",
        monte_carlo_simulations=50,   # small number for fast tests
    )


# ---------------------------------------------------------------------------
# Issue fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_issues() -> list[IssueModel]:
    """A small, deterministic set of IssueModel objects for unit tests."""
    return [
        IssueModel(
            number=1, title="Feature A", state="closed",
            repository="leds-conectafapes/planner",
            html_url="https://github.com/leds-conectafapes/planner/issues/1",
            created_at=_dt(2024, 1, 2), closed_at=_dt(2024, 1, 10),
            author_login="alice", assignee_login="alice", assignee_logins=[],
        ),
        IssueModel(
            number=2, title="Bug B", state="closed",
            repository="leds-conectafapes/planner",
            html_url="https://github.com/leds-conectafapes/planner/issues/2",
            created_at=_dt(2024, 1, 5), closed_at=_dt(2024, 1, 15),
            author_login="bob", assignee_login="alice", assignee_logins=["alice"],
        ),
        IssueModel(
            number=3, title="Task C", state="open",
            repository="leds-conectafapes/planner",
            html_url="https://github.com/leds-conectafapes/planner/issues/3",
            created_at=_dt(2024, 1, 8), closed_at=None,
            author_login="alice", assignee_login=None, assignee_logins=[],
        ),
        IssueModel(
            number=4, title="Task D", state="closed",
            repository="leds-conectafapes/other-repo",
            html_url="https://github.com/leds-conectafapes/other-repo/issues/4",
            created_at=_dt(2024, 1, 10), closed_at=_dt(2024, 1, 20),
            author_login="carol", assignee_login="carol", assignee_logins=[],
        ),
    ]


@pytest.fixture
def issues_df(sample_issues) -> pd.DataFrame:
    """Raw DataFrame as would come from Airbyte (used in controller tests)."""
    rows = []
    for i in sample_issues:
        rows.append({
            "number": i.number,
            "title": i.title,
            "state": i.state,
            "repository": i.repository,
            "html_url": i.html_url,
            "created_at": i.created_at.isoformat(),
            "closed_at": i.closed_at.isoformat() if i.closed_at else None,
            "user": f'{{"login": "{i.author_login}"}}',
            "assignee": f'{{"login": "{i.assignee_login}"}}' if i.assignee_login else None,
            "assignees": "[]",
        })
    return pd.DataFrame(rows)
