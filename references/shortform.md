# SHORT-FORM track (Reels / TikTok / Shorts) — Phase 2 + 3 reference

Read this file when the video is vertical short-form and the Phase-1 cut is
approved. Everything here rides on the **data-driven template** at
`assets/shortform/` — the code is immutable; a video is described by ONE JSON.

## The style (the proven default)

- **Frame rate:** render at **30fps when the source is 30fps or higher** (natural
  motion, matches Instagram/TikTok/Shorts capture); only slower sources use 24.
  `render.py` picks this automatically for `cut.mp4` — then set `edit-data.json`
  `fps` to the SAME value as `cut.mp4` (ffprobe it) so the Remotion render matches.
- **Base:** 1080×1920 (fps per the rule above), `<OffthreadVideo src=cut.mp4>` with the **dynamic
  camera**, whose three parts are separate picks on the Estilo tab: hard zoom per
  cut segment (`zoomCuts`, ~1.10–1.22, cycles), slow push-in (`zoomAuto`,
  +0.04/segment), clamped eye-tracking (`tracking`, target upper third, never
  reveals an edge). `zoomCuts` is what makes a talking head feel edited — if the
  user turns everything off, say what they lose and build it anyway.
- **Visual hook (first ~4s):** static copywriting headline, **always two lines**
  with the size fitted to them (see "Headline styles"). On by default, but the
  Estilo tab offers "Nenhum" — respect it and set `hook.enabled: false`.
- **Captions:** six styles — three animated (**karaoke**, **stacked**, **scatter**)
  and three static (**simples**, **serifada**, **classica**) — plus "Nenhum",
  which is `captions.enabled: false` and no caption generation at all. The user already
  picked one on the Estilo tab; see the "Caption style" section.
  Karaoke: one line ≤3 words, words rise from below, Poppins Black, lower third,
  `measureText` fit into **SAFE_WIDTH 720** (~180px each side — clears
  Instagram/TikTok's right action rail; verified on a real screenshot). Never
  rely on `nowrap` alone.
- **Inserts (upper zone):** rounded-card + shadow motif synced to spoken nouns,
  slow Ken-Burns. Pexels for concrete objects; **bespoke motion graphics** when
  a word names something animatable (timeline for "cortes", typewriter sheet
  for "roteiro" — worked examples in `src/CustomGraphics.tsx`).
- **Zones:** inserts/graphics upper third, captions lower third, face clear.
  Minimalist; accent `#33e0a3`.
- **Audio:** whoosh ~0.09 on card entrances, pop ~0.12 on shapes, music ~0.0445,
  and ALWAYS a final loudnorm pass (voice+music+SFX summed will clip). The
  shared sfx pack (`public/sfx/`) also ships `click1`/`click2` (element pops) and
  `tictac` (clocks/countdowns) — trigger any at a local frame by wrapping
  `<Sfx src="click2.mp3" volume={0.7}/>` in a `<Sequence from={frame} layout="none">`.

## Workflow

**Read `<edit>/preview_style.json` first — it IS the brief.** The user chose it on
the Estilo tab at the end of Fase 1; every key maps to something here:

| Pick | What it means |
|---|---|
| `edit: "limpa"` | **the default** — NO split inserts, full frame throughout. See the "Limpa" section |
| `edit: "split" \| "split2"` | the split-screen variant below — every image insert uses it |
| `headline: "outline" \| "card" \| "realce" \| "misto"` | `hook.style` in edit-data.json |
| `headline: "none"` | **no headline at all** — `hook.enabled: false`. The template already gates on that flag, so nothing else changes |
| `captions: "karaoke" \| "stacked" \| "scatter" \| "simples" \| "serifada" \| "classica"` | `captions.style` in edit-data.json (+ the director step for stacked) |
| `captions: "none"` | **no captions at all** — `captions.enabled: false`. Skip `captions_for_remotion.py` too; nothing reads the file |
| `accent` (hex) | `hook.accent` + `captions.accent`. Only `realce`/`misto`/`stacked` paint it; `accentUsed:false` means the picked styles have none |
| `elements.tracking` | `face_track.py` + `track.json`; OFF → skip it, fixed frame |
| `elements.zoomAuto` | the slow push-in inside each segment (`+0.04/segment`) |
| `elements.zoomCuts` | the hard zoom change ON each cut (~1.10–1.22, cycles) |
| `elements.flashCut` | `transitions[]` in edit-data.json — see "Flash na transição" |
| `elements.musicAI` | the soundtrack ships INSIDE the Fase-2 `final.mp4` — see "Soundtrack is part of the Fase-2 delivery" below. Run `music_local.py --check` the moment the pick lands (start `--setup` in the background if needed); OFF → deliver with voice only |
| `note` | free text — read it, it overrides the defaults above |

An unchecked box is an explicit NO, not a silence. Copy the picks into
`state.json` as `style`, clear `awaitingStyle`, delete `preview_style.json`.

1. **Scaffold (one command, never read the TSX):**
   ```bash
   cp -R <skill>/assets/shortform/. <edit>/remotion/ && cd <edit>/remotion && npm install
   ```
2. **Generate machine data into `remotion/public/`:**
   - `cp cut.mp4 remotion/public/`
   - `transcribe.py cut.mp4 --edit-dir <edit>` → `transcripts/cut.json`
     (cut times are already on the output timeline — never map the source EDL)
   - `captions_for_remotion.py --transcript transcripts/cut.json -o public/captions.json`
   - **Caption style** — from the Estilo tab pick. `stacked` ALSO needs
     `caption_style.py --transcript transcripts/cut.json -o public/caption-cues.json`
     plus `captions.style:"stacked"` (see the "Caption style" section).
   - `face_track.py cut.mp4 -o public/track.json` — **only when
     `elements.tracking` is on.** Off, the frame stays put — but the file must
     still EXIST: the template imports it statically and the bundle fails to
     build without it ("track.json doesn't exist" out of webpack, not a runtime
     warning). Write a neutral one instead: every point pinned to the camera
     target, so the follow has nothing to correct.
     ```bash
     python - <<'EOF'
     import json, pathlib
     ed = json.loads(pathlib.Path('public/edit-data.json').read_text())
     n = round(ed['durationSec'] * ed['fps'])
     tx, ty = ed['camera']['targetX'], ed['camera']['targetY']
     pathlib.Path('public/track.json').write_text(json.dumps(
         {"fps": ed['fps'], "width": ed['width'], "height": ed['height'],
          "count": n, "points": [[tx, ty]] * n, "neutral": True}))
     EOF
     ```
   - `public/segments.json` — cumulative cut boundaries **measured from the
     encoded segments' frame counts, never summed from the EDL's seconds**.
     **Regenerate it after EVERY Phase-1 re-render.** A stale segments.json is
     invisible: the render succeeds, the overlays look plausible, and every cut
     is off by a frame or three. Measured on this project after a re-grade — the
     file still carried EDL-summed times and drifted +1 frame by the 3rd cut and
     +3 by the 20th, while `VIDEO_LAG` quietly absorbed the first frame of it and
     made the error look fixed. The mechanism: ffmpeg quantises each segment to
     whole frames, so EDL arithmetic drifts a fraction of a frame per cut and the
     error ACCUMULATES. Anything that must land on a cut then sits visibly early.
     ```bash
     python - <<'EOF'
     import subprocess, glob, json, pathlib, sys
     def frames(f, count=False):  # header nb_frames, or decode-and-count for cut.mp4
         k = "nb_read_frames" if count else "nb_frames"
         return int(subprocess.run(["ffprobe","-v","error","-select_streams","v:0",
             *(["-count_frames"] if count else []), "-show_entries",f"stream={k}",
             "-of","default=nw=1:nk=1",f], capture_output=True, text=True).stdout)
     edl = json.loads(pathlib.Path("edl.json").read_text())
     jt = edl.get("jcut_timeline")
     # THREE sources that must agree: the J-cut plan, the segment files on disk and
     # the decoded cut.mp4. Globbing alone is only as good as the directory — a
     # re-render with fewer ranges once left old segments behind and gave
     # segments.json 9.23s for a 7.57s video. `_v.mp4` only under a J-cut: the
     # video-only takes are what the picture is concatenated from.
     segs = sorted(glob.glob("clips_graded/seg_*_v.mp4" if jt else "clips_graded/seg_*.mp4"))
     if len(segs) != len(edl["ranges"]):
         sys.exit(f"{len(segs)} segments for {len(edl['ranges'])} ranges — clips_graded is dirty")
     per = [frames(f) for f in segs]
     if jt:
         if "video_frames" not in jt[0]:
             sys.exit("jcut_timeline predates frame-exact J-cut — re-render Phase 1")
         plan = [j["video_frames"] for j in jt]
         if plan != per:
             sys.exit(f"jcut_timeline {plan} != segment files {per} — re-render Phase 1")
     real = frames("cut.mp4", count=True)
     if sum(per) != real:
         sys.exit(f"segments sum {sum(per)}f != cut.mp4 {real}f — do not ship this file")
     fps, cum = 30, [0]  # fps: match cut.mp4
     for n in per:
         cum.append(cum[-1] + n)
     json.dump({"segments": [{"start": round(cum[i]/fps,4), "dur": round(per[i]/fps,4)}
                             for i in range(len(per))]},
               open("remotion/public/segments.json","w"), indent=2)
     EOF
     ```
     Under a J-cut the `start`s equal `jcut_timeline[i].video_start_frame / fps`.
     Before the frame-exact fix in `render.py` they did not: `-ss` + `-r 30`
     duplicated the first frame of some takes (149 frames for a planned 148), the
     `_v` files summed to 2110 while `jcut_timeline` said 2105, and the mux then
     cut the picture to 2102 — the old sum assertion caught it, correctly.
   - **VERIFY segments.json against the picture — do not trust it.** `scdet`
     scores every frame by how much it differs from the one before, so a hard
     cut is a spike. The spike frame in `cut.mp4` must equal
     `round(segments[i].start * fps)`:
     ```bash
     ffmpeg -v info -i cut.mp4 -vf "select='between(n,344,358)',setpts=N/30/TB,scdet=threshold=0" \
       -an -f null - 2>&1 | grep scd.score
     ```
     In the RENDER the same cut lands one frame later — that is the
     `OffthreadVideo` lag `VIDEO_LAG` exists for. Both numbers together are the
     proof: cut spike at frame F in cut.mp4, at F+1 in the render, overlay
     window opening at F+1.
   - `pexels_search.py "<query>" --out-dir public/pexels --count 3 --orientation portrait`
3. **Write `public/edit-data.json`** — the whole edit in one file (schema in
   `assets/shortform/README.md`): durationSec (exact ffprobe of cut.mp4),
   camera zooms, hook lines/logo/sign, captions config, inserts[], behind[],
   soundtrack (leave `enabled:false` until Phase 3).
4. **Verify with stills, batched:** `npx remotion still Reels --frame=<n> f.png`
   for the hook still (user approval), then ONE contact sheet for spot checks:
   `contact_sheet.py <render> --times t1 t2 t3 -o sheet.png` — one image, not N.
5. **Render:** `npx remotion render Reels out/render.mp4`, then loudnorm →
   `edit/final.mp4` (see Phase 3).

Never edit `src/Main.tsx`. Bespoke graphics go in `src/CustomGraphics.tsx`
(the ONE editable file — read it only when the video needs a custom graphic).

## Headline styles — always two lines

Four looks via `hook.style`, picked by the user on the Estilo tab: **`outline`**
(default, white + thick black stroke), **`card`** (dark rounded card, UPPERCASE,
optional logo row), **`realce`** (each line on a solid accent marker block),
**`misto`** (line 1 light white, line 2 heavy accent).

### The accent colour (`accent` in preview_style.json)

`realce`, `misto` and the `stacked` caption are the only things that paint an
accent; the default is `#ff5200`. The user picks it on the Estilo tab and it
arrives as a hex — set it on **`hook.accent`** and **`captions.accent`** in
edit-data.json so headline and caption stay the same colour. `preview_style.json`
also carries `accentUsed`: when it is `false`, the picked styles have no accent
and the colour is not a request to find somewhere to put one.

Hardcoding `#ff5200` anywhere in the template re-breaks this — the preview will
show the user's colour and the render will show orange, which is worse than not
offering the choice.

**Author `hook.text` as one plain sentence.** Whatever you write — `text`, or a
hand-broken `lines[]` — is joined and re-broken into exactly TWO lines balanced by
MEASURED width, then the size is fitted to the widest one. A third line shrinks
the type and costs the glance the headline exists to win.

- The break is measured, not counted: "É assim que vai" (4 words) and "ficar a sua
  headline" (3 words) are nearly the same width. Counting words breaks it wrong.
- **`fontSizePx` is a CEILING, not a fixed size.** As a hard override it defeats
  the whole feature: at a size the text cannot fit in, the line wraps and you are
  back to three lines. Measured, not guessed — the uppercase `card` style did
  exactly that at an inherited `fontSizePx: 66`.
- Per-style geometry (weights, cap, safeWidth, lineHeight, paddingTop) lives in
  `HL_STYLES` in `src/Main.tsx` **and is mirrored in the preview's `app.js`** so
  the Estilo tab shows the real break at the real size. Change one, change both.
- In a split layout, `paddingTop` still has to follow the seam — see the split
  section.

## Caption style — six of them

Three are animated (karaoke, stacked, scatter) and three are STATIC
(`simples`, `serifada`, `classica`) — no animation at all, a cue just replaces
the previous one. All three static ones live in `SimpleCaptions.tsx`, read
`captions.json` alone, and share one rule that is the whole point:

**Lines group by MEASURED WIDTH, capped at `maxWords` — never by word count.**
"inteligência" and "de" cannot obey the same rule: the long word takes the line
alone and the short ones ride together. A fixed 3-words-per-line gets this
backwards on every long word.

- `simples` — Poppins 600 at 66, squeezed to 0.9 on BOTH axes, one line, ≤3 words.
  Poppins ships no condensed cut, so this is a distorted regular: it thins the
  stems in both directions. If it ever reads too light, raise the weight to 700
  rather than compressing further.
- `serifada` — Libre Baskerville 700 at 67, same rules, no distortion.
- `classica` — Inter 500 at 42, TWO lines, classic subtitle. The split is width
  balance PLUS a penalty for ending a line on a short function word ("o", "de"),
  which a pure balance does constantly and no real subtitle ever does.
- **The horizontal squeeze changes the line grouping** (narrower glyphs → more
  words fit); the vertical one does not (grouping is measured on width). Worth
  knowing before "just squashing it a bit".
- All three sit at `bottom: 430`, the same band as the others. Lower than that
  and a 9:16 caption lands under the platform's own UI.

### karaoke (default), STACKED or SCATTER

Short-form ships two caption styles. **The user already picked one on the Estilo
tab**, where both previews run the real animation — do not ask again, just set
`captions.style` from `preview_style.json`. (`caption-styles/stacked.png` is
still there as a montage over real footage if a still is useful.)

- **`"karaoke"`** (default): one line ≤3 words, Poppins Black, lower third.
- **`"scatter"`** ("Disperso"): Lora serif, lowercase, off-white with a slight
  darkening toward the baseline, one word at a time in short ragged lines. Reads
  `captions.json` alone — no extra generation step. Ordinary words FADE only; one
  word per cue (the longest, ≥7 chars) resolves out of a heavy blur at 1.62× and
  dissolves back into blur on the way out. Tunables in `captions`:
  `scatterOffsetY` (block centre, default 0.72), `scatterFontSize` (58),
  `scatterSafeWidth` (820); `SPREAD` in the component caps how far a line wanders.
  Three things it took real footage to learn:
  - **Never `Math.random()`.** Remotion renders frames independently, so a true
    random re-rolls the layout every frame and the text shakes. Positions are
    hashed off the cue index.
  - **The middle of the frame is the FACE.** The reference look lives over B-roll;
    on a talking head the block belongs on the chest (`scatterOffsetY` 0.72).
    Raise it only when the shot behind is not a face.
  - **Motion on every word is motion on nothing.** Ordinary words used to drop in
    from above too, and at one word per ~200ms the screen read as frantic. The
    blur on the highlighted word only reads because everything else is still.
- **`"stacked"`**: words stacked tight, mixing per line — Poppins bold-italic
  (white→gray gradient) / Poppins regular (smaller) / Playfair serif bold-italic
  in ORANGE `#ff5200` / Poppins bold. Emphasis words appear solo; key ones get a
  hand-drawn green pencil ellipse. **Baked SFX** (no extra step, no Premiere): a
  **click** on every solo word, a **scratch** when a word is circled.

For stacked, the ONE extra data step is the director (reads the same cut
transcript as `captions_for_remotion.py`):
```bash
uv run python helpers/caption_style.py --transcript <edit>/transcripts/cut.json \
    -o remotion/public/caption-cues.json
```
Then set `captions.style:"stacked"` in edit-data.json (keep the other caption
fields — they stay valid). Defaults match the user-approved look: the stack sits
~15.6% of the height below center and SFX play from `public/sfx/caption-click.mp3`
+ `caption-scratch.mp3` (both already in the template). Optional overrides inside
`captions`: `stackedOffsetY` (0–1 of height), `fontScale`, and
`sfx:{enabled,clickVolume(0.45),scratchVolume(0.16)}`. The director groups words
into short cues, gives the orange serif accent to the content word (never a
connective), keeps 1-letter/short connectors from standing alone, and flags
solo/circled words. It is language-tuned for pt-BR (`--lang`); for other
languages it falls back to length heuristics.

A solo word also needs DURATION, not just weight — a word spoken in under
`MIN_SOLO_MS` (340ms) renders as a one-frame flash and reads as a glitch, so the
director folds it into a neighbouring stack instead. Fast connective speech hits
this often. After generating cues, sanity-check the plan (it prints a summary):
every non-`STACK_MIXED` cue should span ≥0.34s, and the word list across all
cues must match the transcript exactly, in order.

## Visual hook — static headline, first ~4s (always on)

The first 1–2 seconds decide the swipe. Write `hook.lines` like a
social-media/copywriting/virality specialist, not a summarizer: read the cut
transcript, find the core promise/tension, and craft a scroll-stopper. Levers:
**curiosity gap · high stakes/bold claim · specificity/number · urgency ·
pattern interrupt**. Match the video's language; never clickbait it can't pay off.

**Two locked styles via `hook.style`** (both user-approved, encoded in the
template):
- **`"card"`** (default): Poppins Black white UPPERCASE on a dark-gray `#232326`
  rounded card, **every line the same font size (~54)** — never a big hero line +
  smaller kicker. Optional row above the card: real brand logo (rounded card,
  w300) + transparent symbol (drop-shadow, w128) — prefer real assets in
  `public/brand/` over drawn SVG; pick a symbol that frames the angle (danger,
  money, trophy…).
- **`"outline"`**: white text + thick black stroke (`WebkitTextStroke` +
  `paintOrder:'stroke fill'`), **no card**, **sentence-case** (write `lines[]`
  normally, not caps), sits lower (`paddingTop` ~330 — may overlap the top of the
  head, which is fine). The TikTok/MrBeast headline look. Tune `fontSizePx` (51),
  `strokePx` (7), `paddingTop` (330), `lineHeight` (1.06). Drop logo/sign.

Both are static hold, fade+rise at the edges, soft whoosh.

Example (Claude Fable video): "A IA MAIS / PERIGOSA DO MUNDO / ACABOU DE SER
LIBERADA". Draft 2–3 copy candidates in chat (text — no renders), let the user
pick, then render ONE still for design approval before the full render.

**De-conflict:** the hook owns the upper zone for its window — push any insert
that wants the same zone to after `hook.endSec` (e.g. move a 2.5s cutaway to
~4.1s).

## Flash na transição (`elements.flashCut`)

A transition accent on a cut, with a dry click. When the box is ticked, the
user picks three things under it on the Estilo card (`preview_style.json` →
`flash`). **Build exactly those. Never fall back to a default look they did
not choose.**

| Pick | Values | In `edit-data.json` |
|---|---|---|
| **Tipo** `kind` | `white` Flash branco (dip to white) · `beam` Feixe de luz (diagonal beam + bloom) · `zoom` Zoom burst (radial streaks) · `glitch` (RGB slices) | `transitionStyle.kind` |
| **Força** `strength` | `sutil` 7f · `media` 10f · `forte` 14f (window, lead 2/3/4f, peak 0.6/0.85/1) | `transitionStyle.strength` |
| **Onde** `where` | `beats` every cut where the EDL `beat` changes · `layout` every split-insert entry · `all` every cut | which cuts go into `transitions[]` |

```json
"transitionStyle": {"kind": "white", "strength": "media"},
"transitions": [{"at": 7.0}, {"at": 17.9}, {"at": 36.9}]
```

`at` is the cut time **exactly as segments.json states it**. `VIDEO_LAG` lines
it up with the frame the picture changes on, the same as the split windows.
Never index it off its own clock. `beats` is the default and usually right: a
flash marks a turn in the script (problem → solution → example → CTA), so
~5 on a 60s Reel. `all` on a 20+ cut video reads as a strobe; say so if they
pick it. Optional per entry: `kind` / `intensity` override, `sfx`, `volume`.

Why the picks exist: an edit once shipped with 6 beam flashes of 7 frames,
three of them at 0.7. They were on the video, and the user still asked why
there was no flash. The window and the peak are now tied to a strength the
user saw on screen.

- **The beam LEADS the cut by 2 frames.** Starting it on the cut frame reads as a
  flash after the fact — the eye sees the picture change, then the light. Leading
  it makes the light look like the cause.
- **Blur is what separates a beam from a wash.** At 26px it read as a general
  brightening; 16px reads as a beam. Raise opacity and lower blur together.
- **CHECK THE SFX FILE BEFORE TRUSTING IT.** The pack's `click2.mp3` peaks at
  −25 dB — it is inaudible under speech at any sane volume, and the mix looks
  fine while nothing is heard. `ffmpeg -i <sfx> -af volumedetect -f null -` is
  the check. `cut-click.mp3` (−2 dB, 57ms) is the one that reads.
- **And check WHERE the transient sits inside the file.** The source this click
  came from had 180ms of silence before the hit; delayed to the cut it would have
  landed 180ms late — after a 230ms effect had already finished. Trim the lead-in
  so the transient is at t=0, then delay by the cut time.
- **The delivered click is mixed by ffmpeg, not by Remotion.** The delivery
  re-mux discards Remotion's audio (it drifts), so add the SFX as another input
  with `adelay=<frame/fps*1000>`. The `<Sfx>` in the component only sounds in a
  plain `remotion render`.

## Style: "Limpa" (`edit: "limpa"`) — no split inserts

The whole frame stays on the speaker. **Leave `splitInserts` out of
`edit-data.json` entirely** (an empty array is fine; a populated one is not) and
skip the split director step. Everything else is unchanged — captions, hook,
zoom, tracking, soundtrack and behind-the-subject all still apply, and they are
where the edit gets its life when there is no art on screen.

Two consequences of the frame never being split, both easy to miss:

- **The hook keeps its full-frame padding.** `hook.paddingTop` is tuned per split
  layout (738 / ~920 for a seam that does not exist here). Under `limpa` the
  headline places against the frame, not a seam — start from the template default
  and render one still, rather than carrying a split value over.
- **`captions.windows` has nothing to dodge.** Those entries only exist to move
  the caption off a split seam. Leave the array empty; a stale window from a
  previous render shoves the caption up for no reason.

**This is the default** (`STYLE_CATALOG.edits[0]`), so it is also what a user who
never opens the Estilo tab gets. Split inserts are opted INTO, not out of. It is a
legitimate final look — a talking-head cut, images to be placed by hand later, or
simply no B-roll worth showing — not a placeholder.

## Style: "tela dividida" (split screen) — two variants

Both pin the FACE to a fixed region and give the rest of the frame to the image.
Data lives in `edit-data.json` `splitInserts[]` (`layout: "top" | "bottom"`); the
component is already in the template's `CustomGraphics.tsx`. Hard cut (no fade),
every window snapped to a take cut, consecutive images contiguous, and
`captions.windows` moves the caption to the seam while a window is up. The
`stacked` caption ignores `paddingBottom`. Give each window a
`stackedOffsetY` instead (≈ `-0.125` puts the stack on a 750px seam), or it
lands on the speaker's face. It is decided per cue midpoint, so a cue never
jumps mid-word. Full rules
in `assets/shortform/README.md`.

`splitInserts[].src` accepts images and `.mp4`/`.mov`/`.webm` video. Each video
starts at frame zero of its own window and loops when necessary. Never use the
window's absolute timeline frame as the insert's `startFrom`; that seeks beyond
short clips and freezes them. The re-framed `cut.mp4` is the opposite: it receives
the window start as its offset so its local clock stays aligned with the global
talking-head picture.

| | **Tela dividida** (`top`) | **Tela dividida 2** (`bottom`) |
|---|---|---|
| Art | top band (750) | bottom band (750) |
| Head | raised underneath, `zoom 1.25 / focusY 400` | held high above, `zoom 1.0 / focusY 225` |
| Caption | ON the seam (`paddingBottom` 1074) | just ABOVE the seam (`paddingBottom` 790) |
| Seam gradient | yes — the caption sits over the art | **no** — it only greys the top of the photo |

**`focusY` is a SOURCE y that lands at the top of the video window** — a point
`y_src` renders at `(y_src - focusY) * zoom`. **Measure before trusting the
numbers:** pull a frame out of `cut.mp4`, read the hair-top and chin y, and set
`focusY` so the head lands where the user asked. The defaults fit a head ~660px
tall starting at y 455.

The two are opposites in one specific way, and it is the whole trick: the source
has a lot of headroom above the head. `top` has to zoom in to throw that headroom
away; `bottom` **keeps** it, and that is what puts the face under the frame edge
instead of in the middle. Swapping the zoom/focus pair between them breaks both.

**The hook does not transfer for free.** `hook.paddingTop` is tuned to the seam of
whichever layout is up: 738 for `top` (text on the seam under the art), ~920 for
`bottom` (text in the gap between chin and seam). Left at the `top` value, the
headline lands across the speaker's mouth. Render one hook still after switching.

## Behind-the-subject (element between person and background)

Puts an image or giant word(s) BEHIND the person. Great on medium/wide shots;
on tight close-ups anchor elements to the TOP (template already does). Needs
the matting extra: `uv sync --extra matting` (torch).

```bash
uv run python helpers/person_matte.py cut.mp4 -o remotion/public/fg_<name>.mov --start <s> --duration <d>
```

Then describe each window in `edit-data.json` `behind[]` (kind image/words,
matte file, start, dur, words with per-word `at` times). Gotchas the template
already encodes — do not re-learn them:
- ProRes 4444 `.mov` (libvpx silently drops alpha on some builds)
- source RGB composited with alpha, not RVM's `fgr` (halo otherwise)
- `<OffthreadVideo transparent>` or the matte renders opaque
- matte gets the same camera via `frameOffset` or the person drifts

Matte ONLY the windows you need — each file's frame 0 = its window start.

## Illustrative images

Pexels for generic concepts (key: `PEXELS_API_KEY`). For brands/people/specific
things, **Wikimedia Commons first** (`wikimedia_images.py` — no key, clean
licensing, prints license+author), then `google_images.py` (needs
`GOOGLE_API_KEY`+`GOOGLE_CSE_ID`, mind rights — pass `--rights cc`, flag
licensing to the user for logos/celebrities). Keep photographer credits.

**The user's own images come first.** Files dropped into the preview's **Mídia →
Projeto** land in `<edit>/media/` and are announced by `watch_edits.py`. They
are the user saying "use this here": prefer them over any search for the same
subject.

### Brand logos: library first, never altered

A logo is a registered mark. On screen it appears **exactly as the brand
publishes it**. You may scale it (keeping the aspect ratio), set it on a plain
neutral plate or card when contrast demands, and animate its position,
opacity or scale. You may never recolor, redraw, trace, re-typeset, crop it
into another shape, stretch it, add effects inside it or "clean it up". A
recreated logo is always wrong, even when it looks close.

For every brand the video names (hook card logo, split-screen art, inserts):

1. **Local library:** `uv run python helpers/brand_library.py find "<brand>"`.
   Exit 0 prints the file path. Copy that file into `remotion/public/brand/` and
   use it untouched. It is a normalized exact match on name, slug or alias,
   deliberately not fuzzy: the wrong company's mark is worse than a search.
   Try the spelling the transcript used and the official name.
2. **This edit's media** (`<edit>/media/`), if the user dropped the logo there.
3. **Not found?** Keep doing what the skill always did: find the **official**
   logo. Use the brand's press or media kit first, then Wikimedia Commons (the
   SVG, `wikimedia_images.py`), and only then other sources, with the license
   flagged to the user. Prefer SVG or a transparent PNG. Then **archive it** so
   the next edit skips the search:
   `brand_library.py add <file> --name "<Brand>" --aliases "<variants>" --source <url> --license "<terms>"`.
   Archive only a logo you are confident is official. A guess stays out of the
   library.

The library lives in `<skill>/library/logos/`. It belongs to the user: git
ignores it and the installer preserves it across updates. The **Marcas** shelf
in the preview shows it on a light checker, so the mark is seen as stored.

## Phase 3 — soundtrack (short-form)

The soundtrack is generated **locally and for free** with **ACE-Step 1.5**
(<https://github.com/ace-step/ACE-Step-1.5>). It is MIT-licensed, code and
weights, so the output can be used commercially. It needs no account, no key
and no credits, and runs on Apple Silicon (MLX), NVIDIA, AMD and Intel.
`helpers/music_local.py` drives it. The engine lives outside the skill in its
own uv environment (`$FMCUT_MUSIC_DIR`, default `~/.cache/fm-cut/ACE-Step-1.5`),
because its torch pin differs from WhisperX's.

### Soundtrack is part of the Fase-2 delivery (when `musicAI` is picked)

It is not a later phase the user has to ask for again. Picked on the Estilo tab
means it is IN the `final.mp4` you deliver at the end of Fase 2. This rule
exists because an edit once shipped silent: the music provider was only checked
after the render, and it failed.

1. **At the gate, in the same reply that acknowledges the picks:** run
   `uv run python helpers/music_local.py --check`. `watch_edits.py` already
   says whether the engine is installed. If it is not, start
   `music_local.py --setup` **in the background now**. The first time it clones
   the engine and downloads ~10 GB of models, and it runs while Fase 2 is being
   built. Tell the user in one line that the first use downloads the model.
2. **Write the vibe from the cut transcript, then generate the track IN PARALLEL
   with the Remotion render** (background). Use `--duration` = the edit's length
   + ~2s, and fix a `--seed` so a take the user liked can be reproduced.
3. **Mix it in the delivery mux** (recipes below): the voice source is
   `cut.mp4` or Remotion's own audio (see "Keeping Remotion's audio"), with
   `trilha.mp3` at `volume=0.0445`, a 0.4s fade-in and a 1.5s fade-out. Then
   loudnorm. The music never needs a Remotion re-render; `soundtrack.enabled`
   only matters for plain `remotion render` previews.
4. **Generation failed?** (no disk space, no network on the first download, an
   old Intel Mac without a usable GPU.) Deliver `final_sem_trilha.mp4`, say
   what failed in one line, and offer a local mp3. Never name a silent file
   `final.mp4` when `musicAI` was picked. Once the track exists, only the mux
   runs again, which takes seconds.

Without `musicAI`, ask: **AI-generated** (local, free) or **local file** (copy to
`public/trilha.mp3`). A local mp3 from the user goes through the same mux.

**Writing the vibe: derive it from the video's context, and ask for MUSIC, not
a texture.** Read the cut transcript: what are the topic, the energy and the
emotional arc? Then describe a real **composed instrumental piece**: name a
**genre + key instruments + tempo + mood**. Match the content: a hype tech/AI
reel wants modern electronic with a clear synth melody, a calm tutorial wants
warm lo-fi keys, a luxury or story piece wants cinematic strings. **Avoid
texture words** ("bed", bare "beat", "sound design", "drones", "risers"), which
pull the model toward ambience. `music_local.py` already frames the vibe as an
instrumental with melody and rhythm that sits under a voice (`--raw` skips the
framing), but the vibe you pass still has to read as music.
```bash
uv run python helpers/music_local.py "modern electronic, catchy synth melody, warm analog bass, crisp light drums, bright and motivational" \
  -o remotion/public/trilha.mp3 --duration 72 --bpm 110 --seed 42
```
For a plain `remotion render` preview, flip `soundtrack.enabled: true` in edit-data.json. **Volume:** start at
`0.0445`. This is the approved reference level: **−15 dB** from the former
`0.25` default (`0.25 × 10^(−15/20) ≈ 0.0445`). Confirm by listening, not just
by the meter, and only deviate when the source voice or composition clearly
demands it. The delivery mixes it in ffmpeg. Finish with the mandatory loudnorm:

**Take the PICTURE from Remotion and the AUDIO from `cut.mp4`.** Remotion's own
audio track drifts against the source — measured on a 95s edit: the voice is
+90ms late by 8s and +660ms by 78s, i.e. it slides progressively out of lip sync,
unnoticeable at the start and obvious by the end. Its audio track also comes out
~0.7s longer than its video. So never re-encode Remotion's audio; re-mux the
approved master instead and mix the soundtrack here:

**Remotion's picture is FULL-RANGE and mis-tagged — never `-c:v copy` it.** Its
output is `yuvj420p`, `color_range=pc`, `color_primaries=bt470bg` (PAL!), transfer
unknown. Measured: luma 0–255 where `cut.mp4` sits at 16–235. Copying the stream
carries all of that into the delivery, so a compliant player shifts the hue off the
PAL primaries and a player that ignores the range tag crushes the blacks — the
Phase-1 grade the user approved drifts at the very last step. Convert the range and
stamp the tags. `setparams` is what makes them stick: the bare `-color_primaries` /
`-color_trc` output flags silently leave both `unknown` here.

```bash
VD=$(ffprobe -v error -select_streams v:0 -show_entries stream=duration -of default=nw=1:nk=1 out/render.mp4)
FADE=$(python3 -c "print(f'{$VD-1.5:.3f}')")
ffmpeg -y -i out/render.mp4 -i ../cut.mp4 -i public/trilha.mp3 \
  -filter_complex "[0:v]scale=in_range=full:out_range=limited,format=yuv420p,\
setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709:range=tv[vid];\
                   [1:a]adelay=33:all=1[v];\
                   [2:a]volume=0.0445,afade=t=in:st=0:d=0.4,afade=t=out:st=$FADE:d=1.5[m];\
                   [v][m]amix=inputs=2:duration=first:normalize=0[mix];\
                   [mix]loudnorm=I=-14:TP=-1:LRA=11[out]" \
  -map "[vid]" -map "[out]" -c:v libx264 -preset slow -crf 17 -pix_fmt yuv420p \
  -colorspace bt709 -color_primaries bt709 -color_trc bt709 -color_range tv \
  -c:a aac -b:a 192k -ar 48000 -t "$VD" -movflags +faststart ../final.mp4
```

**Verify the delivery carries the same tags as the cut** — `bt709 / bt709 / bt709 /
tv`, exactly what left Phase 1:
```bash
ffprobe -v error -select_streams v:0 \
  -show_entries stream=color_space,color_primaries,color_transfer,color_range \
  -of default=nw=1 ../final.mp4
```

**Keeping Remotion's audio is sometimes the right call — measure, don't assume.**
The re-mux above exists because Remotion's audio drifts, and on a 95s edit it does
(+660ms by 78s). But the `stacked` caption bakes a click on nearly every word plus
the flash clicks, and the re-mux throws all of that away — reconstructing ~20 SFX
by hand from the cue file is guesswork. Correlate first (15s+ windows, or the whole
clip when it is short): if the offset is CONSTANT across start/middle/end there is
no drift, and Remotion's own audio keeps the SFX with the sync intact. Measured on
a 7.6s edit: +42.7ms at the head, the tail and the whole — constant, and only ~10ms
from the picture's own +33ms lag. There, `-map 0:a` through the same loudnorm beats
the re-mux. Say which one you used and why.

`adelay=33` is one frame at 30fps: OffthreadVideo draws the source frame one
composition frame late (the same VIDEO_LAG the overlays compensate for), so the
picture sits a frame behind cut.mp4's timeline and the voice must follow it.
`-t "$VD"` keeps the audio from outliving the video. **Verify** by correlating the
delivered voice against `cut.mp4` at three points — the offset must be CONSTANT
(≈+33ms). Use 15s windows: short windows lock onto the wrong syllable and report
a drift that is not there. Drop this re-mux ONLY if Phase 2 baked SFX into the
audio (stacked captions' click/scratch), and then verify sync by hand.

**Remotion audio + soundtrack** (stacked captions / flash SFX kept, offset measured
constant). Apply the same range fix on the picture as above; the trilha rides under
Remotion's mix:

```bash
[0:a][2:a]…  →  [2:a]volume=0.0445,afade=t=in:st=0:d=0.4,afade=t=out:st=$FADE:d=1.5[m];
               [0:a][m]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-14:TP=-1:LRA=11[out]
```

If the last spoken word runs past the picture (J-cut tail), crossfade the tail of
`cut.mp4`'s audio (delayed by the measured offset) onto Remotion's audio before the
amix, and hold the last frame with `tpad=stop_mode=clone`. Otherwise the final
syllable gets cut.

If the video has no soundtrack, the same shape without input 2:

```bash
ffmpeg -y -i out/render.mp4 -i ../cut.mp4 -filter_complex "[1:a]adelay=33:all=1,loudnorm=I=-14:TP=-1:LRA=11[out]" \
  -map 0:v -map "[out]" -c:v copy -c:a aac -b:a 192k -ar 48000 -t "$VD" -movflags +faststart ../final.mp4
```

Verify `max_volume ≤ -1 dB` (`-af volumedetect`). Copy to `edit/final.mp4`.

---

## The Estilo tab (between Fase 1 and Fase 2)

The cut is approved and nothing about the LOOK of Fase 2 is decided yet. **Do not
ask the style questions in chat** — set `"awaitingStyle": true` in `state.json`
and the UI opens its own tab, sitting between FASE 1 and FASE 2:

- **Tipo de edição** — `limpa` ("Limpa": no split inserts, full frame throughout —
  **the default**, and the right pick for a talking-head cut or when the user will
  place images by hand later), `split` ("Tela dividida"), `split2` ("Tela
  dividida 2").
- **Cor de destaque** — `accent`, a hex. Sits BEFORE the text styles, because it
  is what they paint with. One spectral swatch (the OS picker) plus a hex field,
  synced both ways — no preset row. Only `realce`/`misto` headlines and the
  `stacked` caption paint an accent, so the save also carries **`accentUsed`**;
  when it is `false` the picked styles have none and the colour is not an
  instruction to invent a place for one.
- **Estilo de headline** — `outline`, `card`, `realce`, `misto`. Always two
  lines, size fitted to the text (see the track reference).
- **Estilo de legenda** — three animated (`karaoke`, `stacked`/"Empilhado",
  `scatter`/"Disperso") and three static (`simples`, `serifada`, `classica`).
- **Elementos da edição** — checkboxes: `tracking` (movimento de tracking),
  `zoomAuto` (automação de zoom in), `zoomCuts` (zoom in/out nos cortes),
  `flashCut` (flash na transição), `musicAI` (trilha sonora com IA), plus a
  free-text observation field.

Saving writes `<edit>/preview_style.json` (its OWN file — a style pick and a
timeline correction are different screens at different moments, and one shared
file would clobber the other) and `watch_edits.py` notifies you with the picks,
**what was left out**, and the observation. Then: build Fase 2 from exactly those
choices, **copy them into `state.json` as `style`**, clear `awaitingStyle`, and
delete `preview_style.json`.

Writing `style` back is not bookkeeping — it is what keeps the tab open. The tab
is enabled while `awaitingStyle` OR `style` is set, so the user can return, change
a caption style or tick one more element, and save again. That save arrives with
`"rerender": true` and the watcher says **REFAÇA a Fase 2** — re-render with the
new choices, don't treat it as a first pick.

**The catalog lives in `STYLE_CATALOG` (app.js), not in a session.** A new editing
or caption style is one entry there plus its implementation in the track
reference; adding it in chat only, for one project, makes it invisible to every
other project. What is in it today is the **short-form** vocabulary (tela
dividida, karaokê/empilhado) — on a longform job the gate has nothing to offer
yet, so skip `awaitingStyle` and ask the layer questions in chat until longform
entries exist here.

---

## Anti-patterns (Fase 2/3)

These moved out of SKILL.md: they only bite after the phase gate, and the
skill prompt is resent every turn.

- Asking the style questions in chat, or starting Phase 2 before the pick lands.
  The gate screen exists so the user SEES what each style does — a chat list of
  names asks them to choose blind. Set `awaitingStyle` and wait for
  `preview_style.json`.
- Treating an unchecked element as "não pediu". It is an explicit NO: the user
  looked at "Movimento de tracking" and left it off. `watch_edits.py` prints the
  `fora:` line for exactly this reason.
- Hardcoding `#ff5200` (or any accent) in the template. The Estilo tab lets the
  user pick it, so a literal makes the preview show their colour and the render
  show orange — worse than not offering the choice. Feed `accent` into
  `hook.accent` + `captions.accent`.
- Changing a caption's look in the template without changing its preview in
  `app.js` (`buildKaraokeDemo` / `buildStackedDemo`). The gate's previews render
  the real faces, sizes and motion, scaled from 1080-wide — that is the whole
  reason the user can choose by looking. A preview that lies about the style is
  worse than no preview.
- Hardcoding a bespoke graphic's timings inside `CustomGraphics.tsx`. Put the
  windows in an `edit-data.json` array (a key the template ignores, e.g.
  `splitInserts`) and map over it — otherwise the graphic is invisible to the
  preview timeline and the user cannot see or retime it.
- Re-rendering Phase 1 without regenerating `segments.json`. Every Phase-2
  overlay that must land on a cut is indexed off that file; stale, it is off by
  frames and nothing errors. Worse, a `VIDEO_LAG`-style constant can absorb the
  first frame of the drift and make a broken file look correct at the one
  boundary you happen to check.
- Delivering Phase 2 with Remotion's own audio track — it drifts progressively against the source (+0.66s by 78s on a 95s edit). Re-mux `cut.mp4`'s audio and mix the soundtrack in ffmpeg (recipe in the track reference).
- Judging A/V sync with short correlation windows — speech is quasi-periodic and a 2–3s window happily locks onto the wrong syllable, inventing a drift. Use 15s+ windows, and remember a PARTIAL render cannot show drift that accumulates over the full timeline.
- Indexing Phase 2 off `Σ(end−start)` when a `jcut_timeline` exists — the J-cut output is shorter, so everything after the first take lands late.

---

## Helpers de Fase 2/3

- **`captions_for_remotion.py`** (karaoke JSON) · **`face_track.py`** (eye-track JSON) · **`person_matte.py`** (RVM alpha matte; `uv sync --extra matting`) · **`pexels_search.py`** · **`wikimedia_images.py`** (no key, brands/people first choice) · **`google_images.py`** (fallback, mind rights) · **`captions_srt.py`** (longform .srt) · **`chapters.py`** (YouTube chapters) · **`music_local.py`** (free local AI soundtrack with ACE-Step 1.5: `--check`, `--setup`, or `"<vibe>" -o trilha.mp3 --duration N`. Pass a MUSICAL vibe (genre + instruments + tempo + mood); it is auto-framed as an instrumental under a voice).

---

## Chaves opcionais (nunca pedidas na instalação)

Nada aqui é necessário para instalar, para a Fase 1 ou para a trilha. A trilha
com IA é local e gratuita (ACE-Step 1.5), sem conta. Peça UMA chave só no
momento em que o recurso for de fato usado, explique para quê e escreva em
`.env` na raiz da skill, nunca em `<videos_dir>`. Se o usuário não quiser, siga
pelo caminho sem chave e diga o que muda.

| Chave | Recurso | Sem ela |
|---|---|---|
| `PEXELS_API_KEY` | imagens/vídeos ilustrativos | Wikimedia Commons cobre a maioria |
| `GOOGLE_API_KEY` + `GOOGLE_CSE_ID` | marcas, pessoas e logos específicos | Wikimedia é o fallback |

Ao receber uma chave: grave no `.env`, confirme em uma linha e **nunca repita
a chave de volta** na conversa nem em saída de ferramenta.

A instalação não menciona nenhuma delas de propósito: a skill não precisa de
chave para funcionar, e listar chaves no primeiro contato faz parecer que precisa.
