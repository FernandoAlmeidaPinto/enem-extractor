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

# `FunctionResource` não tem alias público estável no SDK; este caminho interno
# é válido para mcp 2.x (pinado em pyproject). Reavaliar em upgrades de major.
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
