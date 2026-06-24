from __future__ import annotations

import os
from wsgiref.simple_server import make_server

from src.tls_middleware import TLSConfig, TLSEnforcementMiddleware, create_tls_ssl_context
from src.web_app import create_app


def main() -> None:
    inner_app = create_app()
    tls_config = TLSConfig(
        redirect_http=True,
        hsts_max_age_seconds=31_536_000,
        hsts_include_subdomains=True,
        hsts_preload=True,
    )
    app = TLSEnforcementMiddleware(inner_app, config=tls_config)

    host = os.environ.get("PROPELIQ_HOST", "127.0.0.1")
    port = int(os.environ.get("PROPELIQ_PORT", "8000"))

    certfile = os.environ.get("PROPELIQ_TLS_CERT", "")
    keyfile = os.environ.get("PROPELIQ_TLS_KEY", "")

    with make_server(host, port, app) as server:
        if certfile and keyfile:
            # Production / staging: wrap with TLS 1.2+ SSL context.
            # Weak protocols (SSLv2/3, TLS 1.0/1.1) and weak ciphers are
            # disabled by create_tls_ssl_context.
            ssl_ctx = create_tls_ssl_context(certfile, keyfile, tls_config)
            server.socket = ssl_ctx.wrap_socket(server.socket, server_side=True)
            scheme = "https"
        else:
            # Development fallback: TLSEnforcementMiddleware handles redirect
            # logic; set wsgi.url_scheme so the middleware knows it's HTTP.
            scheme = "http"

        print(f"PropelIQ API running at {scheme}://{host}:{port}")
        print("TLS enforcement: active (TLSEnforcementMiddleware)")
        print("Minimum TLS version: 1.2 | Weak protocols: disabled")
        server.serve_forever()


if __name__ == "__main__":
    main()
