"""Fetches GitHub data via Airbyte source-github connector into a DuckDB cache."""
import airbyte as ab
import pandas as pd

from reportfy.core.config import ReportConfig


class GitHubFetcher:
    """Wraps the Airbyte source-github connector with a shared DuckDB cache."""

    def __init__(self, config: ReportConfig):
        self.config = config
        self._cache = ab.get_default_cache()
        self._source = None

    def _get_source(self):
        if self._source is None:
            self._source = ab.get_source(
                "source-github",
                install_if_missing=True,
                config={
                    "repositories": [self.config.repository],
                    "credentials": {
                        "personal_access_token": self.config.github_token
                    },
                },
            )
            self._source.check()
        return self._source

    def fetch_issues(self) -> pd.DataFrame:
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
        """Fetch both issues and team_members in a single pass."""
        source = self._get_source()
        source.select_streams(["issues", "team_members"])
        source.read(cache=self._cache)
        return {
            "issues": self._cache["issues"].to_pandas() if "issues" in self._cache else pd.DataFrame(),
            "team_members": self._cache["team_members"].to_pandas() if "team_members" in self._cache else pd.DataFrame(),
        }
