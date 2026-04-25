#!/usr/bin/env python3
import hashlib
import json
import mimetypes
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parent
HOST = "127.0.0.1"
PORT = 8765


class Handler(BaseHTTPRequestHandler):
    def _send_bytes(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self._send_bytes(status, body, "application/json; charset=utf-8")

    def do_GET(self) -> None:
        rel = self.path.split("?", 1)[0]
        if rel == "/":
            rel = "/index.html"
        path = (ROOT / rel.lstrip("/")).resolve()
        if ROOT not in path.parents and path != ROOT:
            self._send_json(403, {"error": "forbidden"})
            return
        if not path.exists() or not path.is_file():
            self._send_json(404, {"error": "not found"})
            return
        content_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        self._send_bytes(200, path.read_bytes(), content_type)

    def do_POST(self) -> None:
        if self.path != "/submit":
            self._send_json(404, {"error": "not found"})
            return
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode("utf-8"))
            text = payload.get("text", "")
            if not isinstance(text, str) or not text.strip():
                raise ValueError("missing text")
        except Exception:
            self._send_json(400, {"error": "invalid request"})
            return

        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
        out_path = Path("/tmp") / f"{digest}.txt"
        out_path.write_text(text + "\n", encoding="utf-8")
        self._send_json(200, {"ok": True, "path": str(out_path)})

    def log_message(self, format: str, *args) -> None:
        return


def main() -> None:
    httpd = HTTPServer((HOST, PORT), Handler)
    print(f"serving http://{HOST}:{PORT}", flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
