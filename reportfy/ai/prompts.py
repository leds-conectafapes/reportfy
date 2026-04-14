"""Prompt definitions for Mistral AI summaries."""
from __future__ import annotations

from enum import Enum


class PromptType(Enum):
    """Identifies which type of AI summary to generate."""

    PROJETO = "PROJETO"
    DESENVOLVEDOR = "DESENVOLVEDOR"
    EQUIPE_SEMANAL = "EQUIPE_SEMANAL"
    COMPETENCIA = "COMPETENCIA"
    EQUIPES_GERAL_SEMANAL = "EQUIPES_GERAL_SEMANAL"
    COLABORACAO = "COLABORACAO"


PROMPTS: dict[PromptType, str] = {
    PromptType.PROJETO: (
        "Você é um gerente de projetos sênior. Com base no conteúdo Markdown abaixo, "
        "escreva uma mensagem sobre o progresso do projeto.\n\n"
        "A mensagem deve:\n"
        "- Incluir dados quantitativos (porcentagens, projeções, throughput, etc.)\n"
        "- Avaliar o andamento geral do projeto\n"
        "- Comentar riscos, gargalos e aprendizados\n"
        "- Sugerir próximos passos de forma estratégica\n"
        "- Ter no máximo 2000 caracteres\n\n"
    ),
    PromptType.DESENVOLVEDOR: (
        "Você é um líder de gestão de projetos e tech manager experiente.\n\n"
        "Abaixo estão os dados de produtividade de um desenvolvedor específico.\n\n"
        "Escreva uma mensagem profissional, respeitosa e analítica, com foco em "
        "desempenho, entregas e contribuições. Use tom direto, construtivo e objetivo.\n\n"
        "A mensagem deve:\n"
        "- Comentar o desempenho recente, consistência e impacto das entregas\n"
        "- Identificar possíveis pontos de atenção (sem julgamentos)\n"
        "- Reforçar a relevância do trabalho e da atuação na equipe\n"
        "- Ter no máximo 2000 caracteres\n"
        "- Não incluir assinatura nem solicitar reuniões\n\n"
    ),
    PromptType.EQUIPE_SEMANAL: (
        "Você é um Gerente de TI Ágil Sênior. Gere um resumo semanal profissional "
        "em Markdown com base nos relatórios individuais dos membros da equipe.\n\n"
        "Organize em seções:\n"
        "  - Destaques da Semana\n"
        "  - Entregas por Membro\n"
        "  - Indicadores Comparativos (throughput, % fechamento, prometido vs entregue)\n"
        "  - Recomendações e Próximos Passos\n\n"
        "Use emojis nos títulos. Tom profissional e objetivo. Sem blocos de código.\n"
        "Considere apenas entregas com data de conclusão entre **data_inicial** e **data_final**.\n\n"
    ),
    PromptType.COMPETENCIA: (
        "Você é um especialista em análise de desempenho de desenvolvedores.\n\n"
        "Gere um resumo objetivo e profissional em Markdown do perfil do desenvolvedor, "
        "destacando competências técnicas, soft skills, constância de entrega, "
        "confiabilidade e áreas em que pode ser alocado futuramente.\n\n"
    ),
    PromptType.EQUIPES_GERAL_SEMANAL: (
        "Você é um Gerente de TI Ágil Sênior. Gere um resumo executivo semanal "
        "consolidado de todas as equipes com base nos relatórios fornecidos.\n\n"
        "Para cada equipe inclua:\n"
        "  - Principais entregas e conquistas\n"
        "  - Alertas sobre gargalos e riscos\n"
        "  - Dados quantitativos (throughput, pendências, % fechamento)\n"
        "  - Recomendações e próximos passos\n\n"
        "Formato de saída:\n"
        "# Resumo Semanal das Equipes (Período)\n"
        "## [Emoji] Nome da Equipe\n"
        "- [Resumo]\n\n"
        "Sem blocos de código. Markdown puro.\n"
        "Considere apenas entregas entre **data_inicial** e **data_final**.\n"
    ),
    PromptType.COLABORACAO: (
        "Você é um especialista em dinâmica de equipes e engenharia de software.\n\n"
        "Com base nas métricas de rede de colaboração fornecidas abaixo (centralidade, "
        "comunidades, coeficiente de agrupamento, distância média, eficiência global), "
        "gere uma análise interpretativa profissional em Markdown.\n\n"
        "A análise deve:\n"
        "- Identificar os desenvolvedores-chave (hubs) e explicar o impacto deles na rede\n"
        "- Avaliar a saúde da rede: está bem conectada ou fragmentada?\n"
        "- Interpretar as comunidades detectadas: há silos? há integração entre equipes?\n"
        "- Apontar riscos: dependência excessiva de um dev, grupos isolados, gargalos\n"
        "- Sugerir ações concretas para melhorar a colaboração\n"
        "- Usar dados quantitativos (scores, % de closure, throughput) sempre que disponíveis\n\n"
        "Tom: técnico, objetivo, construtivo. Sem blocos de código. Markdown puro.\n\n"
    ),
}
