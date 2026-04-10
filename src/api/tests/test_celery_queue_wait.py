"""Unit tests for Redis queue wait resolution (mocked)."""

from unittest.mock import MagicMock, patch

import pytest

from helpers.celery_queue_wait import (
    _raw_contains_task_id,
    _scan_queue,
    resolve_queue_wait,
)


def test_raw_contains_task_id_plain():
    tid = "550e8400-e29b-41d4-a716-446655440000"
    assert _raw_contains_task_id(tid.encode(), tid) is True
    assert _raw_contains_task_id(b"no-uuid-here", tid) is False


def test_scan_queue_finds_index():
    tid = "abc-task-id"
    redis_client = MagicMock()
    redis_client.llen.return_value = 3
    redis_client.lrange.return_value = [b"other", f'"{tid}"'.encode(), b"x"]
    hit = _scan_queue(redis_client, "heavy", tid)
    assert hit == (1, 3)


def test_resolve_queue_wait_non_redis():
    app = MagicMock()
    conn = MagicMock()
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)
    app.connection_for_read.return_value = conn
    type(conn.transport).driver_type = MagicMock(return_value="amqp")

    assert resolve_queue_wait(app, "any-id") is None


def test_resolve_queue_wait_found():
    app = MagicMock()
    conn = MagicMock()
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)
    app.connection_for_read.return_value = conn
    type(conn.transport).driver_type = "redis"

    channel = MagicMock()
    redis_client = MagicMock()
    channel.client = redis_client
    conn.channel.return_value = channel

    tid = "550e8400-e29b-41d4-a716-446655440000"
    redis_client.llen.side_effect = [0, 2, 0]
    # heavy: llen 0 (no lrange); light: llen 2 then one lrange
    redis_client.lrange.side_effect = [[tid.encode(), b"x"]]

    with patch("helpers.celery_queue_wait.CELERY_QUEUE_NAMES", ("heavy", "light", "celery")):
        out = resolve_queue_wait(app, tid)

    assert out is not None
    assert out["in_queue"] is True
    assert out["queue"] == "light"
    assert out["position"] == 0
    assert out["queue_length"] == 2
    assert out["broker"] == "redis"
    channel.close.assert_called_once()
