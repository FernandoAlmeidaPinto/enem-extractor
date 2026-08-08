# Design: servidor MCP para o enem-extractor

**Data:** 2026-08-08
**Projeto:** enem-extractor
**Status:** Aprovado

## Objetivo

Expor o extrator via um servidor **MCP** (Model Context Protocol) para que, dentro
de um cliente como o Claude Code, seja possível:

- usar `@` para **listar as provas disponíveis** (via *resources*), e
- **disparar a extração** de uma prova pelo agente (via *tool*).

Escopo enxuto: apenas **resources + tools** (sem *prompts*). Reaproveita toda a
lógica existente (`service.extract`), sem alterar o algoritmo de extração.

## Contexto

Estado atual (pacote `src/enem_extractor/`):
- `service.py` — `extract(pdf_path, output_dir=None, mode="auto") -> dict`,
  `detect_mode`, `default_output_dir`. Imports de PyMuPDF/Pillow são *lazy*.
- `main.py` — CLI que varre `provas/*.pdf` e chama `extract`.
- Núcleo leve: `fitz`/`Pillow` só são importados quando a extração roda de fato.

Não há config MCP no repositório ainda. Provas ficam em `provas/` (PDFs ignorados
no Git).

## Decisões

1. **Abordagem A:** camada MCP fina no mesmo pacote, com `mcp` como
   **dependência opcional** (`pip install ".[mcp]"`). Mantém o núcleo leve.
2. **Registro:** `.mcp.json` versionado no repositório (escopo do projeto).
3. **Transporte:** `stdio` (padrão), servidor local.
4. **Escopo:** resources + tools; sem prompts.

## Arquitetura

### Novo módulo: `src/enem_extractor/catalog.py` (lógica pura)

Responsável por descobrir as provas em uma pasta, sem depender de `mcp` nem
`fitz`. É a camada testável.

```python
from pathlib import Path

def provas_dir() -> Path:
    """Pasta de provas: variável de ambiente PROVAS_DIR ou 'provas' (default)."""

def list_provas(directory=None) -> list[dict]:
    """Varre a pasta e retorna, ordenado por nome, uma lista de:
    {"name": <arquivo.pdf>, "mode": <normal|ampliada>, "path": <str>,
     "size_bytes": <int>}.
    Pasta inexistente/sem PDFs -> lista vazia."""

def resolve_prova(name, directory=None) -> Path:
    """Resolve um nome de prova (arquivo listado) OU caminho para um Path
    existente. Levanta FileNotFoundError se não encontrar."""
```

- `mode` vem de `service.detect_mode`.
- `list_provas` usa `sorted(dir.glob("*.pdf"))` para ordem determinística.
- `resolve_prova`: se `name` for um caminho existente, usa direto; senão procura
  `directory / name` (e aceita `name` com ou sem `.pdf`).

### Novo módulo: `src/enem_extractor/mcp_server.py` (wiring fino)

Monta o servidor MCP em cima de `catalog` + `service`. Import de `mcp` só aqui.

**Resources (para o `@`):**
- No startup, varre `catalog.provas_dir()` e registra **um resource por prova**:
  - URI: `prova://<nome-do-arquivo.pdf>`
  - Conteúdo (JSON): `{"name", "mode", "path", "size_bytes"}`
  - MIME: `application/json`
- Um resource agregado:
  - URI: `provas://list`
  - Conteúdo (JSON): a lista completa de `catalog.list_provas()`.
- Trade-off documentado: provas adicionadas à pasta aparecem no `@` **após
  reiniciar** o servidor. O tool `list_provas` (abaixo) sempre varre ao vivo.

**Tools (ação do agente):**
- `list_provas() -> list[dict]` — varre a pasta **ao vivo** e retorna
  `catalog.list_provas()`. Sempre atual, sem reiniciar.
- `extract_prova(name: str, mode: str = "auto", output_dir: str | None = None) -> dict`
  — resolve `name` via `catalog.resolve_prova`, chama `service.extract` e retorna
  o dict `{pdf, mode, output_dir, images}`.
  - `FileNotFoundError` → erro de tool "prova não encontrada: ...".
  - `ValueError` (mode inválido) → erro de tool com os modos válidos.

**Entry point:**
```python
def main():
    mcp = build_server()
    mcp.run()  # stdio por padrão

if __name__ == "__main__":
    main()
```
`build_server()` cria o servidor, registra resources (scan) e tools, e retorna a
instância — isolando a montagem para permitir teste.

### Empacotamento (`pyproject.toml`)

```toml
[project.optional-dependencies]
mcp = ["mcp>=1.12"]

[project.scripts]
enem-extractor = "enem_extractor.main:main"
enem-extractor-mcp = "enem_extractor.mcp_server:main"
```

> A versão exata do `mcp` e o import correto (`from mcp.server import MCPServer`
> nas versões recentes; `from mcp.server.fastmcp import FastMCP` em versões
> anteriores) são confirmados na implementação, ao instalar o pacote. O plano
> deve verificar qual símbolo a versão instalada expõe e usar o compatível.

### Registro (`.mcp.json`)

```json
{
  "mcpServers": {
    "enem-extractor": {
      "command": "uv",
      "args": ["run", "enem-extractor-mcp"],
      "env": { "PROVAS_DIR": "provas" }
    }
  }
}
```

## Fluxo de dados

```
Claude Code
  ├─ @  → resources/list → [prova://2023_..., prova://2025_..._ampliada, provas://list]
  │        (registrados no startup a partir de PROVAS_DIR)
  └─ agente chama tool:
       list_provas()            → catalog.list_provas() (scan ao vivo)
       extract_prova(name,...)  → catalog.resolve_prova → service.extract → {pdf,mode,output_dir,images}
```

## Configuração e ambiente

- `PROVAS_DIR` (env): pasta das provas; default `provas`. Resolvida em relação ao
  CWD do processo do servidor.
- `output_dir` do `extract_prova`: se omitido, `service.extract` deriva
  `imagens/<ano>/<dia>` (comportamento já existente).

## Tratamento de erros

- `catalog.list_provas`: pasta inexistente/sem PDFs → lista vazia (não levanta).
- `catalog.resolve_prova`: não encontrado → `FileNotFoundError`.
- `extract_prova` (tool): captura `FileNotFoundError`/`ValueError` e retorna
  mensagem de erro clara para o cliente, em vez de estourar exceção crua.
- `extract_prova` é **síncrono**: provas grandes (64–96 páginas) bloqueiam até
  concluir. Aceitável para uso local; documentado no README.

## Testes

- `tests/test_catalog.py` (sem `mcp`/`fitz`): 
  - `list_provas` em pasta temporária com PDFs falsos → nomes/ordem corretos,
    `mode` por arquivo (normal/ampliada/superampliada), `size_bytes`.
  - pasta inexistente e pasta vazia → lista vazia.
  - `resolve_prova`: por nome, por nome sem `.pdf`, por caminho, e inexistente →
    `FileNotFoundError`.
  - `provas_dir`: respeita `PROVAS_DIR` e cai no default.
- `mcp_server.py`: teste opcional que **pula** (`skipUnless`) se `mcp` não estiver
  instalado; quando instalado, verifica que `build_server()` monta sem erro e
  registra as tools esperadas. Não exige um cliente MCP real nem `fitz`.

## Documentação

- Seção no `README.md`: como instalar o extra (`pip install -e ".[mcp]"` /
  `uv sync --extra mcp`), o que o `.mcp.json` registra, e como usar `@` +
  `list_provas`/`extract_prova`. Nota sobre extração síncrona e sobre reiniciar
  para ver provas novas no `@`.

## Fora de escopo

- Prompts MCP.
- Trazer as imagens geradas de volta como resources para o chat.
- Extração assíncrona/streaming de progresso.
- Descoberta dinâmica de resources sem reiniciar (o tool `list_provas` cobre a
  necessidade de ver provas novas).
- Qualquer mudança no algoritmo de extração (`normal.py`/`ampliada.py`).
