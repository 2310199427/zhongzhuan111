from __future__ import annotations

import socket
import threading

import pytest


@pytest.fixture(autouse=True)
def block_real_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """禁止真实网络，同时允许 Windows asyncio 创建内部 socketpair。"""

    original_connect = socket.socket.connect
    original_socketpair = socket.socketpair
    state = threading.local()

    def fail_create_connection(*args: object, **kwargs: object) -> None:
        raise AssertionError("Real network access is forbidden in tests")

    def guarded_connect(sock: socket.socket, address: object) -> object:
        # Windows 的 socket.socketpair() 会临时连接 127.0.0.1；这是事件循环
        # 的进程内唤醒通道，不是对外网络请求。
        if getattr(state, "creating_socketpair", False):
            return original_connect(sock, address)
        raise AssertionError("Real network access is forbidden in tests")

    def allowed_socketpair(*args: object, **kwargs: object) -> tuple[socket.socket, socket.socket]:
        state.creating_socketpair = True
        try:
            return original_socketpair(*args, **kwargs)
        finally:
            state.creating_socketpair = False

    monkeypatch.setattr(socket, "create_connection", fail_create_connection)
    monkeypatch.setattr(socket, "socketpair", allowed_socketpair)
    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
