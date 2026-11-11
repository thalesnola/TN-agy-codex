# -*- coding: utf-8 -*-
"""Executores da ponte agy-codex: despacho do Codex CLI e modelos locais Ollama."""

import json
import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Optional

from .discovery import find_codex_bin, find_local_bin
from .preflight import OllamaSerialLock, ensure_exclusive_model, get_ollama_env, validate_workspace
from .workspace import WorkspaceManager

def run_codex(task: Dict[str, Any], codex_bin: Optional[str] = None, timeout_sec: int = 120) -> Dict[str, Any]:
    bin_path = codex_bin or find_codex_bin()
    if not bin_path:
        return {
            "task_id": task.get("id", "unknown"),
            "status": "error",
            "worker": "codex",
            "model": task.get("model", ""),
            "output_text": "",
            "patch": "",
            "unreviewed_local_output": False,
            "error_message": "Binário oficial do Codex não encontrado na máquina.",
            "duration_s": 0.0,
            "artifacts": []
        }

    task_id = task.get("id", f"codex-{int(time.time())}")
    prompt = task.get("prompt", "")
    model = task.get("model", "gpt-6.1-sol")
    sandbox = task.get("sandbox", "read-only")
    raw_workspace = task.get("workspace", os.getcwd())

    ws_mgr = WorkspaceManager()
    staging_ws: Optional[Path] = None
    exec_ws = Path(raw_workspace).resolve()

    if sandbox == "workspace-write":
        staging_ws = ws_mgr.create_staging(task_id, raw_workspace, task.get("files"))
        exec_ws = staging_ws

    start_t = time.time()
    with tempfile.TemporaryDirectory() as t:
        last_msg_file = Path(t) / "last_message.txt"
        cmd = [
            bin_path,
            "exec",
            "-m", model,
            "-s", sandbox,
            "--skip-git-repo-check",
            "--ephemeral",
            "-o", str(last_msg_file),
            "-C", str(exec_ws),
            prompt
        ]

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_sec)
            duration = round(time.time() - start_t, 2)
            out_text = ""
            if last_msg_file.exists():
                out_text = last_msg_file.read_text(encoding="utf-8").strip()
            if not out_text:
                out_text = (res.stdout or res.stderr or "").strip()

            patch = ""
            if staging_ws:
                patch = ws_mgr.extract_diff(staging_ws)

            status = "ok" if res.returncode == 0 else "error"
            err = res.stderr.strip() if res.returncode != 0 else ""

            return {
                "task_id": task_id,
                "status": status,
                "worker": "codex",
                "model": model,
                "output_text": out_text,
                "patch": patch,
                "unreviewed_local_output": False,
                "error_message": err,
                "duration_s": duration,
                "artifacts": []
            }
        except subprocess.TimeoutExpired:
            return {
                "task_id": task_id,
                "status": "error",
                "worker": "codex",
                "model": model,
                "output_text": "",
                "patch": "",
                "unreviewed_local_output": False,
                "error_message": f"Timeout após {timeout_sec}s.",
                "duration_s": round(time.time() - start_t, 2),
                "artifacts": []
            }
        except Exception as e:
            return {
                "task_id": task_id,
                "status": "error",
                "worker": "codex",
                "model": model,
                "output_text": "",
                "patch": "",
                "unreviewed_local_output": False,
                "error_message": str(e),
                "duration_s": round(time.time() - start_t, 2),
                "artifacts": []
            }
        finally:
            if staging_ws:
                ws_mgr.cleanup(task_id)

def run_local(task: Dict[str, Any], timeout_sec: int = 180) -> Dict[str, Any]:
    worker = task.get("worker", "dsh-local")
    model = task.get("model", "")
    task_id = task.get("id", f"local-{int(time.time())}")
    prompt = task.get("prompt", "")
    start_t = time.time()

    bin_name = "dsh" if worker == "dsh-local" else ("qwen" if worker == "qwen-local" else ("opencode" if worker == "opencode-local" else "ollama"))
    bin_path = find_local_bin(bin_name)

    if not bin_path:
        return {
            "task_id": task_id,
            "status": "error",
            "worker": worker,
            "model": model,
            "output_text": "",
            "patch": "",
            "unreviewed_local_output": True,
            "error_message": f"Executor local '{bin_name}' não encontrado na máquina.",
            "duration_s": 0.0,
            "artifacts": []
        }

    # Despacho sob lock atômico serial estrito
    try:
        with OllamaSerialLock(timeout_sec=timeout_sec):
            # Garante exclusividade de peso residente se informado modelo
            if model:
                ollama_p = find_local_bin("ollama")
                ensure_exclusive_model(model, ollama_p)

            env = get_ollama_env()
            cmd = [bin_path]
            if worker in ["dsh-local", "qwen-local"]:
                cmd.extend(["-p", prompt])
            elif worker == "opencode-local":
                cmd.extend(["run", "--agent", "investigador", prompt])
            else:
                cmd.extend(["run", model or "qwen3-coder:30b", prompt])

            res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_sec, env=env)
            duration = round(time.time() - start_t, 2)
            out_text = (res.stdout or res.stderr or "").strip()
            status = "ok" if res.returncode == 0 else "error"
            err = res.stderr.strip() if res.returncode != 0 else ""

            return {
                "task_id": task_id,
                "status": status,
                "worker": worker,
                "model": model,
                "output_text": out_text,
                "patch": "",
                "unreviewed_local_output": True,  # Marca mandatória para conferência pelo AGY
                "error_message": err,
                "duration_s": duration,
                "artifacts": []
            }
    except Exception as e:
        return {
            "task_id": task_id,
            "status": "error",
            "worker": worker,
            "model": model,
            "output_text": "",
            "patch": "",
            "unreviewed_local_output": True,
            "error_message": str(e),
            "duration_s": round(time.time() - start_t, 2),
            "artifacts": []
        }
