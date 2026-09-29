"""Local brand-logo library — logos the user uploaded or the skill already found.

A logo is a registered mark: it is used EXACTLY as stored. Scale it, place it on
a neutral plate when contrast demands — never recolor, redraw, crop into another
shape, stretch or restyle it. Stdlib-only: the preview server imports this too.

Lives in <skill>/library/logos/ (override: $FMCUT_LIBRARY_DIR). The installer
keeps library/ across updates and git ignores it — it is the user's data.

    uv run python helpers/brand_library.py find "NVIDIA"        # exit 0 + JSON if found
    uv run python helpers/brand_library.py find "Claude" --kind mascote   # mascot/symbol
    uv run python helpers/brand_library.py list
    uv run python helpers/brand_library.py add logo.svg --name "NVIDIA" \
        --aliases "nvidia corp,nvda" --source https://… --license "trademark, press kit"
    uv run python helpers/brand_library.py remove nvidia
    uv run python helpers/brand_library.py seed            # tech/AI marks, Wikimedia
    uv run python helpers/brand_library.py seed --only nvidia,openai --force

Format: every logo is a PNG with a TRANSPARENT background (1600px wide, rendered
by Wikimedia from the official SVG) — works in Remotion, ffmpeg and the preview
alike. When the source is an SVG it is kept next to it (`<slug>.svg`, index
field "svg") for a mark that has to scale past 1600px without softening.
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


def _keys(slug: str, e: dict) -> set[str]:
    return {norm(e.get("name", "")), norm(slug), *(norm(a) for a in e.get("aliases", []))}


def find(name: str, kind: str = "logo") -> dict | None:
    """Exact normalized match on name, slug or alias. Deliberately NOT fuzzy:
    putting the wrong company's mark on screen is worse than searching again.

    kind="logo" (default) returns the brand's main logo. kind="mascote" returns
    its mascot/symbol (Claude spark, DeepSeek whale, Tux…): a mascot also answers
    to its brand's names through its "brand" field, so find("Claude", "mascote")
    works."""
    q = norm(name)
    idx = load()
    for slug, e in idx.items():
        if e.get("kind", "logo") != kind or not (LOGOS / e["file"]).exists():
            continue
        keys = _keys(slug, e)
        base = idx.get(e.get("brand", "")) if kind != "logo" else None
        if base:
            keys |= _keys(e["brand"], base)
        if q in keys:
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
    if e.get("svg"):
        (LOGOS / e["svg"]).unlink(missing_ok=True)
    save(idx)
    return True


SEED = LIB / "seed_brands.json"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
UA = {"User-Agent": "fm-cut-brand-seed/1.0 (FM Solutions; https://github.com/fabianmartinelli-fm/fm-cut)"}


def has_transparency(png: bytes) -> bool:
    from io import BytesIO
    from PIL import Image
    im = Image.open(BytesIO(png)).convert("RGBA")
    return im.getchannel("A").getextrema()[0] < 255


def seed(only: set[str] | None = None, force: bool = False) -> tuple[list[str], list[str]]:
    """Download the curated tech/AI marks (library/seed_brands.json) from
    Wikimedia Commons as transparent PNGs (+ the SVG when there is one).
    Network + requests/Pillow: run it with `uv run`, never from the server."""
    import requests
    from io import BytesIO
    from PIL import Image

    brands = json.loads(SEED.read_text())["brands"]
    LOGOS.mkdir(parents=True, exist_ok=True)
    idx = load()
    done, failed = [], []
    for b in brands:
        slug = b["slug"]
        if only and slug not in only:
            continue
        if slug in idx and not force and (LOGOS / idx[slug]["file"]).exists():
            continue
        try:
            q = requests.get(COMMONS_API, headers=UA, timeout=30, params={
                "action": "query", "format": "json", "titles": f"File:{b['commons']}",
                "prop": "imageinfo", "iiprop": "url|mime|extmetadata|size", "iiurlwidth": "1600"}).json()
            page = next(iter(q["query"]["pages"].values()))
            ii = (page.get("imageinfo") or [None])[0]
            if not ii:
                raise ValueError(f"arquivo não existe no Commons: {b['commons']}")
            is_svg = ii.get("mime") == "image/svg+xml"
            png_url = ii.get("thumburl") if (is_svg or ii.get("width", 0) > 1600) else ii["url"]
            data = requests.get(png_url, headers=UA, timeout=60).content
            if not has_transparency(data):
                raise ValueError("sem fundo transparente — fica fora (logo com fundo não entra)")
            png = LOGOS / f"{slug}.png"
            Image.open(BytesIO(data)).convert("RGBA").save(png, optimize=True)
            svg_name = None
            if is_svg:
                (LOGOS / f"{slug}.svg").write_bytes(requests.get(ii["url"], headers=UA, timeout=60).content)
                svg_name = f"{slug}.svg"
            meta = ii.get("extmetadata") or {}
            idx[slug] = {
                "name": b["name"],
                "kind": b.get("kind", "logo"),
                **({"brand": b["brand"]} if b.get("brand") else {}),
                "aliases": sorted(set(b.get("aliases", []))),
                "file": png.name,
                "svg": svg_name,
                "source": ii.get("descriptionurl", ""),
                "license": (meta.get("LicenseShortName") or {}).get("value", ""),
                "addedAt": time.strftime("%Y-%m-%d"),
                "seed": True,
            }
            save(idx)
            done.append(slug)
            print(f"  ok  {b['name']:22} ← {b['commons']}", flush=True)
        except Exception as e:  # one brand failing must not stop the rest
            failed.append(slug)
            print(f"  x   {b['name']:22} {e}", flush=True)
        time.sleep(0.4)  # be polite to Wikimedia
    return done, failed


def main() -> None:
    ap = argparse.ArgumentParser(description="Biblioteca local de logos de marcas")
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("find")
    f.add_argument("name")
    f.add_argument("--kind", default="logo", choices=["logo", "mascote"])
    sub.add_parser("list")
    a = sub.add_parser("add")
    a.add_argument("file", type=Path)
    a.add_argument("--name", required=True)
    a.add_argument("--aliases", default="")
    a.add_argument("--source", default="")
    a.add_argument("--license", default="")
    r = sub.add_parser("remove")
    r.add_argument("slug")
    sd = sub.add_parser("seed", help="baixa as marcas de tecnologia/IA da lista curada")
    sd.add_argument("--only", default="", help="slugs separados por vírgula")
    sd.add_argument("--force", action="store_true", help="baixa de novo mesmo se já existir")
    args = ap.parse_args()

    if args.cmd == "seed":
        only = {x.strip() for x in args.only.split(",") if x.strip()} or None
        done, failed = seed(only, args.force)
        print(f"seed: {len(done)} baixada(s), {len(failed)} falha(s){': ' + ', '.join(failed) if failed else ''}")
        return

    if args.cmd == "find":
        hit = find(args.name, args.kind)
        print(json.dumps(hit, ensure_ascii=False) if hit else f"não está na biblioteca: {args.name}")
        sys.exit(0 if hit else 1)
    if args.cmd == "list":
        for slug, e in sorted(load().items()):
            al = f"  ({', '.join(e['aliases'])})" if e.get("aliases") else ""
            k = "" if e.get("kind", "logo") == "logo" else "  [mascote]"
            print(f"{slug:24} {e['name']}{al}{k} — {e['file']} · {e.get('source', '')}")
        return
    if args.cmd == "add":
        e = add(args.file, args.name, args.aliases.split(","), args.source, args.license)
        print(f"  salvo na biblioteca: {e['name']} → {LOGOS / e['file']}")
        return
    if args.cmd == "remove":
        sys.exit(0 if remove(args.slug) else 1)


if __name__ == "__main__":
    main()
