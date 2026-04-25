#!/usr/bin/env python3
"""
AI Video Pipeline - Story/Narrative Video Generator
Generates scene images (Pollinations AI) + audio (Kokoro TTS) + stitches via FFmpeg
"""

import json
import os
import sys
import time
import subprocess
import textwrap
import requests
import argparse
from pathlib import Path
from urllib.parse import quote


# ─────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────

POLLINATIONS_URL = "https://image.pollinations.ai/prompt/{prompt}?width={w}&height={h}&seed={seed}&nologo=true&model=flux"
KOKORO_API_URL   = "https://api.kokorotts.com/v1/audio/speech"   # free public endpoint

WORK_DIR    = Path("workspace")
SCENES_DIR  = WORK_DIR / "scenes"
AUDIO_DIR   = WORK_DIR / "audio"
OUTPUT_DIR  = Path("output")

MOOD_MUSIC = {
    "epic":       "#1a0a00",
    "mysterious": "#0a0a1a",
    "tense":      "#1a0000",
    "wonder":     "#001a0a",
    "dramatic":   "#0d0005",
    "reflective": "#0a0a0a",
}

FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


# ─────────────────────────────────────────────
#  SETUP
# ─────────────────────────────────────────────

def setup_dirs():
    for d in [WORK_DIR, SCENES_DIR, AUDIO_DIR, OUTPUT_DIR]:
        d.mkdir(parents=True, exist_ok=True)

def log(msg, icon="▶"):
    print(f"\n{icon}  {msg}", flush=True)


# ─────────────────────────────────────────────
#  IMAGE GENERATION (Pollinations - Free)
# ─────────────────────────────────────────────

def generate_ai_image(scene: dict, resolution: str, out_path: Path):
    """Fetch AI image from Pollinations (completely free, no key needed)."""
    w, h = resolution.split("x")
    prompt = scene.get("image_prompt", "cinematic scene")
    seed   = scene.get("id", 1) * 42  # reproducible per scene
    url    = POLLINATIONS_URL.format(
        prompt=quote(prompt), w=w, h=h, seed=seed
    )
    log(f"Scene {scene['id']}: Generating AI image...", "🎨")
    print(f"   Prompt: {prompt[:80]}...")

    for attempt in range(3):
        try:
            r = requests.get(url, timeout=60)
            r.raise_for_status()
            out_path.write_bytes(r.content)
            log(f"Scene {scene['id']}: Image saved → {out_path}", "✅")
            return
        except Exception as e:
            print(f"   Attempt {attempt+1} failed: {e}")
            time.sleep(5)

    # Fallback to static bg if image fails
    log(f"Scene {scene['id']}: Image failed, using static fallback", "⚠️")
    generate_static_bg(scene, resolution, out_path)


def generate_static_bg(scene: dict, resolution: str, out_path: Path):
    """Generate a stylized static background using FFmpeg drawtext."""
    w, h    = resolution.split("x")
    color   = scene.get("background_color", MOOD_MUSIC.get(scene.get("mood", ""), "#0a0a0a"))
    text    = scene.get("overlay_text", "")
    style   = scene.get("text_style", "normal")

    log(f"Scene {scene['id']}: Generating static background...", "🖼️")

    if text:
        # Wrap text
        wrapped = textwrap.fill(text, width=40)
        escaped = wrapped.replace("'", "\\'").replace(":", "\\:").replace(",", "\\,")

        fontsize = 52 if style == "title" else 38
        vf = (
            f"drawtext=fontfile={FONT_PATH}:"
            f"text='{escaped}':"
            f"fontcolor=white:"
            f"fontsize={fontsize}:"
            f"x=(w-text_w)/2:"
            f"y=(h-text_h)/2:"
            f"line_spacing=12:"
            f"shadowcolor=black@0.8:"
            f"shadowx=2:shadowy=2"
        )
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"color=c={color}:size={w}x{h}:rate=1",
            "-vf", vf,
            "-frames:v", "1",
            str(out_path)
        ]
    else:
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"color=c={color}:size={w}x{h}:rate=1",
            "-frames:v", "1",
            str(out_path)
        ]

    subprocess.run(cmd, check=True, capture_output=True)
    log(f"Scene {scene['id']}: Static BG saved → {out_path}", "✅")


# ─────────────────────────────────────────────
#  AUDIO GENERATION (Kokoro TTS - Free)
# ─────────────────────────────────────────────

def generate_audio(scene: dict, out_path: Path):
    """Generate scene narration using Kokoro TTS public API."""
    text  = scene.get("narration", "")
    voice = scene.get("voice", "af_heart")

    if not text:
        log(f"Scene {scene['id']}: No narration, generating silence", "🔇")
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", "anullsrc=r=44100:cl=stereo",
            "-t", "2", str(out_path)
        ], check=True, capture_output=True)
        return

    log(f"Scene {scene['id']}: Generating Kokoro TTS audio...", "🔊")
    print(f"   Voice: {voice} | Text: {text[:60]}...")

    payload = {
        "model":  "kokoro",
        "input":  text,
        "voice":  voice,
        "speed":  0.95,
        "response_format": "mp3"
    }

    for attempt in range(3):
        try:
            r = requests.post(KOKORO_API_URL, json=payload, timeout=60)
            r.raise_for_status()
            out_path.write_bytes(r.content)
            log(f"Scene {scene['id']}: Audio saved → {out_path}", "✅")
            return
        except Exception as e:
            print(f"   Attempt {attempt+1} failed: {e}")
            # Fallback: edge-tts if installed
            if attempt == 2:
                log(f"Scene {scene['id']}: Trying edge-tts fallback...", "⚠️")
                _edge_tts_fallback(text, out_path)
                return
            time.sleep(5)


def _edge_tts_fallback(text: str, out_path: Path):
    """Use edge-tts as fallback if Kokoro fails."""
    mp3_tmp = out_path.with_suffix(".tmp.mp3")
    try:
        subprocess.run([
            "edge-tts",
            "--voice", "en-US-AriaNeural",
            "--text", text,
            "--write-media", str(mp3_tmp)
        ], check=True, capture_output=True)
        subprocess.run([
            "ffmpeg", "-y", "-i", str(mp3_tmp),
            str(out_path)
        ], check=True, capture_output=True)
        mp3_tmp.unlink(missing_ok=True)
        log("edge-tts fallback succeeded", "✅")
    except Exception as e:
        log(f"edge-tts fallback also failed: {e}", "❌")
        # Last resort: 3s silence
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", "anullsrc=r=44100:cl=stereo",
            "-t", "3", str(out_path)
        ], check=True, capture_output=True)


# ─────────────────────────────────────────────
#  GET AUDIO DURATION
# ─────────────────────────────────────────────

def get_audio_duration(audio_path: Path) -> float:
    """Get duration of audio file in seconds via ffprobe."""
    result = subprocess.run([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(audio_path)
    ], capture_output=True, text=True)
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 3.0


# ─────────────────────────────────────────────
#  SCENE VIDEO ASSEMBLY
# ─────────────────────────────────────────────

def build_scene_clip(scene: dict, img_path: Path, audio_path: Path, out_path: Path, resolution: str):
    """Combine image + audio into a scene clip. Duration matches audio length."""
    w, h     = resolution.split("x")
    duration = get_audio_duration(audio_path)
    # Add 0.5s padding at end for smoother transitions
    duration += 0.5

    log(f"Scene {scene['id']}: Building clip ({duration:.1f}s)...", "🎬")

    transition = scene.get("transition", "fade")
    vf_filters = [f"scale={w}:{h}:force_original_aspect_ratio=decrease",
                  f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:black"]

    if transition == "fade":
        # Fade in 0.5s at start, fade out 0.5s at end
        fade_dur = 0.5
        vf_filters.append(f"fade=t=in:st=0:d={fade_dur},fade=t=out:st={duration-fade_dur}:d={fade_dur}")

    vf = ",".join(vf_filters)

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", str(img_path),
        "-i", str(audio_path),
        "-vf", vf,
        "-c:v", "libx264",
        "-tune", "stillimage",
        "-c:a", "aac",
        "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-t", str(duration),
        "-shortest",
        str(out_path)
    ]

    subprocess.run(cmd, check=True, capture_output=True)
    log(f"Scene {scene['id']}: Clip ready → {out_path}", "✅")


# ─────────────────────────────────────────────
#  FINAL VIDEO CONCAT
# ─────────────────────────────────────────────

def concat_clips(clip_paths: list, output_path: Path):
    """Concatenate all scene clips into the final video."""
    log("Concatenating all scene clips into final video...", "🎞️")

    concat_list = WORK_DIR / "concat_list.txt"
    with open(concat_list, "w") as f:
        for clip in clip_paths:
            f.write(f"file '{clip.resolve()}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_list),
        "-c:v", "libx264",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        str(output_path)
    ]

    subprocess.run(cmd, check=True)
    log(f"Final video → {output_path}", "🎉")


# ─────────────────────────────────────────────
#  MAIN PIPELINE
# ─────────────────────────────────────────────

def run_pipeline(script_path: str):
    setup_dirs()

    with open(script_path, "r") as f:
        script = json.load(f)

    title      = script.get("title", "video")
    resolution = script.get("resolution", "1280x720")
    scenes     = script.get("scenes", [])
    out_name   = script.get("output_filename", f"{title.replace(' ','_')}.mp4")
    output_path = OUTPUT_DIR / out_name

    log(f"Starting pipeline: '{title}' | {len(scenes)} scenes | {resolution}", "🚀")

    clip_paths = []

    for scene in scenes:
        sid      = scene["id"]
        img_path = SCENES_DIR / f"scene_{sid:03d}.png"
        aud_path = AUDIO_DIR  / f"scene_{sid:03d}.mp3"
        clip_path = SCENES_DIR / f"scene_{sid:03d}_clip.mp4"

        # Step 1: Generate visual
        if scene.get("type") == "ai_image":
            generate_ai_image(scene, resolution, img_path)
        else:
            generate_static_bg(scene, resolution, img_path)

        # Step 2: Generate audio
        generate_audio(scene, aud_path)

        # Step 3: Build scene clip
        build_scene_clip(scene, img_path, aud_path, clip_path, resolution)

        clip_paths.append(clip_path)

        # Be kind to free APIs
        time.sleep(1)

    # Step 4: Concat everything
    concat_clips(clip_paths, output_path)

    size_mb = output_path.stat().st_size / (1024 * 1024)
    log(f"Done! '{output_path}' ({size_mb:.1f} MB)", "🎉")
    return str(output_path)


# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Video Pipeline")
    parser.add_argument("script", nargs="?", default="script.json",
                        help="Path to script JSON file (default: script.json)")
    args = parser.parse_args()

    if not Path(args.script).exists():
        print(f"❌ Script file not found: {args.script}")
        sys.exit(1)

    run_pipeline(args.script)
