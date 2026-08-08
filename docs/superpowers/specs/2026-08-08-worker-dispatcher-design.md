# Design: entrada única para uso como worker

**Data:** 2026-08-08
**Projeto:** enem-extractor
**Status:** Aprovado

## Objetivo

Permitir que o extrator seja chamado como um serviço/worker, passando apenas o
caminho de um PDF de prova. O serviço detecta automaticamente se a prova é
**ampliada** (pelo nome do arquivo) e roteia para o extractor correto, ou aceita
um parâmetro para **forçar** o modo. A lógica de extração existente é preservada;
adiciona-se apenas uma camada de entrada uniforme.

## Contexto

Estrutura atual (pacote `src/enem_extractor/`):

- `normal.py` — `extract_questions_normal(path, output)`: prova padrão, layout de
  duas colunas. `path` = caminho do PDF (com `.pdf`), `output` = pasta destino.
  Salva `questao_NNN.png`. Numeração contínua; offset de 90 quando `str(output)`
  contém `/D2`.
- `ampliada.py` — `extract_questions_ampliada(path)`: prova ampliada, coluna
  única. `path` = nome-base **sem** `.pdf`; a função anexa `.pdf`, cria uma pasta
  com o nome-base e salva `page_X_question_Y.png`. Processa apenas 2 páginas.
- `main.py` — varre `provas/*.pdf`, deriva `imagens/<ano>/<dia>` do nome e chama
  `extract_questions_normal` diretamente.

Problema: as assinaturas dos dois extractors são incompatíveis, o que impede uma
chamada uniforme por um worker.

## Convenção de nomes das provas

Fonte oficial: https://www.gov.br/inep/pt-br/areas-de-atuacao/avaliacao-e-exames-educacionais/enem/provas-e-gabaritos

| Arquivo | Tipo |
|---------|------|
| `2023_PV_impresso_D1_CD4.pdf` | normal |
| `2025_PV_impresso_D1_CD9_ampliada.pdf` | ampliada |
| `2025_PV_impresso_D1_CD9_superampliada.pdf` | superampliada → rota da ampliada |

O marcador é a palavra `ampliada` no nome. Como `superampliada` contém
`ampliada` como substring, a detecção por substring cobre ambas.

## Decisões

1. **Detecção:** substring `"ampliada"` (case-insensitive) no nome do arquivo →
   modo `ampliada`; caso contrário `normal`. `superampliada` usa a mesma rota da
   `ampliada`.
2. **Interface (Approach B):** padronizar a *assinatura* de
   `extract_questions_ampliada` para `(path, output)`, igual à `normal`. O
   algoritmo de extração permanece idêntico; muda apenas como recebe o caminho e
   para onde escreve.
3. **Dispatcher:** novo módulo `service.py` com a API pública do pacote.

## Arquitetura

### Módulo novo: `src/enem_extractor/service.py`

```python
def detect_mode(pdf_path) -> str:
    """'ampliada' se 'ampliada' estiver no nome (pega superampliada também),
    senão 'normal'."""
    name = Path(pdf_path).name.lower()
    return "ampliada" if "ampliada" in name else "normal"


def extract(pdf_path, output_dir=None, mode="auto") -> dict:
    """Ponto de entrada único.
    - valida pdf_path e mode
    - resolve o modo (detect_mode se 'auto', senão usa o forçado)
    - resolve output_dir (deriva imagens/<ano>/<dia> se None)
    - garante a pasta de saída (mkdir parents/exist_ok)
    - roteia para o extractor correto
    - retorna metadados do job
    """
```

**Parâmetros de `extract`:**

- `pdf_path` — caminho do PDF a processar (o que o worker recebe).
- `output_dir` — opcional. Se `None`, deriva `imagens/<ano>/<dia>` a partir do
  nome, reutilizando a lógica de `get_year_and_day`. Preserva o comportamento do
  offset `/D2` da `normal`.
- `mode` — `"auto"` (padrão) | `"normal"` | `"ampliada"`. Força o extractor.

**Validações (robustez de worker):**

- `pdf_path` inexistente → `FileNotFoundError`.
- `mode` fora de `{"auto", "normal", "ampliada"}` → `ValueError`.

**Retorno:**

```python
{
    "pdf": "/caminho/2025_..._ampliada.pdf",
    "mode": "ampliada",
    "output_dir": "imagens/2025/D1",
    "images": ["imagens/2025/D1/page_1_question_1.png", ...],
}
```

`images` é obtido via glob da pasta de saída após a extração — não altera o
interior dos extractors. Padrões de nome diferem por modo (`questao_*.png` na
normal, `page_*_question_*.png` na ampliada); o glob usa `*.png`.

### Alteração: `src/enem_extractor/ampliada.py`

```python
# antes
def extract_questions_ampliada(path):        # path sem .pdf; decide a saída
    pdf_path = path + ".pdf"
    Path(path).mkdir(parents=True, exist_ok=True)
    image_path = f"{path}/page_{...}.png"

# depois
def extract_questions_ampliada(path, output):  # igual à normal
    pdf_path = path                            # já vem com .pdf
    Path(output).mkdir(parents=True, exist_ok=True)
    image_path = f"{output}/page_{...}.png"
```

O laço `for page_num in range(2)`, a busca por `QUESTÃO`/`E` e a matemática do
retângulo permanecem inalterados. Mantém-se o bloco `if __name__ == "__main__"`,
ajustado para a nova assinatura.

### Alteração: `src/enem_extractor/main.py`

O loop de `provas/*.pdf` passa a chamar `extract(str(pdf_file))`, deixando o
dispatcher detectar o modo e derivar a saída. CLI e worker compartilham o mesmo
caminho de código. Ganho: o CLI passa a tratar também arquivos ampliada na pasta
(antes só chamava `normal`). `get_year_and_day` migra de `main.py` para
`service.py` (é ela que deriva o `output_dir`); `main.py` passa a importá-la de
`service.py`. Não há reexport a manter — nada externo depende dela hoje.

### Alteração: `src/enem_extractor/__init__.py`

```python
from .service import extract, detect_mode
from .normal import extract_questions_normal
from .ampliada import extract_questions_ampliada

__all__ = [
    "extract", "detect_mode",
    "extract_questions_normal", "extract_questions_ampliada",
]
```

## Uso pelo worker

```python
from enem_extractor import extract

# auto-detecção pelo nome
result = extract("/dados/2025_PV_impresso_D1_CD9_ampliada.pdf")

# forçando modo e destino
result = extract(pdf_path, output_dir="/tmp/out", mode="normal")
```

## Fluxo de dados

```
worker → extract(pdf_path, output_dir, mode)
           │
           ├─ valida pdf_path / mode
           ├─ mode == "auto" ? detect_mode(pdf_path) : mode
           ├─ output_dir is None ? imagens/<ano>/<dia> : output_dir
           ├─ mkdir(output_dir)
           ├─ mode == "ampliada" → extract_questions_ampliada(pdf_path, output_dir)
           │  else                → extract_questions_normal(pdf_path, output_dir)
           └─ glob(output_dir/*.png) → dict de resultado
```

## Tratamento de erros

- Caminho de PDF inválido: `FileNotFoundError` antes de abrir o PDF.
- `mode` inválido: `ValueError` com a lista de valores aceitos.
- Erros do PyMuPDF/Pillow durante a extração propagam para o chamador (o worker
  decide política de retry/log). Não são silenciados.

## Testes

- `detect_mode`: `normal` (`..._CD4.pdf`), `ampliada` (`..._ampliada.pdf`),
  `superampliada` (`..._superampliada.pdf` → `ampliada`), case-insensitive.
- `extract`: `mode` inválido → `ValueError`; `pdf_path` inexistente →
  `FileNotFoundError`; derivação de `output_dir` para um nome de exemplo.
- Testes que dependem de PyMuPDF/Pillow (extração real) ficam fora do escopo
  mínimo; os testes acima não abrem o PDF e não exigem as libs pesadas.

## Fora de escopo (registrado, não alterado)

- **`ampliada` lê apenas 2 páginas** (hardcoded). Comportamento atual mantido.
- **Detecção de `/D2`** na `normal` depende de `str(output_dir)` conter `/D2`.
  Com `output_dir` derivado automaticamente continua funcionando; se o worker
  passar um dir custom sem `D2`, o offset de 90 não é aplicado. Documentado.
- Nenhuma mudança no algoritmo de recorte de nenhum dos extractors.
