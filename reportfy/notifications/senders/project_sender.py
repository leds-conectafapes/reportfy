"""ProjectMessageSender — sends the organisation report to a Discord channel."""
from __future__ import annotations

import os

from reportfy.ai.prompts import PromptType
from reportfy.ai.summarizer import MarkdownSummarizer
from reportfy.notifications.discord_client import DiscordClient
from reportfy.notifications.senders.base_sender import BaseNotificationSender


class ProjectMessageSender(BaseNotificationSender):
    """
    Sends the organisation-level project status to a Discord leadership channel.

    Pipeline:
      1. Read ``{output_dir}/organization_stats.md``.
      2. Generate a Mistral AI summary (``PromptType.PROJETO``).
      3. Post the summary text to the configured leadership channel.
      4. Post the burn-up chart as an image attachment.
    """

    def send(self) -> None:
        """Execute the project status notification pipeline."""
        report_path = os.path.join(self.config.output_dir, "organization_stats.md")
        if not os.path.exists(report_path):
            print(f"[ProjectMessageSender] Report not found: {report_path}")
            return

        channel = self.config.discord_leadership_channel
        if not channel:
            print("[ProjectMessageSender] No discord_leadership_channel configured.")
            return

        # Generate AI summary
        summary = ""
        if self.config.has_ai():
            summarizer = MarkdownSummarizer(
                api_key=self.config.mistral_api_key,
                filepaths=[report_path],
                prompt_type=PromptType.PROJETO,
                model=self.config.mistral_model,
            )
            summary = summarizer.generate_summary()
            print("[ProjectMessageSender] AI summary generated.")

        # Send text
        if summary:
            DiscordClient(
                token=self.config.discord_bot_token,
                channel_name=channel,
                message=summary,
            )

        # Send burn-up chart image
        burnup_path = os.path.join(
            self.config.output_dir, "organization_charts", "organization_burnup.png"
        )
        if os.path.exists(burnup_path):
            DiscordClient(
                token=self.config.discord_bot_token,
                channel_name=channel,
                image_path=burnup_path,
            )
