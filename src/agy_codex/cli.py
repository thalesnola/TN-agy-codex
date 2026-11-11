# -*- coding: utf-8 -*-
"""Interface de Linha de Comando (CLI) para a ponte agy-codex."""

import argparse
import json
import sys
from typing import List, Optional

from .discovery import get_tool_status
from .router import route_task
from .runner import run_codex, run_local
from .mcp_server import serve_stdio

def main(argv: Optional[List[str]] = None):
    parser = argparse.ArgumentParser(
        prog="agy-codex",
        description="Ponte AGY -> Codex & Modelos Locais: servidor MCP stdio e CLI Python comandados pelo Antigravity."
    )
    sub = parser.add_subparsers(dest="subcommand", help="Subcomandos disponíveis")

    # status
    p_status = sub.add_parser("status", help="Verifica disponibilidade e caminhos dos binários")
    p_status.add_argument("--json", action="store_true", help="Saída em formato JSON")

    # route
    p_route = sub.add_parser("route", help="Consulta determinística da hierarquia agy-codex")
    p_route.add_argument("--operation", choices=["ask", "review", "challenge", "delegate", "local", "rag", "refactor"], default="ask")
    p_route.add_argument("--files", type=int, default=0, help="Quantidade de arquivos a processar")
    p_route.add_argument("--rag", action="store_true", help="Se necessita RAG de acervo local")
    p_route.add_argument("--second-opinion", action="store_true", help="Se exige 2ª família técnica")
    p_route.add_argument("--json", action="store_true", help="Saída em formato JSON")

    # ask
    p_ask = sub.add_parser("ask", help="Pergunta geral em sandbox read-only via Codex")
    p_ask.add_argument("prompt", help="Texto da consulta")
    p_ask.add_argument("--model", default="gpt-6.1-sol", help="Modelo Codex")

    # review
    p_rev = sub.add_parser("review", help="Revisão independente de diff/código via Codex")
    p_rev.add_argument("prompt", help="Código ou diff e critérios")
    p_rev.add_argument("--model", default="gpt-6.1-sol", help="Modelo Codex")

    # challenge
    p_cha = sub.add_parser("challenge", help="Desafio de plano ou trade-offs via Codex")
    p_cha.add_argument("prompt", help="Plano e trade-offs")
    p_cha.add_argument("--model", default="gpt-6.1-sol", help="Modelo Codex")

    # delegate
    p_del = sub.add_parser("delegate", help="Delegação de implementação em workspace isolado via Codex")
    p_del.add_argument("prompt", help="Instruções de implementação")
    p_del.add_argument("--workspace", default=".", help="Workspace raiz")
    p_del.add_argument("--files", nargs="*", default=[], help="Arquivos incluídos")
    p_del.add_argument("--model", default="gpt-6.1-sol", help="Modelo Codex")

    # local
    p_loc = sub.add_parser("local", help="Despacho para modelos locais sob lock serial")
    p_loc.add_argument("--worker", choices=["dsh-local", "qwen-local", "opencode-local", "ollama-direct"], default="dsh-local")
    p_loc.add_argument("prompt", help="Instruções para o modelo local")
    p_loc.add_argument("--model", default="", help="Modelo específico no Ollama")

    # mcp
    p_mcp = sub.add_parser("mcp", help="Inicia o servidor MCP stdio JSON-RPC 2.0")

    args = parser.parse_args(argv)

    if not args.subcommand or args.subcommand == "status":
        st = get_tool_status()
        if getattr(args, "json", False):
            print(json.dumps(st, indent=2, ensure_ascii=False))
        else:
            print("=== Status dos Componentes da Ponte agy-codex ===")
            for name, info in st.items():
                status_icon = "✅" if info["found"] else "❌"
                print(f"{status_icon} {name.upper()}:")
                print(f"    Path:    {info['path'] or 'NÃO ENCONTRADO'}")
                print(f"    Versão:  {info['version'] or '—'}")
        return

    if args.subcommand == "route":
        dec = route_task(
            operation=args.operation,
            files_count=args.files,
            needs_rag=args.rag,
            is_second_opinion=args.second_opinion
        )
        res = {
            "operation": args.operation,
            "worker": dec.worker,
            "model": dec.model,
            "sandbox": dec.sandbox,
            "reason": dec.reason,
            "is_local": dec.is_local
        }
        if args.json:
            print(json.dumps(res, indent=2, ensure_ascii=False))
        else:
            print(f"Operação:  {args.operation}")
            print(f"Worker:    {dec.worker} ({'LOCAL' if dec.is_local else 'NUVEM 2ª FAMÍLIA'})")
            print(f"Modelo:    {dec.model}")
            print(f"Sandbox:   {dec.sandbox}")
            print(f"Motivo:    {dec.reason}")
        return

    if args.subcommand in ["ask", "review", "challenge"]:
        task = {
            "operation": args.subcommand,
            "prompt": args.prompt,
            "model": args.model,
            "sandbox": "read-only"
        }
        res = run_codex(task)
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return

    if args.subcommand == "delegate":
        task = {
            "operation": "delegate",
            "prompt": args.prompt,
            "workspace": args.workspace,
            "files": args.files,
            "model": args.model,
            "sandbox": "workspace-write"
        }
        res = run_codex(task)
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return

    if args.subcommand == "local":
        task = {
            "worker": args.worker,
            "prompt": args.prompt,
            "model": args.model
        }
        res = run_local(task)
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return

    if args.subcommand == "mcp":
        serve_stdio()
        return

if __name__ == "__main__":
    main()
