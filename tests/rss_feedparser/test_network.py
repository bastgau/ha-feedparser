"""Tests for the fixture letting a test reach real remote servers."""

from __future__ import annotations

import socket


def test_network_enabled_allows_connections_to_any_address(network_enabled: None) -> None:  # pylint: disable=unused-argument
    """Test that a connection to an address other than 127.0.0.1 is not blocked.

    127.0.0.2 is a loopback address, so the test needs no internet, but it is outside the only address the
    Home Assistant test plugin allows: it fails exactly like a connection to a real server on a CI runner.
    """
    with socket.socket() as server:
        server.bind(("127.0.0.2", 0))
        server.listen()
        with socket.create_connection(server.getsockname(), timeout=5):
            pass
