import argparse
from pathlib import Path

from .service import extract


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Extrai questões de provas do ENEM em provas/ como imagens PNG."
    )
    parser.add_argument(
        "--mode",
        choices=["auto", "normal", "ampliada"],
        default="auto",
        help="Modo de extração (padrão: auto).",
    )
    parser.add_argument(
        "--sem-numero",
        action="store_true",
        help='Recorta logo abaixo do título "Questão NN", removendo-o das imagens.',
    )
    args = parser.parse_args(argv)

    provas_dir = Path("provas")

    for pdf_file in sorted(provas_dir.glob("*.pdf")):
        result = extract(str(pdf_file), mode=args.mode, cut_number=args.sem_numero)
        print(
            f"Processado: {result['pdf']} -> {result['output_dir']} "
            f"(modo={result['mode']}, {len(result['images'])} imagens)"
        )


if __name__ == "__main__":
    main()
