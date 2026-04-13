"""BaseView — abstract base class for all Reportfy views."""
from __future__ import annotations

import os
from abc import ABC, abstractmethod

import matplotlib
matplotlib.use("Agg")  # non-interactive backend for server/CI environments
import matplotlib.pyplot as plt


class BaseView(ABC):
    """
    Abstract base class for all report views.

    A *view* is responsible solely for rendering — it consumes a model
    object and produces:
      - A markdown string (via ``render()``)
      - Chart image files as side-effects (via ``save_charts()``)

    Subclasses must implement ``render()`` and ``save_charts()``.
    """

    def __init__(self, output_dir: str):
        """
        Args:
            output_dir: Root directory where reports and chart images are saved.
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @abstractmethod
    def render(self) -> str:
        """Return the full markdown string for this report."""

    @abstractmethod
    def save_charts(self) -> dict[str, str]:
        """
        Generate and save all charts for this report.

        Returns:
            A dict mapping a human-readable chart name to its file path.
        """

    # ------------------------------------------------------------------
    # Shared chart helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _savefig(path: str) -> str:
        """Save current matplotlib figure to *path*, close it, and return path."""
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
        plt.tight_layout()
        plt.savefig(path, dpi=100)
        plt.close()
        return path

    @staticmethod
    def _monte_carlo_explanation() -> str:
        """Return a standard markdown table explaining Monte Carlo concepts."""
        return (
            "### Explicação da Simulação Monte Carlo\n\n"
            "| Conceito | Explicação |\n"
            "|---------|------------|\n"
            "| **Monte Carlo** | Técnica que usa 1 000 simulações com velocidades históricas"
            " para prever datas de conclusão com intervalos de confiança. |\n"
            "| **P10 (Otimista)** | Apenas 10 % de chance de terminar antes desta data. |\n"
            "| **P50 (Provável)** | Melhor estimativa realista — 50 % acima, 50 % abaixo. |\n"
            "| **P90 (Conservador)** | 90 % de chance de terminar antes desta data."
            " Seguro para comunicação de prazos. |\n\n"
        )
