#!/usr/bin/env python3
"""
Concurrent load smoke test for discharge endpoints that enqueue Celery work.

Fires N parallel HTTP GETs (like 30 concurrent "users"), then polls until every
task finishes. Reports wall-clock time and per-request outcomes.

Usage:
  export HAKESCH_API_URL="https://api.example.com"
  export HAKESCH_BEARER_TOKEN="eyJ..."
  python concurrent_discharge_load_test.py --endpoint prepare

  Optional: pin one project — ``--project-id`` / ``HAKESCH_PROJECT_ID`` (otherwise
  all projects of the token user are loaded from ``GET /project/`` and requests
  are round-robin distributed).

Or pass flags:
  python concurrent_discharge_load_test.py \\
    --base-url https://api.example.com \\
    --token eyJ... \\
    --endpoint calculate \\
    --concurrency 30

Notes:
  - Base URL must be the API root (no trailing slash), e.g. http://localhost:8000
  - With multiple projects, ``prepare`` temp paths are per project id, reducing
    same-file contention compared to a single shared project.
  - ``calculate_project`` returns a chain id; when the chain succeeds, the API
    may still be running a Celery group — this script follows ``group_id`` and
    waits until every child task is SUCCESS.
  - Fortschritt in Prozent/Text kommt aus Celery ``update_state(PROGRESS, meta=…)``,
    sofern die Task das setzt (z. B. ``prepare_discharge_hydroparameters``). Die
    Chain vor ``calculate_project`` liefert oft nur PENDING/STARTED bis zum Ende
    der Kette — danach zeigt das Skript die Gruppen-Auslastung ``fertig/total``.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import requests

# (project_id, title) from GET /project/
ProjectRef = tuple[str, str]

TERMINAL_CHAIN = frozenset({"SUCCESS", "FAILURE", "REVOKED"})
NONTERMINAL_TASK = frozenset({"PENDING", "STARTED", "RETRY", "PROGRESS"})

ANSI_CLEAR = "\x1b[2J"
ANSI_HOME = "\x1b[H"
ANSI_HIDE_CURSOR = "\x1b[?25l"
ANSI_SHOW_CURSOR = "\x1b[?25h"


def _parse_json_maybe(value: Any) -> Any | None:
    if value is None or value == "null":
        return None
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return None
    return None


def _normalize_base(url: str) -> str:
    return url.rstrip("/")


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token.strip()}"}


def _short_id(s: str, head: int = 10) -> str:
    s = str(s)
    if len(s) <= head + 3:
        return s
    return f"{s[:head]}…"


def _project_label(project_id: str, title: str) -> str:
    t = (title or "").strip()
    if t:
        return f"{t!r} [{_short_id(project_id)}]"
    return _short_id(project_id, 16)


def fetch_user_projects(
    session: requests.Session,
    base_url: str,
    headers: dict[str, str],
) -> tuple[list[ProjectRef] | None, str | None]:
    """Load ``(id, title)`` for the authenticated user via ``GET /project/``."""
    url = f"{base_url}/project/"
    try:
        r = session.get(url, headers=headers, timeout=60)
    except requests.RequestException as e:
        return None, str(e)

    if r.status_code != 200:
        return None, f"HTTP {r.status_code}: {(r.text or '')[:400]}"

    try:
        data = r.json()
    except json.JSONDecodeError:
        return None, f"invalid JSON: {r.text[:200]}"

    if not isinstance(data, list):
        return None, "expected a JSON array of projects"

    projects: list[ProjectRef] = []
    for item in data:
        if isinstance(item, dict) and item.get("id") is not None:
            pid = str(item["id"])
            title = str(item.get("title") or "")
            projects.append((pid, title))

    if not projects:
        return None, "no projects returned for this user"

    return projects, None


def start_discharge_task(
    session: requests.Session,
    base_url: str,
    headers: dict[str, str],
    project_id: str,
    endpoint: str,
) -> tuple[str | None, int, str | None]:
    if endpoint == "prepare":
        path = f"/discharge/prepare_discharge_hydroparameters?ProjectId={project_id}"
    elif endpoint == "calculate":
        path = f"/discharge/calculate_project?ProjectId={project_id}"
    else:
        raise ValueError(f"unknown endpoint key: {endpoint}")

    url = f"{base_url}{path}"
    try:
        r = session.get(url, headers=headers, timeout=120)
    except requests.RequestException as e:
        return None, 0, str(e)

    if r.status_code != 200:
        body = (r.text or "")[:500]
        return None, r.status_code, body or None

    try:
        data = r.json()
    except json.JSONDecodeError:
        return None, r.status_code, r.text[:500]

    tid = data.get("task_id")
    if not tid:
        return None, r.status_code, json.dumps(data)[:500]
    return str(tid), r.status_code, None


def _status_histogram(statuses: list[Any]) -> dict[str, int]:
    h: dict[str, int] = {}
    for s in statuses:
        key = str(s or "?")
        h[key] = h.get(key, 0) + 1
    return h


def _vprint(lock: threading.Lock | None, verbose: bool, line: str) -> None:
    if not verbose:
        return
    if lock:
        with lock:
            print(line, flush=True)
    else:
        print(line, flush=True)

def _clip(s: str, width: int) -> str:
    if width <= 0:
        return ""
    if len(s) <= width:
        return s
    if width <= 1:
        return s[:width]
    return s[: width - 1] + "…"


def _fmt_age(seconds: float) -> str:
    if seconds < 0:
        seconds = 0
    if seconds < 60:
        return f"{int(seconds)}s"
    if seconds < 3600:
        return f"{int(seconds // 60)}m{int(seconds % 60):02d}s"
    return f"{int(seconds // 3600)}h{int((seconds % 3600) // 60):02d}m"


class LiveBoard:
    """Minimal terminal UI: redraws a table at a fixed interval without scrolling."""

    def __init__(self, enabled: bool, interval_s: float = 2.0):
        self.enabled = enabled and sys.stdout.isatty()
        self.interval_s = interval_s
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._t0 = time.perf_counter()
        self._deadline_mono: float | None = None
        self._header_lines: list[str] = []
        self._rows: dict[int, dict[str, Any]] = {}
        self._finished: set[int] = set()

    def configure(self, header_lines: list[str], deadline_mono: float | None) -> None:
        with self._lock:
            self._header_lines = header_lines
            self._deadline_mono = deadline_mono

    def set_total_slots(self, n: int) -> None:
        with self._lock:
            for i in range(n):
                self._rows.setdefault(
                    i,
                    {
                        "label": "",
                        "task": "",
                        "state": "INIT",
                        "pct": None,
                        "msg": "",
                        "last_change": time.monotonic(),
                        "done": False,
                    },
                )

    def update(
        self,
        idx: int,
        *,
        label: str | None = None,
        task: str | None = None,
        state: str | None = None,
        pct: int | None = None,
        msg: str | None = None,
        mark_change: bool = False,
        done: bool | None = None,
    ) -> None:
        now = time.monotonic()
        with self._lock:
            row = self._rows.setdefault(
                idx,
                {
                    "label": "",
                    "task": "",
                    "state": "INIT",
                    "pct": None,
                    "msg": "",
                    "last_change": now,
                    "done": False,
                },
            )
            changed = False
            if label is not None:
                changed = changed or (row.get("label") != label)
                row["label"] = label
            if task is not None:
                changed = changed or (row.get("task") != task)
                row["task"] = task
            if state is not None:
                changed = changed or (row.get("state") != state)
                row["state"] = state
            if pct is not None:
                changed = changed or (row.get("pct") != pct)
                row["pct"] = pct
            if msg is not None:
                changed = changed or (row.get("msg") != msg)
                row["msg"] = msg
            if done is not None:
                changed = changed or (row.get("done") != done)
                row["done"] = done
                if done:
                    self._finished.add(idx)
            if mark_change or changed:
                row["last_change"] = now

    def start(self) -> None:
        if not self.enabled or self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, name="liveboard", daemon=True)
        # Hide cursor for nicer UI.
        sys.stdout.write(ANSI_HIDE_CURSOR)
        sys.stdout.flush()
        self._thread.start()

    def stop(self) -> None:
        if not self.enabled:
            return
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1.0)
        # Restore cursor and move to bottom with a newline.
        sys.stdout.write(ANSI_SHOW_CURSOR + "\n")
        sys.stdout.flush()

    def render_once(self) -> None:
        if not self.enabled:
            return
        with self._lock:
            rows = dict(self._rows)
            header = list(self._header_lines)
            finished = len(self._finished)
            total = len(rows) if rows else 0
            deadline = self._deadline_mono

        elapsed = time.perf_counter() - self._t0
        eta_s: str | None = None
        if deadline is not None:
            remaining = deadline - time.monotonic()
            if remaining < 0:
                remaining = 0
            eta_s = _fmt_age(remaining)

        width = shutil.get_terminal_size((120, 30)).columns
        # Column widths (tuned for readability)
        col_idx = 4
        col_state = 12
        col_pct = 5
        col_age = 7
        col_task = 14
        col_label = max(20, int(width * 0.30))
        col_msg = max(20, width - (col_idx + col_state + col_pct + col_age + col_task + col_label + 7))

        lines: list[str] = []
        lines.extend(header)
        top = f"Zeit: {_fmt_age(elapsed)} | Fertig: {finished}/{total}"
        if eta_s is not None:
            top += f" | Timeout in: {eta_s}"
        lines.append(_clip(top, width))
        lines.append(
            _clip(
                f"{'Slot':<{col_idx}}  {'Status':<{col_state}}  {'%':<{col_pct}}  {'Age':<{col_age}}  {'Task':<{col_task}}  {'Projekt':<{col_label}}  {'Info':<{col_msg}}",
                width,
            )
        )
        lines.append(_clip("-" * width, width))

        now = time.monotonic()
        for idx in sorted(rows.keys()):
            r = rows[idx]
            state = str(r.get("state") or "")
            pct = r.get("pct")
            pct_s = f"{int(pct):3d}%" if isinstance(pct, int) else ""
            age = _fmt_age(now - float(r.get("last_change") or now))
            task = _short_id(str(r.get("task") or ""), 12)
            label = str(r.get("label") or "")
            msg = str(r.get("msg") or "")

            line = (
                f"{idx:<{col_idx}}  "
                f"{_clip(state, col_state):<{col_state}}  "
                f"{_clip(pct_s, col_pct):<{col_pct}}  "
                f"{_clip(age, col_age):<{col_age}}  "
                f"{_clip(task, col_task):<{col_task}}  "
                f"{_clip(label, col_label):<{col_label}}  "
                f"{_clip(msg, col_msg):<{col_msg}}"
            )
            lines.append(_clip(line, width))

        out = ANSI_CLEAR + ANSI_HOME + "\n".join(lines)
        sys.stdout.write(out)
        sys.stdout.flush()

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self.render_once()
            except Exception:
                # Never kill the whole test due to UI rendering.
                pass
            self._stop.wait(self.interval_s)


def wait_group_done(
    session: requests.Session,
    base_url: str,
    headers: dict[str, str],
    group_id: str,
    poll_interval: float,
    deadline: float,
    stall_timeout: float,
    log_prefix: str,
    verbose: bool,
    print_lock: threading.Lock | None,
    board: LiveBoard | None,
    slot_idx: int | None,
) -> tuple[bool, str]:
    gurl = f"{base_url}/task/group/{group_id}"
    last_summary: str | None = None
    last_change = time.monotonic()
    last_ok_poll = time.monotonic()
    neterr_streak_started: float | None = None
    while time.monotonic() < deadline:
        try:
            r = session.get(gurl, headers=headers, timeout=120)
        except requests.RequestException as e:
            # Transient network errors happen (deploy/restart). Keep retrying until stall/overall timeout.
            now = time.monotonic()
            if neterr_streak_started is None:
                neterr_streak_started = now
            if board is not None and slot_idx is not None:
                board.update(
                    slot_idx,
                    state="NETERR",
                    msg=f"group poll error ({_fmt_age(now - neterr_streak_started)}): {str(e)[:80]}",
                    mark_change=False,
                )
            # If we cannot reach the API for too long, abort early with a clear reason.
            if (now - (neterr_streak_started or now)) >= min(stall_timeout, 300.0):
                return False, f"group request error for {_fmt_age(now - neterr_streak_started)}: {e}"
            time.sleep(min(5.0, poll_interval))
            continue

        if r.status_code != 200:
            now = time.monotonic()
            if neterr_streak_started is None:
                neterr_streak_started = now
            if board is not None and slot_idx is not None:
                board.update(
                    slot_idx,
                    state="NETERR",
                    msg=f"group HTTP {r.status_code} ({_fmt_age(now - neterr_streak_started)}): {(r.text or '')[:60]}",
                    mark_change=False,
                )
            if (now - (neterr_streak_started or now)) >= min(stall_timeout, 300.0):
                return False, f"group HTTP {r.status_code}: {(r.text or '')[:300]}"
            time.sleep(min(5.0, poll_interval))
            continue

        try:
            payload = r.json()
        except json.JSONDecodeError:
            now = time.monotonic()
            if neterr_streak_started is None:
                neterr_streak_started = now
            if (now - (neterr_streak_started or now)) >= min(stall_timeout, 300.0):
                return False, f"group invalid JSON: {r.text[:200]}"
            time.sleep(min(5.0, poll_interval))
            continue
        last_ok_poll = time.monotonic()
        neterr_streak_started = None

        tasks = payload.get("tasks") or []
        if not tasks:
            time.sleep(poll_interval)
            continue

        total = len(tasks)
        completed = payload.get("completed")
        if completed is None:
            completed = sum(1 for t in tasks if t.get("task_status") == "SUCCESS")
        statuses = [t.get("task_status") for t in tasks]
        pct = int(100 * completed / total) if total else 0
        hist = _status_histogram(statuses)
        hist_s = ", ".join(f"{k}={v}" for k, v in sorted(hist.items()))
        if len(hist_s) > 180:
            hist_s = hist_s[:177] + "…"

        summary_changed = False
        if verbose:
            summary = f"{log_prefix} Celery-Gruppe {_short_id(group_id, 12)}: {completed}/{total} fertig ({pct}%) | {hist_s}"
            if summary != last_summary:
                _vprint(print_lock, True, summary)
                last_summary = summary
                last_change = time.monotonic()
                summary_changed = True

        if board is not None and slot_idx is not None:
            board.update(
                slot_idx,
                state="GROUP",
                pct=pct,
                msg=f"{completed}/{total} | {hist_s}",
                mark_change=summary_changed,
            )

        if any(s == "FAILURE" for s in statuses):
            detail = next(
                (t.get("task_result") for t in tasks if t.get("task_status") == "FAILURE"),
                None,
            )
            return False, f"group child FAILURE: {str(detail)[:400]}"

        if all(s == "SUCCESS" for s in statuses):
            if verbose:
                _vprint(
                    print_lock,
                    True,
                    f"{log_prefix} Gruppe {_short_id(group_id, 12)}: alle {total} Teilaufgaben SUCCESS",
                )
            if board is not None and slot_idx is not None:
                board.update(
                    slot_idx,
                    state="SUCCESS",
                    pct=100,
                    msg=f"group OK ({total})",
                    mark_change=True,
                    done=True,
                )
            return True, f"group SUCCESS ({total} Teilaufgaben)"

        # Abort if nothing changes for too long (helps detect wedged polling / stuck tasks).
        if (time.monotonic() - last_change) >= stall_timeout:
            # Distinguish \"no progress\" vs \"no connectivity\"
            if (time.monotonic() - last_ok_poll) >= min(stall_timeout, 300.0):
                return False, f"group stalled (no successful poll for {int(min(stall_timeout,300.0))}s)"
            return False, f"group stalled (no progress change for {int(stall_timeout)}s)"

        if any(s in NONTERMINAL_TASK or (s and s not in ("SUCCESS", "FAILURE")) for s in statuses):
            time.sleep(poll_interval)
            continue

        return False, f"group unexpected states: {statuses[:10]}"

    return False, "group wait timeout"


def _progress_from_task_payload(data: dict[str, Any]) -> tuple[int | None, str | None]:
    """Celery ``PROGRESS`` stores ``meta`` in ``task_result`` (JSON) with ``progress`` / ``text``."""
    st = data.get("task_status")
    raw = data.get("task_result")
    if st != "PROGRESS":
        return None, None
    meta = _parse_json_maybe(raw)
    if not isinstance(meta, dict):
        return None, None
    prog = meta.get("progress")
    pct: int | None = None
    if isinstance(prog, (int, float)):
        pct = int(prog)
    text = meta.get("text")
    text_s = str(text) if text is not None else None
    return pct, text_s


def fetch_project_prepare_state(
    session: requests.Session,
    base_url: str,
    headers: dict[str, str],
    project_id: str,
) -> tuple[bool | None, str | None]:
    """
    Returns (isozones_running, isozones_taskid) for the project if available.
    If request fails, returns (None, None).
    """
    url = f"{base_url}/project/by-id/{project_id}"
    try:
        r = session.get(url, headers=headers, timeout=30)
    except requests.RequestException:
        return None, None
    if r.status_code != 200:
        return None, None
    try:
        data = r.json()
    except json.JSONDecodeError:
        return None, None
    if not isinstance(data, dict):
        return None, None
    running = data.get("isozones_running")
    taskid = data.get("isozones_taskid")
    running_b: bool | None = None
    if isinstance(running, bool):
        running_b = running
    return running_b, (str(taskid) if taskid is not None else None)


def wait_task_tree_done(
    session: requests.Session,
    base_url: str,
    headers: dict[str, str],
    task_id: str,
    poll_interval: float,
    deadline: float,
    stall_timeout: float,
    log_prefix: str,
    verbose: bool,
    print_lock: threading.Lock | None,
    board: LiveBoard | None,
    slot_idx: int | None,
    endpoint: str | None = None,
    project_id: str | None = None,
) -> tuple[bool, str]:
    turl = f"{base_url}/task/{task_id}"
    last_line: str | None = None
    last_change = time.monotonic()
    last_project_probe = 0.0
    last_ok_poll = time.monotonic()
    neterr_streak_started: float | None = None
    while time.monotonic() < deadline:
        try:
            r = session.get(turl, headers=headers, timeout=120)
        except requests.RequestException as e:
            now = time.monotonic()
            if neterr_streak_started is None:
                neterr_streak_started = now
            if board is not None and slot_idx is not None:
                board.update(
                    slot_idx,
                    state="NETERR",
                    msg=f"task poll error ({_fmt_age(now - neterr_streak_started)}): {str(e)[:80]}",
                    mark_change=False,
                )
            if (now - (neterr_streak_started or now)) >= min(stall_timeout, 300.0):
                return False, f"task request error for {_fmt_age(now - neterr_streak_started)}: {e}"
            time.sleep(min(5.0, poll_interval))
            continue

        if r.status_code != 200:
            now = time.monotonic()
            if neterr_streak_started is None:
                neterr_streak_started = now
            if board is not None and slot_idx is not None:
                board.update(
                    slot_idx,
                    state="NETERR",
                    msg=f"task HTTP {r.status_code} ({_fmt_age(now - neterr_streak_started)}): {(r.text or '')[:60]}",
                    mark_change=False,
                )
            if (now - (neterr_streak_started or now)) >= min(stall_timeout, 300.0):
                return False, f"task HTTP {r.status_code}: {(r.text or '')[:300]}"
            time.sleep(min(5.0, poll_interval))
            continue

        try:
            data = r.json()
        except json.JSONDecodeError:
            now = time.monotonic()
            if neterr_streak_started is None:
                neterr_streak_started = now
            if (now - (neterr_streak_started or now)) >= min(stall_timeout, 300.0):
                return False, f"task invalid JSON: {r.text[:200]}"
            time.sleep(min(5.0, poll_interval))
            continue
        last_ok_poll = time.monotonic()
        neterr_streak_started = None

        st = data.get("task_status")
        if verbose:
            pct, msg = _progress_from_task_payload(data)
            if st in NONTERMINAL_TASK or (st and st not in TERMINAL_CHAIN):
                parts = [f"{log_prefix} Task {_short_id(task_id, 12)}: Status={st}"]
                if pct is not None:
                    parts.append(f"{pct}%")
                if msg:
                    parts.append(f"— {msg[:120]}")
                line = " ".join(parts)
                if line != last_line:
                    _vprint(print_lock, True, line)
                    last_line = line
                    last_change = time.monotonic()
            elif st in TERMINAL_CHAIN and st != "SUCCESS":
                line = f"{log_prefix} Task {_short_id(task_id, 12)}: Status={st}"
                if line != last_line:
                    _vprint(print_lock, True, line)
                    last_line = line
                    last_change = time.monotonic()

        if board is not None and slot_idx is not None:
            pct, msg = _progress_from_task_payload(data)
            # mark_change when state/progress text changes
            state_s = str(st or "")
            ui_msg = (msg or "").strip()
            board.update(
                slot_idx,
                state=state_s,
                pct=pct,
                msg=ui_msg,
                mark_change=False,
            )

        if st in NONTERMINAL_TASK or (st and st not in TERMINAL_CHAIN):
            # For prepare endpoint: sometimes Celery status can stay on PROGRESS even though the
            # task already persisted results and flipped the project flag in DB. Verify via API.
            if endpoint == "prepare" and project_id:
                now = time.monotonic()
                # Probe DB at least every 15s; faster when we haven't seen changes for a while.
                probe_every = 15.0
                if (now - last_change) >= 120.0:
                    probe_every = 8.0
                if now - last_project_probe >= probe_every:
                    last_project_probe = now
                    running, taskid = fetch_project_prepare_state(session, base_url, headers, project_id)
                    if running is False and (taskid is None or taskid == "" or taskid == task_id):
                        if board is not None and slot_idx is not None:
                            board.update(slot_idx, state="SUCCESS", pct=100, msg="OK (verified via project)", done=True, mark_change=True)
                        return True, "task SUCCESS (verified via project state)"
                    # Show DB-side hint in the UI to distinguish \"still running\" vs \"status stuck\".
                    if board is not None and slot_idx is not None and running is not None:
                        db_hint = f"db running={running}"
                        if taskid:
                            db_hint += f", db task={_short_id(taskid, 12)}"
                        board.update(slot_idx, msg=db_hint, mark_change=False)

            # Abort if status/progress does not change for too long.
            if (time.monotonic() - last_change) >= stall_timeout:
                if board is not None and slot_idx is not None:
                    board.update(slot_idx, state="STALL", msg="no change", done=True, mark_change=True)
                if (time.monotonic() - last_ok_poll) >= min(stall_timeout, 300.0):
                    return False, f"task stalled (no successful poll for {int(min(stall_timeout,300.0))}s; last={st})"
                return False, f"task stalled (no status/progress change for {int(stall_timeout)}s; last={st})"
            time.sleep(poll_interval)
            continue

        if st == "FAILURE":
            if board is not None and slot_idx is not None:
                board.update(slot_idx, state="FAILURE", msg="task failed", done=True, mark_change=True)
            return False, f"task FAILURE: {str(data.get('task_result'))[:400]}"

        if st == "SUCCESS":
            parsed = _parse_json_maybe(data.get("task_result"))
            if isinstance(parsed, dict) and parsed.get("group_id"):
                gid = str(parsed["group_id"])
                if verbose:
                    _vprint(
                        print_lock,
                        True,
                        f"{log_prefix} Chain fertig → warte Celery-Gruppe {_short_id(gid, 12)} …",
                    )
                if board is not None and slot_idx is not None:
                    board.update(slot_idx, state="GROUP", pct=None, msg=f"group { _short_id(gid, 12)}", mark_change=True)
                return wait_group_done(
                    session,
                    base_url,
                    headers,
                    gid,
                    poll_interval,
                    deadline,
                    stall_timeout,
                    log_prefix,
                    verbose,
                    print_lock,
                    board,
                    slot_idx,
                )
            if verbose:
                _vprint(
                    print_lock,
                    True,
                    f"{log_prefix} Task {_short_id(task_id, 12)}: fertig (SUCCESS)",
                )
            if board is not None and slot_idx is not None:
                board.update(slot_idx, state="SUCCESS", pct=100, msg="OK", done=True, mark_change=True)
            return True, "task SUCCESS"

        if st == "REVOKED":
            if board is not None and slot_idx is not None:
                board.update(slot_idx, state="REVOKED", msg="revoked", done=True, mark_change=True)
            return False, "task REVOKED"

        return False, f"unknown task_status: {st}"

    return False, "task wait timeout"


def run_load_test(
    base_url: str,
    token: str,
    projects: list[ProjectRef],
    endpoint: str,
    concurrency: int,
    poll_interval: float,
    timeout_sec: float,
    stall_timeout: float,
    heartbeat_s: float,
    tui: bool,
    verbose: bool,
) -> int:
    base_url = _normalize_base(base_url)
    headers = _auth_headers(token)
    print_lock = threading.Lock()
    board = LiveBoard(enabled=(tui and verbose), interval_s=heartbeat_s)

    print(f"API base:     {base_url}")
    print(f"Endpoint:     {endpoint} (concurrency={concurrency})")
    print(f"Verbose:      {verbose} (Fortschritt: Celery-Status + ggf. PROGRESS-Meta aus /task/)")
    print(f"Stall timeout: {stall_timeout}s (Abbruch wenn keine Änderung)")
    print(f"TUI:          {board.enabled} (Heartbeat {heartbeat_s}s)")
    print(f"Projects:     {len(projects)} — Round-robin pro Slot")
    for j, (pid, title) in enumerate(projects[:20]):
        print(f"    [{j}] {_project_label(pid, title)}")
    if len(projects) > 20:
        print(f"    … ({len(projects) - 20} weitere)")
    print(f"Poll interval: {poll_interval}s, max wait: {timeout_sec}s gesamt")
    print()

    session = requests.Session()
    task_ids: list[tuple[int, str | None, str | None, str, str]] = []
    board.set_total_slots(concurrency)

    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        futures = {}
        for i in range(concurrency):
            pid, title = projects[i % len(projects)]
            lbl = _project_label(pid, title)
            board.update(i, label=lbl, state="ENQUEUE", msg="starting…", mark_change=True)
            fut = ex.submit(
                start_discharge_task,
                session,
                base_url,
                headers,
                pid,
                endpoint,
            )
            futures[fut] = (i, pid, title)
        for fut in as_completed(futures):
            idx, pid, title = futures[fut]
            tid, _http, err = fut.result()
            task_ids.append((idx, tid, err, pid, title))
            if tid and verbose:
                lbl = _project_label(pid, title)
                if not board.enabled:
                    print(f"  [#{idx}] gestartet: {lbl} → task_id={tid}", flush=True)
            if tid:
                board.update(idx, task=tid, state="PENDING", msg="", mark_change=True)
            else:
                board.update(idx, state="ENQUEUE_FAIL", msg=str(err or "")[:120], mark_change=True, done=True)

    t_after_start = time.perf_counter()
    start_elapsed = t_after_start - t0

    started = [(i, tid, pid, title) for i, tid, err, pid, title in sorted(task_ids) if tid]
    failed_start = [(i, err, pid, title) for i, tid, err, pid, title in sorted(task_ids) if not tid]

    print()
    print(f"Phase 1 — enqueue: {len(started)}/{concurrency} task_id in {start_elapsed:.2f}s")
    for i, err, pid, title in failed_start:
        print(f"  [#{i}] {_project_label(pid, title)} — {err}")
    print()

    if not started:
        print("Keine Tasks zum Warten; Ende.")
        return 1

    deadline_global = time.monotonic() + timeout_sec
    board.configure(
        header_lines=[
            f"AUGUR Load Test | endpoint={endpoint} | concurrency={concurrency}",
            f"base={base_url}",
        ],
        deadline_mono=deadline_global,
    )
    board.start()
    results: list[tuple[int, bool, str, str, str]] = []

    def wait_one(item: tuple[int, str, str, str]) -> tuple[int, bool, str, str, str]:
        idx, tid, pid, title = item
        log_prefix = f"[#{idx}] {_project_label(pid, title)}"
        ok, msg = wait_task_tree_done(
            session,
            base_url,
            headers,
            tid,
            poll_interval,
            deadline_global,
            stall_timeout,
            log_prefix,
            verbose and (not board.enabled),  # when TUI is enabled, avoid per-line spam
            print_lock,
            board if board.enabled else None,
            idx,
            endpoint=endpoint,
            project_id=pid,
        )
        return idx, ok, msg, pid, title

    if verbose:
        if not board.enabled:
            print("Phase 2 — warte auf Celery (Zeilen nur bei Änderung von Status/Fortschritt):\n")

    t_wait0 = time.perf_counter()
    try:
        with ThreadPoolExecutor(max_workers=min(concurrency, len(started))) as ex:
            futs = [ex.submit(wait_one, pair) for pair in started]
            for fut in as_completed(futs):
                results.append(fut.result())
    except KeyboardInterrupt:
        # Ensure we still print a summary instead of hanging in executor shutdown.
        print("\nKeyboardInterrupt: breche Warten ab und gebe Zwischenstand aus …", flush=True)
    finally:
        board.stop()

    t_end = time.perf_counter()
    wait_elapsed = t_end - t_wait0
    total_elapsed = t_end - t0

    oks = sum(1 for _, ok, _, _, _ in results if ok)
    print(f"\nPhase 2 — fertig: {oks}/{len(results)} OK in {wait_elapsed:.2f}s")
    for idx, ok, msg, pid, title in sorted(results):
        status = "OK" if ok else "FAIL"
        print(f"  [#{idx}] {_project_label(pid, title)} — {status}: {msg}")
    print()
    print("Summary")
    print(f"  Wall clock (enqueue + wait): {total_elapsed:.2f}s")
    print(f"  Enqueue phase:                {start_elapsed:.2f}s")
    print(f"  Wait phase:                   {wait_elapsed:.2f}s")
    print(f"  Started / requested:          {len(started)}/{concurrency}")
    print(f"  Completed successfully:       {oks}/{len(results)}")

    if failed_start or oks < len(results):
        return 1
    return 0


def _single_project_ref(project_id: str) -> ProjectRef:
    return (project_id.strip(), "")


def enrich_project_title(
    session: requests.Session,
    base_url: str,
    headers: dict[str, str],
    project_id: str,
) -> str:
    """Best-effort ``title`` via ``GET /project/by-id/{id}`` (nur bei ``--project-id``)."""
    url = f"{base_url}/project/by-id/{project_id}"
    try:
        r = session.get(url, headers=headers, timeout=30)
    except requests.RequestException:
        return ""
    if r.status_code != 200:
        return ""
    try:
        d = r.json()
    except json.JSONDecodeError:
        return ""
    if isinstance(d, dict) and d.get("title") is not None:
        return str(d["title"] or "")
    return ""


def main() -> int:
    p = argparse.ArgumentParser(description="Concurrent discharge API load test.")
    p.add_argument(
        "--base-url",
        default=os.environ.get("HAKESCH_API_URL", ""),
        help="API root URL (or HAKESCH_API_URL)",
    )
    p.add_argument(
        "--token",
        default=os.environ.get("HAKESCH_BEARER_TOKEN", ""),
        help="Bearer token (or HAKESCH_BEARER_TOKEN)",
    )
    p.add_argument(
        "--project-id",
        default=os.environ.get("HAKESCH_PROJECT_ID", ""),
        help="Optional: single project UUID; if omitted, loads all user projects from GET /project/",
    )
    p.add_argument(
        "--endpoint",
        choices=("prepare", "calculate"),
        default="prepare",
        help="discharge route to hit",
    )
    p.add_argument("--concurrency", type=int, default=30, help="parallel requests (default 30)")
    p.add_argument(
        "--poll-interval",
        type=float,
        default=2.0,
        help="seconds between status polls (default 2)",
    )
    p.add_argument(
        "--timeout",
        type=float,
        default=7200.0,
        help="max seconds from start until all tasks must finish (default 7200)",
    )
    p.add_argument(
        "--stall-timeout",
        type=float,
        default=600.0,
        help="Abbruch, wenn eine Task/Gruppe so lange keine Änderung zeigt (default 600s)",
    )
    p.add_argument(
        "--heartbeat",
        type=float,
        default=2.0,
        help="Heartbeat-Intervall für die Terminal-Übersicht (default 2s)",
    )
    p.add_argument(
        "--no-tui",
        action="store_true",
        help="deaktiviert die Terminal-Übersicht (nur klassische Log-Zeilen)",
    )
    p.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="weniger Ausgabe (kein Fortschritt pro Poll, keine sofortige Zeile pro Enqueue)",
    )
    args = p.parse_args()

    if not args.base_url or not args.token:
        print(
            "Missing --base-url or --token "
            "(or HAKESCH_API_URL / HAKESCH_BEARER_TOKEN).",
            file=sys.stderr,
        )
        return 2

    base_url = _normalize_base(args.base_url)
    headers = _auth_headers(args.token)
    session = requests.Session()

    if args.project_id.strip():
        pid = args.project_id.strip()
        title = enrich_project_title(session, base_url, headers, pid)
        projects = [(pid, title)]
    else:
        projects, err = fetch_user_projects(session, base_url, headers)
        if err:
            print(f"Could not load user projects: {err}", file=sys.stderr)
            return 2
        assert projects is not None

    verbose = not args.quiet
    return run_load_test(
        args.base_url,
        args.token,
        projects,
        args.endpoint,
        args.concurrency,
        args.poll_interval,
        args.timeout,
        args.stall_timeout,
        args.heartbeat,
        tui=(not args.no_tui),
        verbose=verbose,
    )


if __name__ == "__main__":
    raise SystemExit(main())
