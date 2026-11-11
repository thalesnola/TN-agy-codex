# -*- coding: utf-8 -*-
"""Gerenciamento de workspace temporário e isolamento de diffs."""

import os
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple

class WorkspaceManager:
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = Path(base_dir or (Path.cwd() / "agy-codex-ws")).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def create_staging(self, task_id: str, source_dir: str, include_files: Optional[List[str]] = None) -> Path:
        staging = self.base_dir / task_id
        if staging.exists():
            shutil.rmtree(staging)
        staging.mkdir(parents=True, exist_ok=True)

        src = Path(source_dir).resolve()
        if include_files:
            for f in include_files:
                src_file = src / f
                if src_file.exists():
                    dest_file = staging / f
                    dest_file.parent.mkdir(parents=True, exist_ok=True)
                    if src_file.is_file():
                        shutil.copy2(src_file, dest_file)
                    else:
                        shutil.copytree(src_file, dest_file)
        else:
            # Copia shallow
            for item in src.iterdir():
                if item.name in [".git", "node_modules", ".venv", "__pycache__", "agy-codex-ws"]:
                    continue
                dest = staging / item.name
                if item.is_file():
                    shutil.copy2(item, dest)
                elif item.is_dir():
                    shutil.copytree(item, dest, ignore=shutil.ignore_patterns(".git", "node_modules", ".venv", "__pycache__"))

        # Inicializa git raso para poder calcular diff com facilidade
        try:
            subprocess.run(["git", "-C", str(staging), "init", "-q"], capture_output=True, timeout=5)
            subprocess.run(["git", "-C", str(staging), "add", "."], capture_output=True, timeout=10)
            subprocess.run(["git", "-C", str(staging), "-c", "user.name=AGY", "-c", "user.email=agy@local.internal", "commit", "-q", "-m", "baseline"], capture_output=True, timeout=10)
        except Exception:
            pass

        return staging

    def extract_diff(self, staging_path: Path) -> str:
        try:
            res = subprocess.run(["git", "-C", str(staging_path), "diff", "HEAD"], capture_output=True, text=True, timeout=10)
            return res.stdout or ""
        except Exception:
            return ""

    def cleanup(self, task_id: str) -> None:
        target = self.base_dir / task_id
        if target.exists():
            def on_rm_error(func, p, exc_info):
                try:
                    os.chmod(p, 0o777)
                    func(p)
                except Exception:
                    pass
            shutil.rmtree(target, onerror=on_rm_error)
