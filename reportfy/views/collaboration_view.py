"""CollaborationView — renders the developer collaboration network report."""
from __future__ import annotations

import os

import matplotlib.pyplot as plt
import networkx as nx

from reportfy.models.collaboration import CollaborationModel
from reportfy.views.base import BaseView


class CollaborationView(BaseView):
    """
    Renders the collaboration graph dashboard.

    Produces:
      - Network graph PNG visualisation
      - Markdown report with centrality, path, small-world, and community metrics
    """

    def __init__(
        self,
        model: CollaborationModel,
        output_dir: str,
        period_label: str = "",
        chart_filename: str = "collaboration_network.png",
    ):
        """
        Args:
            model: Pre-computed CollaborationModel (graph already built).
            output_dir: Directory where the network PNG and markdown are saved.
            period_label: Optional heading label, e.g. "Abril 2025" or "Semana 2025-04-07".
            chart_filename: PNG filename for the network graph.
        """
        super().__init__(output_dir)
        self.model = model
        self.period_label = period_label
        self.chart_filename = chart_filename
        self.model.build_graph()

    # ------------------------------------------------------------------
    # BaseView implementation
    # ------------------------------------------------------------------

    def render(self) -> str:
        """Build the full collaboration markdown report."""
        chart_paths = self.save_charts()
        centrality = self.model.centrality_metrics()
        net = self.model.network_metrics()
        communities = self.model.community_detection()

        title = f"# Relatório de Colaboração — {self.period_label}\n\n" if self.period_label else "# Relatório de Colaboração entre Desenvolvedores\n\n"
        md = title

        if chart_paths.get("network"):
            md += f"![Grafo de colaboração]({chart_paths['network']})\n\n"

        md += "## Métricas da Rede\n\n"
        md += "| Métrica | Valor |\n|--------|-------|\n"
        md += f"| Desenvolvedores (nós) | {net.num_nodes} |\n"
        md += f"| Colaborações (arestas) | {net.num_edges} |\n"
        md += f"| Coeficiente de Agrupamento | {net.clustering_coefficient:.4f} |\n"
        md += f"| Eficiência Global | {net.global_efficiency:.4f} |\n"
        if net.avg_path_length is not None:
            md += f"| Distância Média | {net.avg_path_length:.2f} |\n"
            md += f"| Diâmetro | {net.diameter} |\n"
        if net.sigma is not None:
            md += f"| Índice Small-World (σ) | {net.sigma} |\n"
            md += f"| Small-World? | {'Sim' if net.sigma > 1 else 'Não'} |\n"
        md += "\n"

        md += "## Hubs de Colaboração — Top Desenvolvedores\n\n"
        md += self._centrality_table("Grau (Degree)", centrality.degree)
        md += self._centrality_table("Intermediação (Betweenness)", centrality.betweenness)
        md += self._centrality_table("Proximidade (Closeness)", centrality.closeness)
        md += self._centrality_table("Vetor Próprio (Eigenvector)", centrality.eigenvector)

        md += "## Comunidades Detectadas\n\n"
        if communities.num_communities > 0:
            md += f"**Comunidades:** {communities.num_communities} | "
            md += f"**Modularidade:** {communities.modularity}\n\n"
            by_community: dict[int, list[str]] = {}
            for node, cid in communities.partition.items():
                by_community.setdefault(cid, []).append(node)
            for cid, members in sorted(by_community.items()):
                md += f"- **Comunidade {cid + 1}:** {', '.join(sorted(members))}\n"
            md += "\n"
        else:
            md += "_Nenhuma comunidade detectada._\n\n"

        md += self._small_world_explanation(net)
        return md

    def render_section(self, heading_level: int = 2) -> str:
        """
        Render a compact markdown section (no top-level H1) for embedding
        inside a larger monthly report.

        Args:
            heading_level: Markdown heading level for sub-sections (default 2 = ##).

        Returns:
            Markdown string without a leading H1 title.
        """
        chart_paths = self.save_charts()
        centrality = self.model.centrality_metrics()
        net = self.model.network_metrics()
        communities = self.model.community_detection()

        h = "#" * heading_level
        hh = "#" * (heading_level + 1)
        md = ""

        if chart_paths.get("network"):
            md += f"![Grafo de colaboração]({chart_paths['network']})\n\n"

        md += f"{h} Métricas da Rede\n\n"
        md += "| Métrica | Valor |\n|--------|-------|\n"
        md += f"| Desenvolvedores (nós) | {net.num_nodes} |\n"
        md += f"| Colaborações (arestas) | {net.num_edges} |\n"
        md += f"| Coeficiente de Agrupamento | {net.clustering_coefficient:.4f} |\n"
        md += f"| Eficiência Global | {net.global_efficiency:.4f} |\n"
        if net.avg_path_length is not None:
            md += f"| Distância Média | {net.avg_path_length:.2f} |\n"
            md += f"| Diâmetro | {net.diameter} |\n"
        if net.sigma is not None:
            md += f"| Índice Small-World (σ) | {net.sigma} |\n"
        md += "\n"

        md += f"{h} Hubs de Colaboração — Top Desenvolvedores\n\n"
        md += self._centrality_table_h(f"{hh} Grau (Degree)", centrality.degree)
        md += self._centrality_table_h(f"{hh} Intermediação (Betweenness)", centrality.betweenness)
        md += self._centrality_table_h(f"{hh} Proximidade (Closeness)", centrality.closeness)
        md += self._centrality_table_h(f"{hh} Vetor Próprio (Eigenvector)", centrality.eigenvector)

        md += f"{h} Comunidades Detectadas\n\n"
        if communities.num_communities > 0:
            md += f"**Comunidades:** {communities.num_communities} | **Modularidade:** {communities.modularity}\n\n"
            by_community: dict[int, list[str]] = {}
            for node, cid in communities.partition.items():
                by_community.setdefault(cid, []).append(node)
            for cid, members in sorted(by_community.items()):
                md += f"- **Comunidade {cid + 1}:** {', '.join(sorted(members))}\n"
            md += "\n"
        else:
            md += "_Nenhuma comunidade detectada._\n\n"

        return md

    def save_charts(self) -> dict[str, str]:
        """Generate and save the network graph visualisation."""
        path = os.path.join(self.output_dir, self.chart_filename)
        g = self.model.undirected
        if g.number_of_nodes() == 0:
            return {}
        plt.figure(figsize=(14, 10))
        pos = nx.spring_layout(g, seed=42, k=1.5)
        weights = [g[u][v].get("weight", 1) for u, v in g.edges()]
        nx.draw_networkx_nodes(g, pos, node_size=600, node_color="steelblue", alpha=0.85)
        nx.draw_networkx_labels(g, pos, font_size=8, font_color="white", font_weight="bold")
        nx.draw_networkx_edges(
            g, pos,
            width=[min(w * 0.5, 4) for w in weights],
            edge_color="gray",
            alpha=0.6,
            arrows=False,
        )
        plt.title("Grafo de Colaboração entre Desenvolvedores", fontsize=14)
        plt.axis("off")
        return {"network": self._savefig(path)}

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _centrality_table(label: str, data: list[tuple[str, float]]) -> str:
        if not data:
            return ""
        md = f"### {label}\n\n"
        md += "| Desenvolvedor | Score |\n|--------------|-------|\n"
        for login, score in data:
            md += f"| {login} | {score:.4f} |\n"
        md += "\n"
        return md

    @staticmethod
    def _centrality_table_h(heading: str, data: list[tuple[str, float]]) -> str:
        """Like _centrality_table but accepts a pre-formatted heading string."""
        if not data:
            return ""
        md = f"{heading}\n\n"
        md += "| Desenvolvedor | Score |\n|--------------|-------|\n"
        for login, score in data:
            md += f"| {login} | {score:.4f} |\n"
        md += "\n"
        return md

    @staticmethod
    def _small_world_explanation(net) -> str:
        md = "## Explicação das Métricas de Rede\n\n"
        md += "| Métrica | O que significa |\n|--------|------------------|\n"
        md += "| **Grau (Degree)** | Quantas conexões diretas um desenvolvedor tem. Alto grau = colabora com muitos. |\n"
        md += "| **Betweenness** | Quão frequentemente um dev aparece no caminho mais curto entre outros. Alto = ponte entre grupos. |\n"
        md += "| **Closeness** | Quão próximo um dev está de todos os outros. Alto = comunicação mais rápida. |\n"
        md += "| **Eigenvector** | Importância considerando a importância dos vizinhos. Alto = conectado a devs influentes. |\n"
        md += "| **Coef. Agrupamento** | Proporção de vizinhos que também colaboram entre si. Alto = clusters bem formados. |\n"
        if net.sigma is not None:
            md += f"| **Índice σ = {net.sigma}** | σ > 1 indica rede small-world: clusters locais + atalhos globais. |\n"
        md += "\n"
        return md
