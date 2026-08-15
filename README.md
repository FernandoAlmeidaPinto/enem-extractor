# ENEM Extractor

Extrai automaticamente cada questão de um PDF de prova do ENEM e salva como uma
imagem PNG individual, organizada por ano e dia de aplicação.

Usa [PyMuPDF](https://pymupdf.readthedocs.io/) para localizar o texto `QUESTÃO NN`
por coordenadas na página e [Pillow](https://python-pillow.org/) para gerar as imagens.

## Requisitos

- Python 3.10+
- Dependências em `requirements.txt` (`PyMuPDF`, `Pillow`)

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

## Uso

1. Coloque os PDFs das provas na pasta `provas/`.
2. Nomeie cada arquivo seguindo o padrão do INEP, começando por **ano** e contendo o **dia** (`D1`/`D2`):

   ```
   provas/2023_PV_impresso_D1_CD4.pdf
   provas/2023_PV_impresso_D2_CD4.pdf
   ```

3. Rode o extrator a partir da raiz do projeto:

   ```bash
   python -m enem_extractor.main
   # ou, se instalado com `pip install -e .`:
   enem-extractor
   ```

As imagens são salvas em:

```
imagens/<ano>/<dia>/questao_NNN.png
```

> No dia 2 (`D2`) a numeração das questões continua a partir de 91, seguindo a
> convenção do ENEM.

## Uso como serviço / worker

O pacote expõe uma entrada única `extract`, ideal para ser chamada por um worker:

```python
from enem_extractor import extract

# auto-detecção do tipo pelo nome do arquivo
result = extract("provas/2025_PV_impresso_D1_CD9_ampliada.pdf")

# forçando modo e pasta de saída
result = extract(pdf_path, output_dir="/tmp/out", mode="normal")

# result == {
#     "pdf": "...",
#     "mode": "ampliada",          # 'normal' | 'ampliada'
#     "output_dir": "imagens/2025/D1",
#     "images": ["imagens/2025/D1/page_1_question_1.png", ...],
# }
```

- `mode`: `"auto"` (padrão) detecta pelo nome (`ampliada`/`superampliada` → extractor
  ampliada; caso contrário normal). Use `"normal"` ou `"ampliada"` para forçar.
- `output_dir`: se omitido, deriva `imagens/<ano>/<dia>` do nome do arquivo.
- Erros: `FileNotFoundError` se o PDF não existir; `ValueError` se `mode` for inválido.

## Uso via MCP (Model Context Protocol)

O projeto inclui um servidor MCP que expõe as provas e a extração para clientes
como o Claude Code.

Instale o extra opcional:

```bash
uv sync --extra mcp
# ou, com pip:
pip install -e ".[mcp]"
```

O servidor é iniciado pelo console script `enem-extractor-mcp` (via stdio). O
arquivo `.mcp.json` (versionado) já o registra para o Claude Code:

```json
{
  "mcpServers": {
    "enem-extractor": {
      "command": "uv",
      "args": ["run", "--extra", "mcp", "enem-extractor-mcp"],
      "env": { "PROVAS_DIR": "provas" }
    }
  }
}
```

Ao abrir o projeto no Claude Code:

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

## Estrutura

```
.
├── src/enem_extractor/
│   ├── service.py     # entrada única: extract() detecta o tipo e roteia
│   ├── catalog.py     # catálogo de provas (list/resolve) para o MCP
│   ├── mcp_server.py  # servidor MCP (resources + tools)
│   ├── main.py        # CLI: varre provas/ e chama o service
│   ├── normal.py      # extração da prova padrão (layout de duas colunas)
│   └── ampliada.py    # extração da prova ampliada (coluna única)
├── tests/             # testes (unittest, sem PyMuPDF/Pillow)
├── provas/            # coloque os PDFs aqui (ignorados no Git)
├── .mcp.json          # registro do servidor MCP (Claude Code)
├── requirements.txt
├── pyproject.toml
└── README.md
```

## Notas

- **Prova padrão** (`normal.py`): detecta as duas colunas da prova, numeração
  contínua entre páginas, renderização com zoom 2x.
- **Prova ampliada** (`ampliada.py`): layout de coluna única, para as versões de
  acessibilidade. Executável diretamente via `python -m enem_extractor.ampliada`.
- A pasta `imagens/` e os PDFs em `provas/` não são versionados (veja `.gitignore`).

## Licença

MIT — veja [LICENSE](LICENSE).
