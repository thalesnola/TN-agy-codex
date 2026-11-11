# -*- coding: utf-8 -*-
"""Preflight, guards de segurança de workspace e trava serial do Ollama."""

import json
import os
import time
import urllib.request
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

class PreflightError(Exception):
    """Erro de pré-verificação ou violação de políticas de segurança."""
    pass

def validate_workspace(workspace_path: str, files: Optional[List[str]] = None) -> Path:
    ws = Path(workspace_path).resolve()
    if not ws.exists() or not ws.is_dir():
        raise PreflightError(f"Workspace não encontrado ou inválido: {workspace_path}")

    # Checa reparse points no próprio workspace
    if os.name == "nt":
        import ctypes
        FILE_ATTRIBUTE_REPARSE_POINT = 0x0400
        attrs = ctypes.windll.kernel32.GetFileAttributesW(str(ws))
        if attrs != -1 and (attrs & FILE_ATTRIBUTE_REPARSE_POINT):
            raise PreflightError("Workspace não pode ser um link simbólico ou reparse point.")

    if files:
        for f in files:
            p = (ws / f).resolve()
            if not str(p).startswith(str(ws)):
                raise PreflightError(f"Caminho escapa do workspace permitido: {f}")
            if p.exists() and os.name == "nt":
                attrs = ctypes.windll.kernel32.GetFileAttributesW(str(p))
                if attrs != -1 and (attrs & FILE_ATTRIBUTE_REPARSE_POINT):
                    raise PreflightError(f"Reparse point / symlink proibido em arquivo incluído: {f}")

    return ws

def get_ollama_env(extra_env: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)

    # Regras mandatórias de ambiente para execução local (Dell Pro Max 16)
    env["OLLAMA_NUM_PARALLEL"] = "1"
    env["OLLAMA_CONTEXT_LENGTH"] = "32768"
    env["OLLAMA_FLASH_ATTENTION"] = "1"
    env["OLLAMA_KV_CACHE_TYPE"] = "q8_0"

    # Proíbe explicitamente num_gpu=0
    if env.get("OLLAMA_NUM_GPU") == "0":
        raise PreflightError("Proibido executar com OLLAMA_NUM_GPU=0 (prefill cai 7x).")

    return env

def get_resident_ollama_models() -> List[str]:
    try:
        req = urllib.request.Request("http://127.0.0.1:11434/api/ps", headers={"User-Agent": "agy-codex"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return [m.get("name", "") for m in data.get("models", []) if m.get("name")]
    except Exception:
        return []

def ensure_exclusive_model(target_model: str, ollama_bin: Optional[str] = None) -> None:
    residents = get_resident_ollama_models()
    for res_name in residents:
        if res_name != target_model:
            # Descarrega modelo concorrente para garantir RAM/VRAM livre
            bin_path = ollama_bin or "ollama"
            try:
                subprocess.run([bin_path, "stop", res_name], capture_output=True, timeout=10)
            except Exception as e:
                raise PreflightError(f"Falha ao descarregar modelo residente concorrente '{res_name}': {e}")

class OllamaSerialLock:
    """Trava atômica de arquivo para exclusão mútua na execução do Ollama local."""
    def __init__(self, timeout_sec: int = 180):
        self.lock_dir = Path.home() / ".agy-codex"
        self.lock_file = self.lock_dir / "ollama-serial.lock"
        self.timeout_sec = timeout_sec
        self.acquired = False

    def __enter__(self):
        self.lock_dir.mkdir(parents=True, exist_ok=True)
        start = time.time()
        while time.time() - start < self.timeout_sec:
            try:
                # Tentativa atômica exclusiva (O_CREAT | O_EXCL)
                self.fd = os.open(str(self.lock_file), os.O_CREAT | os.O_EXCL | os.O_RDWR)
                os.write(self.fd, f"PID={os.getpid()} TIME={time.time()}".encode("utf-8"))
                self.acquired = True
                return self
            except FileExistsError:
                # Verifica se o processo anterior morreu (lock órfão)
                try:
                    stat = self.lock_file.stat()
                    if time.time() - stat.st_mtime > 300:  # 5 minutos
                        self.lock_file.unlink(missing_ok=True)
                        continue
                except Exception:
                    pass
                time.sleep(0.5)
        raise PreflightError(f"Timeout ao aguardar lock serial do Ollama ({self.timeout_sec}s). Outra tarefa local está ativa.")

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.acquired:
            try:
                os.close(self.fd)
                self.lock_file.unlink(missing_ok=True)
            except Exception:
                pass
            self.acquired = False
