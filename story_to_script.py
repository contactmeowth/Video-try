#!/usr/bin/env python3
"""
story_to_script.py
──────────────────
Give a story idea → Gemini generates a full script.json for the video pipeline.

Usage:
    python story_to_script.py "A story about a robot who learns to paint"
    python story_to_script.py --scenes 8 "A tale of two kingdoms at war"

Needs:  pip install google-generativeai
        GEMINI_API_KEY env variable (or KEY1/KEY2 like your existing pipeline)
"""

import os
import sys
import json
import argparse
import google.generativeai as genai


SYSTEM_PROMPT = """
You are a creative video script writer. Given a story idea, generate a JSON script
for an AI video pipeline. The JSON must follow this EXACT structure:

{
  "title": "Short title",
  "output_filename": "snake_case_title.mp4",
  "resolution": "1280x720",
  "default_voice": "af_heart",
  "scenes": [
    {
      "id": 1,
      "type": "ai_image" | "static_bg",
      "image_prompt": "Detailed visual description for AI image generation (only for ai_image type)",
      "background_color": "#hexcolor (only for static_bg type)",
      "overlay_text": "Short display text (only for static_bg type)",
      "text_style": "title" | "quote" (only for static_bg type),
      "narration": "Full narration text for this scene. This becomes the audio.",
      "voice": "af_heart" | "af_bella" | "am_adam" | "am_michael" | "bf_emma" | "bm_george",
      "mood": "epic" | "mysterious" | "tense" | "wonder" | "dramatic" | "reflective",
      "transition": "fade" | "cut"
    }
  ]
}

Rules:
- First scene should be an establishing scene (ai_image, wide/establishing shot)
- Use static_bg for chapter titles, time jumps, or dramatic text moments
- Narration should be natural storytelling prose — 2-4 sentences per scene
- Image prompts should be cinematic, detailed, mention lighting and style
- Vary voices: narrator uses af_heart, male characters use am_adam, etc.
- Mix moods to create emotional flow
- End with a reflective or epic scene
- Return ONLY valid JSON, no markdown, no explanation
"""


def generate_script(story_idea: str, num_scenes: int = 6) -> dict:
    api_key = (
        os.environ.get("GEMINI_API_KEY") or
        os.environ.get("KEY1") or
        os.environ.get("KEY2")
    )
    if not api_key:
        print("❌ Set GEMINI_API_KEY (or KEY1/KEY2) environment variable")
        sys.exit(1)

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

    prompt = (
        f"Story idea: {story_idea}\n\n"
        f"Generate exactly {num_scenes} scenes.\n"
        f"Make it emotionally engaging and visually rich."
    )

    print(f"🤖 Generating {num_scenes}-scene script for: '{story_idea}'...")

    response = model.generate_content(
        prompt,
        generation_config={"temperature": 0.9},
        system_instruction=SYSTEM_PROMPT
    )

    raw = response.text.strip()
    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
    if raw.endswith("```"):
        raw = raw.rsplit("```", 1)[0]

    script = json.loads(raw.strip())
    return script


def main():
    parser = argparse.ArgumentParser(description="Generate video script from story idea")
    parser.add_argument("idea", help="Story idea or concept")
    parser.add_argument("--scenes", type=int, default=6, help="Number of scenes (default: 6)")
    parser.add_argument("--out", default="script.json", help="Output file (default: script.json)")
    args = parser.parse_args()

    script = generate_script(args.idea, args.scenes)

    with open(args.out, "w") as f:
        json.dump(script, f, indent=2, ensure_ascii=False)

    print(f"✅ Script written to {args.out}")
    print(f"   Title: {script.get('title')}")
    print(f"   Scenes: {len(script.get('scenes', []))}")
    print(f"\nNow run: python generate_video.py {args.out}")


if __name__ == "__main__":
    main()
