"""Local web demo. Run: python -m app.web  (then open http://127.0.0.1:8765)

Standard library only. Binds to 127.0.0.1: it is a demo of a local system, not a service to expose.
GET /api/search?q=...&resumen=0|1 returns the same result the CLI prints.
"""
import json
import threading
import urllib.error
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from app import retrieve as R
from app.answer import answer_question

HOST, PORT = "127.0.0.1", 8765
MAX_QUESTION_CHARS = 600
PAGE = Path(__file__).resolve().parent / "static" / "index.html"

_conn = None
_lock = threading.Lock()      # one database connection, one model: requests are served one at a time


def search(question: str, resumen: bool) -> dict:
    global _conn
    with _lock:
        if _conn is None or _conn.closed:
            _conn = R.connect()
        try:
            result = answer_question(_conn, question, resumen)
        except urllib.error.URLError:
            result = answer_question(_conn, question, False)
            result.resumen_nota = "El modelo local no está encendido (docker compose up -d llama); se muestran solo los artículos."
    return asdict(result)


class Handler(BaseHTTPRequestHandler):
    def reply(self, status: int, body: bytes, kind: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        url = urlparse(self.path)
        if url.path == "/":
            return self.reply(200, PAGE.read_bytes(), "text/html; charset=utf-8")
        if url.path == "/api/search":
            query = parse_qs(url.query)
            question = (query.get("q") or [""])[0].strip()[:MAX_QUESTION_CHARS]
            if not question:
                return self.reply(400, b'{"error": "Escribe una pregunta."}', "application/json")
            body = json.dumps(search(question, query.get("resumen") == ["1"]), ensure_ascii=False)
            return self.reply(200, body.encode("utf-8"), "application/json; charset=utf-8")
        self.reply(404, b"not found", "text/plain")

    def log_message(self, *args) -> None:      # keep the terminal quiet: questions can be personal
        pass


if __name__ == "__main__":
    from ingest import embed
    embed.embed_query("calentamiento")         # load the embedding model before the first request
    print(f"http://{HOST}:{PORT}  (Ctrl+C para salir)")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
