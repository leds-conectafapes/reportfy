"""BaseNotificationSender — abstract base for all notification senders."""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Optional

from reportfy.core.config import ReportConfig


class BaseNotificationSender(ABC):
    """
    Abstract base for notification senders.

    Provides shared helpers for AI summary generation and Discord dispatch so
    that concrete senders only implement ``send()`` without duplicating
    boilerplate.

    Subclasses must implement ``send()``.
    """

    #: Default delay (seconds) between successive Mistral API calls to stay
    #: within rate limits.  Override in subclasses when a different value
    #: is needed.
    _AI_DELAY: float = 0.0

    def __init__(self, config: ReportConfig):
        """
        Args:
            config: Shared runtime configuration (holds tokens and paths).
        """
        self.config = config

    @abstractmethod
    def send(self) -> None:
        """Execute the full send pipeline for this notification type."""

    # ------------------------------------------------------------------
    # Shared AI helper
    # ------------------------------------------------------------------

    def _ai_summary(
        self,
        filepaths: list[str],
        prompt_type,
        *,
        delay: Optional[float] = None,
    ) -> str:
        """
        Generate a Mistral AI summary from one or more markdown files.

        A no-op (returns ``""``) when AI is not configured or an error occurs,
        so callers do not need try/except.

        Args:
            filepaths: Markdown files to concatenate and summarise.
            prompt_type: ``PromptType`` enum value selecting the prompt template.
            delay: Seconds to sleep *after* the API call (rate-limiting).
                   Defaults to ``self._AI_DELAY``.

        Returns:
            Generated summary text, or ``""`` on failure.
        """
        if not self.config.has_ai():
            return ""

        try:
            from reportfy.ai.summarizer import MarkdownSummarizer

            summarizer = MarkdownSummarizer(
                api_key=self.config.mistral_api_key,
                filepaths=filepaths,
                prompt_type=prompt_type,
                model=self.config.mistral_model,
            )
            result = summarizer.generate_summary()
            wait = delay if delay is not None else self._AI_DELAY
            if wait > 0:
                time.sleep(wait)
            return result
        except FileNotFoundError as exc:
            print(f"  [AI] Skipping — file not found: {exc}")
            return ""
        except Exception as exc:  # noqa: BLE001
            print(f"  [AI] Error generating summary: {exc}")
            return ""

    # ------------------------------------------------------------------
    # Shared Discord helper
    # ------------------------------------------------------------------

    def _discord_send(
        self,
        message: str = "",
        *,
        channel_name: str = "",
        user_id: int = 0,
        image_path: str = "",
    ) -> None:
        """
        Dispatch a message (and/or image) via Discord.

        A no-op when Discord is not configured.

        Args:
            message: Text to send.
            channel_name: Channel name (used for channel messages).
            user_id: Discord user ID (used for DMs).
            image_path: Path to an image file to attach (optional).
        """
        if not self.config.has_discord():
            return

        try:
            from reportfy.notifications.discord_client import DiscordClient

            kwargs: dict = {"token": self.config.discord_bot_token}
            if channel_name:
                kwargs["channel_name"] = channel_name
            if user_id:
                kwargs["user_id"] = user_id
            if message:
                kwargs["message"] = message
            if image_path:
                kwargs["image_path"] = image_path

            DiscordClient(**kwargs)
        except Exception as exc:  # noqa: BLE001
            print(f"  [Discord] Error sending message: {exc}")
