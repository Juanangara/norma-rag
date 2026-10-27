"""Ask a question from the terminal. Run: python -m app.cli "tu pregunta" [--resumen]

Without --resumen it only searches (under a second once the model is loaded). With it, the local LLM
writes a summary (30 to 95 s on a laptop CPU) that is shown only if it passes the checks.
"""
import argparse
import textwrap

from app import retrieve as R
from app.answer import answer_question


def show(search, resumen: bool) -> None:
    print(f"\n{search.mensaje}")
    for i, f in enumerate(search.fuentes, 1):
        print(f"\n[{i}] {f['norma']}, artículo {f['articulo']}. {f['titulo']}")
        for paragraph in f["texto"].split("\n\n"):
            print(textwrap.indent(textwrap.fill(" ".join(paragraph.split()), 100), "    "))
    if search.resumen:
        print(f"\n--- {search.resumen_nota}\n{textwrap.fill(search.resumen.respuesta, 100)}")
    elif resumen and search.resumen_nota:
        print(f"\n--- {search.resumen_nota}")
    print(f"\n{search.aviso}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("pregunta")
    parser.add_argument("--resumen", action="store_true", help="add a checked summary from the local LLM")
    args = parser.parse_args()
    show(answer_question(R.connect(), args.pregunta, args.resumen), args.resumen)
