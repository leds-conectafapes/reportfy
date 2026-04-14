"""TeamWeeklySender — sends a weekly AI summary per team to a Discord channel."""
from __future__ import annotations

import os

from reportfy.ai.prompts import PromptType
from reportfy.notifications.senders.base_sender import BaseNotificationSender


class TeamWeeklySender(BaseNotificationSender):
    """
    For each team report found in ``{output_dir}/teams/``:

      1. Read the individual team markdown file.
      2. Generate a Mistral AI weekly summary (``PromptType.EQUIPE_SEMANAL``).
      3. Post the summary to the configured Discord leadership channel.
      4. Attach the team biweekly throughput chart.
    """

    def send(self) -> None:
        """Execute the team-weekly notification pipeline for all teams."""
        teams_dir = os.path.join(self.config.output_dir, "teams")
        channel = self.config.discord_leadership_channel

        if not os.path.isdir(teams_dir):
            print(f"[TeamWeeklySender] Teams directory not found: {teams_dir}")
            return
        if not channel:
            print("[TeamWeeklySender] No discord_leadership_channel configured.")
            return

        team_files = sorted([
            os.path.join(teams_dir, f)
            for f in os.listdir(teams_dir)
            if f.endswith(".md") and os.path.isfile(os.path.join(teams_dir, f))
        ])
        if not team_files:
            print("[TeamWeeklySender] No team report files found.")
            return

        for team_path in team_files:
            team_slug = os.path.splitext(os.path.basename(team_path))[0]
            summary = self._ai_summary([team_path], PromptType.EQUIPE_SEMANAL)
            if summary:
                self._discord_send(
                    message=f"**📊 Resumo Semanal — {team_slug}**\n\n{summary}",
                    channel_name=channel,
                )

            chart_path = os.path.join(
                self.config.output_dir, "teams", "graphs",
                f"{team_slug}_biweekly.png",
            )
            if os.path.exists(chart_path):
                self._discord_send(image_path=chart_path, channel_name=channel)

            print(f"[TeamWeeklySender] Sent weekly summary for team: {team_slug}")
