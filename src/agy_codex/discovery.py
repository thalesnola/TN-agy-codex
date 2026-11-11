# -*- coding: utf-8 -*-
"""Descoberta multiplataforma de binários e executores locais."""

import glob
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

def find_codex_bin() -> Optional[str]:
    # 1. Override explícito via variável de ambiente
    env_bin = os.environ.get("AGY_CODEX_BIN")
    if env_bin and Path(env_bin).exists():
        return str(Path(env_bin).resolve())

    # 2. PATH padrão do sistema
    which_bin = shutil.which("codex")
    if which_bin:
        return which_bin

    # 3. Pacote oficial Windows App (OpenAI.Codex)
    if os.name == "nt":
        # 3a. Busca rápida em ~/.codex/config.toml
        try:
            cfg_path = Path.home() / ".codex" / "config.toml"
            if cfg_path.exists():
                text = cfg_path.read_text(encoding="utf-8")
                for line in text.splitlines():
                    if "WindowsApps\\OpenAI.Codex" in line:
                        idx = line.find(":\\Program Files\\WindowsApps\\OpenAI.Codex")
                        if idx != -1:
                            start = idx - 1
                            end = line.find("\\app\\", start)
                            if end != -1:
                                cand = Path(line[start:end]) / "app" / "resources" / "codex.exe"
                                if cand.exists():
                                    return str(cand)
        except Exception:
            pass

        # 3b. Busca via Get-AppxPackage
        try:
            cmd = ["powershell", "-NoProfile", "-Command", "Get-AppxPackage *OpenAI.Codex* | Select-Object -ExpandProperty InstallLocation"]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            for loc in res.stdout.splitlines():
                loc = loc.strip()
                if loc:
                    cand = Path(loc) / "app" / "resources" / "codex.exe"
                    if cand.exists():
                        return str(cand)
        except Exception:
            pass

    # 4. Fallback em %APPDATA%\npm
    appdata = os.environ.get("APPDATA")
    if appdata:
        npm_cmd = Path(appdata) / "npm" / "codex.cmd"
        if npm_cmd.exists():
            return str(npm_cmd)
        npm_vendor = glob.glob(str(Path(appdata) / "npm" / "node_modules" / "@openai" / "*" / "node_modules" / "@openai" / "codex-win32-x64" / "vendor" / "*" / "bin" / "codex.exe"))
        if npm_vendor:
            npm_vendor.sort(reverse=True)
            return npm_vendor[0]

    # 5. Caminhos padrão macOS e Linux
    for p in ["/opt/homebrew/bin/codex", "/usr/local/bin/codex", os.path.expanduser("~/.local/bin/codex")]:
        if Path(p).exists():
            return p

    return None

def find_local_bin(name: str) -> Optional[str]:
    which_bin = shutil.which(name)
    if which_bin:
        return which_bin

    appdata = os.environ.get("APPDATA")
    if appdata:
        cmd = Path(appdata) / "npm" / f"{name}.cmd"
        if cmd.exists():
            return str(cmd)

    if name == "ollama":
        localapp = os.environ.get("LOCALAPPDATA")
        if localapp:
            ol = Path(localapp) / "Programs" / "Ollama" / "ollama.exe"
            if ol.exists():
                return str(ol)

    return None

def get_binary_version(path: str) -> str:
    try:
        res = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=5)
        out = (res.stdout or res.stderr or "").strip().splitlines()
        return out[0] if out else "desconhecido"
    except Exception as e:
        return f"erro: {e}"

def get_tool_status() -> Dict[str, Dict[str, Any]]:
    status: Dict[str, Dict[str, Any]] = {}

    codex_p = find_codex_bin()
    status["codex"] = {
        "found": bool(codex_p),
        "path": codex_p or "",
        "version": get_binary_version(codex_p) if codex_p else ""
    }

    for name in ["dsh", "qwen", "opencode", "ollama"]:
        p = find_local_bin(name)
        status[name] = {
            "found": bool(p),
            "path": p or "",
            "version": get_binary_version(p) if p else ""
        }

    return status
