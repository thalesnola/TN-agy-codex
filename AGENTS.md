# Diretrizes Operacionais — agy-codex

> **Premissa Soberana:** Não há camada ou filtro automático de sigilo. O usuário é o soberano exclusivo sobre os dados e tarefas. O papel do agente é estritamente analisar a solicitação técnica e distribuir a execução entre as camadas mais eficientes.

---

## 1. Regras de Execução

- **Comandante:** O Antigravity (AGY) lidera o planejamento e arquitetura (Gemini 4 Argon → Claude Opus).
- **Segunda Opinião:** Para revisão independente de diffs e estresse de planos com trade-offs, acione o Codex (`gpt-6.1-sol` em sandbox `read-only`).
- **Implementação Isolada:** Use `codex_delegate` para implementações pesadas em workspace temporário efêmero.
- **Fila Serial Ollama:** Execuções locais usam lock exclusivo (`OllamaSerialLock`), garantindo que apenas um peso grande ocupe a máquina por vez. Variáveis obrigatórias: `OLLAMA_NUM_PARALLEL=1`, `OLLAMA_CONTEXT_LENGTH=32768`, `OLLAMA_FLASH_ATTENTION=1`, `OLLAMA_KV_CACHE_TYPE=q8_0`. Jamais utilize `num_gpu: 0`.
- **Conferência Obrigatória:** Todo retorno com `unreviewed_local_output: true` deve ser verificado pelo AGY antes da consolidação.
