"""Runs INSIDE the ACE-Step 1.5 environment — do not call directly.

`music_local.py` launches this with `uv run --project <ACE-Step dir>`, so it can
import `acestep` without the skill's own .venv (WhisperX pins a different torch)
and without ACE-Step's heavy tree leaking into the skill.

ACE-Step 1.5: https://github.com/ace-step/ACE-Step-1.5 (MIT, code and weights).
"""
from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
APPLE_SILICON = sys.platform == "darwin" and platform.machine() == "arm64"
if APPLE_SILICON:
    # the documented macOS path: MLX for the LM (and the DiT) on Apple Silicon
    os.environ.setdefault("ACESTEP_LM_BACKEND", "mlx")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--caption", required=True)
    ap.add_argument("--duration", type=float, required=True)
    ap.add_argument("--bpm", type=int, default=None)
    ap.add_argument("--seed", type=int, default=-1)
    ap.add_argument("--lm", default="acestep-5Hz-lm-1.7B")
    ap.add_argument("--dit", default="acestep-v15-turbo")
    ap.add_argument("--download-only", action="store_true")
    ap.add_argument("-o", "--output", type=Path)
    a = ap.parse_args()

    root = Path.cwd()
    ckpt = root / "checkpoints"
    from acestep.model_downloader import check_main_model_exists, download_main_model

    if not check_main_model_exists(ckpt):
        print("  modelo: baixando ACE-Step 1.5 (primeira vez, ~10 GB)…", flush=True)
        ok, msg = download_main_model(ckpt)
        if not ok:
            sys.exit(f"download do modelo falhou: {msg}")
    if a.download_only:
        print("  modelo: pronto", flush=True)
        return
    if not a.output:
        sys.exit("--output é obrigatório")

    from acestep.handler import AceStepHandler
    from acestep.inference import GenerationConfig, GenerationParams, generate_music
    from acestep.llm_inference import LLMHandler

    dit = AceStepHandler()
    msg, ok = dit.initialize_service(project_root=str(root), config_path=a.dit, device="auto")
    if not ok:
        sys.exit(f"DiT não inicializou: {msg}")
    llm = LLMHandler()
    msg, ok = llm.initialize(
        checkpoint_dir=str(ckpt),
        lm_model_path=a.lm,
        backend="mlx" if APPLE_SILICON else "pt",
        device="auto",
    )
    if not ok:
        sys.exit(f"LM não inicializou: {msg}")

    params = GenerationParams(
        caption=a.caption,
        lyrics="[Instrumental]",
        instrumental=True,
        bpm=a.bpm,
        duration=a.duration,
        seed=a.seed,
    )
    config = GenerationConfig(
        batch_size=1,
        use_random_seed=a.seed < 0,
        seeds=[a.seed] if a.seed >= 0 else None,
        audio_format="wav",
    )
    with tempfile.TemporaryDirectory() as tmp:
        res = generate_music(dit, llm, params, config, save_dir=tmp)
        if not res.success or not res.audios:
            sys.exit(f"geração falhou: {res.error or res.status_message}")
        src = Path(res.audios[0]["path"])
        a.output.parent.mkdir(parents=True, exist_ok=True)
        if a.output.suffix.lower() == ".wav":
            shutil.copy(src, a.output)
        else:
            subprocess.run(
                ["ffmpeg", "-v", "error", "-y", "-i", str(src), "-b:a", "192k", str(a.output)],
                check=True,
            )
    print(f"  saved: {a.output}", flush=True)


if __name__ == "__main__":
    main()
