"""CompetenceMessageSender — generates and saves developer competency assessments."""
from __future__ import annotations

import json
import os

from reportfy.ai.prompts import PromptType
from reportfy.notifications.senders.base_sender import BaseNotificationSender


class CompetenceMessageSender(BaseNotificationSender):
    """
    For each developer listed in ``developers.json``:

      1. Read their individual markdown report.
      2. Generate a Mistral AI competency assessment (``PromptType.COMPETENCIA``).
      3. Save the result as ``{output_dir}/developers/{github_id}_competence.md``.

    This sender writes files — it does not post to Discord.
    """

    _AI_DELAY: float = 10  # seconds between devs — avoids Mistral rate limits

    def send(self) -> None:
        """Execute the competency assessment generation pipeline."""
        if not self.config.has_ai():
            print("[CompetenceMessageSender] AI is not configured — skipping.")
            return

        developers = self._load_developers()
        if not developers:
            print("[CompetenceMessageSender] No developers found in config.")
            return

        for dev in developers:
            github_id: str = dev.get("github_id", "")
            if not github_id:
                continue

            report_path = os.path.join(
                self.config.output_dir, "developers", f"{github_id}.md"
            )
            if not os.path.exists(report_path):
                print(f"[CompetenceMessageSender] Report not found for {github_id}")
                continue

            assessment = self._ai_summary(
                [report_path], PromptType.COMPETENCIA, delay=self._AI_DELAY
            )
            if not assessment:
                continue

            output_path = os.path.join(
                self.config.output_dir, "developers", f"{github_id}_competence.md"
            )
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(assessment)
            print(f"[CompetenceMessageSender] Assessment saved → {output_path}")

    def _load_developers(self) -> list[dict]:
        """Load the developers configuration JSON file."""
        path = self.config.developers_config
        if not os.path.exists(path):
            print(f"[CompetenceMessageSender] developers.json not found at {path}")
            return []
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
