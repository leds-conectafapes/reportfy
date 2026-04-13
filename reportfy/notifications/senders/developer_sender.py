"""DeveloperMessageSender — sends personalised feedback to each developer via Discord DM."""
from __future__ import annotations

import json
import os
import time

from reportfy.ai.prompts import PromptType
from reportfy.ai.summarizer import MarkdownSummarizer
from reportfy.notifications.discord_client import DiscordClient
from reportfy.notifications.senders.base_sender import BaseNotificationSender


class DeveloperMessageSender(BaseNotificationSender):
    """
    For each developer listed in ``developers.json``:

      1. Read their individual markdown report.
      2. Generate a Mistral AI summary (``PromptType.DESENVOLVEDOR``).
      3. Send the summary as a Discord DM.
      4. Attach the Prometido vs Realizado chart.
      5. Attach the Throughput chart.

    ``developers.json`` schema::

        [
          {"github_id": "octocat", "discord_id": 123456789012345678}
        ]
    """

    _DELAY_BETWEEN_DEVS = 10  # seconds — avoids Mistral rate limits

    def send(self) -> None:
        """Execute the developer feedback notification pipeline."""
        developers = self._load_developers()
        if not developers:
            print("[DeveloperMessageSender] No developers found in config.")
            return

        for dev in developers:
            github_id: str = dev.get("github_id", "")
            discord_id: int = int(dev.get("discord_id", 0))
            if not github_id or not discord_id:
                continue

            report_path = os.path.join(
                self.config.output_dir, "developers", f"{github_id}.md"
            )
            if not os.path.exists(report_path):
                print(f"[DeveloperMessageSender] Report not found for {github_id}")
                continue

            # AI summary
            summary = ""
            if self.config.has_ai():
                summarizer = MarkdownSummarizer(
                    api_key=self.config.mistral_api_key,
                    filepaths=[report_path],
                    prompt_type=PromptType.DESENVOLVEDOR,
                    model=self.config.mistral_model,
                )
                summary = summarizer.generate_summary()

            # DM text
            if summary and self.config.has_discord():
                DiscordClient(
                    token=self.config.discord_bot_token,
                    user_id=discord_id,
                    message=summary,
                )

            # DM charts
            graphs_dir = os.path.join(self.config.output_dir, "developers", "graphs")
            for chart_name in (
                f"{github_id}_prometido_realizado.png",
                f"{github_id}_throughput.png",
            ):
                chart_path = os.path.join(graphs_dir, chart_name)
                if os.path.exists(chart_path) and self.config.has_discord():
                    DiscordClient(
                        token=self.config.discord_bot_token,
                        user_id=discord_id,
                        image_path=chart_path,
                        message="",
                    )

            print(f"[DeveloperMessageSender] Sent to {github_id} (discord: {discord_id})")
            time.sleep(self._DELAY_BETWEEN_DEVS)

    def _load_developers(self) -> list[dict]:
        """Load the developers configuration JSON file."""
        path = self.config.developers_config
        if not os.path.exists(path):
            print(f"[DeveloperMessageSender] developers.json not found at {path}")
            return []
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
