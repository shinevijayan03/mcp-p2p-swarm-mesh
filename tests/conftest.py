"""Pytest configuration and shared test fixtures."""

import asyncio
import pytest
from typing import AsyncGenerator, Tuple
from unittest.mock import MagicMock

class MockStreamWriter:
    """Mock StreamWriter that feeds writes directly into a paired StreamReader."""
    def __init__(self, reader: asyncio.StreamReader):
        self._reader = reader
        self._closed = False

    def write(self, data: bytes) -> None:
        if self._closed:
            raise ConnectionResetError("Cannot write to closed stream")
        self._reader.feed_data(data)

    async def drain(self) -> None:
        await asyncio.sleep(0)

    def close(self) -> None:
        self._closed = True
        self._reader.feed_eof()

    async def wait_closed(self) -> None:
        pass

    def is_closing(self) -> bool:
        return self._closed

class MockAsyncSocketPair:
    """Provides paired asyncio.StreamReader and StreamWriter interconnected in-memory."""
    def __init__(self):
        self.client_reader = asyncio.StreamReader()
        self.server_reader = asyncio.StreamReader()
        self.client_writer = MockStreamWriter(self.server_reader)
        self.server_writer = MockStreamWriter(self.client_reader)

@pytest.fixture
def mock_socket_pair() -> MockAsyncSocketPair:
    return MockAsyncSocketPair()

@pytest.fixture
def mock_clock(monkeypatch):
    """Provides controllable time simulation for 15s decay tests."""
    current_time = [1774088400.0]

    def fake_time():
        return current_time[0]

    monkeypatch.setattr("time.time", fake_time)

    def advance_time(seconds: float):
        current_time[0] += seconds

    return advance_time
