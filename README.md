# ENEM Extractor

Extrai automaticamente cada questão de um PDF de prova do ENEM e salva como uma
imagem PNG individual, organizada por ano e dia de aplicação.

Usa [PyMuPDF](https://pymupdf.readthedocs.io/) para localizar o texto `QUESTÃO NN`
por coordenadas na página e [Pillow](https://python-pillow.org/) para gerar as imagens.

## Requisitos

- Python 3.10+
- Dependências em `requirements.txt` (`PyMuPDF`, `Pillow`)

## Instalação

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

## Estrutura

```
.
├── src/enem_extractor/
│   ├── main.py        # ponto de entrada: varre provas/ e organiza a saída
│   ├── normal.py      # extração da prova padrão (layout de duas colunas)
│   └── ampliada.py    # extração da prova ampliada (coluna única)
├── provas/            # coloque os PDFs aqui (ignorados no Git)
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
