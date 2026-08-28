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
