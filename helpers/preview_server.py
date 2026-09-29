"""Edvid preview server — serves the standard editing interface + session media.

The interface app (assets/preview/) is IMMUTABLE and lives in the skill repo;
per-session it is fed by data only:
  - <edit>/state.json          written by the skill (phase, files, message)
  - <edit>/edl.json            the cut (segments shown/trimmed on the timeline)
  - <edit>/cut.mp4             current render (played + scrubbed)
  - <edit>/preview_edits.json  WRITTEN BY THE UI when the user saves timeline
                               adjustments — the skill reads, validates, applies
                               and re-renders. The UI never touches edl.json.
  - <edit>/preview_style.json  WRITTEN BY THE UI at the Fase 1 → Fase 2 gate:
                               editing style, caption style, edit elements.
  - <edit>/post.json           written by the skill (Fase 3): publication caption
                               per network — the Postagem tab shows it.
  - <edit>/preview_post.json   WRITTEN BY THE UI when the user saves caption edits.

Routes:
  /                     the app (from <skill>/assets/preview/)
  /assets/<file>        app files (css/js/logo)
  /media/<path>         files under --root (the edit dir) — Range supported
  /gen/waveform.json    min/max audio peaks of cut.mp4 (auto-(re)generated)
  /gen/thumbs/<n>.jpg   timeline filmstrip thumbs (auto-generated, 1 per 2s)
  /api/state    GET     state.json + mtimes (UI polls this to hot-reload)
  /api/save     POST    body → <edit>/preview_edits.json (atomic), or
                        <edit>/preview_style.json when body.type=="style-setup",
                        <edit>/preview_post.json when body.type=="post-edits"
  /api/export   POST    copy the final render next to the raw footage — opens the
                        OS save dialog in that folder ("Salvar vídeo", Fase 2)

Usage:
    uv run helpers/preview_server.py --root <videos_dir>/edit [--port 4820]
"""
from __future__ import annotations

import argparse
import os
import array
import json
import re
import shutil
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote

sys.path.insert(0, str(Path(__file__).resolve().parent))
import brand_library  # noqa: E402  (stdlib-only sibling helper)
import timer as edit_timer  # noqa: E402  (stdlib-only sibling helper)

APP_DIR = Path(__file__).resolve().parent.parent / "assets" / "preview"
PEAKS_PER_SEC = 40
THUMB_EVERY_S = 2.0
THUMB_HEIGHT = 90

MIME = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".webp": "image/webp",
    ".jpeg": "image/jpeg",
    ".svg": "image/svg+xml",
    ".mp4": "video/mp4",
    ".m4v": "video/mp4",
    ".webm": "video/webm",
    ".mov": "video/quicktime",
    ".mp3": "audio/mpeg",
    ".srt": "text/plain; charset=utf-8",
}

_thumb_lock = threading.Lock()
_thumb_state: dict[str, float] = {}  # video path -> mtime generated


def probe_duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True,
    ).stdout.strip()
    try:
        return float(out)
    except ValueError:
        return 0.0


def gen_waveform(video: Path, out_json: Path) -> None:
    """Decode audio to mono s16 and store min/max peak pairs per bucket (0-100)."""
    rate = 8000
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(video), "-vn",
         "-ac", "1", "-ar", str(rate), "-f", "s16le", "-"],
        capture_output=True,
    ).stdout
    samples = array.array("h")
    samples.frombytes(raw[: len(raw) // 2 * 2])
    per_bucket = max(1, rate // PEAKS_PER_SEC)
    mins: list[int] = []
    maxs: list[int] = []
    for i in range(0, len(samples), per_bucket):
        chunk = samples[i:i + per_bucket]
        if not chunk:
            continue
        mins.append(round(min(chunk) / 32768 * 100))
        maxs.append(round(max(chunk) / 32768 * 100))
    out_json.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_json.with_suffix(".tmp")
    tmp.write_text(json.dumps({
        "peaksPerSec": PEAKS_PER_SEC,
        "duration": len(samples) / rate,
        "min": mins,
        "max": maxs,
        "srcMtime": video.stat().st_mtime,
    }))
    tmp.replace(out_json)


def gen_thumbs(video: Path, out_dir: Path) -> None:
    """Filmstrip thumbs: one small jpg every THUMB_EVERY_S seconds."""
    if out_dir.exists():
        shutil.rmtree(out_dir, ignore_errors=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(video),
         "-vf", f"fps=1/{THUMB_EVERY_S},scale=-2:{THUMB_HEIGHT}",
         "-q:v", "6", str(out_dir / "%04d.jpg")],
        check=False, capture_output=True,
    )
    (out_dir / "meta.json").write_text(json.dumps({
        "everySec": THUMB_EVERY_S,
        "count": len(list(out_dir.glob("*.jpg"))),
        "srcMtime": video.stat().st_mtime,
    }))


def _music_engine_installed() -> bool:
    d = Path(os.environ.get("FMCUT_MUSIC_DIR", Path.home() / ".cache" / "fm-cut" / "ACE-Step-1.5"))
    return (d / "pyproject.toml").exists() and (d / ".venv").exists()


class Handler(BaseHTTPRequestHandler):
    root: Path  # set on the class by main()
    protocol_version = "HTTP/1.1"

    # ---- helpers ----
    def _hdr(self, code: int, ctype: str, length: int | None = None,
             extra: dict[str, str] | None = None) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Accept-Ranges", "bytes")
        if length is not None:
            self.send_header("Content-Length", str(length))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()

    def _json(self, obj: object, code: int = 200) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode()
        self._hdr(code, "application/json; charset=utf-8", len(body))
        self.wfile.write(body)

    def _send_file(self, path: Path) -> None:
        """Static file with HTTP Range support (video scrubbing needs it)."""
        if not path.is_file():
            self._json({"error": f"not found: {path.name}"}, 404)
            return
        size = path.stat().st_size
        ctype = MIME.get(path.suffix.lower(), "application/octet-stream")
        rng = self.headers.get("Range")
        start, end = 0, size - 1
        code = 200
        if rng:
            m = re.match(r"bytes=(\d*)-(\d*)", rng)
            if m:
                if m.group(1):
                    start = int(m.group(1))
                    if m.group(2):
                        end = min(int(m.group(2)), size - 1)
                elif m.group(2):  # suffix range: last N bytes
                    start = max(0, size - int(m.group(2)))
                code = 206
        length = end - start + 1
        extra = {"Content-Range": f"bytes {start}-{end}/{size}"} if code == 206 else None
        self._hdr(code, ctype, length, extra)
        with open(path, "rb") as f:
            f.seek(start)
            remaining = length
            while remaining > 0:
                chunk = f.read(min(1 << 16, remaining))
                if not chunk:
                    break
                try:
                    self.wfile.write(chunk)
                except (BrokenPipeError, ConnectionResetError):
                    return
                remaining -= len(chunk)

    def _safe(self, base: Path, rel: str) -> Path | None:
        p = (base / rel.lstrip("/")).resolve()
        return p if str(p).startswith(str(base.resolve())) else None

    def _current_video(self) -> Path | None:
        state_p = self.root / "state.json"
        rel = "cut.mp4"
        if state_p.exists():
            try:
                rel = json.loads(state_p.read_text()).get("video") or rel
            except json.JSONDecodeError:
                pass
        p = self._safe(self.root, rel)
        return p if p and p.exists() else None

    # ---- routes ----
    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html"):
            self._send_file(APP_DIR / "index.html")
        elif path.startswith("/assets/"):
            p = self._safe(APP_DIR, path[len("/assets/"):])
            self._send_file(p) if p else self._json({"error": "bad path"}, 400)
        elif path.startswith("/media/"):
            p = self._safe(self.root, path[len("/media/"):])
            self._send_file(p) if p else self._json({"error": "bad path"}, 400)
        elif path == "/gen/waveform.json":
            self._waveform()
        elif path.startswith("/gen/thumbs/"):
            self._thumbs(path[len("/gen/thumbs/"):])
        elif path == "/api/state":
            self._state()
        elif path == "/api/media":
            self._media_list()
        elif path.startswith("/raw/"):
            p = self._safe(self._raw_dir(), unquote(path[len("/raw/"):]))
            self._send_file(p) if p else self._json({"error": "bad path"}, 400)
        elif path.startswith("/library/"):
            p = self._safe(brand_library.LIB, unquote(path[len("/library/"):]))
            self._send_file(p) if p else self._json({"error": "bad path"}, 400)
        else:
            self._json({"error": "unknown route"}, 404)

    def do_POST(self) -> None:  # noqa: N802
        route = self.path.split("?", 1)[0]
        if route == "/api/export":
            self._export()
            return
        if route == "/api/upload":
            self._upload()
            return
        if route == "/api/library/delete":
            self._library_delete()
            return
        if route == "/api/project":
            self._project_save()
            return
        if route == "/api/media/remove":
            self._media_remove()
            return
        if route == "/api/process":
            self._process()
            return
        if self.path.split("?", 1)[0] != "/api/save":
            self._json({"error": "unknown route"}, 404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, json.JSONDecodeError):
            self._json({"error": "invalid JSON"}, 400)
            return
        body["savedAt"] = time.strftime("%Y-%m-%d %H:%M:%S")
        # The style pick goes to its own file. It is a one-time setup decision,
        # not a correction, and sharing preview_edits.json would make one save
        # clobber the other (they are written at different moments, by different
        # screens, and the skill consumes+deletes them independently).
        name = {
            "style-setup": "preview_style.json",
            "post-edits": "preview_post.json",
        }.get(body.get("type"), "preview_edits.json")
        out = self.root / name
        # a style pick or saved adjustments put the system back to work
        if name in ("preview_style.json", "preview_edits.json"):
            edit_timer.resume(self.root)
        tmp = out.with_suffix(".tmp")
        tmp.write_text(json.dumps(body, ensure_ascii=False, indent=2))
        tmp.replace(out)
        self._json({"ok": True, "file": str(out)})

    # ---- media panel (CapCut-style bin) ----
    # Three shelves: the raw footage folder, this edit's own images/clips
    # (<edit>/media/), and the brand-logo library shared by every edit.
    VIDEO_EXT = {".mp4", ".mov", ".m4v", ".mkv", ".webm"}

    # <edit>/project_setup.json — the user's project choices from Fase 1:
    # {"aspect": "9:16", "order": ["take2.mov", "take1.mov"]}. Persistent (it is
    # the brief for the cut), unlike the preview_*.json events.
    def _setup(self) -> dict:
        try:
            return json.loads((self.root / "project_setup.json").read_text())
        except (OSError, json.JSONDecodeError):
            return {}

    def _write_json(self, name: str, obj: dict) -> None:
        p = self.root / name
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2))
        tmp.replace(p)

    def _read_body(self) -> dict | None:
        try:
            return json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))) or b"{}")
        except (ValueError, json.JSONDecodeError):
            self._json({"error": "invalid JSON"}, 400)
            return None

    def _project_save(self) -> None:
        body = self._read_body()
        if body is None:
            return
        setup = self._setup()
        if body.get("aspect") in (None, "9:16", "16:9", "1:1", "4:5", "source"):
            if "aspect" in body:
                setup["aspect"] = body["aspect"]
        if isinstance(body.get("order"), list):
            setup["order"] = [Path(str(n)).name for n in body["order"]]
        self._write_json("project_setup.json", setup)
        self._json({"ok": True, "setup": setup})

    def _raw_videos(self, raw: Path, setup: dict) -> list[Path]:
        """Raw footage in the project folder. Excludes renders the user SAVED there
        with "Salvar vídeo" (setup["exports"]) — a finished edit sitting next to
        the footage is not footage, and listing it invited re-editing the output."""
        if not raw.is_dir():
            return []
        skip = set(setup.get("exports", []))
        return [p for p in raw.iterdir()
                if p.is_file() and not p.name.startswith(".")
                and p.suffix.lower() in self.VIDEO_EXT and p.name not in skip]

    def _media_remove(self) -> None:
        """Remove a file from the project. It goes to the system TRASH (macOS
        Finder), never a hard delete — raw footage is irreplaceable. Elsewhere it
        moves into a hidden .lixeira-fm-cut/ next to it."""
        body = self._read_body()
        if body is None:
            return
        scope = body.get("scope")
        base = self._raw_dir() if scope == "source" else self.root / "media" if scope == "project" else None
        p = self._safe(base, Path(str(body.get("name", ""))).name) if base else None
        if not p or not p.is_file():
            self._json({"error": "arquivo não encontrado"}, 404)
            return
        try:
            if sys.platform == "darwin":
                r = subprocess.run(["osascript", "-e",
                                    f'tell application "Finder" to delete (POSIX file "{p}")'],
                                   capture_output=True, text=True)
                if r.returncode:
                    raise OSError(r.stderr.strip() or "Finder recusou")
                where = "Lixeira"
            else:
                bin_ = p.parent / ".lixeira-fm-cut"
                bin_.mkdir(exist_ok=True)
                shutil.move(str(p), str(bin_ / p.name))
                where = str(bin_)
        except OSError as e:
            self._json({"error": f"não consegui remover: {e}"}, 500)
            return
        if scope == "source":
            setup = self._setup()
            setup["order"] = [n for n in setup.get("order", []) if n != p.name]
            self._write_json("project_setup.json", setup)
        self._json({"ok": True, "movedTo": where})

    def _process(self) -> None:
        """"Processar vídeos": hand the ordered footage + format to the agent."""
        body = self._read_body()
        if body is None:
            return
        setup = self._setup()
        raw = self._raw_dir()
        vids = {p.name for p in self._raw_videos(raw, setup)}
        order = [n for n in setup.get("order", []) if n in vids]
        files = order + sorted(vids - set(order))
        if not files:
            self._json({"error": "importe pelo menos um vídeo bruto antes de processar"}, 400)
            return
        edit_timer.start(self.root)  # the stopwatch starts with the work
        self._write_json("preview_process.json", {
            "type": "process", "aspect": setup.get("aspect", "source"),
            "rawDir": str(raw), "files": files, "note": str(body.get("note", "")).strip(),
            "savedAt": time.strftime("%Y-%m-%d %H:%M:%S")})
        self._json({"ok": True, "files": files})

    def _media_list(self) -> None:
        raw = self._raw_dir()
        setup = self._setup()
        rank = {n: i for i, n in enumerate(setup.get("order", []))}
        vids = self._raw_videos(raw, setup)
        vids.sort(key=lambda p: (rank.get(p.name, len(rank)), p.name))
        sources = [{"name": p.name, "url": f"/raw/{quote(p.name)}", "size": p.stat().st_size}
                   for p in vids]
        md = self.root / "media"
        project = [{"name": p.name, "url": f"/media/media/{quote(p.name)}", "size": p.stat().st_size,
                    "kind": "video" if p.suffix.lower() in self.VIDEO_EXT else "image"}
                   for p in sorted(md.iterdir())
                   if p.is_file() and not p.name.startswith(".")] if md.is_dir() else []
        library = [{"slug": s, "name": e["name"], "aliases": e.get("aliases", []),
                    "source": e.get("source", ""),
                    "url": f"/library/logos/{quote(e['file'])}"}
                   for s, e in sorted(brand_library.load().items())
                   if (brand_library.LOGOS / e["file"]).exists()]
        self._json({"rawDir": str(raw), "sources": sources, "project": project, "library": library,
                    "setup": setup})

    def _upload(self) -> None:
        """Raw body upload, streamed to disk. ?scope=source|project|library
        &filename=…  (+ &name=…&aliases=… for library)."""
        q = {k: v[0] for k, v in parse_qs(self.path.split("?", 1)[1] if "?" in self.path else "").items()}
        scope = q.get("scope", "project")
        fname = re.sub(r"[^\w.\- ]", "_", Path(q.get("filename", "")).name, flags=re.U).strip() or "arquivo"
        ext = Path(fname).suffix.lower()
        length = int(self.headers.get("Content-Length", "0"))
        if scope == "library":
            if ext not in brand_library.IMAGE_EXT:
                self._drain(length)
                self._json({"error": "logo precisa ser PNG, SVG, WEBP ou JPG"}, 400)
                return
            name = (q.get("name") or Path(fname).stem).strip()
            data = self.rfile.read(length)
            e = brand_library.add(Path(fname), name, (q.get("aliases") or "").split(","),
                                  source="upload", data=data)
            self._media_event({"scope": "library", "name": e["name"], "file": e["file"],
                               "aliases": e["aliases"]})
            self._json({"ok": True, "entry": e})
            return
        if scope == "source":
            if ext not in self.VIDEO_EXT:
                self._drain(length)
                self._json({"error": "vídeo bruto precisa ser MP4, MOV, M4V, MKV ou WEBM"}, 400)
                return
            dest_dir = self._raw_dir()
        else:
            dest_dir = self.root / "media"
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / fname
        n = 1
        while dest.exists():  # never overwrite footage or a previous upload
            dest = dest_dir / f"{Path(fname).stem} ({n}){ext}"
            n += 1
        tmp = dest.with_name(dest.name + ".part")
        with open(tmp, "wb") as f:
            remaining = length
            while remaining > 0:
                chunk = self.rfile.read(min(1 << 20, remaining))
                if not chunk:
                    break
                f.write(chunk)
                remaining -= len(chunk)
        if remaining:
            tmp.unlink(missing_ok=True)
            self._json({"error": "upload interrompido"}, 400)
            return
        tmp.replace(dest)
        self._media_event({"scope": scope, "file": str(dest)})
        self._json({"ok": True, "path": str(dest)})

    def _library_delete(self) -> None:
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))) or b"{}")
        except (ValueError, json.JSONDecodeError):
            self._json({"error": "invalid JSON"}, 400)
            return
        ok = brand_library.remove(str(body.get("slug", "")))
        self._json({"ok": ok} if ok else {"error": "logo não encontrada"}, 200 if ok else 404)

    def _drain(self, length: int) -> None:
        while length > 0:
            chunk = self.rfile.read(min(1 << 20, length))
            if not chunk:
                break
            length -= len(chunk)

    def _media_event(self, ev: dict) -> None:
        """Append to <edit>/preview_media.json so watch_edits.py tells the agent."""
        p = self.root / "preview_media.json"
        try:
            items = json.loads(p.read_text()).get("items", []) if p.exists() else []
        except (OSError, json.JSONDecodeError):
            items = []
        items.append({**ev, "at": time.strftime("%H:%M:%S")})
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps({"type": "media-added", "items": items}, ensure_ascii=False, indent=2))
        tmp.replace(p)

    # ---- export: "Salvar vídeo" on the Fase-2 tab ----
    def _export(self) -> None:
        """Copy the delivered render next to the raw footage (or wherever the user
        picks). Opens the OS's own save dialog, already in the raw footage folder,
        so the finished video lands where the project lives instead of in edit/."""
        try:
            state = json.loads((self.root / "state.json").read_text())
        except (OSError, json.JSONDecodeError):
            state = {}
        src = self._safe(self.root, state.get("finalVideo") or "final.mp4")
        if not src or not src.exists():
            self._json({"error": "ainda não há vídeo final renderizado"}, 404)
            return
        dest_dir = self._raw_dir()
        stem = re.sub(r"[^\w\s.-]", "", str(state.get("project") or "video"), flags=re.U).strip() or "video"
        name = f"{time.strftime('%Y-%m-%d')} - {stem} - FINAL.mp4"
        dest = self._save_dialog(dest_dir, name)
        if dest is None:
            self._json({"cancelled": True})
            return
        if dest.suffix.lower() != ".mp4":
            dest = dest.with_suffix(".mp4")
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
        except OSError as e:
            self._json({"error": f"não consegui salvar: {e}"}, 500)
            return
        if dest.parent.resolve() == dest_dir.resolve():
            # saved next to the footage: remember it is an OUTPUT, so the Mídia
            # gallery and "Processar vídeos" never treat it as raw footage
            setup = self._setup()
            setup["exports"] = sorted(set(setup.get("exports", [])) | {dest.name})
            self._write_json("project_setup.json", setup)
        self._json({"ok": True, "path": str(dest)})

    def _raw_dir(self) -> Path:
        """Folder of the raw footage: first source in edl.json, else edit/.."""
        try:
            edl = json.loads((self.root / "edl.json").read_text())
            first = next(iter((edl.get("sources") or {}).values()), None)
            if first:
                return Path(first).expanduser().resolve().parent
        except (OSError, json.JSONDecodeError, StopIteration):
            pass
        return self.root.parent

    @staticmethod
    def _save_dialog(start: Path, name: str) -> Path | None:
        """Native "save as" dialog. None = cancelled. Without a dialog on this
        platform, save straight into the raw footage folder."""
        try:
            if sys.platform == "darwin":
                script = (f'POSIX path of (choose file name with prompt "Salvar vídeo editado" '
                          f'default location (POSIX file "{start}") default name "{name}")')
                r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
                return Path(r.stdout.strip()) if r.returncode == 0 and r.stdout.strip() else None
            if sys.platform.startswith("win"):
                ps = ("Add-Type -AssemblyName System.Windows.Forms;"
                      "$d=New-Object System.Windows.Forms.SaveFileDialog;"
                      f"$d.InitialDirectory='{start}';$d.FileName='{name}';$d.Filter='MP4|*.mp4';"
                      "if($d.ShowDialog() -eq 'OK'){$d.FileName}")
                r = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True)
                return Path(r.stdout.strip()) if r.stdout.strip() else None
            if shutil.which("zenity"):
                r = subprocess.run(["zenity", "--file-selection", "--save", "--confirm-overwrite",
                                    f"--filename={start / name}"], capture_output=True, text=True)
                return Path(r.stdout.strip()) if r.returncode == 0 and r.stdout.strip() else None
        except OSError:
            pass
        return start / name

    # ---- dynamic bits ----
    def _state(self) -> None:
        state_p = self.root / "state.json"
        state: dict = {}
        try:
            if state_p.exists():
                state = json.loads(state_p.read_text())
        except json.JSONDecodeError:
            state = {"error": "state.json inválido"}
        except OSError as e:
            # A read that is refused (macOS privacy, or a permission change made
            # after startup) used to raise here and 500 the endpoint, which the
            # UI shows as its ordinary waiting screen — indistinguishable from
            # "the cut is not rendered yet". Say what happened instead.
            state = {"error": f"sem permissão para ler state.json: {e}"}
        # attach small data files + mtimes so the UI hot-reloads on change
        mtimes: dict[str, float] = {}
        for key in ("video", "finalVideo", "edl", "captions", "editData", "post"):
            rel = state.get(key)
            if not rel:
                continue
            p = self._safe(self.root, rel)
            if p and p.exists():
                mtimes[key] = p.stat().st_mtime
        edl = None
        rel = state.get("edl") or "edl.json"
        p = self._safe(self.root, rel)
        if p and p.exists():
            try:
                edl = json.loads(p.read_text())
            except json.JSONDecodeError:
                pass
        edits_p = self.root / "preview_edits.json"
        video = self._current_video()
        self._json({
            "state": state,
            "edl": edl,
            "mtimes": mtimes,
            "videoDuration": probe_duration(video) if video else 0,
            "hasPendingEdits": edits_p.exists(),
            "timer": edit_timer.load(self.root),
            # local music engine status, so the Estilo tab can say BEFORE the pick
            # that "Trilha sonora com IA" still has a one-time download ahead
            "music": {"installed": _music_engine_installed()},
            "now": time.time(),
        })

    def _waveform(self) -> None:
        video = self._current_video()
        if not video:
            self._json({"error": "sem vídeo ainda"}, 404)
            return
        out = self.root / ".preview_cache" / "waveform.json"
        stale = True
        if out.exists():
            try:
                stale = json.loads(out.read_text()).get("srcMtime") != video.stat().st_mtime
            except json.JSONDecodeError:
                pass
        if stale:
            gen_waveform(video, out)
        self._send_file(out)

    def _thumbs(self, name: str) -> None:
        video = self._current_video()
        if not video:
            self._json({"error": "sem vídeo ainda"}, 404)
            return
        out_dir = self.root / ".preview_cache" / "thumbs"
        meta = out_dir / "meta.json"
        with _thumb_lock:
            stale = True
            if meta.exists():
                try:
                    stale = json.loads(meta.read_text()).get("srcMtime") != video.stat().st_mtime
                except json.JSONDecodeError:
                    pass
            if stale:
                gen_thumbs(video, out_dir)
        p = self._safe(out_dir, name)
        self._send_file(p) if p else self._json({"error": "bad path"}, 400)

    def log_message(self, fmt: str, *args: object) -> None:
        pass  # quiet


def _check_access(root: Path) -> None:
    """Fail loudly, at startup, when the edit dir cannot be read or written.

    Without this the failure is silent in the worst way: the server starts, the
    UI opens on its waiting screen, and it waits forever for a state.json that
    the skill was never allowed to write. The user sees a working preview with
    no video and nothing to act on.

    The errno is the diagnosis on macOS. Its privacy layer (TCC) guards
    ~/Documents, ~/Desktop, ~/Downloads and iCloud Drive, and denies with
    EPERM (1) "Operation not permitted" — an app the user never granted Files
    and Folders access to gets that even though the file permissions are fine.
    Ordinary permission or ownership problems come back as EACCES (13). The two
    need completely different fixes, so do not merge the messages.
    """
    probe = root / ".edvid_write_probe"
    err: OSError | None = None
    try:
        probe.write_text("ok")
        probe.unlink()
        for _ in root.iterdir():
            break
    except OSError as exc:
        # Bind outside the handler: Python deletes the `except` name on exit.
        err = exc
    if err is None:
        return

    where = f"{root}"
    if getattr(err, "errno", None) == 1 and sys.platform == "darwin":
        raise SystemExit(
            f"sem permissão para escrever em {where}\n"
            "\n"
            "No macOS isso é a proteção de privacidade do sistema, não a permissão\n"
            "do arquivo: ~/Documents, ~/Desktop, ~/Downloads e o iCloud Drive são\n"
            "protegidos, e o app precisa ser autorizado uma vez.\n"
            "\n"
            "  Ajustes do Sistema → Privacidade e Segurança → Arquivos e Pastas\n"
            "  (ou Acesso Total ao Disco) → ligue para o Claude / o Terminal\n"
            "\n"
            "Depois feche e reabra o app.\n"
            "\n"
            "SE AS PERMISSÕES JÁ ESTIVEREM LIGADAS: reinicie o Mac. O cache de\n"
            "permissões do macOS às vezes fica preso mostrando a chave ativa sem\n"
            "conceder o acesso, e só o reinício resolve. (Visto em produção — foi\n"
            "exatamente isso, e nenhuma mexida nos Ajustes tinha efeito.)\n"
            "\n"
            "Se preferir não lidar com permissão, mova a pasta dos vídeos para fora\n"
            "dessas três pastas — por exemplo ~/Videos."
        )
    raise SystemExit(
        f"sem permissão para ler/escrever em {where}: {err}\n"
        "Confira o dono e as permissões da pasta."
    )


def main() -> None:
    ap = argparse.ArgumentParser(description="Edvid preview interface server")
    ap.add_argument("--root", type=Path, required=True, help="the session <edit> dir")
    ap.add_argument("--port", type=int, default=4820)
    args = ap.parse_args()

    root = args.root.resolve()
    if not root.exists():
        raise SystemExit(f"edit dir not found: {root}")
    _check_access(root)
    if not (APP_DIR / "index.html").exists():
        raise SystemExit(f"app not found at {APP_DIR}")

    Handler.root = root
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Edvid preview → http://127.0.0.1:{args.port}  (root: {root})", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
