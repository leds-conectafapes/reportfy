"""Unit tests for IssueModel."""
from __future__ import annotations

import pytest

from reportfy.models.issue import IssueModel


class TestIssueModelFromRow:
    """Tests for IssueModel.from_row() factory method."""

    def test_parses_basic_fields(self):
        row = {
            "number": 42,
            "title": "Fix the thing",
            "state": "closed",
            "repository": "org/repo",
            "html_url": "https://github.com/org/repo/issues/42",
            "created_at": "2024-03-01T10:00:00Z",
            "closed_at": "2024-03-05T12:00:00Z",
            "user": '{"login": "dev1"}',
            "assignee": '{"login": "dev2"}',
            "assignees": '[{"login": "dev2"}, {"login": "dev3"}]',
        }
        issue = IssueModel.from_row(row)

        assert issue.number == 42
        assert issue.title == "Fix the thing"
        assert issue.state == "closed"
        assert issue.author_login == "dev1"
        assert issue.assignee_login == "dev2"
        assert set(issue.assignee_logins) == {"dev2", "dev3"}

    def test_closed_at_none_when_missing(self):
        row = {
            "number": 1, "title": "Open issue", "state": "open",
            "repository": "org/repo", "html_url": "https://github.com/org/repo/issues/1",
            "created_at": "2024-01-01T00:00:00Z", "closed_at": None,
            "user": '{"login": "alice"}', "assignee": None, "assignees": "[]",
        }
        issue = IssueModel.from_row(row)
        assert issue.closed_at is None

    def test_is_closed_property(self):
        row = {
            "number": 1, "title": "T", "state": "closed",
            "repository": "r", "html_url": "u",
            "created_at": "2024-01-01T00:00:00Z", "closed_at": "2024-01-02T00:00:00Z",
            "user": '{"login": "a"}', "assignee": None, "assignees": "[]",
        }
        assert IssueModel.from_row(row).is_closed is True

    def test_is_open_property(self):
        row = {
            "number": 2, "title": "T", "state": "open",
            "repository": "r", "html_url": "u",
            "created_at": "2024-01-01T00:00:00Z", "closed_at": None,
            "user": '{"login": "a"}', "assignee": None, "assignees": "[]",
        }
        assert IssueModel.from_row(row).is_closed is False

    def test_all_assignees_deduplicates(self):
        row = {
            "number": 3, "title": "T", "state": "open",
            "repository": "r", "html_url": "u",
            "created_at": "2024-01-01", "closed_at": None,
            "user": '{"login": "a"}',
            "assignee": '{"login": "dev1"}',
            "assignees": '[{"login": "dev1"}, {"login": "dev2"}]',
        }
        issue = IssueModel.from_row(row)
        # dev1 appears in both assignee and assignees — should be deduplicated
        assert issue.all_assignees.count("dev1") == 1
        assert "dev2" in issue.all_assignees


class TestExtractLogin:
    """Tests for the static _extract_login helper."""

    def test_extracts_from_json_string(self):
        assert IssueModel._extract_login('{"login": "octocat"}') == "octocat"

    def test_extracts_from_dict(self):
        assert IssueModel._extract_login({"login": "octocat"}) == "octocat"

    def test_returns_none_for_none(self):
        assert IssueModel._extract_login(None) is None

    def test_returns_none_for_invalid_json(self):
        assert IssueModel._extract_login("not-json") is None


class TestExtractLogins:
    """Tests for the static _extract_logins helper."""

    def test_extracts_list(self):
        result = IssueModel._extract_logins('[{"login": "a"}, {"login": "b"}]')
        assert result == ["a", "b"]

    def test_returns_empty_for_none(self):
        assert IssueModel._extract_logins(None) == []

    def test_returns_empty_for_empty_list(self):
        assert IssueModel._extract_logins("[]") == []
