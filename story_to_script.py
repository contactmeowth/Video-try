#!/usr/bin/env python3
import os
import sys
import json
import argparse
from google import genai
from google.genai import types

SYSTEM_PROMPT = """
You are a creative video script writer for a Manhwa Recap channel. Given a topic/chapter, generate a JSON script for an AI video pipeline. 

The JSON must follow this EXACT structure:
{
  "title": "Short title",
  "output_filename": "recap_video.mp4",
  "resolution": "1280x720",
  "default_voice": "af_heart",
  "scenes": [
    {
      "id": 1,
      "type": "ai_image",
      "image_prompt": "Cinematic Manhwa style art, detailed visual description",
      "narration": "Full narration text for this scene. Make it sound like a dramatic storyteller.",
      "voice": "af_heart",
      "mood": "epic",
      "transition": "fade"
    }
  ]
}

Rules:
- Generate ONLY valid JSON, no markdown formatting (no ```json).
- Narration should summarize the story dramatically (3-5 sentences per scene).
- ONLY use these specific Kokoro voices: 'af_heart' (female narrator), 'af_bella', 'am_adam' (male narrator), 'am_michael'. Do NOT use any other voices.
- Make the image prompts 'Manhwa/Webtoon style, cinematic lighting, highly detailed'.
"""

def generate_script(story_idea: str, num_scenes: int = 15) -> dict:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("❌ Set GEMINI_API_KEY environment variable")
        sys.exit(1)

    # Naya SDK initialization
    client = genai.Client(api_key=api_key)

    prompt = (
        f"Topic/Chapters to cover: {story_idea}\n\n"
        f"Generate exactly {num_scenes} scenes for a Manhwa recap video.\n"
    )

    print("🧠 Fetching script from Gemini...")
    
    # Naya syntax content generate karne ke liye
    response = client.models.generate_content(
        model='gemini-1.5-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.8,
        )
    )

    raw = response.text.strip()
    
    # JSON formatting fix
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
    if raw.endswith("```"):
        raw = raw.rsplit("```", 1)[0]

    return json.loads(raw.strip())

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("idea", help="Story idea")
    parser.add_argument("--scenes", type=int, default=15)
    args = parser.parse_args()
    
    script = generate_script(args.idea, args.scenes)
    
    with open("script.json", "w") as f:
        json.dump(script, f, indent=2, ensure_ascii=False)
