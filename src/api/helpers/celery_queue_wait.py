"""Resolve Celery task position in Redis broker lists (heavy/light/celery)."""

from __future__ import annotations

import gzip
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

CELERY_QUEUE_NAMES: tuple[str, ...] = ("heavy", "light", "celery")


def _raw_contains_task_id(raw: bytes, task_id: str) -> bool:
    if task_id.encode("utf-8") in raw:
        return True
    if raw.startswith(b"\x1f\x8b"):
        try:
            decompressed = gzip.decompress(raw)
            return task_id.encode("utf-8") in decompressed
        except OSError:
            return False
    return False


def _scan_queue(redis_client: Any, queue_name: str, task_id: str) -> Optional[tuple[int, int]]:
    """Return (0-based index from Redis list head, length) if task_id is found.

    With Celery's Redis transport, new messages are typically pushed on one end and
    workers pop from the other; index 0 is not necessarily "next to run". The frontend
    maps this to a human place-in-line as queue_length - position (1 = next).
    """
    try:
        length = int(redis_client.llen(queue_name))
    except Exception:
        return None
    if length <= 0:
        return None
    try:
        items: List[bytes] = redis_client.lrange(queue_name, 0, -1)
    except Exception as e:
        logger.debug("lrange failed for queue %s: %s", queue_name, e)
        return None
    for i, raw in enumerate(items):
        if not isinstance(raw, (bytes, bytearray)):
            raw = str(raw).encode("utf-8", errors="ignore")
        if _raw_contains_task_id(bytes(raw), task_id):
            return (i, length)
    return None


def resolve_queue_wait(celery_app: Any, task_id: str) -> Optional[Dict[str, Any]]:
    """
    If broker is Redis, search known queues for a message containing task_id.
    Returns None if transport is not Redis or lookup fails.
    """
    if not task_id:
        return None
    try:
        with celery_app.connection_for_read() as connection:
            if getattr(connection.transport, "driver_type", None) != "redis":
                return None
            channel = connection.channel()
            try:
                redis_client = getattr(channel, "client", None)
                if redis_client is None:
                    return None
                for q in CELERY_QUEUE_NAMES:
                    hit = _scan_queue(redis_client, q, task_id)
                    if hit is not None:
                        pos, qlen = hit
                        return {
                            "in_queue": True,
                            "queue": q,
                            "position": pos,
                            "queue_length": qlen,
                            "broker": "redis",
                        }
                return {
                    "in_queue": False,
                    "queue": None,
                    "position": None,
                    "queue_length": None,
                    "broker": "redis",
                }
            finally:
                channel.close()
    except Exception as e:
        logger.debug("resolve_queue_wait failed: %s", e)
        return None


def resolve_queue_wait_for_pending_tasks(celery_app: Any, task_ids: List[str]) -> Optional[Dict[str, Any]]:
    """
    For several pending task ids (e.g. group children), pick the best queue_wait:
    prefer an entry that is in_queue with minimal position; else last non-None wait info.
    """
    if not task_ids:
        return None
    best_in_queue: Optional[Dict[str, Any]] = None
    last_wait: Optional[Dict[str, Any]] = None
    for tid in task_ids:
        w = resolve_queue_wait(celery_app, tid)
        if w is None:
            continue
        last_wait = w
        if w.get("in_queue") and w.get("position") is not None:
            if best_in_queue is None or w["position"] < best_in_queue["position"]:
                best_in_queue = w
    return best_in_queue or last_wait
