# MCP Server Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expor o enem-extractor via um servidor MCP (stdio) que lista as provas como *resources* (para o `@`) e permite extrair uma prova via *tools*, reusando `service.extract` sem alterar o algoritmo.

**Architecture:** Uma camada pura `catalog.py` (varredura da pasta de provas, testável sem `mcp`/`fitz`) e um wiring fino `mcp_server.py` (registra um resource por prova + tools `list_provas`/`extract_prova`). `mcp` entra como dependência **opcional** para manter o núcleo leve. Registro via `.mcp.json` no repositório.

**Tech Stack:** Python 3.12, `mcp==2.0.0` (SDK oficial, API `MCPServer`), `unittest` stdlib. Reusa `enem_extractor.service`.

---

## API do SDK (verificada na versão instalada `mcp==2.0.0`)

- `from mcp.server import MCPServer` — classe do servidor (a antiga `FastMCP`).
- `from mcp.server.mcpserver.resources import FunctionResource` — resource dinâmico.
- `FunctionResource.from_function(fn=<callable-zero-arg>, uri=..., name=..., mime_type=...)`.
- `mcp.add_resource(resource)` — registra um resource concreto (aparece em `resources/list`, logo no `@`).
- `mcp.tool(name="...")(func)` — registra uma tool.
- `mcp.run()` — roda em `stdio` por padrão (bloqueante).

> Se um dia a versão instalada não expuser `mcp.server.MCPServer`, o import falha explicitamente na inicialização — preferível a um fallback silencioso. Pinamos `mcp>=2.0`.

## File Structure

- Create: `src/enem_extractor/catalog.py` — lógica pura: `provas_dir`, `list_provas`, `resolve_prova`.
- Create: `src/enem_extractor/mcp_server.py` — wiring MCP: `_resource_specs`, `list_provas_tool`, `extract_prova_tool`, `build_server`, `main`.
- Create: `tests/test_catalog.py` — testes puros (sem `mcp`/`fitz`).
- Create: `tests/test_mcp_server.py` — testes com `@skipUnless(mcp instalado)`.
- Modify: `pyproject.toml` — extra opcional `mcp` + console script `enem-extractor-mcp`.
- Modify: `uv.lock` — atualizado por `uv sync --extra mcp`.
- Create: `.mcp.json` — registro do servidor (stdio, via `uv run --extra mcp`).
- Modify: `README.md` — seção de uso via MCP.

**Comandos de teste:**
- Sem libs pesadas (catalog puro): `PYTHONPATH=src python3 -m unittest discover -s tests -v` (os testes de `mcp_server` se auto-pulam se `mcp` não estiver disponível).
- Com `mcp`/`fitz` (para rodar os testes de `mcp_server`): `PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v` (o `.venv` já tem `mcp`, `PyMuPDF` e `Pillow` instalados; `PYTHONPATH=src` garante importar do código-fonte).

---

## Task 1: `catalog.py` (lógica pura de catálogo)

**Files:**
- Create: `src/enem_extractor/catalog.py`
- Test: `tests/test_catalog.py`

- [ ] **Step 1: Escrever os testes que falham**

Criar `tests/test_catalog.py`:

```python
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from enem_extractor import catalog


class ProvasDirTests(unittest.TestCase):
    def test_default(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(catalog.provas_dir(), Path("provas"))

    def test_env_override(self):
        with mock.patch.dict(os.environ, {"PROVAS_DIR": "/tmp/x"}, clear=True):
            self.assertEqual(catalog.provas_dir(), Path("/tmp/x"))


class ListProvasTests(unittest.TestCase):
    def test_lista_ordenada_com_modo_e_tamanho(self):
        with TemporaryDirectory() as d:
            (Path(d) / "2025_PV_impresso_D1_CD9_ampliada.pdf").write_bytes(b"AA")
            (Path(d) / "2023_PV_impresso_D1_CD4.pdf").write_bytes(b"B")
            (Path(d) / "2025_PV_impresso_D1_CD9_superampliada.pdf").write_bytes(b"CCC")
            (Path(d) / "nota.txt").write_text("ignorar")
            provas = catalog.list_provas(d)

        names = [p["name"] for p in provas]
        self.assertEqual(
            names,
            [
                "2023_PV_impresso_D1_CD4.pdf",
                "2025_PV_impresso_D1_CD9_ampliada.pdf",
                "2025_PV_impresso_D1_CD9_superampliada.pdf",
            ],
        )
        modes = {p["name"]: p["mode"] for p in provas}
        self.assertEqual(modes["2023_PV_impresso_D1_CD4.pdf"], "normal")
        self.assertEqual(modes["2025_PV_impresso_D1_CD9_ampliada.pdf"], "ampliada")
        self.assertEqual(modes["2025_PV_impresso_D1_CD9_superampliada.pdf"], "ampliada")
        first = provas[0]
        self.assertEqual(first["size_bytes"], 1)
        self.assertTrue(first["path"].endswith("2023_PV_impresso_D1_CD4.pdf"))

    def test_pasta_inexistente(self):
        self.assertEqual(catalog.list_provas("/caminho/que/nao/existe"), [])

    def test_pasta_vazia(self):
        with TemporaryDirectory() as d:
            self.assertEqual(catalog.list_provas(d), [])


class ResolveProvaTests(unittest.TestCase):
    def test_por_nome(self):
        with TemporaryDirectory() as d:
            pdf = Path(d) / "2023_PV_impresso_D1_CD4.pdf"
            pdf.write_bytes(b"x")
            self.assertEqual(catalog.resolve_prova(pdf.name, d), pdf)

    def test_por_nome_sem_extensao(self):
        with TemporaryDirectory() as d:
            pdf = Path(d) / "2023_PV_impresso_D1_CD4.pdf"
            pdf.write_bytes(b"x")
            self.assertEqual(
                catalog.resolve_prova("2023_PV_impresso_D1_CD4", d), pdf
            )

    def test_por_caminho(self):
        with TemporaryDirectory() as d:
            pdf = Path(d) / "2023_PV_impresso_D1_CD4.pdf"
            pdf.write_bytes(b"x")
            self.assertEqual(catalog.resolve_prova(str(pdf)), pdf)

    def test_inexistente(self):
        with TemporaryDirectory() as d:
            with self.assertRaises(FileNotFoundError):
                catalog.resolve_prova("nao_existe.pdf", d)
```

- [ ] **Step 2: Rodar os testes e ver falhar**

Run: `PYTHONPATH=src python3 -m unittest discover -s tests -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'enem_extractor.catalog'`.

- [ ] **Step 3: Implementar `src/enem_extractor/catalog.py`**

```python
"""Catálogo de provas: descobre PDFs numa pasta e resolve nomes para caminhos.

Camada pura — depende apenas de stdlib e de `service.detect_mode`. Não importa
PyMuPDF/Pillow nem o SDK do MCP, então é testável em qualquer ambiente.
"""

import os
from pathlib import Path

from .service import detect_mode


def provas_dir() -> Path:
    """Pasta das provas: variável de ambiente PROVAS_DIR ou 'provas' (default)."""
    return Path(os.environ.get("PROVAS_DIR", "provas"))


def list_provas(directory=None) -> list[dict]:
    """Varre a pasta e retorna, ordenado por nome, uma lista de dicts:
    {"name", "mode", "path", "size_bytes"}. Pasta inexistente/sem PDFs -> []."""
    base = Path(directory) if directory is not None else provas_dir()
    if not base.is_dir():
        return []
    provas = []
    for pdf in sorted(base.glob("*.pdf")):
        provas.append(
            {
                "name": pdf.name,
                "mode": detect_mode(pdf.name),
                "path": str(pdf),
                "size_bytes": pdf.stat().st_size,
            }
        )
    return provas


def resolve_prova(name, directory=None) -> Path:
    """Resolve `name` (arquivo listado, com ou sem `.pdf`, ou um caminho) para um
    Path existente. Levanta FileNotFoundError se não encontrar."""
    direct = Path(name)
    if direct.is_file():
        return direct
    base = Path(directory) if directory is not None else provas_dir()
    candidate = base / name
    if candidate.is_file():
        return candidate
    if not str(name).endswith(".pdf"):
        candidate_pdf = base / f"{name}.pdf"
        if candidate_pdf.is_file():
            return candidate_pdf
    raise FileNotFoundError(f"prova não encontrada: {name!r} (em {base})")
```

- [ ] **Step 4: Rodar os testes e ver passar**

Run: `PYTHONPATH=src python3 -m unittest discover -s tests -v`
Expected: PASS — todos os testes de `test_catalog.py` e `test_service.py` OK (os de `mcp_server` ainda não existem).

- [ ] **Step 5: Commit**

```bash
git add src/enem_extractor/catalog.py tests/test_catalog.py
git commit -m "feat(catalog): catálogo puro de provas (list/resolve, testável sem deps)"
```

---

## Task 2: `mcp_server.py` (wiring do servidor MCP)

**Files:**
- Create: `src/enem_extractor/mcp_server.py`
- Test: `tests/test_mcp_server.py`

- [ ] **Step 1: Escrever os testes que falham**

Criar `tests/test_mcp_server.py`:

```python
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

try:
    import mcp  # noqa: F401
    from enem_extractor import mcp_server

    _HAS_MCP = True
except Exception:
    _HAS_MCP = False


@unittest.skipUnless(_HAS_MCP, "mcp não instalado")
class McpServerTests(unittest.TestCase):
    def test_build_server_ok(self):
        srv = mcp_server.build_server()
        self.assertEqual(srv.name, "enem-extractor")

    def test_resource_specs_inclui_provas_e_agregado(self):
        with TemporaryDirectory() as d:
            (Path(d) / "2023_PV_impresso_D1_CD4.pdf").write_bytes(b"%PDF")
            (Path(d) / "2025_PV_impresso_D1_CD9_ampliada.pdf").write_bytes(b"%PDF")
            specs = mcp_server._resource_specs(d)

        uris = [s["uri"] for s in specs]
        self.assertIn("prova://2023_PV_impresso_D1_CD4.pdf", uris)
        self.assertIn("prova://2025_PV_impresso_D1_CD9_ampliada.pdf", uris)
        self.assertIn("provas://list", uris)

    def test_list_provas_tool_scan_ao_vivo(self):
        with TemporaryDirectory() as d:
            (Path(d) / "2023_PV_impresso_D1_CD4.pdf").write_bytes(b"%PDF")
            old = os.environ.get("PROVAS_DIR")
            os.environ["PROVAS_DIR"] = d
            try:
                provas = mcp_server.list_provas_tool()
            finally:
                if old is None:
                    os.environ.pop("PROVAS_DIR", None)
                else:
                    os.environ["PROVAS_DIR"] = old

        self.assertEqual(len(provas), 1)
        self.assertEqual(provas[0]["mode"], "normal")

    def test_extract_prova_tool_arquivo_inexistente(self):
        with self.assertRaises(FileNotFoundError):
            mcp_server.extract_prova_tool("nao_existe.pdf")

    def test_extract_prova_tool_mode_invalido(self):
        with TemporaryDirectory() as d:
            pdf = Path(d) / "2023_PV_impresso_D1_CD4.pdf"
            pdf.write_bytes(b"%PDF")
            with self.assertRaises(ValueError):
                mcp_server.extract_prova_tool(str(pdf), mode="bogus")
```

- [ ] **Step 2: Rodar os testes e ver falhar**

Run: `PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v`
Expected: FAIL — `test_mcp_server` não consegue importar `enem_extractor.mcp_server` (`_HAS_MCP` fica False e os testes são pulados, OU, se importados, `ModuleNotFoundError`). Para forçar a falha explícita, confirme que o módulo ainda não existe:
Run: `PYTHONPATH=src .venv/bin/python -c "from enem_extractor import mcp_server"`
Expected: `ModuleNotFoundError: No module named 'enem_extractor.mcp_server'`.

- [ ] **Step 3: Implementar `src/enem_extractor/mcp_server.py`**

```python
"""Servidor MCP (stdio) do enem-extractor.

Wiring fino sobre `catalog` (descoberta de provas) e `service.extract` (extração).
Expõe:
- Resources: um por prova (`prova://<arquivo>.pdf`) + agregado `provas://list`,
  para aparecerem no seletor `@` de clientes MCP.
- Tools: `list_provas` (scan ao vivo) e `extract_prova` (dispara a extração).

Requer o extra opcional `mcp` (`pip install ".[mcp]"` ou `uv sync --extra mcp`).
"""

import json

from mcp.server import MCPServer
from mcp.server.mcpserver.resources import FunctionResource

from . import catalog, service


def _resource_specs(directory=None) -> list[dict]:
    """Specs de resource: um por prova + o agregado 'provas://list'.
    Cada spec: {"uri", "name", "json"} (conteúdo JSON já serializado)."""
    provas = catalog.list_provas(directory)
    specs = []
    for p in provas:
        specs.append(
            {
                "uri": f"prova://{p['name']}",
                "name": p["name"],
                "json": json.dumps(p, ensure_ascii=False),
            }
        )
    specs.append(
        {
            "uri": "provas://list",
            "name": "provas",
            "json": json.dumps(provas, ensure_ascii=False),
        }
    )
    return specs


def _make_reader(payload: str):
    """Fábrica de leitor zero-argumento para um resource (evita late-binding)."""

    def _read() -> str:
        return payload

    return _read


def list_provas_tool() -> list[dict]:
    """Lista as provas disponíveis (varredura ao vivo de PROVAS_DIR)."""
    return catalog.list_provas()


def extract_prova_tool(name: str, mode: str = "auto", output_dir: str | None = None) -> dict:
    """Extrai as questões de uma prova.

    `name`: arquivo listado (com ou sem `.pdf`) ou um caminho.
    `mode`: 'auto' (detecta pelo nome) | 'normal' | 'ampliada'.
    Retorna {pdf, mode, output_dir, images}.
    """
    pdf = catalog.resolve_prova(name)
    return service.extract(str(pdf), output_dir=output_dir, mode=mode)


def build_server() -> MCPServer:
    """Monta o servidor: registra um resource por prova (scan de startup) e as tools."""
    mcp = MCPServer("enem-extractor")

    for spec in _resource_specs():
        mcp.add_resource(
            FunctionResource.from_function(
                fn=_make_reader(spec["json"]),
                uri=spec["uri"],
                name=spec["name"],
                mime_type="application/json",
            )
        )

    mcp.tool(name="list_provas")(list_provas_tool)
    mcp.tool(name="extract_prova")(extract_prova_tool)
    return mcp


def main():
    build_server().run()  # stdio por padrão


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Rodar os testes e ver passar**

Run: `PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v`
Expected: PASS — os 5 testes de `test_mcp_server` executam (não são pulados, pois `mcp` está no `.venv`) e todos os demais continuam OK.

- [ ] **Step 5: Commit**

```bash
git add src/enem_extractor/mcp_server.py tests/test_mcp_server.py
git commit -m "feat(mcp): servidor MCP com resources de provas e tools list/extract"
```

---

## Task 3: Empacotamento (extra opcional `mcp` + console script)

**Files:**
- Modify: `pyproject.toml`
- Modify: `uv.lock`

- [ ] **Step 1: Editar `pyproject.toml`**

Localize o bloco `[project.scripts]`:

```toml
[project.scripts]
enem-extractor = "enem_extractor.main:main"
```

Substitua-o por (adiciona o extra opcional ANTES e o novo script):

```toml
[project.optional-dependencies]
mcp = ["mcp>=2.0"]

[project.scripts]
enem-extractor = "enem_extractor.main:main"
enem-extractor-mcp = "enem_extractor.mcp_server:main"
```

- [ ] **Step 2: Sincronizar o ambiente e o lockfile**

Run: `UV_HTTP_TIMEOUT=180 uv sync --extra mcp`
Expected: sincroniza sem erro; `uv.lock` é atualizado incluindo `mcp` e suas dependências. (O download já está em cache desta sessão.)

- [ ] **Step 3: Verificar o entry point e que o servidor monta**

Run: `uv run --extra mcp python -c "from enem_extractor.mcp_server import build_server; print('server:', build_server().name)"`
Expected: `server: enem-extractor`

- [ ] **Step 4: Rodar os testes (garantia)**

Run: `PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v`
Expected: PASS — todos os testes OK.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "build: extra opcional mcp e console script enem-extractor-mcp"
```

---

## Task 4: Registro `.mcp.json`

**Files:**
- Create: `.mcp.json`

- [ ] **Step 1: Criar `.mcp.json` na raiz do projeto**

```json
{
  "mcpServers": {
    "enem-extractor": {
      "command": "uv",
      "args": ["run", "--extra", "mcp", "enem-extractor-mcp"],
      "env": {
        "PROVAS_DIR": "provas"
      }
    }
  }
}
```

- [ ] **Step 2: Validar que é JSON bem-formado**

Run: `python3 -c "import json; json.load(open('.mcp.json')); print('json OK')"`
Expected: `json OK`

- [ ] **Step 3: Commit**

```bash
git add .mcp.json
git commit -m "chore: registra servidor MCP enem-extractor (.mcp.json, stdio via uv)"
```

---

## Task 5: Documentar uso via MCP no README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Adicionar a seção de MCP no `README.md`**

Inserir o bloco abaixo IMEDIATAMENTE APÓS a seção `## Uso como serviço / worker` e ANTES de `## Estrutura`. Escreva-o em markdown válido (sem a indentação de exibição):

````markdown
## Uso via MCP (Model Context Protocol)

O projeto inclui um servidor MCP que expõe as provas e a extração para clientes
como o Claude Code.

Instale o extra opcional:

```bash
uv sync --extra mcp
# ou, com pip:
pip install -e ".[mcp]"
```

O arquivo `.mcp.json` (versionado) já registra o servidor `enem-extractor` via
stdio. Ao abrir o projeto no Claude Code:

- **`@`** lista as provas disponíveis como *resources* (`prova://<arquivo>.pdf`,
  além do agregado `provas://list`).
- **Tools** disponíveis para o agente:
  - `list_provas()` — varre `PROVAS_DIR` ao vivo e devolve as provas com o modo
    detectado.
  - `extract_prova(name, mode="auto", output_dir=None)` — extrai a prova
    (`name` é o arquivo listado ou um caminho) e devolve
    `{pdf, mode, output_dir, images}`.

A pasta das provas é configurável pela variável `PROVAS_DIR` (default `provas`).

Notas:
- `extract_prova` é **síncrona** — provas grandes (dezenas de páginas) bloqueiam
  até concluir.
- Provas novas na pasta aparecem no `@` **após reiniciar** o servidor; o tool
  `list_provas` sempre enxerga a pasta ao vivo.
````

- [ ] **Step 2: Rodar os testes (garantia de que nada quebrou)**

Run: `PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v`
Expected: PASS — todos os testes OK.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: uso do servidor MCP (resources + tools)"
```

---

## Verificação de integração (manual, no Claude Code)

Estes passos exigem reiniciar o cliente MCP para carregar o `.mcp.json`.

- [ ] **Servidor monta e expõe as tools:**

Run: `uv run --extra mcp python -c "from enem_extractor.mcp_server import build_server, list_provas_tool; print('server:', build_server().name); print('provas:', [p['name'] for p in list_provas_tool()])"`
Expected: `server: enem-extractor` e a lista dos PDFs em `provas/`.

- [ ] **No Claude Code:** reabrir o projeto (ou reiniciar) para carregar `.mcp.json`. Digitar `@` e confirmar que as provas aparecem como resources. Pedir ao agente para chamar `list_provas` e depois `extract_prova` numa prova normal — confirmar que as imagens são geradas em `imagens/<ano>/<dia>/` e o retorno traz `mode`, `output_dir` e a lista `images`.

---

## Notas de escopo (do spec, não alterar)

- Sem *prompts* MCP.
- Sem trazer as imagens geradas de volta como resources.
- Sem extração assíncrona/streaming.
- Sem descoberta dinâmica de resources sem reiniciar (o tool `list_provas` cobre).
- Nenhuma mudança no algoritmo de extração (`normal.py`/`ampliada.py`).
