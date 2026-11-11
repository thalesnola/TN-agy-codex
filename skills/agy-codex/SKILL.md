---
name: agy-codex
description: Ponte onde o Antigravity (AGY) comanda o Codex (segunda família técnica em nuvem) e os modelos locais do Ollama sob fila serial estrita.
---

# Ponte AGY -> Codex & Modelos Locais (`agy-codex`)

Esta skill orienta o **Cérebro Orquestrador (`Gemini 4 Argon` → `Claude Opus`)** e os **Agentes Rápidos (`Gemini 3.8 Flash` → `Claude Sonnet`)** a acionarem o Codex como 2ª família técnica e os modelos locais do Ollama sem entupir a janela de contexto.

---

## 1. Ferramentas MCP Disponíveis (`agy-codex-mcp`)

| Ferramenta | Descrição | Sandbox / Modo |
|---|---|---|
| `agy_codex_status` | Verifica caminhos e versões do Codex CLI, DSH, Qwen Code, OpenCode e Ollama. | Read-only |
| `agy_codex_route` | Consulta determinística da hierarquia para selecionar o executor ideal. | Read-only |
| `codex_ask` | Pergunta geral ou raciocínio à 2ª família (Codex / `gpt-6.1-sol`). | Read-only |
| `codex_review` | Auditoria independente de código ou diff por 2ª família técnica. | Read-only |
| `codex_challenge` | Estresse e desafio de trade-offs arquiteturais de planos do AGY. | Read-only |
| `codex_delegate` | Delegação de implementação em cópia efêmera isolada, devolvendo patch e JSON. | `workspace-write` isolado |
| `local_dispatch` | Despacho para executores locais Ollama sob lock serial atômico. | Local (`unreviewed: true`) |

---

## 2. Matriz de Hierarquização de Tarefas

```
                            [ AGY: Cérebro Orquestrador ]
                             (Argon 1º Degrau -> Opus 2º)
                                          │
                   ┌──────────────────────┴──────────────────────┐
                   ▼                                             ▼
       [ 2ª Família: Codex CLI ]                     [ Executores Locais: Ollama ]
        (gpt-6.1-sol / gpt-6-luna)                    (Fila Serial NUM_PARALLEL=1)
                   │                                             │
      ┌────────────┴────────────┐                  ┌─────────────┴─────────────┐
      ▼                         ▼                  ▼                           ▼
[ codex_review ]       [ codex_delegate ]    [ dsh-local ]               [ qwen-local ]
Auditoria independente   Workspace isolado   1 a 4 arquivos              Lote mecânico >= 5 arqs
de diffs e planos       Patch git limpo     gpt-oss:20b (~70s)          Qwen3-Coder-Next 36 GB
```

1. **Revisão e Desafio de 2ª Família:**
   - Acione `codex_review` ou `codex_challenge` para obter um crivo independente de modelo concorrente antes de aprovar grandes refatorações.
2. **Delegação Isolada:**
   - Acione `codex_delegate` para tarefas de codificação pesada onde o Codex atua em workspace temporário, devolvendo apenas o diff e resumo ao AGY.
3. **Trabalho Mecânico Local:**
   - 1 a 4 arquivos: `dsh-local` (`gpt-oss:20b`).
   - Lote mecânico ≥ 5 arquivos: `qwen-local` (`Qwen3-Coder-Next :NOTPL 36 GB`, num único prompt sem fatiar).
   - Acervo / RAG estruturado: `opencode-local` (`nemotron-3.5-lightning:30b-a3b`).
   - Todo retorno local carrega `unreviewed_local_output: true` e **deve ser conferido pelo AGY antes de integrar**.

---

## 3. Regras de Execução Local no Hardware (Dell Pro Max 16)

- **Fila serial estrita:** apenas um peso pesado roda por vez (`OLLAMA_NUM_PARALLEL=1`). A trava de arquivo `~/.agy-codex/ollama-serial.lock` impede colisões.
- **Ambiente calibrado:** `OLLAMA_CONTEXT_LENGTH=32768`, `OLLAMA_FLASH_ATTENTION=1`, `OLLAMA_KV_CACHE_TYPE=q8_0`.
- **Proibição absoluta de `num_gpu: 0`:** o prefill cai 7x sem aceleração de GPU.
