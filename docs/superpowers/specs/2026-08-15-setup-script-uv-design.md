# Design: Script de setup com `uv` para o ENEM Extractor

**Data:** 2026-08-15
**Status:** Aprovado

## Contexto e problema

O ENEM Extractor é um projeto Python puro (deps: `PyMuPDF`, `Pillow`), gerenciado
por `uv`, com `pyproject.toml` e `uv.lock` versionados. Exige **Python 3.10+**.

Um usuário tentou rodar a aplicação empacotando-a em Docker por conta própria,
porque o **Ubuntu 18.04** dele traz Python 3.6/3.7 de fábrica e o projeto exige
3.10+. Duas dores resultaram disso:

1. **Dependências não aceitas** no Ubuntu 18 ao montar a imagem.
2. **Toda alteração exigia rebuild** da imagem e subir o container de novo —
   ciclo de edição lento.

O `uv` resolve a raiz do problema: consegue baixar e gerenciar um Python 3.10+
standalone sem tocar no Python do sistema, e edições no código valem na hora
(sem rebuild). O objetivo é **abandonar o Docker** e oferecer um setup nativo de
um comando.

## Escopo

- **Alvo de uso:** apenas a extração via CLI (`enem-extractor` /
  `python -m enem_extractor.main`).
- **Plataforma primária:** Ubuntu 18.04 (do amigo). O script também deve
  funcionar em macOS/Linux modernos, o que sai de graça com o `uv`.

## Solução

Duas entregas: um script de setup e uma seção no README.

### Componente 1 — `setup.sh` (raiz do projeto)

Shell script Bash, idempotente, com `set -euo pipefail`. Fluxo:

1. **Localiza a raiz** — `cd` para o diretório do próprio script, para funcionar
   independentemente do diretório de onde é chamado.
2. **Garante o `uv`** — se `command -v uv` falhar, instala via
   `curl -LsSf https://astral.sh/uv/install.sh | sh` e adiciona
   `$HOME/.local/bin` ao `PATH` da sessão atual (senão o `uv` recém-instalado
   não é encontrado no mesmo shell).
3. **Prepara o ambiente** — roda `uv sync`, que:
   - baixa um Python 3.10+ standalone (não mexe no Python do Ubuntu 18),
   - cria o `.venv` local,
   - instala as dependências exatas do `uv.lock`.
4. **Mensagem final** — imprime como usar: colocar PDFs em `provas/` e rodar
   `uv run enem-extractor`.

**Tratamento de erro:**
- `set -euo pipefail` aborta em qualquer falha de comando.
- Checagem amigável se `curl` não existir (mensagem clara pedindo para instalar
  `curl` antes de continuar).
- Re-execução é segura: `uv` já instalado é pulado; `uv sync` é idempotente.

### Componente 2 — Doc no README

Nova subseção em **Instalação**, "Instalação rápida (recomendada)", posicionada
antes do método manual atual:

```bash
git clone <repo> && cd ExtractImagemEnem
./setup.sh
uv run enem-extractor
```

Uma frase explicando que o `uv` cuida do Python 3.10+ automaticamente — ideal
para Ubuntu antigo — e que não é preciso Docker nem rebuild a cada alteração.

## Verificação

- Por ser shell script, não há teste unitário.
- Validação = rodar `./setup.sh` numa máquina e confirmar que
  `uv run enem-extractor` executa.
- Validar localmente (macOS) que o fluxo funciona ponta a ponta.
- O Ubuntu 18 em si não é testável a partir do ambiente de desenvolvimento, mas
  o `uv` suporta oficialmente glibc ≥ 2.17 (Ubuntu 18.04 tem 2.27) e o Python
  standalone (python-build-standalone) roda nele.

## Fora de escopo (YAGNI)

- Servidor MCP (`enem-extractor-mcp`).
- `Makefile` ou outros wrappers.
- Flags/opções de linha de comando no script.
- CI/automação.
- Remoção/alteração do fluxo de instalação manual existente (permanece no README).
