#!/usr/bin/env python3
import json, os, sys, time, subprocess, requests
from pathlib import Path
from urllib.parse import quote

POLLINATIONS_URL = "https://image.pollinations.ai/prompt/{prompt}?width={w}&height={h}&seed={seed}&nologo=true&model=flux"
KOKORO_API_URL   = "https://api.kokorotts.com/v1/audio/speech"

WORK_DIR = Path("workspace")
SCENES_DIR = WORK_DIR / "scenes"
AUDIO_DIR = WORK_DIR / "audio"
OUTPUT_DIR = Path("output")

def setup_dirs():
    for d in [WORK_DIR, SCENES_DIR, AUDIO_DIR, OUTPUT_DIR]:
        d.mkdir(parents=True, exist_ok=True)

def log(msg, icon="▶"):
    print(f"\n{icon}  {msg}", flush=True)

def generate_ai_image(scene, resolution, out_path):
    w, h = resolution.split("x")
    prompt = scene.get("image_prompt", "cinematic manhwa scene")
    seed = scene.get("id", 1) * 42
    url = POLLINATIONS_URL.format(prompt=quote(prompt), w=w, h=h, seed=seed)
    
    log(f"Scene {scene['id']}: Generating image...", "🎨")
    for attempt in range(3):
        try:
            r = requests.get(url, timeout=60)
            r.raise_for_status()
            out_path.write_bytes(r.content)
            log(f"Image saved", "✅")
            return
        except Exception as e:
            time.sleep(5)
    
    # Fallback to black screen if API completely fails
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c=black:size={w}x{h}", "-frames:v", "1", str(out_path)], check=True)

def generate_audio(scene, out_path):
    text = scene.get("narration", "")
    voice = scene.get("voice", "af_heart")
    
    if not text:
        subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-t", "2", str(out_path)], check=True)
        return

    log(f"Scene {scene['id']}: Generating Kokoro TTS...", "🔊")
    payload = {
        "model": "kokoro", "input": text, "voice": voice,
        "speed": 0.95, "response_format": "mp3"
    }

    for attempt in range(3):
        try:
            r = requests.post(KOKORO_API_URL, json=payload, timeout=60)
            r.raise_for_status()
            out_path.write_bytes(r.content)
            log(f"Kokoro Audio saved", "✅")
            return
        except Exception as e:
            print(f"   Kokoro Attempt {attempt+1} failed: {e}")
            time.sleep(5)
    
    # STRICT RULE: ONLY KOKORO. No Edge-TTS Fallback. 
    # If it fails 3 times, generate 3 seconds of silence to prevent pipeline crash.
    log("Kokoro failed entirely. Generating silence.", "❌")
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-t", "3", str(out_path)], check=True)

def get_audio_duration(audio_path):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)],
        capture_output=True, text=True
    )
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 3.0

def build_scene_clip(scene, img_path, audio_path, out_path, resolution):
    w, h = resolution.split("x")
    duration = get_audio_duration(audio_path) + 0.5
    frames = int(duration * 25) # 25 fps
    
    log(f"Scene {scene['id']}: Building video clip with Ken Burns...", "🎬")

    # Ken Burns Zoom Effect (Fixed 234 error by removing stillimage)
    vf = (
        f"scale={w*2}:{h*2},zoompan=z='min(zoom+0.0005,1.1)':d={frames}:s={w}x{h},"
        f"fade=t=in:st=0:d=0.5,fade=t=out:st={duration-0.5}:d=0.5"
    )

    cmd = [
        "ffmpeg", "-y", "-loop", "1", "-i", str(img_path), "-i", str(audio_path),
        "-vf", vf, "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-t", str(duration),
        str(out_path)
    ]
    subprocess.run(cmd, check=True)

def concat_clips(clip_paths, output_path):
    log("Stitching all scenes together...", "🎞️")
    concat_list = WORK_DIR / "concat_list.txt"
    with open(concat_list, "w") as f:
        for clip in clip_paths:
            f.write(f"file '{clip.resolve()}'\n")

    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list),
        "-c:v", "libx264", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
        str(output_path)
    ]
    subprocess.run(cmd, check=True)
    log(f"Final video ready → {output_path}", "🎉")

def run_pipeline(script_path):
    setup_dirs()
    with open(script_path, "r") as f:
        script = json.load(f)

    resolution = script.get("resolution", "1280x720")
    scenes = script.get("scenes", [])
    output_path = OUTPUT_DIR / script.get("output_filename", "final_video.mp4")

    clip_paths = []
    for scene in scenes:
        sid = scene["id"]
        img_path = SCENES_DIR / f"scene_{sid:03d}.png"
        aud_path = AUDIO_DIR / f"scene_{sid:03d}.mp3"
        clip_path = SCENES_DIR / f"scene_{sid:03d}.mp4"

        generate_ai_image(scene, resolution, img_path)
        generate_audio(scene, aud_path)
        build_scene_clip(scene, img_path, aud_path, clip_path, resolution)
        clip_paths.append(clip_path)

    concat_clips(clip_paths, output_path)

if __name__ == "__main__":
    if not Path("script.json").exists():
        print("❌ script.json not found!")
        sys.exit(1)
    run_pipeline("script.json")
