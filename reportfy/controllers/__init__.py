from reportfy.controllers.base import BaseController
from reportfy.controllers.organization_controller import OrganizationController
from reportfy.controllers.repository_controller import RepositoryController
from reportfy.controllers.developer_controller import DeveloperController
from reportfy.controllers.team_controller import TeamController
from reportfy.controllers.collaboration_controller import CollaborationController

# ReportController imports GitHubFetcher (airbyte) — load lazily
def __getattr__(name):
    if name == "ReportController":
        from reportfy.controllers.report_controller import ReportController  # noqa: PLC0415
        return ReportController
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "BaseController",
    "OrganizationController",
    "RepositoryController",
    "DeveloperController",
    "TeamController",
    "CollaborationController",
    "ReportController",
]
