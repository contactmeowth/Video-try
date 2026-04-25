# 🎬 AI Video Pipeline — Story/Narrative Generator

Automatically generates story videos with **AI images** + **Kokoro TTS narration** using **GitHub Actions** — completely free.

---

## 📁 Project Structure

```
ai-video-pipeline/
├── script.json              ← Your main story script
├── scripts/                 ← Additional scripts (episode2.json, etc.)
├── generate_video.py        ← Core pipeline script
├── requirements.txt
├── output/                  ← Generated videos land here
└── .github/
    └── workflows/
        └── generate_video.yml  ← GitHub Actions automation
```

---

## 📝 How to Write a Script

Edit `script.json`. Each scene has:

| Field | Description |
|---|---|
| `id` | Scene number (1, 2, 3...) |
| `type` | `"ai_image"` or `"static_bg"` |
| `image_prompt` | What to generate (for `ai_image` type) |
| `narration` | Full narration text — audio is generated for the whole scene |
| `voice` | Kokoro voice (see voices below) |
| `mood` | `epic` / `mysterious` / `tense` / `wonder` / `dramatic` / `reflective` |
| `transition` | `"fade"` or `"cut"` |
| `background_color` | Hex color for `static_bg` type |
| `overlay_text` | Text to display on `static_bg` scenes |

### Scene Types

**`ai_image`** — Pollinations AI generates an image from your prompt:
```json
{
  "id": 1,
  "type": "ai_image",
  "image_prompt": "A dark castle on a hill at night, moonlight, cinematic",
  "narration": "The castle had stood for five hundred years...",
  "voice": "af_heart",
  "mood": "mysterious",
  "transition": "fade"
}
```

**`static_bg`** — Solid color background with optional text overlay:
```json
{
  "id": 2,
  "type": "static_bg",
  "background_color": "#0a0a1a",
  "overlay_text": "Chapter 1: The Beginning",
  "text_style": "title",
  "narration": "Chapter one. The beginning.",
  "mood": "epic",
  "transition": "cut"
}
```

---

## 🎙️ Kokoro TTS Voices

| Voice ID | Style |
|---|---|
| `af_heart` | Warm female (default) |
| `af_bella` | Expressive female |
| `af_nicole` | Soft female |
| `am_adam` | Male narrative |
| `am_michael` | Deep male |
| `bf_emma` | British female |
| `bm_george` | British male |

Different scenes can use different voices — great for narrator vs character.

---

## 🚀 How to Run

### Locally
```bash
pip install -r requirements.txt
# Also needs: ffmpeg installed on your system

python generate_video.py                  # uses script.json
python generate_video.py scripts/ep2.json # specific script
```

### On GitHub Actions (Automatic)
1. **Push `script.json`** → workflow triggers automatically
2. **Manual trigger** → Go to Actions tab → "AI Video Pipeline" → "Run workflow"
3. Download the video from the **Artifacts** section of the run

---

## ⚙️ GitHub Secrets Required

| Secret | Value |
|---|---|
| `TG_TOKEN` | Your Telegram bot token |
| `USER_ID` | Your Telegram user/chat ID |

> Add them in: `Settings → Secrets and variables → Actions → New repository secret`

---

## 🎨 Workflow: How Each Video is Made

```
script.json
    │
    ▼
For each scene:
    ├── type=ai_image  → Pollinations AI → PNG image (free, no API key)
    └── type=static_bg → FFmpeg drawtext → PNG image

    ├── narration text → Kokoro TTS API → MP3 audio
    │                  (fallback: edge-tts if Kokoro fails)
    │
    └── image + audio → FFmpeg → scene clip (duration = audio length)

All clips → FFmpeg concat → final MP4
    │
    ├── Uploaded as GitHub Actions Artifact (download from Actions tab)
    └── Optionally committed to output/ folder in repo
```

---

## 💡 Tips

- **Narration drives duration** — scene length auto-matches your narration audio. Write more = longer scene.
- **Mix types** — use `static_bg` for chapter titles/transitions between `ai_image` scenes
- **Seed is scene ID × 42** — same script always generates same images (reproducible)
- **Free limits** — Pollinations has no rate limit for personal use; Kokoro public API is rate-limited, edge-tts kicks in as fallback

---

## 🔧 Customization Ideas

- Add **background music** by mixing an ambient audio track in the final concat step
- Add **subtitle/caption burns** via FFmpeg `subtitles` filter from an SRT file
- Generate **multiple episodes** by adding `scripts/ep2.json`, `scripts/ep3.json`
- Gemini API can **auto-generate the script JSON** from a story idea prompt
