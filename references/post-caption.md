# PHASE 3 — Publication caption (always the last step)

Read this after `final.mp4` is rendered. Every edit ends with the text the video
is published with: per-network caption, title where the network has one,
hashtags and search keywords. It lands in the **Postagem** tab of the preview,
where the user edits it, toggles hashtags and copies it straight into the app.

There is no gate in front of it. You just watched every second of the video and
know its promise better than anyone, so write it right after the final render,
in the same turn that reports the delivery. It is short, and it is what the user
would otherwise have to write alone at posting time.

## Inputs, in this order

1. **The user's own content rules win.** If the user has a skill for their
   profile or brand (a brand-voice guide, a content playbook, a caption
   template), read its caption format, CTA funnel and base hashtags first. It overrides every default below.
   A caption that ignores the profile's funnel is wrong even when it reads well.
2. **The corrected cut transcript.** Use the text you fixed for the on-screen
   captions (product names, "IA" instead of "ar"), not the raw Whisper output.
3. **The hook headline** in `edit-data.json`. The caption's first line carries
   the same promise in different words. Repeating the on-screen text verbatim
   wastes the one line people read before "…mais".
4. **Anything you verified in Phase 2**, such as product names and what a tool
   actually does. Use the same spelling as on screen.

## Per network

| Network | `limit` | Shape |
|---|---|---|
| Instagram Reels | 2200 | Line 1 is the hook, ≤125 characters: it is all that shows before "…mais". Then 2–4 short lines of value (the one takeaway, the concrete names and facts from the video), then ONE primary CTA. Weave the search keywords into the sentences, because Instagram search reads captions. Hashtags go after a blank line. |
| TikTok | 4000 | 1–3 lines. Hook, then a question that invites a comment, then the CTA. 3–5 hashtags. |
| YouTube Shorts | description 5000 · `titleLimit` 100 | **Title** with the main keyword up front, ~40–60 characters. Description of 2–3 lines. Its first 3 hashtags show above the title. |
| LinkedIn | 3000 | Only when the user publishes there. A hook line, then 3–6 short paragraphs with a declared opinion, ending on a question. ≤5 hashtags. |

Default set: Instagram, TikTok, YouTube Shorts. Add LinkedIn when the profile
skill or the user says they post there.

**Hashtags.** Relevant beats popular. Mix broad, mid-size and niche tags, and
include the profile's own base tags when its skill defines them. Never pad with
generic tags just to fill space.

**Keywords.** 5–8 terms someone would actually type into search to find this
video, e.g. "segurança de agentes de IA" or "NVIDIA OpenShell". They show as
chips in the tab and should already appear inside the captions.

## Hard lines

- **Every factual claim traces back** to the video or to a source you checked.
  The caption must not promise more than the video delivers.
- **No template copy.** No "Transforme seu negócio", no wall of emoji, no
  "neste vídeo eu vou falar sobre". Use at most one or two emoji, and only if
  the profile uses them.
- **Write in the user's voice and language.** Use their pronouns ("a gente",
  "eu uso") and the register the video already has.
- **Do not repeat the CTA across networks mechanically.** Each network gets the
  action that works there: follow and save on Instagram, comment on TikTok,
  subscribe on YouTube.

## Output — `<edit>/post.json`

```json
{
  "version": 1,
  "keywords": ["segurança de agentes de IA", "NVIDIA OpenShell"],
  "notes": ["Linha 1 reescreve a headline com outra palavra — mesma promessa."],
  "platforms": [
    {"id": "instagram", "name": "Instagram", "limit": 2200,
     "caption": "…", "hashtags": ["#ia", "#agentesdeia"]},
    {"id": "tiktok", "name": "TikTok", "limit": 4000,
     "caption": "…", "hashtags": ["#ia"]},
    {"id": "youtube", "name": "YouTube Shorts", "limit": 5000,
     "title": "…", "titleLimit": 100, "caption": "…", "hashtags": ["#shorts"]}
  ]
}
```

- `caption` holds the text **without** hashtags. The tab appends the active ones
  when copying, so one toggle updates the count and the copy together.
- `title` is present only for networks that have one. Its presence is what
  shows the Title field.
- `notes`: 2–4 short lines on why the caption is shaped this way (hook angle,
  CTA choice, keyword placement), written for the user to read.

Then set `"post": "post.json"`, `"phase": 4` and a `message` in `state.json`.
The tab unlocks and hot-reloads by itself. In chat, give the Instagram hook line
and point to the tab. Do not paste all the captions into the chat, because the
tab is where they get edited and copied.

## When the user saves edits

The UI writes `<edit>/preview_post.json`
(`{type:"post-edits", platforms:[{id, caption, title?, hashtags, removedHashtags}]}`)
and `watch_edits.py` announces it. Copy `caption`, `title` and `hashtags` of
each listed platform into `post.json`, then delete `preview_post.json`. The
user's text wins; do not "improve" it back. If they asked for a change in chat
instead, edit `post.json` directly. The tab picks it up either way.
