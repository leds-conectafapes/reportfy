"""Fetches GitHub data via Airbyte source-github connector into a DuckDB cache."""
import airbyte as ab
import pandas as pd
import requests

from reportfy.core.config import ReportConfig


class GitHubFetcher:
    """
    Wraps the Airbyte source-github connector with a shared DuckDB cache.

    Supports two modes controlled by ``ReportConfig.repository``:

    - **Single repo**: ``"owner/repo"``  — fetches only that repository.
    - **Org wildcard**: ``"owner/*"``     — auto-discovers all repositories in
      the organisation and fetches all of them in a single Airbyte sync.
    """

    def __init__(self, config: ReportConfig):
        self.config = config
        self._cache = ab.get_default_cache()
        self._source = None
        self._repositories: list[str] = []  # resolved list (1 or many)

    # ------------------------------------------------------------------
    # Repository resolution
    # ------------------------------------------------------------------

    def _resolve_repositories(self) -> list[str]:
        """
        Return the list of repositories to fetch.

        If ``config.repository`` ends with ``/*``, all repos in the org are
        fetched via the GitHub REST API.  Otherwise the single value is used.
        """
        if self._repositories:
            return self._repositories

        repo = self.config.repository.strip()

        if repo.endswith("/*"):
            org = repo[:-2]  # strip "/*"
            self._repositories = self._list_org_repos(org)
            print(f"Org mode: found {len(self._repositories)} repositories in '{org}'.")
        else:
            self._repositories = [repo]

        return self._repositories

    def _list_org_repos(self, org: str) -> list[str]:
        """Return all repository full_names for *org* via the GitHub REST API."""
        repos: list[str] = []
        page = 1
        headers = {"Authorization": f"token {self.config.github_token}"}
        while True:
            resp = requests.get(
                f"https://api.github.com/orgs/{org}/repos",
                headers=headers,
                params={"per_page": 100, "type": "all", "page": page},
                timeout=30,
            )
            resp.raise_for_status()
            batch = resp.json()
            if not batch:
                break
            repos.extend(r["full_name"] for r in batch)
            if len(batch) < 100:
                break
            page += 1
        return repos

    # ------------------------------------------------------------------
    # Airbyte source
    # ------------------------------------------------------------------

    def _get_source(self):
        if self._source is None:
            repos = self._resolve_repositories()
            self._source = ab.get_source(
                "source-github",
                install_if_missing=True,
                config={
                    "repositories": repos,
                    "credentials": {
                        "personal_access_token": self.config.github_token
                    },
                },
            )
            self._source.check()
        return self._source

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fetch_issues(self) -> pd.DataFrame:
        """Fetch only the issues stream."""
        print(f"Fetching issues for {self.config.repository}...")
        source = self._get_source()
        source.select_streams(["issues"])
        source.read(cache=self._cache)
        if "issues" in self._cache:
            df = self._cache["issues"].to_pandas()
            print(f"Loaded {len(df)} issues.")
            return df
        print("No issues found.")
        return pd.DataFrame()

    def fetch_team_members(self) -> pd.DataFrame:
        """Fetch only the team_members stream."""
        print("Fetching team members...")
        source = self._get_source()
        source.select_streams(["team_members"])
        source.read(cache=self._cache)
        if "team_members" in self._cache:
            df = self._cache["team_members"].to_pandas()
            print(f"Loaded {len(df)} team members.")
            return df
        print("No team members found.")
        return pd.DataFrame()

    def fetch_all(self) -> dict[str, pd.DataFrame]:
        """Fetch issues and team_members in a single Airbyte sync pass."""
        source = self._get_source()
        source.select_streams(["issues", "team_members"])
        source.read(cache=self._cache)
        return {
            "issues": self._cache["issues"].to_pandas() if "issues" in self._cache else pd.DataFrame(),
            "team_members": self._cache["team_members"].to_pandas() if "team_members" in self._cache else pd.DataFrame(),
        }
