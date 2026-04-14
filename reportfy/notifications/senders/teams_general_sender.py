"""TeamsGeneralSender — sends a consolidated cross-team executive summary to Discord."""
from __future__ import annotations

import os

from reportfy.ai.prompts import PromptType
from reportfy.notifications.senders.base_sender import BaseNotificationSender


class TeamsGeneralSender(BaseNotificationSender):
    """
    Sends a consolidated executive weekly summary covering **all teams** to the
    configured Discord leadership channel.

    Pipeline:
      1. Collect all individual team markdown files from ``{output_dir}/teams/``.
      2. Feed all files together to Mistral (``PromptType.EQUIPES_GERAL_SEMANAL``).
      3. Post the consolidated cross-team summary to the leadership channel.
      4. Attach the summary delivery and throughput summary charts.
    """

    def send(self) -> None:
        """Execute the consolidated teams executive summary pipeline."""
        teams_dir = os.path.join(self.config.output_dir, "teams")
        channel = self.config.discord_leadership_channel

        if not os.path.isdir(teams_dir):
            print(f"[TeamsGeneralSender] Teams directory not found: {teams_dir}")
            return
        if not channel:
            print("[TeamsGeneralSender] No discord_leadership_channel configured.")
            return

        team_files = sorted([
            os.path.join(teams_dir, f)
            for f in os.listdir(teams_dir)
            if f.endswith(".md") and os.path.isfile(os.path.join(teams_dir, f))
        ])
        if not team_files:
            print("[TeamsGeneralSender] No team report files found.")
            return

        summary = self._ai_summary(team_files, PromptType.EQUIPES_GERAL_SEMANAL)
        if summary:
            print(f"[TeamsGeneralSender] Consolidated summary generated ({len(summary)} chars).")
            self._discord_send(
                message=f"**📋 Resumo Executivo Semanal — Todas as Equipes**\n\n{summary}",
                channel_name=channel,
            )

        graphs_dir = os.path.join(teams_dir, "graphs")
        for chart_name in ("summary_delivery.png", "summary_throughput.png"):
            chart_path = os.path.join(graphs_dir, chart_name)
            if os.path.exists(chart_path):
                self._discord_send(image_path=chart_path, channel_name=channel)

        print("[TeamsGeneralSender] Consolidated executive summary sent.")
