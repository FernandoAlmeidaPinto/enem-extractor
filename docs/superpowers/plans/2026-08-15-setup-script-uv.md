# Script de Setup com `uv` — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fornecer um script `setup.sh` de um comando que prepara o ambiente do ENEM Extractor com `uv`, dispensando Docker e rebuilds, mais uma seção "instalação rápida" no README.

**Architecture:** Um shell script Bash idempotente na raiz do projeto instala o `uv` (se ausente), e roda `uv sync` — que baixa um Python 3.10+ standalone, cria o `.venv` local e instala as dependências travadas do `uv.lock`. O README ganha uma subseção apontando para o script. Sem código de aplicação novo.

**Tech Stack:** Bash, `uv` (astral), Python 3.10+ (gerenciado pelo `uv`), `uv.lock`/`pyproject.toml` existentes.

**Nota sobre testes:** Não há teste unitário viável para um shell script deste tipo. A verificação é feita por (a) checagem de sintaxe com `bash -n`, (b) `shellcheck` quando disponível, e (c) execução ponta a ponta confirmando que `uv run enem-extractor` roda.

---

### Task 1: Criar `setup.sh`

**Files:**
- Create: `setup.sh`

- [ ] **Step 1: Escrever o script**

Crie `setup.sh` na raiz do projeto com exatamente este conteúdo:

```bash
#!/usr/bin/env bash
# Setup do ENEM Extractor com uv.
# Instala o uv (se preciso), baixa um Python 3.10+ standalone, cria o .venv
# e instala as dependencias travadas do uv.lock. Dispensa Docker e rebuilds.
set -euo pipefail

# 1. Vai para a raiz do projeto (diretorio deste script), rode de onde rodar.
cd "$(dirname "$0")"

# 2. Garante o uv.
if ! command -v uv >/dev/null 2>&1; then
  echo "==> uv nao encontrado. Instalando..."
  if ! command -v curl >/dev/null 2>&1; then
    echo "ERRO: 'curl' nao esta instalado. Instale o curl e rode novamente." >&2
    echo "      Ubuntu/Debian: sudo apt-get update && sudo apt-get install -y curl" >&2
    exit 1
  fi
  curl -LsSf https://astral.sh/uv/install.sh | sh
  # O instalador coloca o uv em ~/.local/bin; disponibiliza na sessao atual.
  export PATH="$HOME/.local/bin:$PATH"
else
  echo "==> uv ja instalado: $(uv --version)"
fi

# 3. Prepara o ambiente: baixa Python 3.10+, cria .venv, instala deps do lock.
echo "==> Preparando ambiente com 'uv sync'..."
uv sync

# 4. Mensagem final.
echo ""
echo "==> Pronto! O ambiente esta configurado."
echo "    1. Coloque os PDFs das provas em: provas/"
echo "    2. Rode a extracao com:           uv run enem-extractor"
```

- [ ] **Step 2: Tornar executável**

Run: `chmod +x setup.sh`
Expected: sem saída (sucesso).

- [ ] **Step 3: Verificar sintaxe do Bash**

Run: `bash -n setup.sh && echo OK`
Expected: imprime `OK` sem erros.

- [ ] **Step 4: Lint com shellcheck (se disponível)**

Run: `command -v shellcheck >/dev/null 2>&1 && shellcheck setup.sh || echo "shellcheck ausente, pulando"`
Expected: `shellcheck` sem avisos, OU a mensagem `shellcheck ausente, pulando`.

- [ ] **Step 5: Commit**

```bash
git add setup.sh
git commit -m "feat: script setup.sh para ambiente com uv (sem docker)"
```

---

### Task 2: Validar `setup.sh` ponta a ponta

Executa o script de verdade nesta máquina (macOS) e confirma que a CLI roda pelo ambiente que ele criou. Isso valida o fluxo real do amigo, exceto o SO.

**Files:** nenhum (validação).

- [ ] **Step 1: Rodar o script**

Run: `./setup.sh`
Expected: termina com a mensagem `==> Pronto! O ambiente esta configurado.` e sem erro. Um diretório `.venv/` passa a existir na raiz.

- [ ] **Step 2: Confirmar que a CLI executa pelo ambiente criado**

Run: `uv run enem-extractor --help 2>&1 | head -5 || uv run enem-extractor 2>&1 | head -20`
Expected: a CLI inicia (mostra ajuda, ou processa a pasta `provas/` sem `ModuleNotFoundError`/erro de import). O objetivo é confirmar que `PyMuPDF`/`Pillow` estão instalados e o entry point resolve.

- [ ] **Step 3: Confirmar idempotência (re-execução segura)**

Run: `./setup.sh`
Expected: desta vez imprime `==> uv ja instalado: ...`, roda `uv sync` sem reinstalar tudo, e termina com a mesma mensagem de sucesso. Sem erros.

- [ ] **Step 4: Sem commit**

Nada a commitar nesta task — `.venv/` é ignorado pelo Git (confirme com `git status --short`, que não deve listar `.venv/`).

---

### Task 3: Documentar no README

**Files:**
- Modify: `README.md` (seção `## Instalação`, linhas 14-22)

- [ ] **Step 1: Inserir a subseção "Instalação rápida"**

Substitua o bloco atual (do cabeçalho `## Instalação` até o fim do bloco de código `pip install -e .`, linhas 14-22) por:

````markdown
## Instalação

### Instalação rápida (recomendada)

Um único comando prepara tudo com [uv](https://docs.astral.sh/uv/): ele baixa um
Python 3.10+ isolado (sem mexer no Python do sistema — ideal para Ubuntu antigo),
cria o `.venv` e instala as dependências. Não precisa de Docker nem de rebuild a
cada alteração.

```bash
git clone <repo> && cd ExtractImagemEnem
./setup.sh
uv run enem-extractor
```

### Instalação manual

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
# ou, como pacote editável (habilita o comando `enem-extractor`):
pip install -e .
```
````

- [ ] **Step 2: Verificar que o restante do README continua íntegro**

Run: `grep -n "Instalação rápida" README.md && grep -n "Instalação manual" README.md`
Expected: ambas as linhas são encontradas. A seção `## Uso` logo abaixo permanece intacta.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: seção de instalação rápida com uv (setup.sh)"
```

---

## Self-Review

**Spec coverage:**
- Componente 1 (`setup.sh`: localiza raiz, garante uv, `uv sync`, mensagem final, tratamento de erro para `curl` ausente, idempotência) → Task 1 + Task 2. ✅
- Componente 2 (subseção "Instalação rápida" antes do método manual) → Task 3. ✅
- Verificação (rodar script + confirmar `uv run enem-extractor`, validação local macOS) → Task 2. ✅
- Fora de escopo (MCP, Makefile, flags, CI) → não incluído. ✅

**Placeholder scan:** O `<repo>` no exemplo do README é intencional (o usuário insere a URL do próprio fork/clone), consistente com o spec. Nenhum outro placeholder.

**Consistência:** Nomes de comandos (`uv sync`, `uv run enem-extractor`), caminho do script (`./setup.sh`) e diretório (`provas/`) idênticos entre tasks, spec e README.
