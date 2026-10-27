"""Defense 2: constrain generation. The model sees only the retrieved articles, split into numbered
paragraphs, and answers in a JSON shape enforced by the llama.cpp server (a grammar made from the schema).
It cites by paragraph number, never by copying text: a 1B model asked to copy quotes returned article
headings instead (0 of 8 quotes were literal in the first trial), so the quote is taken from the corpus."""
import json
import os
import time
import urllib.request
from dataclasses import dataclass

from app.retrieve import Hit

# Articles sent to the model. 4 loses nothing against 5 on the development sets (hit@k 0.77 / 0.97) and 3 loses
# 0.09 on the non-lawyer one; fewer articles means a shorter prompt, and prompt reading is half the latency.
SOURCES = 4

# Bounds keep the JSON short: without them the 1B model sometimes never closes the string and runs
# to max_tokens (about 100 s on this CPU).
MIN_ANSWER_CHARS = 80   # forces an explanation: the 1B model otherwise answers a bare "Sí" or "No"
MAX_ANSWER_CHARS = 450

SYSTEM = (
    "Eres un asistente que responde preguntas sobre la protección de datos personales en Colombia "
    "usando SOLO los artículos numerados que se te entregan. Reglas:\n"
    "- No uses conocimiento que no esté en los artículos.\n"
    "- Si los artículos no bastan para responder, dilo en la respuesta y no inventes.\n"
    "- En \"citas\" pon los códigos de los párrafos que sustentan tu respuesta.\n"
    "- Explica en dos a cuatro frases completas; nunca respondas solo \"Sí\" o \"No\".\n"
    "- No escribas los códigos dentro de la respuesta.\n"
    "- Si la pregunta parte de algo que los artículos contradicen, corrígelo.\n"
    "- Responde en español claro, para alguien que no es abogado."
)


@dataclass
class Answer:
    respuesta: str
    citas: list[str]           # paragraph codes such as "S2P1": source 2, paragraph 1
    raw: str
    seconds: float
    prompt_tokens: int = 0
    completion_tokens: int = 0
    valid: bool = True         # False when the output was cut off or is not the expected JSON


def llm_url() -> str:
    return f"http://127.0.0.1:{os.environ.get('LLAMA_PORT', '8082')}/v1/chat/completions"


def split_paragraphs(text: str) -> list[str]:
    return text.split("\n\n")


def paragraphs(hits: list[Hit]) -> dict[str, str]:
    """'S2P1' -> first paragraph of the second hit. These codes are what the model cites."""
    return {f"S{i}P{j}": p for i, h in enumerate(hits, 1) for j, p in enumerate(split_paragraphs(h.texto), 1)}


def schema(units: list[str]) -> dict:
    return {
        "type": "object",
        "properties": {
            "respuesta": {"type": "string", "minLength": MIN_ANSWER_CHARS, "maxLength": MAX_ANSWER_CHARS},
            "citas": {"type": "array", "minItems": 1, "maxItems": 3, "items": {"enum": units}},
        },
        "required": ["respuesta", "citas"],
    }


def render_sources(hits: list[Hit]) -> str:
    blocks = []
    for i, h in enumerate(hits, 1):
        body = "\n".join(f"[S{i}P{j}] {p}" for j, p in enumerate(split_paragraphs(h.texto), 1))
        blocks.append(f"{h.norma}, artículo {h.articulo}. {h.titulo_articulo}\n{body}")
    return "\n\n".join(blocks)


def messages(question: str, hits: list[Hit]) -> list[dict]:
    return [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": f"Artículos:\n\n{render_sources(hits)}\n\nPregunta: {question}"},
    ]


def generate(question: str, hits: list[Hit], max_tokens: int = 450) -> Answer:
    body = {
        "messages": messages(question, hits),
        "temperature": 0,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object", "schema": schema(list(paragraphs(hits)))},
    }
    request = urllib.request.Request(llm_url(), json.dumps(body).encode("utf-8"),
                                     {"Content-Type": "application/json; charset=utf-8"})
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=600) as response:
        reply = json.load(response)
    seconds = time.perf_counter() - started
    raw = reply["choices"][0]["message"]["content"]
    usage = reply.get("usage", {})
    tokens = (usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0))
    try:
        data = json.loads(raw)
        return Answer(data["respuesta"], data["citas"], raw, seconds, *tokens)
    except (json.JSONDecodeError, KeyError):
        # Cut off at max_tokens or malformed: never show it as an answer.
        return Answer("", [], raw, seconds, *tokens, valid=False)
