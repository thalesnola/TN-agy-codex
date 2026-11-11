# -*- coding: utf-8 -*-
"""Suíte de testes da ponte agy-codex."""

import json
import os
import sys
import tempfile
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from agy_codex.contracts import validate_task, validate_result, validate_review
from agy_codex.discovery import find_codex_bin, find_local_bin, get_tool_status
from agy_codex.router import route_task
from agy_codex.preflight import (
    PreflightError,
    validate_workspace,
    get_ollama_env,
    ensure_exclusive_model,
    OllamaSerialLock
)
from agy_codex.workspace import WorkspaceManager
from agy_codex.runner import run_codex, run_local
from agy_codex.mcp_server import handle_call_tool, TOOLS

# 1. Contratos
def test_contracts_validation():
    task = {"id": "t1", "operation": "review", "prompt": "check code"}
    validate_task(task)

    with pytest.raises(ValueError, match="Campo obrigatório ausente"):
        validate_task({"id": "t1"})

    with pytest.raises(ValueError, match="Operação inválida"):
        validate_task({"id": "t1", "operation": "invalid_op", "prompt": "x"})

    res = {"task_id": "t1", "status": "ok", "worker": "codex", "unreviewed_local_output": False}
    validate_result(res)

    rev = {"summary": "ok", "risk_level": "low", "findings": []}
    validate_review(rev)

# 2. Descoberta
def test_discovery():
    status = get_tool_status()
    assert "codex" in status
    assert "dsh" in status
    assert "qwen" in status
    assert "opencode" in status
    assert "ollama" in status
    # Na máquina Dell Pro Max Windows todos devem ser encontrados
    assert status["codex"]["found"] is True
    assert status["dsh"]["found"] is True
    assert status["qwen"]["found"] is True
    assert status["opencode"]["found"] is True
    assert status["ollama"]["found"] is True

# 3. Roteamento Hierárquico
def test_router_hierarchy():
    # 1. Review e Challenge vão ao Codex em sandbox read-only
    r_rev = route_task("review")
    assert r_rev.worker == "codex"
    assert r_rev.sandbox == "read-only"
    assert r_rev.is_local is False

    r_cha = route_task("challenge")
    assert r_cha.worker == "codex"
    assert r_cha.sandbox == "read-only"

    # 2. Delegate vai ao Codex em workspace-write
    r_del = route_task("delegate")
    assert r_del.worker == "codex"
    assert r_del.sandbox == "workspace-write"
    assert r_del.is_local is False

    # 3. RAG / Investigação vai ao OpenCode
    r_rag = route_task("rag")
    assert r_rag.worker == "opencode-local"
    assert r_rag.is_local is True

    # 4. Lote grande (>= 5 arquivos) vai ao Qwen Code local
    r_batch = route_task("local", files_count=5)
    assert r_batch.worker == "qwen-local"
    assert r_batch.is_local is True

    # 5. Código pequeno (1 a 4 arquivos) vai ao DSH
    r_small = route_task("code", files_count=2, prefer_local=True)
    assert r_small.worker == "dsh-local"
    assert r_small.is_local is True

    # 6. Refatoração pontual / quick review vai ao Ollama direct
    r_ref = route_task("refactor")
    assert r_ref.worker == "ollama-direct"
    assert r_ref.is_local is True

# 4. Preflight e Guards
def test_preflight_workspace_validation(tmp_path):
    ws = tmp_path / "valid_ws"
    ws.mkdir()
    (ws / "file.txt").write_text("hello")

    # Válido
    res_ws = validate_workspace(str(ws), ["file.txt"])
    assert res_ws == ws

    # Escape fora do workspace
    with pytest.raises(PreflightError, match="escapa do workspace"):
        validate_workspace(str(ws), ["../outside.txt"])

def test_preflight_ollama_env():
    env = get_ollama_env()
    assert env["OLLAMA_NUM_PARALLEL"] == "1"
    assert env["OLLAMA_CONTEXT_LENGTH"] == "32768"
    assert env["OLLAMA_FLASH_ATTENTION"] == "1"
    assert env["OLLAMA_KV_CACHE_TYPE"] == "q8_0"

    # Proíbe num_gpu=0
    with pytest.raises(PreflightError, match="Proibido executar com OLLAMA_NUM_GPU=0"):
        get_ollama_env({"OLLAMA_NUM_GPU": "0"})

@patch("agy_codex.preflight.get_resident_ollama_models")
@patch("subprocess.run")
def test_preflight_exclusive_model(mock_sub, mock_resident):
    mock_resident.return_value = ["other-model:latest"]
    mock_sub.return_value = MagicMock(returncode=0)

    ensure_exclusive_model("target-model:latest", ollama_bin="ollama")
    mock_sub.assert_called_once_with(["ollama", "stop", "other-model:latest"], capture_output=True, timeout=10)

def test_ollama_serial_lock():
    with OllamaSerialLock(timeout_sec=5) as lock1:
        assert lock1.acquired is True
        # Segunda tentativa imediata deve recusar/aguardar
        lock2 = OllamaSerialLock(timeout_sec=1)
        with pytest.raises(PreflightError, match="Timeout ao aguardar lock serial"):
            with lock2:
                pass

# 5. Workspace e Diff
def test_workspace_manager(tmp_path):
    mgr = WorkspaceManager(base_dir=str(tmp_path / "ws"))
    src = tmp_path / "src"
    src.mkdir()
    (src / "app.py").write_text("x = 1\n")

    stg = mgr.create_staging("task-123", str(src))
    assert (stg / "app.py").exists()

    # Faz modificação no staging
    (stg / "app.py").write_text("x = 2\n")
    diff = mgr.extract_diff(stg)
    assert "-x = 1" in diff
    assert "+x = 2" in diff

    mgr.cleanup("task-123")
    assert not stg.exists()

# 6. Runner com Fake Codex
def test_run_codex_with_mock(tmp_path):
    fake_py = Path(__file__).parent / "fake_codex.py"
    cmd = f"{sys.executable} {fake_py}"

    task = {
        "id": "t-mock-1",
        "operation": "review",
        "prompt": "verify architecture",
        "model": "gpt-6.1-sol",
        "sandbox": "read-only",
        "workspace": str(tmp_path)
    }

    with patch("agy_codex.runner.find_codex_bin", return_value=sys.executable):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="Fake review ok", stderr="")
            res = run_codex(task, codex_bin=sys.executable)
            assert res["status"] == "ok"
            assert res["worker"] == "codex"
            assert res["unreviewed_local_output"] is False

def test_run_local_unreviewed_flag():
    task = {
        "id": "loc-1",
        "worker": "dsh-local",
        "prompt": "refactor code"
    }
    with patch("agy_codex.runner.find_local_bin", return_value="fake_dsh"):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="Local result", stderr="")
            res = run_local(task)
            assert res["status"] == "ok"
            assert res["worker"] == "dsh-local"
            # MANDATÓRIO: saída local deve ser marcada unreviewed para conferência do AGY
            assert res["unreviewed_local_output"] is True

# 7. Servidor MCP
def test_mcp_tools():
    assert len(TOOLS) == 7
    tool_names = [t["name"] for t in TOOLS]
    assert "agy_codex_status" in tool_names
    assert "agy_codex_route" in tool_names
    assert "codex_ask" in tool_names
    assert "codex_review" in tool_names
    assert "codex_challenge" in tool_names
    assert "codex_delegate" in tool_names
    assert "local_dispatch" in tool_names

    # Teste chamada de status
    st = handle_call_tool("agy_codex_status", {})
    assert "codex" in st

    # Teste chamada de route
    rt = handle_call_tool("agy_codex_route", {"operation": "challenge"})
    assert rt["worker"] == "codex"
    assert rt["sandbox"] == "read-only"
