# -*- coding: utf-8 -*-
"""Mock CLI executável simulando o comportamento do binário codex exec."""

import argparse
import sys
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(prog="fake-codex")
    parser.add_argument("command", choices=["exec", "--version", "login"])
    parser.add_argument("-m", "--model", default="gpt-6.1-sol")
    parser.add_argument("-s", "--sandbox", default="read-only")
    parser.add_argument("--skip-git-repo-check", action="store_true")
    parser.add_argument("--ephemeral", action="store_true")
    parser.add_argument("-o", "--output-last-message")
    parser.add_argument("-C", "--cd")
    parser.add_argument("prompt", nargs="?", default="")

    args, unknown = parser.parse_known_args()

    if "--version" in sys.argv:
        print("codex-cli 0.167.0-fake")
        return

    if args.command == "exec":
        # Simula resposta
        resp = f"Fake Codex response for model {args.model} sandbox {args.sandbox}: {args.prompt}"
        if args.output_last_message:
            Path(args.output_last_message).write_text(resp, encoding="utf-8")
        if args.sandbox == "workspace-write" and args.cd:
            # Modifica um arquivo para gerar diff se solicitado
            p = Path(args.cd) / "generated_by_fake_codex.txt"
            p.write_text("Hello from fake codex\n", encoding="utf-8")
        print(resp)

if __name__ == "__main__":
    main()
