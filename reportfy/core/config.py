"""Central configuration dataclass for Reportfy."""
from dataclasses import dataclass


@dataclass
class ReportConfig:
    # Required
    github_token: str
    repository: str  # "owner/repo"

    # Paths
    output_dir: str = "./report"
    developers_config: str = "./developers.json"

    # Analysis settings
    monte_carlo_simulations: int = 1000

    # AI — Mistral (optional)
    mistral_api_key: str = ""
    mistral_model: str = "mistral-large-latest"

    # Discord (optional)
    discord_bot_token: str = ""
    discord_leadership_channel: str = ""

    # Feature flags
    enable_organization_report: bool = True
    enable_repository_report: bool = True
    enable_developer_report: bool = True
    enable_team_report: bool = True
    enable_collaboration_report: bool = True
    enable_discord_notifications: bool = False
    enable_ai_summaries: bool = False
    commit_reports: bool = True

    def has_discord(self) -> bool:
        return bool(self.discord_bot_token) and self.enable_discord_notifications

    def has_ai(self) -> bool:
        return bool(self.mistral_api_key) and self.enable_ai_summaries
