#!/usr/bin/env python3
"""Emit one event per save from the preview UI.

Three files, all written by the UI and none able to reach the chat on its own:
  - preview_edits.json — timeline adjustments and correction markers
  - preview_style.json — the Fase 1 → Fase 2 gate: editing style, caption style,
    edit elements
  - preview_post.json  — caption edits from the Postagem tab (Fase 3)

Run this under the Monitor tool so every save notifies the session automatically:

    Monitor(command="python3 <skill>/helpers/watch_edits.py '<edit>'",
            description="marcações do preview", persistent=True)

Each stdout line is one notification. Stays quiet while nothing changes.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path


def digest(p: Path) -> str:
    try:
        d = json.loads(p.read_text())
    except (OSError, json.JSONDecodeError) as e:
        return f"preview_edits.json ilegível ({e.__class__.__name__}) — peça ao usuário para salvar de novo"

    parts: list[str] = []
    notes = d.get("notes") or []
    for i, n in enumerate(notes, 1):
        start, end = n.get("start", 0), n.get("end", 0)
        fase = n.get("phase", 1)
        parts.append(f'  {i}. [{fmt(start)} → {fmt(end)}] (fase {fase}) {n.get("text", "").strip()}')

    edl = d.get("edl") or {}
    n_ch = len(edl.get("changes") or [])
    n_rm = len(edl.get("removed") or [])
    ed = d.get("editData") or {}

    head = []
    if notes:
        head.append(f"{len(notes)} marcação(ões)")
    if n_ch:
        head.append(f"{n_ch} take(s) reajustado(s)")
    if n_rm:
        head.append(f"{n_rm} take(s) removido(s)")
    if ed:
        head.append("inserts/gancho movidos")
    if not head:
        head.append("ajustes salvos")

    out = [f"AJUSTES DO PREVIEW ({d.get('savedAt', '')}) — {', '.join(head)}. Aplique-os."]
    out += parts
    return "\n".join(out)


def music_engine_installed() -> bool:
    """Same test as music_local.installed(), kept dependency-free here."""
    import os
    d = Path(os.environ.get("FMCUT_MUSIC_DIR", Path.home() / ".cache" / "fm-cut" / "ACE-Step-1.5"))
    return (d / "pyproject.toml").exists() and (d / ".venv").exists()


def style_digest(p: Path) -> str:
    """The gate choice: what Fase 2 should be built as."""
    try:
        d = json.loads(p.read_text())
    except (OSError, json.JSONDecodeError) as e:
        return f"preview_style.json ilegível ({e.__class__.__name__}) — peça ao usuário para salvar de novo"

    els = d.get("elementNames") or [
        k for k, v in (d.get("elements") or {}).items() if v
    ]
    head = (
        "TROCA DE ESTILO NO PREVIEW ({}) — REFAÇA a Fase 2 assim:"
        if d.get("rerender")
        else "ESTILO ESCOLHIDO NO PREVIEW ({}) — monte a Fase 2 assim:"
    ).format(d.get("savedAt", ""))
    out = [
        head,
        f'  · tipo de edição: {d.get("editName") or d.get("edit")}',
        f'  · headline: {d.get("headlineName") or d.get("headline")}',
        f'  · legenda: {d.get("captionsName") or d.get("captions")}',
    ]
    # Only worth reporting when the chosen styles actually paint an accent —
    # naming a colour that nothing uses reads as an instruction to go find a
    # place for it.
    accent = d.get("accent")
    if accent:
        if d.get("accentUsed"):
            name = d.get("accentName") or accent
            label = f"{name} ({accent})" if name.lower() != str(accent).lower() else accent
            out.append(f"  · cor de destaque: {label}")
        else:
            out.append("  · cor de destaque: não se aplica (os estilos escolhidos não usam destaque)")
    out.append(f'  · elementos: {", ".join(els) if els else "nenhum"}')
    # everything NOT chosen is an instruction too — it is what must stay out
    off = [k for k, v in (d.get("elements") or {}).items() if not v]
    if off:
        out.append(f'  · fora: {", ".join(off)}')
    if (d.get("elements") or {}).get("flashCut"):
        f = d.get("flash") or {}
        n = d.get("flashNames") or {}
        out.append(f'  · flash: {n.get("kind") or f.get("kind", "white")} · força {n.get("strength") or f.get("strength", "media")}'
                   f' · onde: {n.get("where") or f.get("where", "beats")}'
                   f' → edit-data "transitionStyle": {{"kind": "{f.get("kind", "white")}", "strength": "{f.get("strength", "media")}"}}'
                   f' + transitions[] em {"cada troca de beat" if f.get("where", "beats") == "beats" else "cada entrada de layout" if f.get("where") == "layout" else "todos os cortes"}')
    if (d.get("note") or "").strip():
        out.append(f'  · observação do usuário: {d["note"].strip()}')
    # The soundtrack is part of the Fase-2 delivery, not an afterthought. A key
    # asked for only after the render leaves final.mp4 shipping silent.
    if (d.get("elements") or {}).get("musicAI"):
        if music_engine_installed():
            out.append("  · trilha IA: ACE-Step 1.5 instalado — gere a trilha (music_local.py) EM PARALELO ao render da Fase 2 e mixe no final.mp4")
        else:
            out.append("  ⚠️ trilha IA escolhida e ACE-Step 1.5 NÃO instalado — rode `music_local.py --setup` AGORA em background (baixa ~10 GB uma vez), em paralelo à Fase 2")
    return "\n".join(out)


def post_digest(p: Path) -> str:
    """Caption edits from the Postagem tab (Fase 3)."""
    try:
        d = json.loads(p.read_text())
    except (OSError, json.JSONDecodeError) as e:
        return f"preview_post.json ilegível ({e.__class__.__name__}) — peça ao usuário para salvar de novo"
    out = [f"LEGENDA DA POSTAGEM AJUSTADA NO PREVIEW ({d.get('savedAt', '')}) — grave no post.json:"]
    for n in d.get("platforms") or []:
        cap = (n.get("caption") or "").strip().replace("\n", " ⏎ ")
        line = f"  · {n.get('id')}: legenda ({len(n.get('caption') or '')} car.) \"{cap[:90]}{'…' if len(cap) > 90 else ''}\""
        if n.get("title") is not None:
            line += f" · título \"{n['title']}\""
        if n.get("removedHashtags"):
            line += f" · hashtags removidas: {' '.join(n['removedHashtags'])}"
        out.append(line)
    out.append("  → copie caption/title/hashtags de preview_post.json para post.json e apague preview_post.json")
    return "\n".join(out)


def media_digest(p: Path) -> str:
    """Files dropped into the preview's Mídia panel."""
    try:
        items = json.loads(p.read_text()).get("items") or []
    except (OSError, json.JSONDecodeError) as e:
        return f"preview_media.json ilegível ({e.__class__.__name__})"
    out = ["MÍDIA ADICIONADA NO PREVIEW:"]
    for it in items:
        sc = it.get("scope")
        if sc == "library":
            al = f" (apelidos: {', '.join(it['aliases'])})" if it.get("aliases") else ""
            out.append(f"  · marca na biblioteca: {it.get('name')}{al} → use EXATAMENTE este arquivo quando a marca for citada")
        elif sc == "source":
            out.append(f"  · vídeo bruto novo: {it.get('file')} → transcreva e inclua no inventário/EDL se fizer parte da edição")
        else:
            out.append(f"  · imagem/clipe desta edição: {it.get('file')} → candidato a insert/tela dividida")
    out.append("  → depois de considerar, apague preview_media.json")
    return "\n".join(out)


ASPECT_NAMES = {"9:16": "vertical 9:16 (Reels/TikTok/Shorts)", "16:9": "horizontal 16:9 (YouTube)",
                "1:1": "quadrado 1:1", "4:5": "retrato 4:5 (feed)", "source": "mesmo formato da gravação"}


def process_digest(p: Path) -> str:
    """The "Processar vídeos" button: start (or redo) Fase 1 from the gallery."""
    try:
        d = json.loads(p.read_text())
    except (OSError, json.JSONDecodeError) as e:
        return f"preview_process.json ilegível ({e.__class__.__name__})"
    aspect = d.get("aspect", "source")
    out = [f"PROCESSAR VÍDEOS PEDIDO NO PREVIEW ({d.get('savedAt', '')}) — rode a Fase 1:",
           f"  · formato de saída: {ASPECT_NAMES.get(aspect, aspect)}"
           + ("" if aspect == "source" else f' → edl "aspect": "{aspect}" + crop_x/crop_y por take'),
           f"  · pasta: {d.get('rawDir')}",
           "  · vídeos, NESTA ordem (a ordem da galeria é a ordem da história):"]
    out += [f"      {i}. {n}" for i, n in enumerate(d.get("files") or [], 1)]
    if (d.get("note") or "").strip():
        out.append(f"  · observação do usuário: {d['note'].strip()}")
    out.append("  → transcreva (cache), pack, voice_levels, escolha o melhor take de cada frase,"
               " corte respiros e erros, render + verify_cut; depois apague preview_process.json")
    return "\n".join(out)


def fmt(t: float) -> str:
    m, s = divmod(max(0.0, float(t)), 60)
    return f"{int(m)}:{s:05.2f}"


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").expanduser().resolve()
    watched = {
        root / "preview_edits.json": digest,
        root / "preview_style.json": style_digest,
        root / "preview_post.json": post_digest,
        root / "preview_media.json": media_digest,
        root / "preview_process.json": process_digest,
    }
    # a file already sitting there at startup means it is pending — say so once
    last: dict[Path, float | None] = {}
    for target, fn in watched.items():
        last[target] = target.stat().st_mtime if target.exists() else None
        if last[target] is not None:
            print(fn(target), flush=True)

    while True:
        for target, fn in watched.items():
            try:
                cur = target.stat().st_mtime if target.exists() else None
            except OSError:
                cur = None
            if cur is not None and cur != last[target]:
                last[target] = cur
                time.sleep(0.15)  # let the atomic replace settle before reading
                print(fn(target), flush=True)
            elif cur is None:
                last[target] = None  # applied and deleted — re-arm for the next save
        time.sleep(2)


if __name__ == "__main__":
    raise SystemExit(main())
