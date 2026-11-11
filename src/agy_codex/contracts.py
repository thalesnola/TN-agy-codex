# -*- coding: utf-8 -*-
"""Contratos determinísticos e validação por JSON Schema da ponte agy-codex."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

SCHEMA_DIR = Path(__file__).resolve().parent.parent.parent / "schemas"

def load_schema(name: str) -> Dict[str, Any]:
    path = SCHEMA_DIR / f"{name}.schema.json"
    if not path.exists():
        path = SCHEMA_DIR / f"{name}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}

def validate_task(data: Dict[str, Any]) -> None:
    required = ["id", "operation", "prompt"]
    for r in required:
        if r not in data or not str(data[r]).strip():
            raise ValueError(f"Campo obrigatório ausente na tarefa: {r}")
    allowed_ops = ["ask", "review", "challenge", "delegate", "local", "status", "route"]
    if data["operation"] not in allowed_ops:
        raise ValueError(f"Operação inválida '{data['operation']}'. Permitidas: {allowed_ops}")
    allowed_workers = ["auto", "codex", "dsh-local", "qwen-local", "opencode-local", "ollama-direct"]
    if "worker" in data and data["worker"] not in allowed_workers:
        raise ValueError(f"Worker inválido '{data['worker']}'. Permitidos: {allowed_workers}")

def validate_result(data: Dict[str, Any]) -> None:
    required = ["task_id", "status", "worker", "unreviewed_local_output"]
    for r in required:
        if r not in data:
            raise ValueError(f"Campo obrigatório ausente no resultado: {r}")
    if data["status"] not in ["ok", "error", "rejected"]:
        raise ValueError(f"Status inválido '{data['status']}'")

def validate_review(data: Dict[str, Any]) -> None:
    required = ["summary", "risk_level", "findings"]
    for r in required:
        if r not in data:
            raise ValueError(f"Campo obrigatório ausente na revisão: {r}")
    if data["risk_level"] not in ["low", "medium", "high", "critical"]:
        raise ValueError(f"Nível de risco inválido '{data['risk_level']}'")
