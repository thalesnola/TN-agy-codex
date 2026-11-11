# Arquitetura Técnica — Ponte agy-codex

A ponte **`agy-codex`** estabelece o canal onde o **Google Antigravity (AGY)** atua como a **Inteligência Artificial Comandante**, orquestrando o **Codex** (segunda família técnica em nuvem) e os **modelos locais do Ollama** (hardware local Dell Pro Max 16).

---

## 1. Topologia em Camadas

```
[ Camada 1: Cérebro Orquestrador ]
Gemini 4 Argon (1º Degrau) -> Claude Opus (2º Degrau)
                │
                ▼
[ Camada 2: Agentes Rápidos ]
Gemini 3.8 Flash (1º Degrau) -> Claude Sonnet (2º Degrau)
(Varredura ilimitada sem limite de arquivo e acionamento da ponte)
                │
                ▼
      ┌───────────────────┐
      │  agy-codex-mcp    │ (Servidor MCP stdio JSON-RPC 2.0 / CLI Python)
      └─────────┬─────────┘
                │
     ┌──────────┴──────────┐
     ▼                     ▼
[ 2ª Família Nuvem ]   [ Hardware Local (Ollama) ]
Codex CLI              Fila Serial Estrita (NUM_PARALLEL=1)
(gpt-6.1-sol / luna)   ├── dsh-local (gpt-oss:20b)
                       ├── qwen-local (Qwen3-Coder-Next :NOTPL 36 GB)
                       ├── opencode-local (nemotron-3.5-lightning:30b-a3b)
                       └── ollama-direct (qwen3-coder:30b)
```

---

## 2. Princípios de Projeto

1. **Soberania do AGY:**
   O AGY mantém todo o contexto de planejamento, histórico e arquitetura. Tarefas enviadas ao Codex ou modelos locais são pontuais, efêmeras e retornam apenas patches git e sínteses estruturadas em JSON.
2. **Lock Serial Atômico (`OllamaSerialLock`):**
   Modelos grandes não podem colidir em memória. O lock de exclusão mútua (`~/.agy-codex/ollama-serial.lock`) e a checagem via `ollama ps` garantem que modelos residentes sejam descarregados antes de subir um novo peso pesado.
3. **Marcação Mandatória de Saídas Locais:**
   Qualquer resultado produzido por modelos locais recebe a flag `"unreviewed_local_output": true`, exigindo revisão pelo AGY antes da consolidação no repositório.
4. **Isolamento em Workspace Temporário:**
   Tarefas de delegação de código (`codex_delegate`) são executadas em `agy-codex-ws/<task_id>` com `--skip-git-repo-check` e `--ephemeral`, extraindo diffs limpos sem alterar o workspace principal diretamente.
