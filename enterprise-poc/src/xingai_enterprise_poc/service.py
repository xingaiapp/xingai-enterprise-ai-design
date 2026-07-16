from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from json import dumps
from os import getenv


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        if self.path not in {"/healthz", "/readyz"}:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        body = dumps({"status": "ok", "check": self.path.removeprefix("/")}).encode()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


def serve() -> None:
    host = getenv("HOST", "0.0.0.0")
    port = int(getenv("PORT", "8080"))
    ThreadingHTTPServer((host, port), HealthHandler).serve_forever()


if __name__ == "__main__":
    serve()
