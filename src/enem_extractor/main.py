from pathlib import Path

from .service import extract


def main():
    provas_dir = Path("provas")

    for pdf_file in sorted(provas_dir.glob("*.pdf")):
        result = extract(str(pdf_file))
        print(
            f"Processado: {result['pdf']} -> {result['output_dir']} "
            f"(modo={result['mode']}, {len(result['images'])} imagens)"
        )


if __name__ == "__main__":
    main()
