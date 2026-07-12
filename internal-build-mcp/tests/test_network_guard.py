from __future__ import annotations

import socket

import pytest


def test_real_socket_connection_is_blocked() -> None:
    sock = socket.socket()
    try:
        with pytest.raises(AssertionError, match="Real network access is forbidden"):
            sock.connect(("203.0.113.1", 9))
    finally:
        sock.close()


def test_socketpair_is_allowed_for_asyncio_internals() -> None:
    left, right = socket.socketpair()
    try:
        left.sendall(b"x")
        assert right.recv(1) == b"x"
    finally:
        left.close()
        right.close()
