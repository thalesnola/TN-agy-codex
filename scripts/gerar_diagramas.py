# -*- coding: utf-8 -*-
"""
Gerador determinístico dos 2 diagramas da ponte agy-codex:
1. Diagrama Motion da Hierarquização (docs/hierarquia-motion.svg / .png)
2. Diagrama Técnico da Ponte Okabe-Ito (docs/arquitetura-ponte.svg / .png)
Renderização em alta resolução via Chrome/Edge Headless com escala 1.6x.
"""

import os
import sys
import shutil
import subprocess
import tempfile
import math
from pathlib import Path
from xml.sax.saxutils import escape

W = 1000
CORAL, AZUL, MENTA, SOL, VIOLETA, ROSA = "#FF5A6E", "#2F9BFF", "#16C79A", "#FFB300", "#7B5CFF", "#FF7AC6"
NAVY = "#1B1F3B"
CINZ = "#5B6286"
TEXTO = "#3C4268"
FONT = "'Segoe UI Variable Display','Segoe UI','SF Pro Display','Helvetica Neue',Arial,sans-serif"

def esc(t):
    return escape(str(t))

def wrap(txt, larg, tam):
    n = max(int(larg / (tam * 0.53)), 6)
    ls, cur = [], ""
    for w_ in str(txt).split():
        if len((cur + " " + w_).strip()) > n:
            ls.append(cur)
            cur = w_
        else:
            cur = (cur + " " + w_).strip()
    if cur:
        ls.append(cur)
    return ls

def tx(x, y, ls, size=23, cor=NAVY, peso=400, anchor="start", dy=None):
    if isinstance(ls, str):
        ls = [ls]
    dy = dy or size * 1.35
    t = "".join(f'<tspan x="{x}" dy="{0 if i == 0 else dy}">{esc(s)}</tspan>' for i, s in enumerate(ls))
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{cor}" font-weight="{peso}" text-anchor="{anchor}">{t}</text>'

def cab(titulo, sub):
    tl = wrap(titulo, 900, 42)
    s = tx(50, 85, tl, 42, NAVY, 800, "start", 52)
    y = 85 + 52 * (len(tl) - 1) + 40
    sl = wrap(sub, 900, 24)[:2]
    s += tx(52, y, sl, 24, CINZ, 400, "start", 32)
    y += 32 * (len(sl) - 1) + 46
    return s, y

def card(x, y, w, cor, titulo, texto, size=21, tsize=25, h_min=0):
    ls = wrap(texto, w - 70, size) if isinstance(texto, str) else texto
    tl = wrap(titulo, w - 60, tsize)
    calc_h = 24 + len(tl) * tsize * 1.3 + 8 + len(ls) * size * 1.35 + 20
    h = max(calc_h, h_min)
    s = (f'<g filter="url(#sh)"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="24" fill="#fff"/>'
         f'<rect x="{x}" y="{y}" width="12" height="{h}" rx="6" fill="{cor}"/></g>')
    s += tx(x + 32, y + 24 + tsize * 0.85, tl, tsize, NAVY, 800, "start", tsize * 1.3)
    s += tx(x + 32, y + 24 + len(tl) * tsize * 1.3 + 8 + size * 0.8, ls, size, TEXTO, 400)
    return s, h

def faixa(y, texto, cor=NAVY, size=23, x=50, w=900):
    ls = wrap(texto, w - 60, size)
    h = 28 + len(ls) * size * 1.35
    s = f'<g filter="url(#sh)"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="28" fill="{cor}"/></g>'
    s += tx(x + w / 2, y + 20 + size, ls, size, "#fff", 800, "middle")
    return s, y + h + 20

def montar_svg(corpo, H, bg_grad="motion"):
    if bg_grad == "motion":
        bg_def = """<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#F3EEFF"/><stop offset="0.55" stop-color="#FFFFFF"/><stop offset="1" stop-color="#E9F7FF"/></linearGradient>
<linearGradient id="trail" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#7B5CFF" stop-opacity="0"/><stop offset="1" stop-color="#7B5CFF" stop-opacity="0.2"/></linearGradient>
<filter id="sh" x="-20%" y="-20%" width="140%" height="150%"><feDropShadow dx="0" dy="8" stdDeviation="11" flood-color="#1B1F3B" flood-opacity="0.16"/></filter>
<filter id="glow" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="22"/></filter>"""
        decor = f"""<circle cx="930" cy="110" r="160" fill="{ROSA}" opacity="0.14" filter="url(#glow)"/>
<circle cx="70" cy="{H - 130}" r="180" fill="{AZUL}" opacity="0.13" filter="url(#glow)"/>
<rect x="-60" y="{H * 0.42}" width="700" height="28" rx="14" fill="url(#trail)" transform="rotate(-12 300 {H * 0.42})"/>
<rect x="520" y="{H - 100}" width="600" height="24" rx="12" fill="url(#trail)" transform="rotate(-12 800 {H - 100})"/>"""
    else: # técnico Okabe-Ito
        bg_def = """<linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#F8FAFC"/><stop offset="1" stop-color="#F1F5F9"/></linearGradient>
<filter id="sh" x="-10%" y="-10%" width="120%" height="130%"><feDropShadow dx="0" dy="4" stdDeviation="6" flood-color="#0F172A" flood-opacity="0.12"/></filter>"""
        decor = ""

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="{FONT}">
<defs>
{bg_def}
<marker id="ar" viewBox="0 0 12 12" refX="9" refY="6" markerWidth="9" markerHeight="9" orient="auto"><path d="M1 1 L11 6 L1 11 z" fill="{NAVY}"/></marker>
<marker id="ar_blue" viewBox="0 0 12 12" refX="9" refY="6" markerWidth="9" markerHeight="9" orient="auto"><path d="M1 1 L11 6 L1 11 z" fill="{AZUL}"/></marker>
<marker id="ar_mint" viewBox="0 0 12 12" refX="9" refY="6" markerWidth="9" markerHeight="9" orient="auto"><path d="M1 1 L11 6 L1 11 z" fill="{MENTA}"/></marker>
</defs>
<rect width="{W}" height="{H}" fill="url(#bg)"/>
{decor}
{corpo}
</svg>"""

def _navegador():
    cands = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        shutil.which("chrome") or "",
        shutil.which("msedge") or ""
    ]
    for c in cands:
        if c and Path(c).exists():
            return c
    sys.exit("Navegador Chrome ou Edge não localizado.")

def salvar_diagrama(nome, svg_content, y_final, out_dir, bg_grad="motion"):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    H = int(y_final + 30)
    full_svg = montar_svg(svg_content, H, bg_grad)
    svg_path = out_dir / f"{nome}.svg"
    svg_path.write_text(full_svg, encoding="utf-8")
    png_path = out_dir / f"{nome}.png"

    with tempfile.TemporaryDirectory() as t:
        cmd = [
            _navegador(),
            "--headless=new",
            "--no-sandbox",
            f"--user-data-dir={t}",
            f"--window-size={W},{H}",
            "--force-device-scale-factor=1.6",
            "--hide-scrollbars",
            f"--screenshot={png_path.resolve()}",
            svg_path.resolve().as_uri()
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        if res.returncode != 0:
            print(f"Aviso screenshot {nome}: {res.stderr}")
    return svg_path, png_path


# ==============================================================================
# 1. DIAGRAMA MOTION DA HIERARQUIZAÇÃO (docs/hierarquia-motion)
# ==============================================================================
def gerar_diagrama_hierarquia_motion(out_dir):
    titulo = "O AGY comanda; o Codex e os modelos locais executam"
    sub = "Hierarquização da ponte agy-codex — segunda família em nuvem e fila local a custo zero"
    cabs, y = cab(titulo, sub)
    s = cabs

    # Nível 1: Cartão Comandante Topo (VIOLETA)
    c_top, h_top = card(50, y, 900, VIOLETA,
                        "NÍVEL 1 · IA COMANDANTE: ANTIGRAVITY (AGY)",
                        "Cérebro (Gemini 4 Argon → Opus) define a arquitetura; Agentes Rápidos (Flash 3.8 → Sonnet) fazem leitura ilimitada e acionam a ponte.",
                        size=23, tsize=26)
    s += c_top
    y += h_top + 24

    # Seta 1 para baixo com respiro generoso (~4 pontos visíveis)
    s += f'<line x1="500" y1="{y}" x2="500" y2="{y + 65}" stroke="{NAVY}" stroke-width="6" stroke-dasharray="3 12" stroke-linecap="round" marker-end="url(#ar)"/>'
    y += 75

    # Hub Central (r=124, texto em duas linhas com ampla folga interna)
    cy = y + 124
    s += f'<circle cx="500" cy="{cy}" r="124" fill="{NAVY}" stroke="#fff" stroke-width="8" filter="url(#sh)"/>'
    s += tx(500, cy - 26, ["PONTE", "AGY → OPERÁRIAS"], 22, "#fff", 900, "middle", 28)
    s += tx(500, cy + 42, ["MCP stdio · CLI JSON · Preflight"], 15, "#fff", 600, "middle")
    y = cy + 124 + 18

    # Bifurcação ortogonal limpa do hub para as duas colunas (Nível 2A e Nível 2B)
    y_mid = y + 26
    s += f'<line x1="500" y1="{y}" x2="500" y2="{y_mid}" stroke="{NAVY}" stroke-width="5" stroke-linecap="round"/>'
    s += f'<line x1="270" y1="{y_mid}" x2="730" y2="{y_mid}" stroke="{NAVY}" stroke-width="5" stroke-linecap="round"/>'
    s += f'<line x1="270" y1="{y_mid}" x2="270" y2="{y + 72}" stroke="{AZUL}" stroke-width="6" stroke-dasharray="3 11" stroke-linecap="round" marker-end="url(#ar_blue)"/>'
    s += f'<line x1="730" y1="{y_mid}" x2="730" y2="{y + 72}" stroke="{MENTA}" stroke-width="6" stroke-dasharray="3 11" stroke-linecap="round" marker-end="url(#ar_mint)"/>'
    y += 90

    # Nível 2: 2 Colunas Simétricas
    col_w = 440
    gap = 20
    x_esq = 50
    x_dir = 50 + col_w + gap

    # Badges dos Cabeçalhos
    h_badge = 46
    s += f'<g filter="url(#sh)"><rect x="{x_esq}" y="{y}" width="{col_w}" height="{h_badge}" rx="23" fill="{AZUL}"/></g>'
    s += tx(x_esq + col_w / 2, y + 29, ["NÍVEL 2A · CODEX CLI (2ª FAMÍLIA)"], 18, "#fff", 800, "middle")

    s += f'<g filter="url(#sh)"><rect x="{x_dir}" y="{y}" width="{col_w}" height="{h_badge}" rx="23" fill="{MENTA}"/></g>'
    s += tx(x_dir + col_w / 2, y + 29, ["NÍVEL 2B · OLLAMA SERIAL (LOCAL)"], 18, "#fff", 800, "middle")

    y += h_badge + 18

    # Linha 1 de Cartões (Colunas)
    c1, h1 = card(x_esq, y, col_w, AZUL, "codex_review & codex_challenge",
                  "Auditoria independente de diffs e estresse de planos em sandbox read-only por outra família de IA.",
                  size=21, tsize=24, h_min=170)
    c2, h2 = card(x_dir, y, col_w, MENTA, "dsh-local & ollama-direct",
                  "Tarefas de 1 a 4 arquivos (gpt-oss:20b) e refatorações rápidas locais sem consumir cota de nuvem.",
                  size=21, tsize=24, h_min=170)
    s += c1 + c2
    h_lin1 = max(h1, h2)
    y += h_lin1 + 18

    # Linha 2 de Cartões (Colunas)
    c3, h3 = card(x_esq, y, col_w, AZUL, "codex_delegate & codex_ask",
                  "Execução efêmera em workspace isolado, devolvendo apenas patch auditável e síntese JSON.",
                  size=21, tsize=24, h_min=170)
    c4, h4 = card(x_dir, y, col_w, MENTA, "qwen-local & opencode-local",
                  "Lotes mecânicos ≥ 5 arquivos num único prompt (Qwen3-Coder-Next 36 GB) e consulta RAG (Nemotron 30B).",
                  size=21, tsize=24, h_min=170)
    s += c3 + c4
    h_lin2 = max(h3, h4)
    y += h_lin2 + 24

    # Nível 3: Grade 2 Colunas de Governança (SOL e CORAL)
    c_gov1, h_g1 = card(x_esq, y, col_w, SOL, "Guarda de Memória & Fila Serial",
                        "Lock exclusivo (NUM_PARALLEL=1) e descarga automática via ollama ps impedem colisão de pesos grandes.",
                        size=21, tsize=24, h_min=165)
    c_gov2, h_g2 = card(x_dir, y, col_w, CORAL, "Conferência Obrigatória no Retorno",
                        "Todo resultado operário volta validado por JSON Schema e passa pelo crivo do AGY antes de integrar.",
                        size=21, tsize=24, h_min=165)
    s += c_gov1 + c_gov2
    y += max(h_g1, h_g2) + 24

    # Faixa Final NAVY
    s_faixa, y = faixa(y, "Hierarquia clara: o AGY pensa e valida; o Codex audita em 2ª família; o hardware local absorve o volume.")
    s += s_faixa

    return salvar_diagrama("hierarquia-motion", s, y, out_dir, "motion")


# ==============================================================================
# 2. DIAGRAMA TÉCNICO DA PONTE (docs/arquitetura-ponte - Okabe-Ito)
# ==============================================================================
def gerar_diagrama_arquitetura_ponte(out_dir):
    titulo = "Arquitetura Técnica da Ponte agy-codex"
    sub = "Contratos JSON-RPC 2.0, validação por Schema, isolamento de workspace e preflight serial"
    cabs, y = cab(titulo, sub)
    s = cabs

    # Bloco 1: AGY Core MCP Client
    s += f'<g filter="url(#sh)"><rect x="50" y="{y}" width="900" height="122" rx="20" fill="#fff" stroke="{VIOLETA}" stroke-width="3"/>'
    s += tx(78, y + 42, ["CLIENTE: GOOGLE ANTIGRAVITY (AGY)"], 23, VIOLETA, 800)
    s += tx(78, y + 76, ["• Cérebro (Gemini 4 Argon / Claude Opus) & Agentes Rápidos (Gemini 3.8 Flash / Claude Sonnet)"], 16.5, TEXTO, 500)
    s += tx(78, y + 102, ["• Comunica via stdio JSON-RPC 2.0 com o servidor MCP nativo agy-codex-mcp ou CLI JSON"], 16, CINZ, 400)
    s += '</g>'
    y += 142

    # Seta para baixo
    s += f'<line x1="500" y1="{y - 20}" x2="500" y2="{y + 20}" stroke="{NAVY}" stroke-width="5" marker-end="url(#ar)"/>'
    y += 30

    # Bloco 2: Servidor MCP & Roteador (Núcleo da Ponte)
    s += f'<g filter="url(#sh)"><rect x="50" y="{y}" width="900" height="230" rx="20" fill="#fff" stroke="{NAVY}" stroke-width="3"/>'
    s += f'<rect x="50" y="{y}" width="900" height="42" rx="20" fill="{NAVY}"/>'
    s += tx(75, y + 28, ["SERVIDOR MCP STDIO & MOTOR DE ROTEAMENTO (agy_codex)"], 19, "#fff", 800)

    # 4 Módulos internos
    mods = [
        ("mcp_server.py", "JSON-RPC 2.0 · 7 tools"),
        ("router.py", "Hierarquia determinística"),
        ("discovery.py", "Auto-busca WindowsApps/npm"),
        ("preflight.py", "Workspace & lock serial")
    ]
    for i, (mod_t, mod_d) in enumerate(mods):
        bx = 75 + i * 215
        s += f'<rect x="{bx}" y="{y + 60}" width="200" height="75" rx="12" fill="#F8FAFC" stroke="{CINZ}" stroke-width="1.5"/>'
        s += tx(bx + 12, y + 88, [mod_t], 16.5, NAVY, 800)
        s += tx(bx + 12, y + 115, [mod_d], 12.8, CINZ, 500)

    # Contratos
    s += tx(75, y + 165, ["Contratos JSON Schemas: task.schema.json  ·  result.schema.json  ·  review.schema.json"], 17, NAVY, 700)
    s += tx(75, y + 195, ["Locks & Proteções: ~/.agy-codex/ollama-serial.lock  ·  Rejeição de reparse points  ·  Proibição num_gpu=0"], 15.5, CINZ, 400)
    s += '</g>'
    y += 250

    # Seta bifurcada para baixo
    s += f'<line x1="280" y1="{y - 20}" x2="280" y2="{y + 20}" stroke="{AZUL}" stroke-width="5" marker-end="url(#ar_blue)"/>'
    s += f'<line x1="720" y1="{y - 20}" x2="720" y2="{y + 20}" stroke="{MENTA}" stroke-width="5" marker-end="url(#ar_mint)"/>'
    y += 30

    # Bloco 3: 2 Motores de Execução (Codex CLI x Executores Locais)
    col_w = 435
    x_esq = 50
    x_dir = 515
    box_h = 318

    # Coluna Esquerda: Codex CLI Runner
    s += f'<g filter="url(#sh)"><rect x="{x_esq}" y="{y}" width="{col_w}" height="{box_h}" rx="18" fill="#fff" stroke="{AZUL}" stroke-width="2.5"/>'
    s += f'<rect x="{x_esq}" y="{y}" width="{col_w}" height="38" rx="18" fill="{AZUL}"/>'
    s += tx(x_esq + 20, y + 26, ["CODEX CLI EXEC RUNNER"], 17, "#fff", 800)
    s += tx(x_esq + 20, y + 66, ["Binário:", "codex.exe / codex CLI (auto-descoberto)"], 15.5, NAVY, 700, dy=20)
    s += tx(x_esq + 20, y + 116, ["Modelos & Perfis:", "2ª família OpenAI/GPT (sol / luna / default)"], 15.5, NAVY, 700, dy=20)
    s += tx(x_esq + 20, y + 166, ["Flags de Isolamento:", "exec -m <model> -s <sandbox> --ephemeral"], 15, TEXTO, 500, dy=20)
    s += tx(x_esq + 20, y + 216, ["Workspace:", "Staging efêmero (agy-codex-ws/) + git diff limpo"], 15, TEXTO, 500, dy=20)
    s += tx(x_esq + 20, y + 268, ["Retorno:", "JSON validado por Schema + patch auditável"], 15, VIOLETA, 700, dy=20)
    s += '</g>'

    # Coluna Direita: Local Ollama Runners
    s += f'<g filter="url(#sh)"><rect x="{x_dir}" y="{y}" width="{col_w}" height="{box_h}" rx="18" fill="#fff" stroke="{MENTA}" stroke-width="2.5"/>'
    s += f'<rect x="{x_dir}" y="{y}" width="{col_w}" height="38" rx="18" fill="{MENTA}"/>'
    s += tx(x_dir + 20, y + 26, ["OLLAMA SERIAL LOCAL RUNNERS"], 17, "#fff", 800)
    s += tx(x_dir + 20, y + 66, ["dsh-local:", "gpt-oss:20b (~70 s) · código e revisão 1–4 arqs"], 15.5, NAVY, 700, dy=20)
    s += tx(x_dir + 20, y + 116, ["qwen-local:", "Qwen3-Coder-Next 36 GB · lote mecânico ≥ 5 arqs"], 15.5, NAVY, 700, dy=20)
    s += tx(x_dir + 20, y + 166, ["opencode-local:", "Nemotron 30B · consulta estruturada / RAG"], 15.5, NAVY, 700, dy=20)
    s += tx(x_dir + 20, y + 216, ["ollama-direct:", "qwen3-coder:30b / 7b · refatoração rápida"], 15.5, NAVY, 700, dy=20)
    s += tx(x_dir + 20, y + 268, ["Governança:", "Lock serial atômico + unreviewed_local_output"], 15, CORAL, 700, dy=20)
    s += '</g>'
    y += box_h + 24

    # Faixa Final
    s_faixa, y = faixa(y, "Contrato estrito: dados fluem em JSONL/stdio; o AGY mantém a soberania analítica sobre qualquer diff.")
    s += s_faixa

    return salvar_diagrama("arquitetura-ponte", s, y, out_dir, "tecnico")


if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parent.parent
    dest_docs = Path(sys.argv[1]) if len(sys.argv) > 1 else (repo_root / "docs")
    dest_docs.mkdir(parents=True, exist_ok=True)

    print("1/2 Gerando Diagrama Motion da Hierarquização...")
    s1, p1 = gerar_diagrama_hierarquia_motion(dest_docs)

    print("2/2 Gerando Diagrama Técnico da Ponte (Okabe-Ito)...")
    s2, p2 = gerar_diagrama_arquitetura_ponte(dest_docs)

    extra_dir = os.environ.get("AGY_BRAIN_OUT", "")
    if extra_dir:
        eb = Path(extra_dir)
        eb.mkdir(parents=True, exist_ok=True)
        shutil.copy(p1, eb / "motion-agy-codex-hierarquia.png")
        shutil.copy(p2, eb / "arquitetura-ponte-agy-codex.png")

    print("Diagramas gerados com sucesso em:", dest_docs)
