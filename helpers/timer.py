"""Edit stopwatch shown in the preview header — how long the edit takes.

Stored in <edit>/timer.json as a list of RUNS: the clock only counts while the
system is working. It pauses while the edit waits on the user (cut approval,
style pick) and stops when the Fase-2 `final.mp4` is ready to save.

    python3 helpers/timer.py <edit> start    # "Processar vídeos" (server does it)
    python3 helpers/timer.py <edit> pause    # handing over to the user
    python3 helpers/timer.py <edit> resume   # the user answered / saved
    python3 helpers/timer.py <edit> stop     # final.mp4 delivered
    python3 helpers/timer.py <edit> show

Stdlib-only: the preview server imports it too.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path


def path(edit: Path) -> Path:
    return Path(edit) / "timer.json"


def load(edit: Path) -> dict:
    try:
        return json.loads(path(edit).read_text())
    except (OSError, json.JSONDecodeError):
        return {"runs": [], "state": "idle"}


def _save(edit: Path, t: dict) -> dict:
    p = path(edit)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(t, indent=2))
    tmp.replace(p)
    return t


def elapsed(t: dict, now: float | None = None) -> float:
    now = now or time.time()
    return sum((r["end"] or now) - r["start"] for r in t.get("runs", []))


def start(edit: Path) -> dict:
    """A fresh measurement: a new "Processar vídeos" is a new edit."""
    return _save(edit, {"runs": [{"start": time.time(), "end": None}], "state": "running",
                        "startedAt": time.strftime("%Y-%m-%d %H:%M:%S")})


def pause(edit: Path) -> dict:
    t = load(edit)
    if t.get("state") == "running" and t["runs"] and t["runs"][-1]["end"] is None:
        t["runs"][-1]["end"] = time.time()
        t["state"] = "paused"
    return _save(edit, t)


def resume(edit: Path) -> dict:
    t = load(edit)
    if t.get("state") in ("paused", "done") or not t.get("runs"):
        t.setdefault("runs", []).append({"start": time.time(), "end": None})
        t["state"] = "running"
    return _save(edit, t)


def stop(edit: Path) -> dict:
    t = load(edit)
    if t.get("runs") and t["runs"][-1]["end"] is None:
        t["runs"][-1]["end"] = time.time()
    t["state"] = "done"
    t["doneAt"] = time.strftime("%Y-%m-%d %H:%M:%S")
    t["seconds"] = round(elapsed(t), 1)
    return _save(edit, t)


def fmt(sec: float) -> str:
    sec = int(sec)
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[2] not in ("start", "pause", "resume", "stop", "show"):
        sys.exit(__doc__)
    edit, cmd = Path(sys.argv[1]).expanduser(), sys.argv[2]
    t = {"start": start, "pause": pause, "resume": resume, "stop": stop, "show": load}[cmd](edit)
    print(f"cronômetro: {t.get('state')} · {fmt(elapsed(t))}")
