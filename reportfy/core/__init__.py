from reportfy.core.config import ReportConfig

__all__ = ["ReportConfig"]

# GitHubFetcher uses airbyte (optional heavy dependency) — import lazily
def __getattr__(name):
    if name == "GitHubFetcher":
        from reportfy.core.fetcher import GitHubFetcher  # noqa: PLC0415
        return GitHubFetcher
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
