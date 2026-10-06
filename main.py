"""Servidor de Matriz Saciante: entrega la página y reenvía las consultas a Gemini.

Solo usa la biblioteca estándar. Variables de entorno:
  PORT            puerto donde escuchar (Railway lo pone solo)
  GEMINI_API_KEY  clave de Gemini; así no hay que pegarla en el navegador
  GEMINI_MODEL    modelo a usar (opcional)
"""
import json
import os
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PAGINA = Path(__file__).parent / "Matriz Saciante.html"
MODELO = os.environ.get("GEMINI_MODEL", "gemini-flash-latest")
MAX_CUERPO = 6 * 1024 * 1024  # una foto reducida pesa mucho menos


def clave():
    return os.environ.get("GEMINI_API_KEY", "").strip()


class Servidor(BaseHTTPRequestHandler):
    def responder(self, estado, cuerpo, tipo="application/json; charset=utf-8"):
        self.send_response(estado)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(cuerpo)

    def json(self, estado, datos):
        self.responder(estado, json.dumps(datos).encode("utf-8"))

    def do_GET(self):
        ruta = self.path.split("?")[0]
        if ruta in ("/", "/index.html"):
            self.responder(200, PAGINA.read_bytes(), "text/html; charset=utf-8")
        elif ruta == "/api/estado":
            self.json(200, {"gemini": bool(clave())})
        else:
            self.json(404, {"error": {"message": "No existe"}})

    do_HEAD = do_GET

    def do_POST(self):
        if self.path.split("?")[0] != "/api/gemini":
            return self.json(404, {"error": {"message": "No existe"}})
        if not clave():
            return self.json(503, {"error": {"message": "Falta GEMINI_API_KEY en el servidor"}})
        try:
            largo = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            largo = 0
        if not 0 < largo <= MAX_CUERPO:
            return self.json(413, {"error": {"message": "Solicitud vacía o demasiado grande"}})
        cuerpo = self.rfile.read(largo)
        pedido = urllib.request.Request(
            f"https://generativelanguage.googleapis.com/v1beta/models/{MODELO}:generateContent",
            data=cuerpo,
            headers={"Content-Type": "application/json", "x-goog-api-key": clave()},
        )
        try:
            with urllib.request.urlopen(pedido, timeout=60) as r:
                self.responder(r.status, r.read())
        except urllib.error.HTTPError as e:
            self.responder(e.code, e.read())
        except (urllib.error.URLError, TimeoutError):
            self.json(502, {"error": {"message": "No se pudo conectar con Gemini"}})


if __name__ == "__main__":
    puerto = int(os.environ.get("PORT", "8000"))
    print(f"Matriz Saciante en http://localhost:{puerto}")
    ThreadingHTTPServer(("0.0.0.0", puerto), Servidor).serve_forever()
