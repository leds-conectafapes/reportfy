"""BaseNotificationSender — abstract base for all notification senders."""
from __future__ import annotations

from abc import ABC, abstractmethod

from reportfy.core.config import ReportConfig


class BaseNotificationSender(ABC):
    """
    Abstract base for notification senders.

    A *sender* is responsible for:
      1. Reading one or more generated report files.
      2. Optionally generating an AI summary via ``MarkdownSummarizer``.
      3. Dispatching the content (text + images) via ``DiscordClient``.

    Subclasses must implement ``send()``.
    """

    def __init__(self, config: ReportConfig):
        """
        Args:
            config: Shared runtime configuration (holds tokens and paths).
        """
        self.config = config

    @abstractmethod
    def send(self) -> None:
        """Execute the full send pipeline for this notification type."""
