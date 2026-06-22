from __future__ import annotations

from wsgiref.simple_server import make_server

from src.web_app import create_app


def main() -> None:
    app = create_app()
    host = "127.0.0.1"
    port = 8000
    with make_server(host, port, app) as server:
        print(f"Appointment search app running at http://{host}:{port}")
        server.serve_forever()


if __name__ == "__main__":
    main()
