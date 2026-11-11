# -*- coding: utf-8 -*-
"""Motor determinístico de roteamento e hierarquização para a ponte agy-codex."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

@dataclass
class RouteDecision:
    worker: str
    model: str
    sandbox: str
    reason: str
    is_local: bool

def route_task(
    operation: str,
    files_count: int = 0,
    needs_rag: bool = False,
    is_second_opinion: bool = False,
    prefer_local: bool = False
) -> RouteDecision:
    """Decide determinística e hierarquicamente qual executor e modelo devem atender a tarefa.
    
    Hierarquia:
    1. Revisão, desafio e segunda opinião de 2ª família -> Codex (read-only, gpt-6.1-sol).
    2. Delegação de implementação isolada em 2ª família -> Codex (workspace-write, gpt-6.1-sol).
    3. Consulta de acervo / memória técnica local -> OpenCode (nemotron-3.5-lightning:30b-a3b).
    4. Lote mecânico grande (>= 5 arquivos) local -> Qwen Code (Qwen3-Coder-Next :NOTPL 36 GB).
    5. Edição/código pequeno (1 a 4 arquivos) local -> DSH (gpt-oss:20b).
    6. Refatoração rápida / quick review local -> Ollama direct (qwen3-coder:30b).
    7. Pergunta/consulta geral na 2ª família -> Codex (read-only, gpt-6.1-sol / gpt-6-luna).
    """
    op = operation.lower().strip()

    # 1. Auditoria e Desafio em Segunda Família
    if op in ["review", "challenge"] or is_second_opinion:
        return RouteDecision(
            worker="codex",
            model="gpt-6.1-sol",
            sandbox="read-only",
            reason="Auditoria independente ou estresse arquitetural por segunda família técnica.",
            is_local=False
        )

    # 2. Delegação de Implementação Isolada em Segunda Família
    if op == "delegate" and not prefer_local:
        return RouteDecision(
            worker="codex",
            model="gpt-6.1-sol",
            sandbox="workspace-write",
            reason="Implementação isolada em 2ª família devolvendo apenas patch e JSON.",
            is_local=False
        )

    # 3. Consulta de Acervo / RAG Estruturado Local
    if needs_rag or op in ["rag", "ingest", "investigate"]:
        return RouteDecision(
            worker="opencode-local",
            model="nemotron-3.5-lightning:30b-a3b",
            sandbox="read-only",
            reason="Investigação de acervo e RAG agentico local (custo zero offline).",
            is_local=True
        )

    # 4. Lotes Mecânicos Grandes (>= 5 arquivos)
    if files_count >= 5 or (prefer_local and files_count >= 5):
        return RouteDecision(
            worker="qwen-local",
            model="hf.co/unsloth/Qwen3-Coder-Next-GGUF:UD-Q3_K_XL",
            sandbox="workspace-write",
            reason="Lote mecânico pesado em arquivo único sem fatiar no hardware local.",
            is_local=True
        )

    # 5. Código/Edição Pequena (1 a 4 arquivos)
    if (1 <= files_count <= 4) or (prefer_local and op in ["code", "edit", "local_code"]):
        return RouteDecision(
            worker="dsh-local",
            model="gpt-oss:20b",
            sandbox="workspace-write",
            reason="Código ou edição rápida local com DeepSeek Harness (1 a 4 arquivos).",
            is_local=True
        )

    # 6. Refatoração Rápida / Revisão Local
    if op in ["refactor", "quick_review", "local_review"]:
        return RouteDecision(
            worker="ollama-direct",
            model="qwen3-coder:30b",
            sandbox="read-only",
            reason="Refatoração pontual ou revisão local rápida via MCP ollama-router.",
            is_local=True
        )

    # 7. Pergunta Geral / Raciocínio (Default Codex)
    return RouteDecision(
        worker="codex",
        model="gpt-6.1-sol",
        sandbox="read-only",
        reason="Consulta geral e raciocínio profundo via Codex CLI.",
        is_local=False
    )
