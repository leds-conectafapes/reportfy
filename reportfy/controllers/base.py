"""BaseController — abstract base for all Reportfy domain controllers."""
from __future__ import annotations

import os
from abc import ABC, abstractmethod

from reportfy.core.config import ReportConfig


class BaseController(ABC):
    """
    Abstract base class for domain controllers.

    A *controller* is responsible for:
      1. Receiving pre-fetched data and a ReportConfig.
      2. Instantiating the appropriate Model with that data.
      3. Instantiating the appropriate View with the Model.
      4. Calling ``view.render()`` and persisting the result to disk.

    Subclasses must implement ``run()``.
    """

    def __init__(self, config: ReportConfig):
        """
        Args:
            config: Shared runtime configuration.
        """
        self.config = config
        os.makedirs(config.output_dir, exist_ok=True)

    @abstractmethod
    def run(self) -> str:
        """
        Execute the full pipeline for this controller.

        Returns:
            Path to the primary output markdown file.
        """

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def _save_report(self, content: str, filename: str) -> str:
        """
        Write *content* to ``{output_dir}/{filename}``.

        Args:
            content: Markdown string to write.
            filename: Relative filename inside output_dir.

        Returns:
            Absolute path to the written file.
        """
        path = os.path.join(self.config.output_dir, filename)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Report saved → {path}")
        return path
