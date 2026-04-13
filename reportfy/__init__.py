"""
Reportfy — GitHub project management reporting library for GitHub Actions.

Generates dashboards, charts, Monte Carlo simulations, AI summaries (Mistral),
and Discord notifications from GitHub Issues data.

Architecture: Model-View-Controller (MVC)
"""

from reportfy.core.config import ReportConfig

# ReportController imports GitHubFetcher (airbyte) — import lazily to keep
# the package importable even when airbyte is not installed (e.g. test envs)
def __getattr__(name):
    if name == "ReportController":
        from reportfy.controllers.report_controller import ReportController  # noqa: PLC0415
        return ReportController
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__version__ = "0.1.0"
__all__ = ["ReportConfig", "ReportController"]
