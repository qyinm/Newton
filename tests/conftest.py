from __future__ import annotations

import contextlib
import functools
import http.server
import socket
import socketserver
import threading
from pathlib import Path
from typing import Iterator

import pytest


class QuietSimpleHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        return


def _free_port() -> int:
    with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture
def playwright_fixture_base_url() -> Iterator[str]:
    fixture_dir = Path(__file__).parent / "fixtures" / "web"
    port = _free_port()
    handler = functools.partial(QuietSimpleHTTPRequestHandler, directory=str(fixture_dir))
    server = socketserver.ThreadingTCPServer(("127.0.0.1", port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
