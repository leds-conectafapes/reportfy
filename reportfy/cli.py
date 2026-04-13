"""CLI entry point for Reportfy — used directly and by the GitHub Action Docker container."""
import argparse
import os
import sys

from reportfy.core.config import ReportConfig


def _bool_env(key: str, default: bool = True) -> bool:
    val = os.getenv(key, str(default)).lower()
    return val in ("1", "true", "yes")


def build_config_from_env() -> ReportConfig:
    """Build ReportConfig entirely from environment variables (GitHub Action mode)."""
    return ReportConfig(
        github_token=os.environ["TOKEN"],
        repository=os.environ["REPOSITORY"],
        output_dir=os.getenv("REPORT_OUTPUT_DIR", "./report"),
        monte_carlo_simulations=int(os.getenv("MONTE_CARLO_SIMULATIONS", "1000")),
        mistral_api_key=os.getenv("MISTRAL_API_KEY", ""),
        mistral_model=os.getenv("MISTRAL_MODEL", "mistral-large-latest"),
        discord_bot_token=os.getenv("DISCORD_BOT_TOKEN", ""),
        discord_leadership_channel=os.getenv("DISCORD_LEADERSHIP_CHANNEL", ""),
        developers_config=os.getenv("DEVELOPERS_CONFIG", "./developers.json"),
        enable_organization_report=_bool_env("ENABLE_ORGANIZATION_REPORT", True),
        enable_repository_report=_bool_env("ENABLE_REPOSITORY_REPORT", True),
        enable_developer_report=_bool_env("ENABLE_DEVELOPER_REPORT", True),
        enable_team_report=_bool_env("ENABLE_TEAM_REPORT", True),
        enable_collaboration_report=_bool_env("ENABLE_COLLABORATION_REPORT", True),
        enable_discord_notifications=_bool_env("ENABLE_DISCORD_NOTIFICATIONS", False),
        enable_ai_summaries=_bool_env("ENABLE_AI_SUMMARIES", False),
        commit_reports=_bool_env("COMMIT_REPORTS", True),
    )


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="reportfy",
        description="Generate GitHub project management reports.",
    )
    parser.add_argument("--token", default=os.getenv("TOKEN"), help="GitHub Personal Access Token")
    parser.add_argument("--repository", default=os.getenv("REPOSITORY"), help="owner/repo")
    parser.add_argument("--output-dir", default=os.getenv("REPORT_OUTPUT_DIR", "./report"))
    parser.add_argument("--simulations", type=int, default=int(os.getenv("MONTE_CARLO_SIMULATIONS", "1000")))
    parser.add_argument("--mistral-key", default=os.getenv("MISTRAL_API_KEY", ""))
    parser.add_argument("--mistral-model", default=os.getenv("MISTRAL_MODEL", "mistral-large-latest"))
    parser.add_argument("--discord-token", default=os.getenv("DISCORD_BOT_TOKEN", ""))
    parser.add_argument("--discord-channel", default=os.getenv("DISCORD_LEADERSHIP_CHANNEL", ""))
    parser.add_argument("--developers-config", default=os.getenv("DEVELOPERS_CONFIG", "./developers.json"))
    parser.add_argument("--no-organization", action="store_true")
    parser.add_argument("--no-repository", action="store_true")
    parser.add_argument("--no-developer", action="store_true")
    parser.add_argument("--no-team", action="store_true")
    parser.add_argument("--no-collaboration", action="store_true")
    parser.add_argument("--discord", action="store_true", help="Send Discord notifications")
    parser.add_argument("--ai-summaries", action="store_true", help="Generate AI summaries via Mistral")
    parser.add_argument("--no-commit", action="store_true", help="Skip git commit of reports")
    return parser.parse_args(argv)


def main(argv=None):
    from reportfy.controllers.report_controller import ReportController

    if os.getenv("GITHUB_ACTIONS") == "true" or (os.getenv("TOKEN") and not argv):
        try:
            config = build_config_from_env()
        except KeyError as exc:
            print(f"[reportfy] Missing required environment variable: {exc}", file=sys.stderr)
            sys.exit(1)
    else:
        args = parse_args(argv)
        if not args.token or not args.repository:
            print(
                "[reportfy] --token and --repository are required (or set TOKEN / REPOSITORY env vars).",
                file=sys.stderr,
            )
            sys.exit(1)
        config = ReportConfig(
            github_token=args.token,
            repository=args.repository,
            output_dir=args.output_dir,
            monte_carlo_simulations=args.simulations,
            mistral_api_key=args.mistral_key,
            mistral_model=args.mistral_model,
            discord_bot_token=args.discord_token,
            discord_leadership_channel=args.discord_channel,
            developers_config=args.developers_config,
            enable_organization_report=not args.no_organization,
            enable_repository_report=not args.no_repository,
            enable_developer_report=not args.no_developer,
            enable_team_report=not args.no_team,
            enable_collaboration_report=not args.no_collaboration,
            enable_discord_notifications=args.discord,
            enable_ai_summaries=args.ai_summaries,
            commit_reports=not args.no_commit,
        )

    ReportController(config).run()
