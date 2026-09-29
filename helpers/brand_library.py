"""Local brand-logo library — logos the user uploaded or the skill already found.

A logo is a registered mark: it is used EXACTLY as stored. Scale it, place it on
a neutral plate when contrast demands — never recolor, redraw, crop into another
shape, stretch or restyle it. Stdlib-only: the preview server imports this too.

Lives in <skill>/library/logos/ (override: $FMCUT_LIBRARY_DIR). The installer
keeps library/ across updates and git ignores it — it is the user's data.

    uv run python helpers/brand_library.py find "NVIDIA"        # exit 0 + JSON if found
    uv run python helpers/brand_library.py list
    uv run python helpers/brand_library.py add logo.svg --name "NVIDIA" \
        --aliases "nvidia corp,nvda" --source https://… --license "trademark, press kit"
    uv run python helpers/brand_library.py remove nvidia
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import time
import unicodedata
from pathlib import Path

LIB = Path(os.environ.get("FMCUT_LIBRARY_DIR", Path(__file__).resolve().parent.parent / "library"))
LOGOS = LIB / "logos"
INDEX = LOGOS / "index.json"
IMAGE_EXT = {".png", ".svg", ".webp", ".jpg", ".jpeg"}


def norm(s: str) -> str:
    """'Nvídia Corp.' -> 'nvidia corp' — accents, case and punctuation do not
    decide a match; the transcript spells brands however Whisper heard them."""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def slugify(s: str) -> str:
    return norm(s).replace(" ", "-") or "logo"


def load() -> dict:
    try:
        return json.loads(INDEX.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def save(idx: dict) -> None:
    LOGOS.mkdir(parents=True, exist_ok=True)
    tmp = INDEX.with_suffix(".tmp")
    tmp.write_text(json.dumps(idx, ensure_ascii=False, indent=2))
    tmp.replace(INDEX)


def find(name: str) -> dict | None:
    """Exact normalized match on name, slug or alias. Deliberately NOT fuzzy:
    putting the wrong company's mark on screen is worse than searching again."""
    q = norm(name)
    for slug, e in load().items():
        keys = {norm(e.get("name", "")), norm(slug), *(norm(a) for a in e.get("aliases", []))}
        if q in keys and (LOGOS / e["file"]).exists():
            return {"slug": slug, **e, "path": str(LOGOS / e["file"])}
    return None


def add(src: Path, name: str, aliases: list[str] | None = None,
        source: str = "", license: str = "", data: bytes | None = None) -> dict:
    ext = src.suffix.lower()
    if ext not in IMAGE_EXT:
        raise ValueError(f"formato não suportado: {ext} (use {', '.join(sorted(IMAGE_EXT))})")
    slug = slugify(name)
    LOGOS.mkdir(parents=True, exist_ok=True)
    idx = load()
    old = idx.get(slug)
    if old and old.get("file") and old["file"] != f"{slug}{ext}":
        (LOGOS / old["file"]).unlink(missing_ok=True)
    dest = LOGOS / f"{slug}{ext}"
    if data is not None:
        dest.write_bytes(data)
    else:
        shutil.copy2(src, dest)
    idx[slug] = {
        "name": name.strip(),
        "aliases": sorted({a.strip() for a in (aliases or []) if a.strip()}),
        "file": dest.name,
        "source": source or (old or {}).get("source", "upload"),
        "license": license or (old or {}).get("license", ""),
        "addedAt": time.strftime("%Y-%m-%d"),
    }
    save(idx)
    return {"slug": slug, **idx[slug]}


def remove(slug: str) -> bool:
    idx = load()
    e = idx.pop(slug, None)
    if not e:
        return False
    (LOGOS / e["file"]).unlink(missing_ok=True)
    save(idx)
    return True


def main() -> None:
    ap = argparse.ArgumentParser(description="Biblioteca local de logos de marcas")
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("find")
    f.add_argument("name")
    sub.add_parser("list")
    a = sub.add_parser("add")
    a.add_argument("file", type=Path)
    a.add_argument("--name", required=True)
    a.add_argument("--aliases", default="")
    a.add_argument("--source", default="")
    a.add_argument("--license", default="")
    r = sub.add_parser("remove")
    r.add_argument("slug")
    args = ap.parse_args()

    if args.cmd == "find":
        hit = find(args.name)
        print(json.dumps(hit, ensure_ascii=False) if hit else f"não está na biblioteca: {args.name}")
        sys.exit(0 if hit else 1)
    if args.cmd == "list":
        for slug, e in sorted(load().items()):
            al = f"  ({', '.join(e['aliases'])})" if e.get("aliases") else ""
            print(f"{slug:24} {e['name']}{al} — {e['file']} · {e.get('source', '')}")
        return
    if args.cmd == "add":
        e = add(args.file, args.name, args.aliases.split(","), args.source, args.license)
        print(f"  salvo na biblioteca: {e['name']} → {LOGOS / e['file']}")
        return
    if args.cmd == "remove":
        sys.exit(0 if remove(args.slug) else 1)


if __name__ == "__main__":
    main()
