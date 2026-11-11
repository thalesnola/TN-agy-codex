# -*- coding: utf-8 -*-
"""Servidor MCP stdio para o Google Antigravity (AGY) comandar o Codex e modelos locais."""

import json
import sys
from typing import Any, Dict, List

from .discovery import get_tool_status
from .router import route_task
from .runner import run_codex, run_local

TOOLS = [
    {
        "name": "agy_codex_status",
        "description": "Verifica disponibilidade, versões e caminhos do Codex CLI e executores locais (dsh, qwen, opencode, ollama).",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "agy_codex_route",
        "description": "Consulta determinística da hierarquia agy-codex: seleciona o menor modelo e executor capaz de resolver a tarefa.",
        "inputSchema": {
            "type": "object",
            "required": ["operation"],
            "properties": {
                "operation": { "type": "string", "enum": ["ask", "review", "challenge", "delegate", "local", "rag", "refactor"] },
                "files_count": { "type": "integer", "description": "Quantidade de arquivos a processar", "default": 0 },
                "needs_rag": { "type": "boolean", "description": "Se a tarefa exige consulta a acervo indexado", "default": False },
                "is_second_opinion": { "type": "boolean", "description": "Se exige auditoria de 2ª família técnica", "default": False }
            }
        }
    },
    {
        "name": "codex_ask",
        "description": "Consulta geral ou raciocínio à segunda família técnica (Codex / gpt-6.1-sol) em sandbox read-only.",
        "inputSchema": {
            "type": "object",
            "required": ["prompt"],
            "properties": {
                "prompt": { "type": "string", "description": "Pergunta ou instrução" },
                "model": { "type": "string", "default": "gpt-6.1-sol" }
            }
        }
    },
    {
        "name": "codex_review",
        "description": "Auditoria independente de código ou diff pela segunda família técnica (Codex) em sandbox read-only.",
        "inputSchema": {
            "type": "object",
            "required": ["prompt"],
            "properties": {
                "prompt": { "type": "string", "description": "Diff ou código e critérios de revisão" },
                "model": { "type": "string", "default": "gpt-6.1-sol" }
            }
        }
    },
    {
        "name": "codex_challenge",
        "description": "Estresse e desafio de trade-offs arquiteturais pela segunda família técnica (Codex) em sandbox read-only.",
        "inputSchema": {
            "type": "object",
            "required": ["prompt"],
            "properties": {
                "prompt": { "type": "string", "description": "Plano arquitetural e trade-offs a desafiar" },
                "model": { "type": "string", "default": "gpt-6.1-sol" }
            }
        }
    },
    {
        "name": "codex_delegate",
        "description": "Delegação de implementação em workspace isolado efêmero ao Codex, retornando patch e JSON conciso.",
        "inputSchema": {
            "type": "object",
            "required": ["prompt", "workspace"],
            "properties": {
                "prompt": { "type": "string", "description": "Instruções objetivas de implementação" },
                "workspace": { "type": "string", "description": "Caminho do diretório de trabalho raiz" },
                "files": { "type": "array", "items": { "type": "string" }, "description": "Lista de arquivos incluídos" },
                "model": { "type": "string", "default": "gpt-6.1-sol" }
            }
        }
    },
    {
        "name": "local_dispatch",
        "description": "Despacha tarefa a executores locais Ollama (dsh-local, qwen-local, opencode-local) sob lock serial estrito.",
        "inputSchema": {
            "type": "object",
            "required": ["worker", "prompt"],
            "properties": {
                "worker": { "type": "string", "enum": ["dsh-local", "qwen-local", "opencode-local", "ollama-direct"] },
                "prompt": { "type": "string", "description": "Instruções para o modelo local" },
                "model": { "type": "string", "description": "Nome do modelo no Ollama" }
            }
        }
    }
]

def handle_call_tool(name: str, arguments: Dict[str, Any]) -> Any:
    if name == "agy_codex_status":
        return get_tool_status()

    if name == "agy_codex_route":
        decision = route_task(
            operation=arguments.get("operation", "ask"),
            files_count=arguments.get("files_count", 0),
            needs_rag=arguments.get("needs_rag", False),
            is_second_opinion=arguments.get("is_second_opinion", False)
        )
        return {
            "worker": decision.worker,
            "model": decision.model,
            "sandbox": decision.sandbox,
            "reason": decision.reason,
            "is_local": decision.is_local
        }

    if name in ["codex_ask", "codex_review", "codex_challenge"]:
        task = {
            "operation": name.replace("codex_", ""),
            "prompt": arguments.get("prompt", ""),
            "model": arguments.get("model", "gpt-6.1-sol"),
            "sandbox": "read-only"
        }
        return run_codex(task)

    if name == "codex_delegate":
        task = {
            "operation": "delegate",
            "prompt": arguments.get("prompt", ""),
            "workspace": arguments.get("workspace", "."),
            "files": arguments.get("files", []),
            "model": arguments.get("model", "gpt-6.1-sol"),
            "sandbox": "workspace-write"
        }
        return run_codex(task)

    if name == "local_dispatch":
        task = {
            "worker": arguments.get("worker", "dsh-local"),
            "prompt": arguments.get("prompt", ""),
            "model": arguments.get("model", "")
        }
        return run_local(task)

    raise ValueError(f"Ferramenta desconhecida: {name}")

def serve_stdio():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            req_id = req.get("id")
            method = req.get("method")
            params = req.get("params", {})

            if method == "initialize":
                res = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "serverInfo": { "name": "agy-codex-mcp", "version": "1.0.0" },
                        "capabilities": { "tools": {} }
                    }
                }
            elif method == "tools/list":
                res = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": { "tools": TOOLS }
                }
            elif method == "tools/call":
                tool_name = params.get("name", "")
                args = params.get("arguments", {})
                tool_result = handle_call_tool(tool_name, args)
                res = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{ "type": "text", "text": json.dumps(tool_result, ensure_ascii=False, indent=2) }]
                    }
                }
            else:
                res = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": { "code": -32601, "message": f"Método não suportado: {method}" }
                }
        except Exception as e:
            res = {
                "jsonrpc": "2.0",
                "id": None,
                "error": { "code": -32603, "message": str(e) }
            }

        sys.stdout.write(json.dumps(res, ensure_ascii=False) + "\n")
        sys.stdout.flush()

if __name__ == "__main__":
    serve_stdio()
