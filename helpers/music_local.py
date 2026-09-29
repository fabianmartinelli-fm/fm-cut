"""Instrumental soundtrack, generated LOCALLY and for free with ACE-Step 1.5.

No account, no API key, no credits. ACE-Step 1.5 (MIT — code and weights,
https://github.com/ace-step/ACE-Step-1.5) runs on Apple Silicon (MLX), NVIDIA,
AMD and Intel. Its output can be used commercially.

The engine lives OUTSIDE the skill, in its own uv environment, because its torch
pin differs from WhisperX's and it is several GB:
    $FMCUT_MUSIC_DIR  (default: ~/.cache/fm-cut/ACE-Step-1.5)
Models (~10 GB) download on first use into <that dir>/checkpoints.

Usage:
    uv run python helpers/music_local.py --check          # installed? (exit 0/1)
    uv run python helpers/music_local.py --setup          # clone + uv sync + models
    uv run python helpers/music_local.py "<vibe>" -o remotion/public/trilha.mp3 \
        --duration 72 [--bpm 100] [--seed 42]

Write the vibe as MUSIC, not texture: genre + key instruments + tempo + mood.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO_URL = "https://github.com/ace-step/ACE-Step-1.5.git"
ENGINE_DIR = Path(os.environ.get("FMCUT_MUSIC_DIR", Path.home() / ".cache" / "fm-cut" / "ACE-Step-1.5"))
RUNNER = Path(__file__).resolve().parent / "acestep_runner.py"

# ACE-Step reads a descriptive caption. Framing it as a finished instrumental
# keeps it from drifting into ambience or sound design under a voice-over.
FRAME = ("instrumental background music for a spoken video, full arrangement with "
         "melody, chords and a steady rhythm section, no vocals, mixed to sit under a voice. ")


def installed() -> bool:
    return (ENGINE_DIR / "pyproject.toml").exists() and (ENGINE_DIR / ".venv").exists()


def need(tool: str) -> None:
    if not shutil.which(tool):
        sys.exit(f"'{tool}' não encontrado no PATH — instale e rode de novo")


def run_engine(args: list[str]) -> None:
    need("uv")
    cmd = ["uv", "run", "--project", str(ENGINE_DIR), "python", str(RUNNER), *args]
    r = subprocess.run(cmd, cwd=ENGINE_DIR)
    if r.returncode:
        sys.exit(r.returncode)


def setup() -> None:
    need("git")
    need("uv")
    if not (ENGINE_DIR / "pyproject.toml").exists():
        ENGINE_DIR.parent.mkdir(parents=True, exist_ok=True)
        print(f"  clonando ACE-Step 1.5 → {ENGINE_DIR}", flush=True)
        subprocess.run(["git", "clone", "--depth", "1", REPO_URL, str(ENGINE_DIR)], check=True)
    print("  instalando dependências (uv sync)…", flush=True)
    subprocess.run(["uv", "sync"], cwd=ENGINE_DIR, check=True)
    run_engine(["--caption", "-", "--duration", "1", "--download-only"])
    print("  trilha local pronta: ACE-Step 1.5 instalado", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser(description="Trilha instrumental local e gratuita (ACE-Step 1.5)")
    ap.add_argument("vibe", nargs="?", help="genre + instruments + tempo + mood")
    ap.add_argument("-o", "--output", type=Path)
    ap.add_argument("--duration", type=float, help="seconds — the edit's length plus ~2s")
    ap.add_argument("--bpm", type=int, default=None)
    ap.add_argument("--seed", type=int, default=-1, help="fix it to reproduce a take")
    ap.add_argument("--raw", action="store_true", help="send the vibe without the framing")
    ap.add_argument("--check", action="store_true", help="exit 0 if the engine is installed")
    ap.add_argument("--setup", action="store_true", help="clone + install + download models")
    a = ap.parse_args()

    if a.check:
        print(f"ACE-Step 1.5: {'ok' if installed() else 'não instalado'} ({ENGINE_DIR})")
        sys.exit(0 if installed() else 1)
    if a.setup:
        setup()
        return
    if not (a.vibe and a.output and a.duration):
        ap.error("vibe, -o/--output and --duration are required (or --check / --setup)")
    if not installed():
        print("  ACE-Step 1.5 ainda não instalado — instalando agora (uma vez só)…", flush=True)
        setup()
    caption = a.vibe if a.raw else FRAME + a.vibe
    print(f"  prompt → {caption}", flush=True)
    args = ["--caption", caption, "--duration", str(a.duration), "--seed", str(a.seed),
            "-o", str(a.output.resolve())]
    if a.bpm:
        args += ["--bpm", str(a.bpm)]
    run_engine(args)


if __name__ == "__main__":
    main()
